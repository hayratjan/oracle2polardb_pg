"""
Oracle 表结构扩展迁移：约束、索引、列默认值（含序列 nextval 绑定）。
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from .pg_identifiers import apply_identifier_case, build_qualified_table_name, quote_identifier

logger = logging.getLogger(__name__)

# Oracle DATA_DEFAULT 中序列引用模式
_SEQ_DEFAULT_RE = re.compile(
    r'"?([A-Za-z0-9_$#]+)"?\."?([A-Za-z0-9_$#]+)"?\.NEXTVAL',
    re.IGNORECASE,
)


def pg_table_exists(
    pg_cursor,
    target_schema: str,
    table_name: str,
    id_case: str = 'lower',
) -> bool:
    """按 identifier_case 检测目标表是否存在。"""
    pg_table = apply_identifier_case(table_name, id_case)
    pg_cursor.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """,
        (target_schema, pg_table),
    )
    return pg_cursor.fetchone() is not None


def fetch_column_defaults(
    oracle_cursor,
    source_schema: str,
    table_name: str,
) -> Dict[str, str]:
    """读取 Oracle 列默认值（DATA_DEFAULT）。"""
    oracle_cursor.execute(
        """
        SELECT COLUMN_NAME, DATA_DEFAULT
        FROM ALL_TAB_COLUMNS
        WHERE OWNER = :schema AND TABLE_NAME = :table_name
          AND DATA_DEFAULT IS NOT NULL
        """,
        {'schema': source_schema.upper(), 'table_name': table_name.upper()},
    )
    result: Dict[str, str] = {}
    for col_name, data_default in oracle_cursor.fetchall():
        if data_default:
            result[col_name] = str(data_default).strip()
    return result


def _convert_oracle_default_to_pg(
    oracle_default: str,
    *,
    target_schema: str,
    id_case: str,
    log_list: List[str],
    column_name: str,
) -> Optional[str]:
    """
    将 Oracle 列默认值转为 PostgreSQL DEFAULT 表达式。
    序列引用映射为 nextval('schema.seq'::regclass)。
    """
    text = oracle_default.strip()
    if not text:
        return None

    # 序列 .NEXTVAL
    m = _SEQ_DEFAULT_RE.search(text)
    if m:
        seq_schema, seq_name = m.group(1), m.group(2)
        pg_seq = apply_identifier_case(seq_name, id_case)
        pg_schema = target_schema or apply_identifier_case(seq_schema, id_case)
        log_list.append(
            f"列 {column_name} 默认值序列绑定: {seq_schema}.{seq_name} → nextval('{pg_schema}.{pg_seq}')"
        )
        return f"nextval('{pg_schema}.{pg_seq}'::regclass)"

    upper = text.upper()
    if upper in ('SYSDATE', 'CURRENT_DATE', 'CURRENT_TIMESTAMP'):
        return 'CURRENT_TIMESTAMP'
    if upper.startswith('TO_DATE(') or upper.startswith('TO_TIMESTAMP('):
        log_list.append(f"列 {column_name} 默认值含 TO_DATE/TO_TIMESTAMP，需人工复核: {text}")
        return None
    # 字面量或简单表达式
    if re.match(r'^-?\d+(\.\d+)?$', text):
        return text
    if text.startswith("'") and text.endswith("'"):
        return text
    log_list.append(f"列 {column_name} 默认值未自动转换，需人工处理: {text}")
    return None


def apply_column_defaults(
    oracle_cursor,
    pg_cursor,
    pg_conn,
    source_schema: str,
    target_schema: str,
    table_name: str,
    log_list: List[str],
    *,
    id_case: str = 'lower',
) -> None:
    """为已建表添加列 DEFAULT（含序列 nextval 绑定）。"""
    defaults = fetch_column_defaults(oracle_cursor, source_schema, table_name)
    if not defaults:
        return

    qualified = build_qualified_table_name(
        target_schema,
        apply_identifier_case(table_name, id_case),
    )
    for col_name, ora_def in defaults.items():
        pg_def = _convert_oracle_default_to_pg(
            ora_def,
            target_schema=target_schema,
            id_case=id_case,
            log_list=log_list,
            column_name=col_name,
        )
        if not pg_def:
            continue
        pg_col = apply_identifier_case(col_name, id_case)
        alter_sql = (
            f"ALTER TABLE {qualified} "
            f"ALTER COLUMN {quote_identifier(pg_col)} SET DEFAULT {pg_def}"
        )
        try:
            pg_cursor.execute(alter_sql)
            pg_conn.commit()
            log_list.append(f"已设置列默认值: {table_name}.{col_name}")
        except Exception as e:
            pg_conn.rollback()
            log_list.append(f"设置列 {col_name} 默认值失败: {e}")


def fetch_table_constraints(
    oracle_cursor,
    source_schema: str,
    table_name: str,
) -> List[dict]:
    """读取表级约束（PK/UK/CHECK，不含 FK 创建）。"""
    oracle_cursor.execute(
        """
        SELECT c.CONSTRAINT_NAME, c.CONSTRAINT_TYPE, c.SEARCH_CONDITION, c.R_CONSTRAINT_NAME
        FROM ALL_CONSTRAINTS c
        WHERE c.OWNER = :schema AND c.TABLE_NAME = :table_name
          AND c.CONSTRAINT_TYPE IN ('P', 'U', 'C')
          AND c.STATUS = 'ENABLED'
        ORDER BY c.CONSTRAINT_TYPE, c.CONSTRAINT_NAME
        """,
        {'schema': source_schema.upper(), 'table_name': table_name.upper()},
    )
    constraints = []
    for row in oracle_cursor.fetchall():
        c_name, c_type, search_cond, r_cons = row
        oracle_cursor.execute(
            """
            SELECT COLUMN_NAME FROM ALL_CONS_COLUMNS
            WHERE OWNER = :schema AND CONSTRAINT_NAME = :cname
            ORDER BY POSITION
            """,
            {'schema': source_schema.upper(), 'cname': c_name},
        )
        columns = [r[0] for r in oracle_cursor.fetchall()]
        constraints.append({
            'name': c_name,
            'type': c_type,
            'columns': columns,
            'search_condition': search_cond,
            'ref_constraint': r_cons,
        })
    return constraints


def _build_constraint_ddl(
    constraint: dict,
    qualified_table: str,
    id_case: str,
) -> Optional[str]:
    """生成 ALTER TABLE ADD CONSTRAINT DDL。"""
    cols = constraint.get('columns') or []
    if not cols:
        return None
    quoted_cols = ', '.join(
        quote_identifier(apply_identifier_case(c, id_case)) for c in cols
    )
    c_type = constraint['type']
    c_name = apply_identifier_case(constraint['name'], id_case)

    if c_type == 'P':
        return f"ALTER TABLE {qualified_table} ADD CONSTRAINT {quote_identifier(c_name)} PRIMARY KEY ({quoted_cols})"
    if c_type == 'U':
        return f"ALTER TABLE {qualified_table} ADD CONSTRAINT {quote_identifier(c_name)} UNIQUE ({quoted_cols})"
    if c_type == 'C' and constraint.get('search_condition'):
        cond = constraint['search_condition']
        # 简单替换 SYSDATE
        cond = re.sub(r'\bSYSDATE\b', 'CURRENT_TIMESTAMP', cond, flags=re.IGNORECASE)
        return (
            f"ALTER TABLE {qualified_table} ADD CONSTRAINT {quote_identifier(c_name)} "
            f"CHECK ({cond})"
        )
    return None


def apply_table_constraints(
    oracle_cursor,
    pg_cursor,
    pg_conn,
    source_schema: str,
    target_schema: str,
    table_name: str,
    log_list: List[str],
    *,
    id_case: str = 'lower',
) -> None:
    """在目标表上创建主键、唯一、检查约束。"""
    constraints = fetch_table_constraints(oracle_cursor, source_schema, table_name)
    if not constraints:
        return

    qualified = build_qualified_table_name(
        target_schema,
        apply_identifier_case(table_name, id_case),
    )
    for cons in constraints:
        ddl = _build_constraint_ddl(cons, qualified, id_case)
        if not ddl:
            continue
        try:
            pg_cursor.execute(ddl)
            pg_conn.commit()
            log_list.append(f"已创建约束 {cons['name']} ({cons['type']}) 于表 {table_name}")
        except Exception as e:
            pg_conn.rollback()
            log_list.append(f"创建约束 {cons['name']} 失败（可人工补建）: {e}")


def fetch_table_indexes(
    oracle_cursor,
    source_schema: str,
    table_name: str,
) -> List[dict]:
    """读取非约束自动创建的索引（排除 PK/UK 约束索引）。"""
    oracle_cursor.execute(
        """
        SELECT i.INDEX_NAME, i.UNIQUENESS, ic.COLUMN_NAME, ic.COLUMN_POSITION
        FROM ALL_INDEXES i
        JOIN ALL_IND_COLUMNS ic
          ON i.OWNER = ic.INDEX_OWNER AND i.INDEX_NAME = ic.INDEX_NAME
        WHERE i.TABLE_OWNER = :schema AND i.TABLE_NAME = :table_name
          AND i.INDEX_TYPE = 'NORMAL'
          AND NOT EXISTS (
            SELECT 1 FROM ALL_CONSTRAINTS c
            WHERE c.OWNER = i.TABLE_OWNER AND c.INDEX_NAME = i.INDEX_NAME
          )
        ORDER BY i.INDEX_NAME, ic.COLUMN_POSITION
        """,
        {'schema': source_schema.upper(), 'table_name': table_name.upper()},
    )
    index_map: Dict[str, dict] = {}
    for idx_name, uniqueness, col_name, _pos in oracle_cursor.fetchall():
        if idx_name not in index_map:
            index_map[idx_name] = {
                'name': idx_name,
                'unique': uniqueness == 'UNIQUE',
                'columns': [],
            }
        index_map[idx_name]['columns'].append(col_name)
    return list(index_map.values())


def apply_table_indexes(
    oracle_cursor,
    pg_cursor,
    pg_conn,
    source_schema: str,
    target_schema: str,
    table_name: str,
    log_list: List[str],
    *,
    id_case: str = 'lower',
) -> None:
    """在目标表上创建索引。"""
    indexes = fetch_table_indexes(oracle_cursor, source_schema, table_name)
    if not indexes:
        return

    qualified = build_qualified_table_name(
        target_schema,
        apply_identifier_case(table_name, id_case),
    )
    for idx in indexes:
        cols = idx.get('columns') or []
        if not cols:
            continue
        quoted_cols = ', '.join(
            quote_identifier(apply_identifier_case(c, id_case)) for c in cols
        )
        idx_name = apply_identifier_case(idx['name'], id_case)
        unique_kw = 'UNIQUE ' if idx.get('unique') else ''
        ddl = f"CREATE {unique_kw}INDEX {quote_identifier(idx_name)} ON {qualified} ({quoted_cols})"
        try:
            pg_cursor.execute(ddl)
            pg_conn.commit()
            log_list.append(f"已创建索引 {idx['name']} 于表 {table_name}")
        except Exception as e:
            pg_conn.rollback()
            log_list.append(f"创建索引 {idx['name']} 失败（可人工补建）: {e}")


def apply_post_table_schema(
    oracle_cursor,
    pg_cursor,
    pg_conn,
    source_schema: str,
    target_schema: str,
    table_name: str,
    log_list: List[str],
    *,
    id_case: str = 'lower',
    skip_constraints: bool = False,
) -> None:
    """
    建表并导数后执行的 Schema 扩展：默认值 → 约束 → 索引。
    """
    log_list.append(f"【Schema 扩展】开始处理表 {table_name} 的默认值/约束/索引")
    apply_column_defaults(
        oracle_cursor, pg_cursor, pg_conn,
        source_schema, target_schema, table_name, log_list, id_case=id_case,
    )
    if not skip_constraints:
        apply_table_constraints(
            oracle_cursor, pg_cursor, pg_conn,
            source_schema, target_schema, table_name, log_list, id_case=id_case,
        )
    apply_table_indexes(
        oracle_cursor, pg_cursor, pg_conn,
        source_schema, target_schema, table_name, log_list, id_case=id_case,
    )
