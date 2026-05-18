"""
「所有表」任务：多表并行迁移（每表独立 Oracle/PostgreSQL 连接，线程池调度）。
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from django.db import close_old_connections

from .batch_config import MIGRATION_PARALLEL_TABLE_WORKERS
from .resume import build_batch_view_progress, mark_table_completed

logger = logging.getLogger(__name__)


def _migrate_one_table_job(
    *,
    oracle_connection_id: int,
    postgres_connection_id: int,
    postgres_database: Optional[str],
    source_schema: str,
    target_schema: str,
    table_name: str,
    conflict_strategy: str,
) -> Dict[str, Any]:
    """
    在线程中迁移单张表（独立连接，不写 task 进度，避免并发写库冲突）。
    返回 {table, ok, error, log_lines, rows}。
    """
    from .views import (
        _migrate_single_table,
        get_oracle_connection,
        get_postgres_connection,
    )

    close_old_connections()
    table_log: List[str] = []
    oracle_conn = None
    pg_conn = None
    oracle_cursor = None
    pg_cursor = None
    try:
        table_log.append(f"【并行】开始迁移表 {table_name}")
        oracle_conn = get_oracle_connection(oracle_connection_id)
        oracle_cursor = oracle_conn.cursor()
        pg_conn = get_postgres_connection(postgres_connection_id, postgres_database)
        pg_cursor = pg_conn.cursor()
        _migrate_single_table(
            oracle_cursor,
            pg_conn,
            pg_cursor,
            source_schema,
            target_schema,
            table_name,
            conflict_strategy,
            table_log,
            task=None,
            all_tables_context=None,
        )
        return {'table': table_name, 'ok': True, 'error': None, 'log_lines': table_log, 'rows': 0}
    except Exception as e:
        table_log.append(f"表 {table_name} 迁移失败: {e}")
        logger.exception('并行迁移表 %s 失败', table_name)
        return {'table': table_name, 'ok': False, 'error': str(e), 'log_lines': table_log, 'rows': 0}
    finally:
        try:
            if oracle_cursor:
                oracle_cursor.close()
            if oracle_conn:
                oracle_conn.close()
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()
        except Exception:
            pass
        close_old_connections()


def run_parallel_table_migrations(
    *,
    task,
    tables: List[str],
    total_tables: int,
    base_done: int,
    completed_set: Set[str],
    log: List[str],
    failed_tables: List[Tuple[str, str]],
    running_tables: Set[str],
    postgres_database: Optional[str],
    on_progress: Callable[[], None],
    should_cancel: Callable[[], bool],
) -> None:
    """
    线程池并行迁移表列表；结果写入 failed_tables / completed_set / log（调用方与 on_progress 共享锁）。
    """
    workers = max(1, int(MIGRATION_PARALLEL_TABLE_WORKERS))
    log.append(f"【并行迁移】最多同时 {workers} 张表（每张表独立数据库连接）")
    lock = threading.Lock()

    def _sync_progress() -> None:
        on_progress()

    oracle_id = task.oracle_connection_id
    pg_id = task.postgres_connection_id
    source_schema = task.source_schema
    target_schema = task.target_schema or 'public'
    strategy = task.conflict_strategy or 'error'

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='migrate_tbl_') as executor:
        futures = {}
        for table_name in tables:
            if should_cancel():
                log.append("用户取消，停止提交新的并行迁移任务")
                break
            with lock:
                running_tables.add(table_name)
            _sync_progress()
            fut = executor.submit(
                _migrate_one_table_job,
                oracle_connection_id=oracle_id,
                postgres_connection_id=pg_id,
                postgres_database=postgres_database,
                source_schema=source_schema,
                target_schema=target_schema,
                table_name=table_name,
                conflict_strategy=strategy,
            )
            futures[fut] = table_name

        for fut in as_completed(futures):
            table_name = futures[fut]
            try:
                result = fut.result()
            except Exception as e:
                result = {
                    'table': table_name,
                    'ok': False,
                    'error': str(e),
                    'log_lines': [f"表 {table_name} 执行异常: {e}"],
                }
            with lock:
                running_tables.discard(table_name)
                log.extend(result.get('log_lines') or [])
                if result.get('ok'):
                    mark_table_completed(completed_set, table_name)
                    log.append(f"【完成】并行表 {table_name}")
                else:
                    err = result.get('error') or '未知错误'
                    failed_tables.append((table_name, err))
                _sync_progress()
