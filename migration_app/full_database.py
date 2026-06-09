"""
整库一键迁移编排：多 Schema、多对象类型按依赖顺序迁移。
"""
from __future__ import annotations

import traceback
from typing import Any

from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import MigrationTask
from .pg_identifiers import apply_identifier_case
from .target_provisioning import prepare_target_env
from .views import (
    get_oracle_connection,
    get_postgres_connection,
    _migrate_one_sequence,
    _migrate_single_table,
)

# Oracle 系统用户排除列表
_ORACLE_SYSTEM_USERS = (
    'SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'AUDSYS', 'CTXSYS',
    'DVSYS', 'GSMADMIN_INTERNAL', 'LBACSYS', 'MDSYS', 'OJVMSYS', 'OLAPSYS',
    'ORDDATA', 'ORDSYS', 'REMOTE_SCHEDULER_AGENT', 'WMSYS', 'XDB',
)

# 编排阶段顺序
PHASES = ['prepare', 'sequences', 'tables', 'views', 'materialized_views', 'triggers', 'routines', 'done']

_OBJECT_QUERIES = {
    'tables': ("SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = :schema ORDER BY TABLE_NAME", None),
    'sequences': ("SELECT SEQUENCE_NAME FROM ALL_SEQUENCES WHERE SEQUENCE_OWNER = :schema ORDER BY SEQUENCE_NAME", None),
    'views': ("SELECT VIEW_NAME FROM ALL_VIEWS WHERE OWNER = :schema ORDER BY VIEW_NAME", None),
    'materialized_views': ("SELECT MVIEW_NAME FROM ALL_MVIEWS WHERE OWNER = :schema ORDER BY MVIEW_NAME", None),
    'triggers': (
        "SELECT TRIGGER_NAME FROM ALL_TRIGGERS WHERE OWNER = :schema "
        "AND BASE_OBJECT_TYPE IN ('TABLE', 'VIEW') ORDER BY TRIGGER_NAME",
        None,
    ),
    'routines': (
        "SELECT DISTINCT OBJECT_NAME FROM ALL_OBJECTS WHERE OWNER = :schema "
        "AND OBJECT_TYPE IN ('PROCEDURE', 'FUNCTION') ORDER BY OBJECT_NAME",
        None,
    ),
}


def discover_oracle_instance(connection_id: int) -> dict[str, Any]:
    """发现 Oracle 实例下所有非系统 Schema 及对象统计。"""
    conn = get_oracle_connection(connection_id)
    cur = conn.cursor()
    placeholders = ', '.join([f"'{u}'" for u in _ORACLE_SYSTEM_USERS])
    cur.execute(f"""
        SELECT USERNAME FROM ALL_USERS
        WHERE USERNAME NOT IN ({placeholders})
        ORDER BY USERNAME
    """)
    schemas = [row[0] for row in cur.fetchall()]

    result_schemas = []
    for schema in schemas:
        stats = {}
        for key, (query, _) in _OBJECT_QUERIES.items():
            cur.execute(query, {'schema': schema})
            stats[key] = len(cur.fetchall())
        result_schemas.append({'name': schema, 'stats': stats})

    cur.close()
    conn.close()
    return {
        'connection_id': connection_id,
        'schema_count': len(result_schemas),
        'schemas': result_schemas,
    }


def _list_objects(oracle_cursor, schema: str, object_key: str) -> list[str]:
    """查询指定 Schema 下的对象名列表。"""
    query, _ = _OBJECT_QUERIES[object_key]
    oracle_cursor.execute(query, {'schema': schema})
    return [row[0] for row in oracle_cursor.fetchall()]


def _get_orchestration_config(task: MigrationTask) -> dict[str, Any]:
    """从 target_provisioning 读取整库编排配置。"""
    cfg = task.target_provisioning or {}
    return {
        'schema_mappings': cfg.get('schema_mappings') or [],
        'object_types': cfg.get('object_types') or {
            'sequences': True, 'tables': True, 'views': True,
            'materialized_views': True, 'triggers': True, 'routines': True,
        },
        'auto_prepare': bool(cfg.get('auto_prepare')),
        'prepare_config': cfg.get('prepare_config'),
    }


def _default_schema_mappings(oracle_schemas: list[str], id_case: str) -> list[dict[str, str]]:
    """默认 Oracle Schema → PG Schema 映射（小写）。"""
    return [
        {
            'source_schema': s,
            'target_schema': apply_identifier_case(s, id_case),
        }
        for s in oracle_schemas
    ]


def migrate_full_database(task_id: int, postgres_database: str | None = None) -> None:
    """整库一键迁移主入口。"""
    from .resume import normalize_view_progress
    from .trigger_export import export_one_trigger
    from . import views

    task = get_object_or_404(MigrationTask, pk=task_id)
    orch = _get_orchestration_config(task)
    pgdb = postgres_database or task.postgres_database or (
        task.postgres_connection.database if task.postgres_connection else None
    )

    vp = normalize_view_progress(task.view_progress) or {}
    resume_mode = bool(vp.pop('resume', False))
    completed_objects = set(vp.get('completed_objects') or [])
    current_phase = vp.get('phase') or PHASES[0]
    phase_index = int(vp.get('phase_index') or 0)

    task.status = 'running'
    if not task.started_at:
        task.started_at = timezone.now()
    log = [] if not resume_mode else [ln for ln in (task.log or '').split('\n') if ln]
    failed_objects: list[dict[str, str]] = list(vp.get('failed_objects') or [])

    # 确定 Schema 映射
    schema_mappings = orch['schema_mappings']
    if not schema_mappings:
        discovery = discover_oracle_instance(task.oracle_connection_id)
        id_case = getattr(task, 'identifier_case', 'lower') or 'lower'
        schema_mappings = _default_schema_mappings(
            [s['name'] for s in discovery['schemas']], id_case,
        )

    object_types = orch['object_types']
    id_case = getattr(task, 'identifier_case', 'lower') or 'lower'

    def _phase_enabled(phase: str) -> bool:
        key_map = {
            'sequences': 'sequences',
            'tables': 'tables',
            'views': 'views',
            'materialized_views': 'materialized_views',
            'triggers': 'triggers',
            'routines': 'routines',
        }
        return object_types.get(key_map.get(phase, phase), True)

    oracle_conn = oracle_cur = pg_conn = pg_cur = None
    try:
        # 阶段 0：准备目标环境（续传时若已过 prepare 则跳过）
        if not resume_mode and orch['auto_prepare'] and orch.get('prepare_config'):
            prep_cfg = dict(orch['prepare_config'])
            prep_cfg['connection_id'] = task.postgres_connection_id
            log.append('【整库迁移】开始准备目标环境...')
            prep_result = prepare_target_env(prep_cfg)
            for step in prep_result.get('steps', []):
                log.append(f"  [{step.get('step')}] {step.get('status')}: {step.get('message')}")
            resolved = prep_result.get('resolved') or {}
            if resolved.get('database'):
                pgdb = resolved['database']
                task.postgres_database = pgdb
            if prep_result.get('status') != 'success':
                raise RuntimeError(prep_result.get('message', '目标环境准备失败'))
            current_phase = 'sequences'
            phase_index = 1

        oracle_conn = get_oracle_connection(task.oracle_connection_id)
        oracle_cur = oracle_conn.cursor()
        pg_conn = get_postgres_connection(task.postgres_connection_id, pgdb)
        pg_cur = pg_conn.cursor()
        pg_cur.execute('SELECT current_database()')
        log.append(f'已连接目标库: {pg_cur.fetchone()[0]}')

        total_schemas = len(schema_mappings)

        for phase in PHASES[1:-1]:
            if phase == 'prepare':
                continue
            if not _phase_enabled(phase):
                continue
            if resume_mode and PHASES.index(phase) < phase_index:
                continue

            current_phase = phase
            phase_index = PHASES.index(phase)
            log.append(f'【整库迁移】进入阶段: {phase}')

            for si, mapping in enumerate(schema_mappings):
                src_schema = mapping['source_schema']
                tgt_schema = mapping.get('target_schema') or apply_identifier_case(src_schema, id_case)
                log.append(f'  Schema [{si + 1}/{total_schemas}] {src_schema} → {tgt_schema}')

                if phase == 'sequences':
                    for seq_name in _list_objects(oracle_cur, src_schema, 'sequences'):
                        obj_id = f'{src_schema}.{seq_name}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            seq_log: list[str] = []
                            _migrate_one_sequence(
                                oracle_cur, pg_conn, pg_cur,
                                src_schema, tgt_schema, seq_name,
                                task.conflict_strategy, seq_log, id_case=id_case,
                            )
                            completed_objects.add(obj_id)
                            log.extend([f'    {ln}' for ln in seq_log])
                        except Exception as e:
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            log.append(f'    序列 {seq_name} 失败: {e}')

                elif phase == 'tables':
                    for tbl in _list_objects(oracle_cur, src_schema, 'tables'):
                        obj_id = f'{src_schema}.{tbl}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            tbl_log: list[str] = []
                            _migrate_single_table(
                                oracle_cur, pg_conn, pg_cur,
                                src_schema, tgt_schema, tbl,
                                task.conflict_strategy, tbl_log, task=task,
                            )
                            completed_objects.add(obj_id)
                            log.extend([f'    {ln}' for ln in tbl_log[-3:]])
                        except Exception as e:
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            log.append(f'    表 {tbl} 失败: {e}')

                elif phase == 'views':
                    for vname in _list_objects(oracle_cur, src_schema, 'views'):
                        obj_id = f'{src_schema}.{vname}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            task.source_schema = src_schema
                            task.target_schema = tgt_schema
                            task.source_object = vname
                            views.migrate_view(task.id, pgdb)
                            task.refresh_from_db()
                            completed_objects.add(obj_id)
                            log.append(f'    视图 {vname} 完成')
                        except Exception as e:
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            log.append(f'    视图 {vname} 失败: {e}')
                        task.status = 'running'

                elif phase == 'materialized_views':
                    for mv in _list_objects(oracle_cur, src_schema, 'materialized_views'):
                        obj_id = f'{src_schema}.{mv}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            task.source_schema = src_schema
                            task.target_schema = tgt_schema
                            task.source_object = mv
                            views.migrate_materialized_view(task.id, pgdb)
                            task.refresh_from_db()
                            completed_objects.add(obj_id)
                            log.append(f'    物化视图 {mv} 完成')
                        except Exception as e:
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            log.append(f'    物化视图 {mv} 失败: {e}')
                        task.status = 'running'

                elif phase == 'triggers':
                    for tname in _list_objects(oracle_cur, src_schema, 'triggers'):
                        obj_id = f'{src_schema}.{tname}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            _, _, export_log = export_one_trigger(oracle_cur, src_schema, tname)
                            completed_objects.add(obj_id)
                            log.append(f'    触发器 {tname} 已导出')
                        except Exception as e:
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            log.append(f'    触发器 {tname} 失败: {e}')

                elif phase == 'routines':
                    for rname in _list_objects(oracle_cur, src_schema, 'routines'):
                        obj_id = f'{src_schema}.{rname}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            task.source_schema = src_schema
                            task.target_schema = tgt_schema
                            task.source_object = rname
                            views.migrate_routine(task.id, pgdb)
                            task.refresh_from_db()
                            completed_objects.add(obj_id)
                            log.append(f'    例程 {rname} 完成')
                        except Exception as e:
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            log.append(f'    例程 {rname} 失败: {e}')
                        task.status = 'running'

                # 更新进度
                progress = min(99.0, (
                    (phase_index / max(len(PHASES) - 1, 1)) * 80
                    + (si / max(total_schemas, 1)) * (80 / max(len(PHASES) - 1, 1))
                ))
                task.progress = progress
                task.view_progress = {
                    'orchestration': 'full_database',
                    'phase': current_phase,
                    'phase_index': phase_index,
                    'phases': PHASES,
                    'schema_index': si,
                    'schemas': [m['source_schema'] for m in schema_mappings],
                    'completed_objects': sorted(completed_objects),
                    'failed_objects': failed_objects,
                }
                task.log = '\n'.join(log)
                task.save(update_fields=['progress', 'view_progress', 'log', 'status', 'postgres_database'])

        current_phase = 'done'
        if failed_objects:
            task.status = 'partial'
            log.append(f'【整库迁移】完成，部分对象失败 ({len(failed_objects)} 个)')
        else:
            task.status = 'completed'
            log.append('【整库迁移】全部完成')
        task.progress = 100.0
        task.view_progress = {
            'orchestration': 'full_database',
            'phase': 'done',
            'phase_index': len(PHASES) - 1,
            'phases': PHASES,
            'completed_objects': sorted(completed_objects),
            'failed_objects': failed_objects,
        }
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

    except Exception as e:
        from .migration_errors import format_db_error, rollback_quietly, safe_close_db_resources
        rollback_quietly(pg_conn)
        task.status = 'failed'
        log.append(format_db_error(e))
        log.append(traceback.format_exc())
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
    finally:
        from .migration_errors import safe_close_db_resources
        safe_close_db_resources(oracle_cur, oracle_conn, pg_cur, pg_conn)
