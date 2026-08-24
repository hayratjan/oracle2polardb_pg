"""
整库一键迁移编排：多 Schema、多对象类型按依赖顺序迁移。

日志采用统一前缀格式 `[LEVEL] message`，便于前端解析着色：
  [STEP] 阶段步骤    [INFO] 一般信息    [OK] 成功    [WARN] 警告
  [ERROR] 错误      [DATA] 数据导入    [SQL] DDL    [META] 元数据
"""
from __future__ import annotations

import logging
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import MigrationTask
from .pg_identifiers import apply_identifier_case
from .target_provisioning import prepare_target_env
from .task_logging import (
    build_log_line,
    make_error_log,
    make_info_log,
    make_ok_log,
    make_step_log,
    make_warn_log,
)
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

logger = logging.getLogger(__name__)

# 编排阶段顺序（外键在表数据导入完成后回放）
PHASES = [
    'prepare', 'sequences', 'tables', 'foreign_keys',
    'views', 'materialized_views', 'triggers', 'routines', 'done',
]

# 阶段中文标签（用于日志与前端展示）
PHASE_LABELS = {
    'prepare': '准备目标环境',
    'sequences': '序列',
    'tables': '物理表',
    'foreign_keys': '外键约束回放',
    'views': '视图',
    'materialized_views': '物化视图',
    'triggers': '触发器',
    'routines': '例程',
    'done': '完成',
}

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


def discover_oracle_instance(connection_id: int, *, timeout_seconds: int = 90) -> dict[str, Any]:
    """发现 Oracle 实例下所有非系统 Schema 及对象统计。

    优化点：
    1. 用 GROUP BY OWNER 批量聚合，替代逐 Schema 循环查询。
       原方案 N 个 Schema 需 10N 次往返，现仅需 7 次查询。
    2. 用 ThreadPoolExecutor 包裹整体逻辑，超时自动中断。
    3. 各步骤输出进度日志，便于诊断卡在哪一步。
    """
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_discover_oracle_instance_impl, connection_id)
            return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        logger.error("discover_oracle_instance 超时 (%ss), connection_id=%s", timeout_seconds, connection_id)
        raise TimeoutError(f"Oracle Discovery 超时（{timeout_seconds}秒），请检查 Oracle 连接配置或网络")


def _discover_oracle_instance_impl(connection_id: int) -> dict[str, Any]:
    """discover_oracle_instance 的实际实现（在子线程中执行）。"""
    logger.info("[STEP] 开始 Oracle Discovery, connection_id=%s", connection_id)
    conn = get_oracle_connection(connection_id, call_timeout_ms=20000)
    try:
        cur = conn.cursor()
        placeholders = ', '.join([f"'{u}'" for u in _ORACLE_SYSTEM_USERS])
        logger.info("[INFO] 查询非系统 Schema 列表...")
        cur.execute(f"""
            SELECT USERNAME FROM ALL_USERS
            WHERE USERNAME NOT IN ({placeholders})
            ORDER BY USERNAME
        """)
        schemas = [row[0] for row in cur.fetchall()]
        logger.info("[OK] 发现 %d 个 Schema", len(schemas))

        # 批量聚合：每类对象一次 GROUP BY 查询，替代逐 Schema 循环
        stats_map: dict[str, dict[str, int]] = {s: {} for s in schemas}
        _GROUP_QUERIES = {
            'tables': f"SELECT OWNER, COUNT(*) FROM ALL_TABLES WHERE OWNER NOT IN ({placeholders}) GROUP BY OWNER",
            'sequences': f"SELECT SEQUENCE_OWNER, COUNT(*) FROM ALL_SEQUENCES WHERE SEQUENCE_OWNER NOT IN ({placeholders}) GROUP BY SEQUENCE_OWNER",
            'views': f"SELECT OWNER, COUNT(*) FROM ALL_VIEWS WHERE OWNER NOT IN ({placeholders}) GROUP BY OWNER",
            'materialized_views': f"SELECT OWNER, COUNT(*) FROM ALL_MVIEWS WHERE OWNER NOT IN ({placeholders}) GROUP BY OWNER",
            'triggers': f"SELECT OWNER, COUNT(*) FROM ALL_TRIGGERS WHERE OWNER NOT IN ({placeholders}) AND BASE_OBJECT_TYPE IN ('TABLE', 'VIEW') GROUP BY OWNER",
            'routines': (
                f"SELECT OWNER, COUNT(*) FROM ALL_OBJECTS WHERE OWNER NOT IN ({placeholders}) "
                "AND OBJECT_TYPE IN ('PROCEDURE', 'FUNCTION') GROUP BY OWNER"
            ),
        }
        for key, sql in _GROUP_QUERIES.items():
            logger.info("[INFO] 查询 %s 统计...", key)
            cur.execute(sql)
            for owner, cnt in cur.fetchall():
                if owner in stats_map:
                    stats_map[owner][key] = int(cnt)

        result_schemas = [
            {'name': s, 'stats': stats_map[s]}
            for s in schemas
        ]

        # 未自动迁移的对象类型统计（Discovery 告警）
        unsupported: dict[str, int] = {}
        _UNSUPPORTED_GROUP_QUERIES = {
            'synonyms': f"SELECT COUNT(*) FROM ALL_SYNONYMS WHERE OWNER NOT IN ({placeholders})",
            'packages': (
                f"SELECT COUNT(*) FROM ALL_OBJECTS WHERE OWNER NOT IN ({placeholders}) "
                "AND OBJECT_TYPE IN ('PACKAGE', 'PACKAGE BODY')"
            ),
            'db_links': f"SELECT COUNT(*) FROM ALL_DB_LINKS WHERE OWNER NOT IN ({placeholders})",
            'partitioned_tables': f"SELECT COUNT(*) FROM ALL_PART_TABLES WHERE OWNER NOT IN ({placeholders})",
        }
        for key, sql in _UNSUPPORTED_GROUP_QUERIES.items():
            cur.execute(sql)
            unsupported[key] = int(cur.fetchone()[0])
        logger.info("[OK] 对象统计完成: %d schema, unsupported=%s", len(schemas), unsupported)

        cur.close()
    finally:
        try:
            conn.close()
        except Exception:
            pass
    warnings = []
    if unsupported.get('synonyms', 0):
        warnings.append(f"发现 {unsupported['synonyms']} 个同义词，当前不支持自动迁移")
    if unsupported.get('packages', 0):
        warnings.append(f"发现 {unsupported['packages']} 个包对象，需人工迁移")
    if unsupported.get('db_links', 0):
        warnings.append(f"发现 {unsupported['db_links']} 个 DB Link，需人工处理")
    if unsupported.get('partitioned_tables', 0):
        warnings.append(f"发现 {unsupported['partitioned_tables']} 个分区表，将按普通表迁移（不含分区 DDL）")

    return {
        'connection_id': connection_id,
        'schema_count': len(result_schemas),
        'schemas': result_schemas,
        'unsupported_stats': unsupported,
        'warnings': warnings,
    }


def fetch_trigger_base_object_type(oracle_cursor, schema: str, trigger_name: str) -> str:
    """读取触发器绑定对象的类型（TABLE/VIEW），供触发器模板做 INSTEAD OF 校验。

    列名/表名为固定字面量，条件值经 :o/:n 绑定变量传入。
    查询失败时保守返回 TABLE。
    """
    base_sql = (
        'SELECT BASE_OBJECT_TYPE FROM ALL_TRIGGERS '
        'WHERE OWNER = :o AND TRIGGER_NAME = :n'
    )
    try:
        oracle_cursor.execute(base_sql, {'o': schema.upper(), 'n': trigger_name.upper()})
        row = oracle_cursor.fetchone()
        return str(row[0]).upper() if row and row[0] else 'TABLE'
    except Exception as e:
        logger.warning('读取触发器基对象类型失败: %s', e)
        return 'TABLE'


def _list_objects(oracle_cursor, schema: str, object_key: str) -> list[str]:
    """查询指定 Schema 下的对象名列表。"""
    query, _ = _OBJECT_QUERIES[object_key]
    oracle_cursor.execute(query, {'schema': schema})
    return [row[0] for row in oracle_cursor.fetchall()]


def _topological_sort_by_dependencies(
    oracle_cursor,
    schema: str,
    names: list[str],
    object_types: tuple[str, ...],
    referenced_types: tuple[str, ...],
) -> list[str]:
    """按 ALL_DEPENDENCIES 依赖关系拓扑排序（被依赖者在前）。

    视图 B 依赖视图 A 时 A 排在前，避免整库迁移按字母序处理导致
    CREATE VIEW 报「关系不存在」。环或无法解析的边按字母序追加
    （与表 FK 排序 _topological_sort_tables_by_fk 同样的兜底策略）。
    依赖过滤（REFERENCED_TYPE / 引用对象是否在集合内）在 Python 侧完成，
    SQL 仅使用绑定变量。
    """
    if not names or len(names) == 1:
        return names
    name_set = {n.upper() for n in names}
    orig_by_upper = {n.upper(): n for n in names}

    edges: dict[str, list[str]] = {}
    for obj_type in object_types:
        try:
            oracle_cursor.execute(
                """
                SELECT NAME, REFERENCED_NAME, REFERENCED_TYPE
                FROM ALL_DEPENDENCIES
                WHERE OWNER = :o AND TYPE = :t AND REFERENCED_OWNER = :o
                """,
                {'o': schema.upper(), 't': obj_type},
            )
            for name, ref_name, ref_type in oracle_cursor.fetchall():
                if not name or not ref_name or not ref_type:
                    continue
                nu, ru = name.upper(), ref_name.upper()
                if nu in name_set and ru in name_set and nu != ru:
                    if str(ref_type).upper() in {t.upper() for t in referenced_types}:
                        edges.setdefault(nu, []).append(ru)
        except Exception as e:
            logger.warning('读取 ALL_DEPENDENCIES 失败(退化为字母序): %s', e)
            return names

    from collections import defaultdict
    from heapq import heappush, heappop

    indegree = defaultdict(int)
    children = defaultdict(list)
    for nu, deps in edges.items():
        for ru in deps:
            children[ru].append(nu)
            indegree[nu] += 1

    heap = [n for n in name_set if indegree[n] == 0]
    import heapq
    heapq.heapify(heap)
    ordered: list[str] = []
    while heap:
        n = heappop(heap)
        ordered.append(n)
        for ch in sorted(children[n]):
            indegree[ch] -= 1
            if indegree[ch] == 0:
                heappush(heap, ch)

    remaining = sorted(name_set - set(ordered))
    ordered.extend(remaining)
    return [orig_by_upper[u] for u in ordered]


def _classify_seq_error(err_msg: str) -> str:
    """对序列迁移失败原因分类，便于同类错误合并显示，避免日志刷屏。

    例如「超出 bigint 范围」即使数值不同也算同一类，
    「模式 xxx 不存在」即使 schema 名不同也算同一类。
    """
    msg = err_msg or ''
    if '超出类型 bigint 的范围' in msg or 'bigint' in msg.lower():
        return 'bigint 范围溢出'
    if '模式' in msg and '不存在' in msg:
        return '目标 schema 不存在'
    if '当前事务被终止' in msg:
        return '事务中断连锁'
    if '已存在' in msg:
        return '对象已存在'
    if '找不到序列' in msg:
        return '源序列不存在'
    return f'其他: {msg[:40]}'


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
    # v2.4.2: 仅导出、未在目标库创建的对象（触发器模板/未执行的例程），
    # 终态需降级为 partial 并列出清单，避免用户误以为已可用
    manual_objects: list[str] = list(vp.get('manual_objects') or [])

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
            make_step_log(log, '阶段 0 · 准备目标环境')
            prep_result = prepare_target_env(prep_cfg)
            for step in prep_result.get('steps', []):
                status_str = step.get('status') or ''
                line_msg = f"  [{step.get('step')}] {status_str}: {step.get('message')}"
                if status_str == 'success':
                    make_ok_log(log, line_msg)
                elif status_str == 'skipped':
                    make_info_log(log, line_msg)
                else:
                    make_warn_log(log, line_msg)
            resolved = prep_result.get('resolved') or {}
            if resolved.get('database'):
                pgdb = resolved['database']
                task.postgres_database = pgdb
                make_ok_log(log, f'已解析目标数据库名: {pgdb}')
            if prep_result.get('status') != 'success':
                make_error_log(log, f"目标环境准备失败: {prep_result.get('message', '')}")
                raise RuntimeError(prep_result.get('message', '目标环境准备失败'))
            current_phase = 'sequences'
            phase_index = 1

        oracle_conn = get_oracle_connection(task.oracle_connection_id)
        oracle_cur = oracle_conn.cursor()
        pg_conn = get_postgres_connection(task.postgres_connection_id, pgdb)
        pg_cur = pg_conn.cursor()
        pg_cur.execute('SELECT current_database()')
        make_ok_log(log, f'已连接目标 PostgreSQL 库: {pg_cur.fetchone()[0]}')
        make_ok_log(log, '已连接 Oracle 源端')

        total_schemas = len(schema_mappings)
        make_info_log(log, f'待迁移 Schema 数: {total_schemas} | 启用的对象类型: ' +
                      ', '.join(k for k, v in object_types.items() if v))

        for phase in PHASES[1:-1]:
            if phase == 'prepare':
                continue
            if not _phase_enabled(phase):
                make_info_log(log, f'阶段「{PHASE_LABELS.get(phase, phase)}」未启用，跳过')
                continue
            if resume_mode and PHASES.index(phase) < phase_index:
                continue

            current_phase = phase
            phase_index = PHASES.index(phase)
            phase_label = PHASE_LABELS.get(phase, phase)
            make_step_log(log, f'阶段 {phase_index} · {phase_label}')

            for si, mapping in enumerate(schema_mappings):
                src_schema = mapping['source_schema']
                tgt_schema = mapping.get('target_schema') or apply_identifier_case(src_schema, id_case)
                make_info_log(log, f'Schema [{si + 1}/{total_schemas}] {src_schema} → {tgt_schema}')

                if phase == 'sequences':
                    seq_list = _list_objects(oracle_cur, src_schema, 'sequences')
                    make_info_log(log, f'  序列数: {len(seq_list)}')
                    seq_ok, seq_fail = 0, 0
                    # 记录第一个失败的原因（根因），后续相同原因只计数
                    seq_first_error: str | None = None
                    seq_error_count = 0
                    # 错误分类计数器：按错误类型分组，避免同类错误刷屏
                    # （如「超出 bigint 范围」即使数值不同也算同类）
                    seq_error_groups: dict[str, list] = {}
                    for seq_name in seq_list:
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
                            seq_ok += 1
                            log.extend([f'    {ln}' for ln in seq_log])
                        except Exception as e:
                            seq_fail += 1
                            err_msg = str(e)
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': err_msg})
                            # 按错误类型分类，避免同类错误重复打印
                            err_key = _classify_seq_error(err_msg)
                            if err_key not in seq_error_groups:
                                seq_error_groups[err_key] = {'first': seq_name, 'msg': err_msg, 'count': 0}
                            else:
                                seq_error_groups[err_key]['count'] += 1
                    # 输出分组后的错误：每类只打印一条根因 + 计数
                    for err_key, info in seq_error_groups.items():
                        make_error_log(log, f'    序列 {info["first"]} 失败（{err_key}）: {info["msg"]}')
                        if info['count']:
                            make_warn_log(log, f'      另有 {info["count"]} 个序列因同类错误失败')
                    if seq_fail:
                        make_warn_log(log, f'  Schema {src_schema} 序列完成 ({seq_ok} 成功 / {seq_fail} 失败)')
                    elif seq_ok:
                        make_ok_log(log, f'  Schema {src_schema} 序列完成 ({seq_ok} 成功 / {seq_fail} 失败)')

                elif phase == 'tables':
                    tbl_list = _list_objects(oracle_cur, src_schema, 'tables')
                    make_info_log(log, f'  物理表数: {len(tbl_list)}')
                    tbl_ok, tbl_fail = 0, 0
                    for tbl in tbl_list:
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
                            tbl_ok += 1
                            log.extend([f'    {ln}' for ln in tbl_log[-3:]])
                        except Exception as e:
                            tbl_fail += 1
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            make_error_log(log, f'    表 {tbl} 失败: {e}')
                    if tbl_ok or tbl_fail:
                        make_ok_log(log, f'  Schema {src_schema} 物理表完成 ({tbl_ok} 成功 / {tbl_fail} 失败)')

                elif phase == 'foreign_keys':
                    from .schema_converter import apply_foreign_keys_for_schema
                    fk_log: list[str] = []
                    fk_phase_id = f'__fk__{src_schema}'
                    if fk_phase_id in completed_objects:
                        make_info_log(log, f'  Schema {src_schema} 外键已回放，跳过')
                        continue
                    try:
                        n = apply_foreign_keys_for_schema(
                            oracle_cur, pg_cur, pg_conn,
                            src_schema, tgt_schema, fk_log,
                            id_case=id_case, schema_mappings=schema_mappings,
                        )
                        completed_objects.add(fk_phase_id)
                        log.extend([f'    {ln}' for ln in fk_log])
                        make_ok_log(log, f'  Schema {src_schema} 外键回放 {n} 个')
                    except Exception as e:
                        failed_objects.append({'object': fk_phase_id, 'phase': phase, 'error': str(e)})
                        make_error_log(log, f'  Schema {src_schema} 外键回放失败: {e}')

                elif phase == 'views':
                    view_list = _list_objects(oracle_cur, src_schema, 'views')
                    # v2.4.4: 按 ALL_DEPENDENCIES 拓扑排序——视图 B 依赖视图 A 时 A 先建，
                    # 消除字母序处理导致的「关系不存在」失败
                    view_list = _topological_sort_by_dependencies(
                        oracle_cur, src_schema, view_list,
                        object_types=('VIEW',),
                        referenced_types=('VIEW', 'TABLE', 'MATERIALIZED VIEW'),
                    )
                    make_info_log(log, f'  视图数: {len(view_list)}')
                    vw_ok, vw_fail = 0, 0
                    vw_failed_names: list[str] = []

                    def _migrate_one_view(vname: str) -> bool:
                        """迁移单个视图（必须在调用前持久化 task 源对象字段）。"""
                        task.source_schema = src_schema
                        task.target_schema = tgt_schema
                        task.source_object = vname
                        # 关键：必须先 save 再调用 migrate_view，因为后者会重新
                        # 从数据库读取 task，内存中修改的 source_schema/source_object
                        # 若不持久化就会丢失，导致「未指定要迁移的视图」错误
                        task.save(update_fields=['source_schema', 'target_schema', 'source_object'])
                        views.migrate_view(task.id, pgdb)
                        task.refresh_from_db()
                        task.status = 'running'
                        return True

                    for vname in view_list:
                        obj_id = f'{src_schema}.{vname}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            _migrate_one_view(vname)
                            completed_objects.add(obj_id)
                            vw_ok += 1
                            make_ok_log(log, f'    视图 {vname} 完成')
                        except Exception as e:
                            vw_fail += 1
                            vw_failed_names.append(vname)
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            make_error_log(log, f'    视图 {vname} 失败: {e}')

                    # v2.4.4: 第二轮重试——失败多因依赖视图尚未建成，
                    # 一轮结束后依赖可能已就绪，重试一轮可救回大部分
                    if vw_failed_names:
                        make_info_log(log, f'  重试 {len(vw_failed_names)} 个失败视图（依赖就绪检查）…')
                        for vname in list(vw_failed_names):
                            obj_id = f'{src_schema}.{vname}'
                            try:
                                _migrate_one_view(vname)
                                completed_objects.add(obj_id)
                                vw_ok += 1
                                vw_fail -= 1
                                vw_failed_names.remove(vname)
                                failed_objects[:] = [
                                    f for f in failed_objects if f.get('object') != obj_id
                                ]
                                make_ok_log(log, f'    视图 {vname} 重试成功')
                            except Exception as e:
                                make_warn_log(log, f'    视图 {vname} 重试仍失败: {e}')
                    if vw_ok or vw_fail:
                        make_ok_log(log, f'  Schema {src_schema} 视图完成 ({vw_ok} 成功 / {vw_fail} 失败)')

                elif phase == 'materialized_views':
                    mv_list = _list_objects(oracle_cur, src_schema, 'materialized_views')
                    # v2.4.4: MV 依赖表/视图/其他 MV，同样拓扑排序
                    mv_list = _topological_sort_by_dependencies(
                        oracle_cur, src_schema, mv_list,
                        object_types=('MATERIALIZED VIEW',),
                        referenced_types=('VIEW', 'TABLE', 'MATERIALIZED VIEW'),
                    )
                    make_info_log(log, f'  物化视图数: {len(mv_list)}')
                    mv_ok, mv_fail = 0, 0
                    for mv in mv_list:
                        obj_id = f'{src_schema}.{mv}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            # 必须先 save，否则 migrate_materialized_view 重新读取 task 时
                            # source_object 为空会报错
                            task.source_schema = src_schema
                            task.target_schema = tgt_schema
                            task.source_object = mv
                            task.save(update_fields=['source_schema', 'target_schema', 'source_object'])
                            views.migrate_materialized_view(task.id, pgdb)
                            task.refresh_from_db()
                            completed_objects.add(obj_id)
                            mv_ok += 1
                            make_ok_log(log, f'    物化视图 {mv} 完成')
                        except Exception as e:
                            mv_fail += 1
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            make_error_log(log, f'    物化视图 {mv} 失败: {e}')
                        task.status = 'running'
                    if mv_ok or mv_fail:
                        make_ok_log(log, f'  Schema {src_schema} 物化视图完成 ({mv_ok} 成功 / {mv_fail} 失败)')

                elif phase == 'triggers':
                    trg_list = _list_objects(oracle_cur, src_schema, 'triggers')
                    make_info_log(log, f'  触发器数: {len(trg_list)}')
                    trg_ok, trg_fail = 0, 0
                    for tname in trg_list:
                        obj_id = f'{src_schema}.{tname}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            _, _, export_log = export_one_trigger(oracle_cur, src_schema, tname)
                            completed_objects.add(obj_id)
                            trg_ok += 1
                            # 触发器仅导出 PL/pgSQL 模板，未在目标库创建
                            manual_objects.append(obj_id)
                            log.append(export_log)
                        except Exception as e:
                            trg_fail += 1
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            make_error_log(log, f'    触发器 {tname} 失败: {e}')
                    if trg_ok or trg_fail:
                        make_ok_log(log, f'  Schema {src_schema} 触发器导出完成 ({trg_ok} 成功 / {trg_fail} 失败)')

                elif phase == 'routines':
                    rtn_list = _list_objects(oracle_cur, src_schema, 'routines')
                    # v2.4.4: 函数间调用依赖排序——被调用者先创建，
                    # 避免 PG 端「函数不存在」导致创建失败
                    rtn_list = _topological_sort_by_dependencies(
                        oracle_cur, src_schema, rtn_list,
                        object_types=('FUNCTION', 'PROCEDURE'),
                        referenced_types=('FUNCTION', 'PROCEDURE', 'PACKAGE', 'TABLE', 'VIEW'),
                    )
                    make_info_log(log, f'  例程数: {len(rtn_list)}')
                    rtn_ok, rtn_fail = 0, 0
                    for rname in rtn_list:
                        obj_id = f'{src_schema}.{rname}'
                        if obj_id in completed_objects:
                            continue
                        try:
                            # 必须先 save，否则 migrate_routine 重新读取 task 时
                            # source_object 为空会报错
                            task.source_schema = src_schema
                            task.target_schema = tgt_schema
                            task.source_object = rname
                            task.save(update_fields=['source_schema', 'target_schema', 'source_object'])
                            views.migrate_routine(task.id, pgdb)
                            task.refresh_from_db()
                            # 检测例程是否真正在目标库创建（安全校验不过时仅导出源码）
                            pg_cur.execute(
                                """
                                SELECT 1 FROM pg_proc p
                                JOIN pg_namespace n ON n.oid = p.pronamespace
                                WHERE n.nspname = %s AND p.proname = %s
                                """,
                                (tgt_schema, apply_identifier_case(rname, id_case)),
                            )
                            if pg_cur.fetchone() is None:
                                manual_objects.append(obj_id)
                                make_warn_log(log, f'    例程 {rname} 含不兼容语法，仅导出源码未自动创建')
                            completed_objects.add(obj_id)
                            rtn_ok += 1
                            make_ok_log(log, f'    例程 {rname} 完成')
                        except Exception as e:
                            rtn_fail += 1
                            failed_objects.append({'object': obj_id, 'phase': phase, 'error': str(e)})
                            make_error_log(log, f'    例程 {rname} 失败: {e}')
                        task.status = 'running'
                    if rtn_ok or rtn_fail:
                        make_ok_log(log, f'  Schema {src_schema} 例程完成 ({rtn_ok} 成功 / {rtn_fail} 失败)')

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
                    'manual_objects': sorted(set(manual_objects)),
                }
                task.log = '\n'.join(log)
                task.save(update_fields=['progress', 'view_progress', 'log', 'status', 'postgres_database'])

        current_phase = 'done'
        make_step_log(log, '整库迁移结束')
        if failed_objects:
            task.status = 'partial'
            make_warn_log(log, f'部分对象失败 ({len(failed_objects)} 个)，详见 failed_objects')
        elif manual_objects:
            task.status = 'partial'
            make_warn_log(
                log,
                f'迁移完成，但 {len(manual_objects)} 个对象仅导出未自动创建'
                f'（触发器模板/不兼容例程），需人工改写后执行，详见 manual_objects',
            )
        else:
            task.status = 'completed'
            make_ok_log(log, f'整库迁移全部完成，共迁移 {len(completed_objects)} 个对象')
        task.progress = 100.0
        task.view_progress = {
            'orchestration': 'full_database',
            'phase': 'done',
            'phase_index': len(PHASES) - 1,
            'phases': PHASES,
            'completed_objects': sorted(completed_objects),
            'failed_objects': failed_objects,
            'manual_objects': sorted(set(manual_objects)),
        }
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

    except Exception as e:
        from .migration_errors import format_db_error, rollback_quietly, safe_close_db_resources
        rollback_quietly(pg_conn)
        task.status = 'failed'
        make_error_log(log, f'整库迁移异常: {format_db_error(e)}')
        make_error_log(log, traceback.format_exc())
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
    finally:
        from .migration_errors import safe_close_db_resources
        safe_close_db_resources(oracle_cur, oracle_conn, pg_cur, pg_conn)
