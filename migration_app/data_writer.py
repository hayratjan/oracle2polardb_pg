"""
PostgreSQL 数据写入：小批量 executemany，大批量 execute_values / COPY。
"""
from __future__ import annotations

import io
import logging
from typing import List, Optional, Sequence

from psycopg2.extras import execute_values

from .batch_config import MIGRATION_COPY_ROW_THRESHOLD, MIGRATION_FETCH_BATCH_SIZE
from .oracle_row_adapter import adapt_oracle_rows

logger = logging.getLogger(__name__)


def _format_copy_value(value) -> str:
    """将 Python 值格式化为 COPY 文本格式。"""
    if value is None:
        return r'\N'
    if isinstance(value, bool):
        return 't' if value else 'f'
    if isinstance(value, bytes):
        return '\\x' + value.hex()
    s = str(value)
    # COPY 文本格式转义
    s = s.replace('\\', '\\\\')
    s = s.replace('\t', '\\t')
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    return s


def insert_rows_batch(
    pg_cursor,
    pg_conn,
    qualified_table: str,
    quoted_columns: List[str],
    rows: Sequence[Sequence],
    column_oracle_types: Sequence[Optional[str]],
    *,
    total_rows_hint: int = 0,
    use_fast_path: Optional[bool] = None,
) -> int:
    """
    批量插入行到 PostgreSQL。
    当预估总行数超过阈值时使用 execute_values 加速。
    返回写入行数。
    """
    if not rows:
        return 0

    adapted = adapt_oracle_rows(rows, column_oracle_types)
    col_list = ', '.join(quoted_columns)
    placeholders = ', '.join(['%s'] * len(quoted_columns))
    insert_sql = f"INSERT INTO {qualified_table} ({col_list}) VALUES ({placeholders})"

    fast = use_fast_path
    if fast is None:
        fast = total_rows_hint >= MIGRATION_COPY_ROW_THRESHOLD

    if fast and len(adapted) > 0:
        # execute_values 比 executemany 快，COPY 需要额外格式化，超大批量时再走 COPY
        if total_rows_hint >= MIGRATION_COPY_ROW_THRESHOLD * 10:
            return _copy_rows(pg_cursor, qualified_table, quoted_columns, adapted)
        execute_values(
            pg_cursor,
            f"INSERT INTO {qualified_table} ({col_list}) VALUES %s",
            adapted,
            page_size=MIGRATION_FETCH_BATCH_SIZE,
        )
    else:
        pg_cursor.executemany(insert_sql, adapted)

    return len(adapted)


def _copy_rows(
    pg_cursor,
    qualified_table: str,
    quoted_columns: List[str],
    rows: Sequence[Sequence],
) -> int:
    """使用 COPY FROM 高速写入（无 LOB 或已转为 str/bytes 时）。"""
    # 解析 schema.table
    parts = qualified_table.replace('"', '').split('.')
    if len(parts) == 2:
        schema, table = parts
    else:
        schema, table = 'public', parts[0]

    buf = io.StringIO()
    for row in rows:
        line = '\t'.join(_format_copy_value(v) for v in row)
        buf.write(line + '\n')
    buf.seek(0)
    col_names = [c.strip('"') for c in quoted_columns]
    pg_cursor.copy_from(buf, table, sep='\t', null=r'\N', columns=col_names, schema=schema)
    return len(rows)
