"""
迁移后数据校验：源端与目标端行数对比等。
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def count_oracle_rows(
    oracle_cursor,
    source_schema: str,
    object_name: str,
    *,
    where_sql: str = '',
    bind_params: Optional[dict] = None,
) -> int:
    """统计 Oracle 源对象行数。"""
    sql = f"SELECT COUNT(*) FROM {source_schema}.{object_name}"
    if where_sql:
        sql += f" {where_sql}"
    if bind_params:
        oracle_cursor.execute(sql, bind_params)
    else:
        oracle_cursor.execute(sql)
    return int(oracle_cursor.fetchone()[0])


def count_pg_rows(
    pg_cursor,
    target_schema: str,
    table_name: str,
    *,
    pg_table_name: Optional[str] = None,
) -> int:
    """统计 PostgreSQL 目标表行数。"""
    from .pg_identifiers import build_qualified_table_name

    tbl = pg_table_name or table_name
    qualified = build_qualified_table_name(target_schema, tbl)
    pg_cursor.execute(f"SELECT COUNT(*) FROM {qualified}")
    return int(pg_cursor.fetchone()[0])


def validate_row_counts(
    oracle_cursor,
    pg_cursor,
    source_schema: str,
    source_object: str,
    target_schema: str,
    target_table: str,
    log_list: List[str],
    *,
    pg_table_name: Optional[str] = None,
    watermark_where: str = '',
    watermark_params: Optional[dict] = None,
) -> Tuple[bool, int, int]:
    """
    对比源端与目标端行数。
    返回 (是否一致, 源行数, 目标行数)。
    """
    try:
        src_count = count_oracle_rows(
            oracle_cursor,
            source_schema,
            source_object,
            where_sql=watermark_where,
            bind_params=watermark_params,
        )
        tgt_count = count_pg_rows(
            pg_cursor,
            target_schema,
            target_table,
            pg_table_name=pg_table_name,
        )
        if src_count == tgt_count:
            log_list.append(
                f"[OK] 行数校验通过 · {source_object}: 源端 {src_count} 行 = 目标端 {tgt_count} 行"
            )
            return True, src_count, tgt_count
        log_list.append(
            f"[WARN] 行数校验失败 · {source_object}: 源端 {src_count} 行 ≠ 目标端 {tgt_count} 行，请人工核查"
        )
        return False, src_count, tgt_count
    except Exception as e:
        from .migration_errors import format_db_error
        logger.warning('行数校验异常: %s', e)
        log_list.append(
            f"[WARN] 行数校验跳过 · {source_object}: 行数对比异常 ({format_db_error(e)})，请检查连接与权限"
        )
        return True, -1, -1  # 校验失败不阻塞迁移，仅记日志
