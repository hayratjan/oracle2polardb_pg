"""
视图数据物化到 PolarDB-PG 表：migrate_view 与 migrate_view_to_table 共用实现。
支持分批读取、进度跟踪、取消、部分成功、行数校验。

日志采用统一前缀格式 `[LEVEL] message`，便于前端解析着色：
  [STEP] 阶段步骤    [INFO] 一般信息    [OK] 成功    [WARN] 警告
  [ERROR] 错误      [DATA] 数据导入    [SQL] DDL/DML    [META] 元数据
"""
from __future__ import annotations

import json
import logging
import traceback
from typing import Callable, List, Optional, Tuple

import psycopg2
from psycopg2 import sql as pg_sql

from django.utils import timezone

from .batch_config import (
    MIGRATION_COMMIT_EVERY_BATCHES,
    MIGRATION_FETCH_BATCH_SIZE,
    MIGRATION_PROGRESS_SAVE_ROWS,
)
from .data_writer import insert_rows_batch
from .migration_validation import validate_row_counts
from .models import MigrationTask
from .oracle_row_adapter import adapt_oracle_rows
from .pg_identifiers import (
    apply_identifier_case,
    build_pg_column_definition,
    build_qualified_table_name,
    quote_identifier,
    safe_oracle_identifier,
)
from .task_logging import (
    LEVEL_DATA,
    LEVEL_ERROR,
    LEVEL_INFO,
    LEVEL_OK,
    LEVEL_SQL,
    LEVEL_STEP,
    LEVEL_WARN,
    build_log_line,
    make_data_log,
    make_error_log,
    make_info_log,
    make_meta_log,
    make_ok_log,
    make_sql_log,
    make_step_log,
    make_warn_log,
)

logger = logging.getLogger(__name__)


def _resolve_view_names(task: MigrationTask) -> List[str]:
    """解析任务中的视图名列表。"""
    if task.source_objects and str(task.source_objects).strip():
        return [v.strip() for v in task.source_objects.split(',') if v.strip()]
    if task.source_object and str(task.source_object).strip():
        return [task.source_object.strip()]
    return []


def _resolve_target_table_name(
    task: MigrationTask,
    view_name: str,
    *,
    multi_view: bool,
) -> str:
    """计算目标表名。"""
    id_case = getattr(task, 'identifier_case', 'lower') or 'lower'
    target_prefix = (task.target_object or '').strip()
    if multi_view:
        # v2.3.1: 多视图模式下未指定前缀时,默认用源 schema 名作为前缀
        # 避免整库迁移 1330 个视图时强制要求用户填写前缀
        if not target_prefix:
            target_prefix = (task.source_schema or 'view').strip()
        return apply_identifier_case(f"{target_prefix}_{view_name}", id_case)
    derived = (task.target_object or task.source_object or view_name).strip()
    if not derived:
        raise ValueError('未指定目标表名')
    if not task.target_object:
        derived = apply_identifier_case(derived, id_case)
    return derived


def _filter_columns(columns, selected_fields: List[str], log: List[str]):
    """按 selected_fields 过滤列（仅单视图）。"""
    if not selected_fields:
        return columns
    lookup = {col[0].upper(): col for col in columns}
    filtered, missing = [], []
    for field in selected_fields:
        col = lookup.get(field)
        if col:
            filtered.append(col)
        else:
            missing.append(field)
    if missing:
        raise ValueError(f"以下字段在视图中不存在: {', '.join(missing)}")
    make_info_log(log, f"用户选择字段 ({len(filtered)} 个): {', '.join(selected_fields)}")
    return filtered


def materialize_one_view(
    *,
    task: MigrationTask,
    oracle_cursor,
    pg_conn,
    pg_cursor,
    view_name: str,
    view_index: int,
    total_views: int,
    log: List[str],
    convert_oracle_to_pg_type: Callable,
    get_oracle_connection=None,
) -> Tuple[bool, Optional[str]]:
    """
    将单个 Oracle 视图物化到 PG 表。
    返回 (是否成功, 错误信息)。
    """
    source_schema = task.source_schema
    target_schema = (task.target_schema or 'public').strip()
    id_case = getattr(task, 'identifier_case', 'lower') or 'lower'
    conflict_strategy = task.conflict_strategy or 'error'
    multi_view = total_views > 1

    make_step_log(log, f'视图物化 {source_schema}.{view_name}', total=total_views, index=view_index)

    # 读取视图定义（仅记录，物化模式不用于 DDL）
    oracle_cursor.execute(
        "SELECT TEXT FROM ALL_VIEWS WHERE OWNER = :schema AND VIEW_NAME = :view_name",
        schema=source_schema,
        view_name=view_name,
    )
    view_row = oracle_cursor.fetchone()
    if not view_row:
        make_error_log(log, f'找不到视图 {source_schema}.{view_name}')
        return False, f"找不到视图 {source_schema}.{view_name}"
    view_text = view_row[0]
    make_meta_log(log, f'视图定义（仅记录）: {str(view_text)[:500]}')

    # 列元数据
    oracle_cursor.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE
        FROM ALL_TAB_COLUMNS
        WHERE OWNER = :schema AND TABLE_NAME = :view_name
        ORDER BY COLUMN_ID
        """,
        schema=source_schema,
        view_name=view_name,
    )
    columns = list(oracle_cursor.fetchall())
    if not columns:
        make_error_log(log, f'找不到视图 {source_schema}.{view_name} 的列信息')
        return False, f"找不到视图 {source_schema}.{view_name} 的列信息"

    selected_fields: List[str] = []
    if total_views == 1 and task.selected_fields:
        import re
        raw = re.split(r'[,\n;，；]+', task.selected_fields)
        selected_fields = [f.strip().upper() for f in raw if f and f.strip()]
    try:
        columns = _filter_columns(columns, selected_fields, log)
    except ValueError as e:
        make_error_log(log, str(e))
        return False, str(e)

    make_meta_log(log, f'视图列数: {len(columns)}')

    target_table = _resolve_target_table_name(task, view_name, multi_view=multi_view)
    qualified_table = build_qualified_table_name(target_schema, target_table)
    display_name = f"{target_schema}.{target_table}"
    make_info_log(log, f'目标表: {display_name}（大小写: {id_case}）')

    # 建表 DDL
    column_defs = []
    for col in columns:
        col_name, data_type, data_length, data_precision, data_scale, nullable = col
        pg_type = convert_oracle_to_pg_type(data_type, data_length, data_precision, data_scale)
        if data_type == 'VARCHAR2' and (data_length is None or data_length == 0):
            pg_type = 'VARCHAR(255)'
            make_warn_log(log, f'列 {col_name} 的 VARCHAR 长度为 0，已调整为 VARCHAR(255)')
        column_defs.append(
            build_pg_column_definition(col_name, pg_type, nullable, id_case=id_case)
        )
    create_sql = f"CREATE TABLE {qualified_table} (\n" + ',\n'.join(column_defs) + "\n)"

    from .schema_converter import pg_table_exists

    pg_table = apply_identifier_case(target_table, id_case)
    table_exists = pg_table_exists(pg_cursor, target_schema, target_table, id_case)

    if table_exists:
        if conflict_strategy == 'error':
            make_error_log(log, f'表 {display_name} 已存在（冲突策略: error）')
            return False, f"表 {display_name} 已存在"
        if conflict_strategy == 'skip':
            make_ok_log(log, f'表 {display_name} 已存在，跳过（冲突策略: skip）')
            return True, None
        if conflict_strategy == 'replace':
            make_warn_log(log, f'冲突策略 replace，删除表 {display_name}')
            pg_cursor.execute(
                pg_sql.SQL('DROP TABLE IF EXISTS {}').format(
                    pg_sql.Identifier(target_schema, target_table))
            )
            pg_conn.commit()
            table_exists = False
        elif conflict_strategy == 'truncate':
            make_warn_log(log, f'冲突策略 truncate，清空表 {display_name}')
            pg_cursor.execute(
                pg_sql.SQL('TRUNCATE TABLE {}').format(
                    pg_sql.Identifier(target_schema, target_table))
            )
            pg_conn.commit()
        elif conflict_strategy == 'append':
            make_info_log(log, f'冲突策略 append，向表 {display_name} 追加数据')

    if not table_exists:
        try:
            pg_cursor.execute(create_sql)
            pg_conn.commit()
            make_ok_log(log, f'成功创建表 {display_name}（{len(column_defs)} 列）')
        except Exception as e:
            make_error_log(log, f'建表失败: {e}')
            make_sql_log(log, create_sql)
            return False, str(e)

    # 统计行数
    total_count = 0
    try:
        # v2.4: schema/view 名经 safe_oracle_identifier 强校验,防注入
        _src_qualified = f"{safe_oracle_identifier(source_schema)}.{safe_oracle_identifier(view_name)}"
        oracle_cursor.execute(f"SELECT COUNT(*) FROM {_src_qualified}")
        total_count = int(oracle_cursor.fetchone()[0])
        make_meta_log(log, f'视图 {view_name} 总行数: {total_count}')
    except Exception as count_err:
        err_str = str(count_err).upper()
        if 'ORA-00942' in err_str or '00942' in err_str:
            make_error_log(log, f'无法访问源视图 {source_schema}.{view_name}: {count_err}')
            return False, f"无法访问源视图 {source_schema}.{view_name}: {count_err}"
        make_warn_log(log, f'未获取总行数，进度按已迁移行数估算: {count_err}')

    # 分批导数
    _src_qualified = f"{safe_oracle_identifier(source_schema)}.{safe_oracle_identifier(view_name)}"
    if selected_fields:
        oracle_cols = ', '.join(c[0] for c in columns)
        oracle_query = f"SELECT {oracle_cols} FROM {_src_qualified}"
    else:
        oracle_query = f"SELECT * FROM {_src_qualified}"

    fetch_batch = MIGRATION_FETCH_BATCH_SIZE
    commit_every = MIGRATION_COMMIT_EVERY_BATCHES
    progress_interval = MIGRATION_PROGRESS_SAVE_ROWS
    oracle_cursor.arraysize = fetch_batch
    oracle_cursor.execute(oracle_query)
    make_info_log(log, f'开始分批读取 (batch_size={fetch_batch}, commit_every={commit_every})')

    column_names = [
        apply_identifier_case(desc[0], id_case) for desc in oracle_cursor.description
    ]
    column_oracle_types = [c[1] for c in columns]
    quoted_cols = [quote_identifier(c) for c in column_names]

    total_rows = 0
    batches_since_commit = 0
    last_saved_pct = -1
    last_saved_rows = 0
    widened_columns = set()

    while True:
        task.refresh_from_db()
        if task.cancel_requested:
            make_warn_log(log, f'用户取消，视图 {view_name} 已导入 {total_rows} 行')
            return False, 'canceled'

        rows = oracle_cursor.fetchmany(fetch_batch)
        if not rows:
            break

        try:
            insert_rows_batch(
                pg_cursor,
                pg_conn,
                qualified_table,
                quoted_cols,
                rows,
                column_oracle_types,
                total_rows_hint=total_count,
            )
        except psycopg2.errors.StringDataRightTruncation as trunc_err:
            pg_conn.rollback()
            col_name = getattr(getattr(trunc_err, 'diag', None), 'column_name', None)
            if not col_name or col_name in widened_columns:
                make_error_log(log, f'字符串截断: {trunc_err}')
                return False, str(trunc_err)
            widened_columns.add(col_name)
            make_warn_log(log, f'列 {col_name} 字符串截断，自动扩展为 TEXT')
            pg_cursor.execute(
                f"ALTER TABLE {qualified_table} "
                f"ALTER COLUMN {quote_identifier(col_name)} TYPE TEXT"
            )
            pg_conn.commit()
            insert_rows_batch(
                pg_cursor,
                pg_conn,
                qualified_table,
                quoted_cols,
                rows,
                column_oracle_types,
                total_rows_hint=total_count,
            )
        except psycopg2.Error as pg_err:
            pg_conn.rollback()
            make_error_log(log, f'写入失败: {pg_err}')
            return False, str(pg_err)

        total_rows += len(rows)
        batches_since_commit += 1
        if batches_since_commit >= commit_every:
            pg_conn.commit()
            batches_since_commit = 0

        progress_pct = min(100.0, (total_rows / total_count) * 100) if total_count > 0 else 0.0
        should_save = (
            int(progress_pct) > last_saved_pct
            or (total_rows - last_saved_rows) >= progress_interval
        )
        if should_save:
            vp = task.view_progress or {}
            if isinstance(vp, str):
                try:
                    vp = json.loads(vp)
                except Exception:
                    vp = {}
            vp[view_name] = {
                'progress': progress_pct,
                'total_rows': total_count,
                'migrated_rows': total_rows,
            }
            task.view_progress = vp
            view_weight = 100.0 / total_views
            task.progress = min(
                100.0,
                (view_index / total_views) * 100 + (progress_pct / 100.0) * view_weight,
            )
            task.save(update_fields=['view_progress', 'progress'])
            last_saved_pct = int(progress_pct)
            last_saved_rows = total_rows
            make_data_log(
                log,
                f'视图 {view_name} 已迁移 {total_rows}/{total_count} 行 ({progress_pct:.1f}%)',
            )

    if batches_since_commit > 0:
        pg_conn.commit()

    if total_rows == 0:
        make_warn_log(log, f'视图 {view_name} 无数据行')
    else:
        make_ok_log(log, f'成功从视图导入 {total_rows} 行到表 {display_name}')

    # 行数校验
    validate_row_counts(
        oracle_cursor,
        pg_cursor,
        source_schema,
        view_name,
        target_schema,
        target_table,
        log,
        pg_table_name=pg_table,
    )
    return True, None


def run_view_materialization_task(
    task_id: int,
    postgres_database=None,
    *,
    get_oracle_connection,
    get_postgres_connection,
    convert_oracle_to_pg_type,
) -> None:
    """执行视图物化任务（view / view_to_table 共用入口）。"""
    from django.shortcuts import get_object_or_404

    task = get_object_or_404(MigrationTask, pk=task_id)
    task.status = 'running'
    task.started_at = timezone.now()
    task.progress = 0
    # v2.4.2: 不再清空 view_progress —— 整库编排把 phase/completed_objects 等
    # 断点续传状态也存在 view_progress 中，清空会导致中断后 resume 语义损坏。
    task.save()

    log: List[str] = []
    make_step_log(log, f'视图物化任务 #{task_id} 启动')
    if postgres_database:
        make_info_log(log, f'目标 PostgreSQL 数据库: {postgres_database}')

    oracle_conn = None
    pg_conn = None
    try:
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        pg_conn = get_postgres_connection(task.postgres_connection.id, postgres_database)
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute('SELECT current_database()')
        make_ok_log(log, f'已连接 PostgreSQL: {pg_cursor.fetchone()[0]}')
        make_ok_log(log, '已连接 Oracle 源端')

        views = _resolve_view_names(task)
        if not views:
            raise ValueError('未指定要迁移的视图')
        make_info_log(log, f'待迁移视图数: {len(views)}')

        successful, failed, canceled = [], [], False
        total = len(views)

        for idx, view_name in enumerate(views):
            task.refresh_from_db()
            if task.cancel_requested:
                canceled = True
                break
            ok, err = materialize_one_view(
                task=task,
                oracle_cursor=oracle_cursor,
                pg_conn=pg_conn,
                pg_cursor=pg_cursor,
                view_name=view_name,
                view_index=idx,
                total_views=total,
                log=log,
                convert_oracle_to_pg_type=convert_oracle_to_pg_type,
            )
            if err == 'canceled':
                canceled = True
                break
            if ok:
                successful.append(view_name)
            else:
                failed.append(view_name)
                if err:
                    make_error_log(log, f'视图 {view_name} 失败: {err}')
                try:
                    pg_conn.rollback()
                except Exception:
                    pass

        make_step_log(log, '任务结束')
        if canceled:
            task.status = 'canceled'
            make_warn_log(log, '任务已取消（已迁移的视图已保留）')
        elif failed and successful:
            task.status = 'partial'
            make_ok_log(log, f'部分成功 ({len(successful)}/{total}): {", ".join(successful)}')
            make_error_log(log, f'失败 ({len(failed)}): {", ".join(failed)}')
        elif failed and not successful:
            task.status = 'failed'
            make_error_log(log, f'全部失败 ({len(failed)}): {", ".join(failed)}')
        else:
            task.status = 'completed'
            make_ok_log(log, f'全部视图物化成功 ({len(successful)}/{total}): {", ".join(successful)}')
        task.progress = 100.0 if task.status == 'completed' else task.progress
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

    except Exception as e:
        make_error_log(log, f'任务异常: {e}')
        make_error_log(log, traceback.format_exc())
        task.status = 'failed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
    finally:
        try:
            if oracle_conn:
                oracle_conn.close()
            if pg_conn:
                pg_conn.close()
        except Exception:
            pass
