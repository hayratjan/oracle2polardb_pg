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
    if upper == 'SYSDATE':
        return 'CURRENT_TIMESTAMP'
    if upper == 'CURRENT_DATE':
        # Oracle CURRENT_DATE 含会话时区的日期时间；语义上取日期部分更接近 PG CURRENT_DATE
        return 'CURRENT_DATE'
    if upper == 'CURRENT_TIMESTAMP':
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
    """读取非约束自动创建的索引（排除 PK/UK 约束索引）。

    仅返回 NORMAL 类型索引。函数索引/位图索引/反向键索引由
    fetch_unsupported_indexes 单独统计并告警。
    """
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


def fetch_unsupported_indexes(
    oracle_cursor,
    source_schema: str,
    table_name: str,
) -> List[dict]:
    """统计不被自动迁移的索引类型（函数索引/位图索引/反向键索引等）。

    用于在迁移日志中告警，提示用户需人工补建。
    PG 对应策略参考：
      - FUNCTION-BASED NORMAL → PG 表达式索引
      - BITMAP → PG 无原生位图，转 GIN 或普通索引
      - REVERSE → PG 无反向键索引，转普通索引
      - DOMAIN/CLUSTER → PG 无对应，人工处理
    """
    oracle_cursor.execute(
        """
        SELECT i.INDEX_NAME, i.INDEX_TYPE, i.UNIQUENESS,
               ic.COLUMN_NAME, ic.COLUMN_POSITION,
               ie.COLUMN_EXPRESSION
        FROM ALL_INDEXES i
        JOIN ALL_IND_COLUMNS ic
          ON i.OWNER = ic.INDEX_OWNER AND i.INDEX_NAME = ic.INDEX_NAME
        LEFT JOIN ALL_IND_EXPRESSIONS ie
          ON i.OWNER = ie.INDEX_OWNER AND i.INDEX_NAME = ie.INDEX_NAME
          AND ic.COLUMN_POSITION = ie.COLUMN_POSITION
        WHERE i.TABLE_OWNER = :schema AND i.TABLE_NAME = :table_name
          AND i.INDEX_TYPE != 'NORMAL'
          AND NOT EXISTS (
            SELECT 1 FROM ALL_CONSTRAINTS c
            WHERE c.OWNER = i.TABLE_OWNER AND c.INDEX_NAME = i.INDEX_NAME
          )
        ORDER BY i.INDEX_NAME, ic.COLUMN_POSITION
        """,
        {'schema': source_schema.upper(), 'table_name': table_name.upper()},
    )
    index_map: Dict[str, dict] = {}
    for row in oracle_cursor.fetchall():
        idx_name, idx_type, uniqueness, col_name, _pos, col_expr = row
        if idx_name not in index_map:
            index_map[idx_name] = {
                'name': idx_name,
                'type': idx_type,
                'unique': uniqueness == 'UNIQUE',
                'columns': [],
                'expressions': [],
            }
        index_map[idx_name]['columns'].append(col_name)
        if col_expr:
            index_map[idx_name]['expressions'].append(col_expr)
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
    """在目标表上创建索引，并对不支持的索引类型输出告警。"""
    indexes = fetch_table_indexes(oracle_cursor, source_schema, table_name)
    # 检查不被自动迁移的索引（函数索引/位图/反向键等）
    unsupported = fetch_unsupported_indexes(oracle_cursor, source_schema, table_name)
    if unsupported:
        log_list.append(f"[WARN] 表 {table_name} 有 {len(unsupported)} 个索引未自动迁移（需人工补建）：")
        for idx in unsupported:
            idx_type = idx.get('type', 'UNKNOWN')
            exprs = idx.get('expressions') or []
            if exprs:
                log_list.append(f"  - {idx['name']} ({idx_type}): 表达式 {' | '.join(exprs)}")
            else:
                log_list.append(f"  - {idx['name']} ({idx_type}): 列 {', '.join(idx.get('columns', []))}")
            # 给出 PG 对应建议
            if 'FUNCTION' in idx_type.upper() or exprs:
                log_list.append(f"    建议：在 PG 上创建表达式索引 CREATE INDEX ... ON ... ({', '.join(exprs) if exprs else '...'})")
            elif 'BITMAP' in idx_type.upper():
                log_list.append(f"    建议：PG 无位图索引，转 GIN 或普通 B-tree 索引")
            elif 'REVERSE' in idx_type.upper():
                log_list.append(f"    建议：PG 无反向键索引，转普通 B-tree 索引")

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


def align_sequences_with_data(
    pg_cursor,
    pg_conn,
    target_schema: str,
    table_name: str,
    log_list: List[str],
    *,
    id_case: str = 'lower',
) -> None:
    """数据导入后将 IDENTITY 列与 nextval 默认列的序列推进到 MAX(列值)。

    否则目标序列/IDENTITY 停留在初始值 1，业务切换后新插入会主键冲突。
    """
    pg_table = apply_identifier_case(table_name, id_case)
    qualified = build_qualified_table_name(target_schema, pg_table)
    seq_columns: List[Tuple[str, str]] = []
    try:
        # IDENTITY 列 → 通过 pg_get_serial_sequence 取隐式序列
        pg_cursor.execute(
            """
            SELECT a.attname, pg_get_serial_sequence(%s, a.attname)
            FROM pg_attribute a
            WHERE a.attrelid = %s::regclass
              AND a.attnum > 0 AND NOT a.attisdropped
              AND a.attidentity IN ('a', 'd')
            """,
            (qualified, qualified),
        )
        seq_columns.extend(r for r in pg_cursor.fetchall() if r[1])
        # nextval(...) 默认列 → 从默认表达式提取 'schema.seq' 字面量
        pg_cursor.execute(
            """
            SELECT a.attname, (SELECT (regexp_matches(
                pg_get_expr(d.adbin, d.adrelid),
                'nextval\\(''([^'']+)''::regclass\\)'))[1])
            FROM pg_attribute a
            JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
            WHERE a.attrelid = %s::regclass
              AND a.attnum > 0 AND NOT a.attisdropped
              AND a.attidentity NOT IN ('a', 'd')
              AND pg_get_expr(d.adbin, d.adrelid) LIKE 'nextval(%'
            """,
            (qualified,),
        )
        seq_columns.extend(r for r in pg_cursor.fetchall() if r[1])
    except Exception as e:
        log_list.append(f"[WARN] 序列对齐: 查询表 {table_name} 序列列失败(跳过): {e}")
        return

    from psycopg2 import sql as pg_sql
    for col, seq_name in seq_columns:
        try:
            # 全部标识符/字面量经 psycopg2.sql 安全组合（Composed），非字符串拼接
            stmt: pg_sql.Composed = (
                pg_sql.SQL('SELECT setval(')
                + pg_sql.Literal(seq_name)
                + pg_sql.SQL('::regclass, GREATEST((SELECT MAX(')
                + pg_sql.Identifier(col)
                + pg_sql.SQL(') FROM ')
                + pg_sql.Identifier(target_schema, pg_table)
                + pg_sql.SQL('), 1))')
            )
            pg_cursor.execute(stmt)
            pg_conn.commit()
            log_list.append(f'已对齐序列 {seq_name} 至 {table_name}.{col} 最大值')
        except Exception as e:
            pg_conn.rollback()
            log_list.append(f'[WARN] 序列对齐失败 {table_name}.{col} ({seq_name}): {e}')


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
    建表并导数后执行的 Schema 扩展：默认值 → 约束 → 索引 → 注释 → 序列对齐。
    """
    log_list.append(f"【Schema 扩展】开始处理表 {table_name} 的默认值/约束/索引/注释")
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
    apply_table_comments(
        oracle_cursor, pg_cursor, pg_conn,
        source_schema, target_schema, table_name, log_list, id_case=id_case,
    )
    # v2.4.2: 数据导入后将 IDENTITY/nextval 序列推进到 MAX(列值)，避免切换后主键冲突
    align_sequences_with_data(
        pg_cursor, pg_conn, target_schema, table_name, log_list, id_case=id_case,
    )


def apply_table_comments(
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
    """迁移表级和列级注释到 PolarDB/PostgreSQL。

    Oracle 注释存储在 ALL_TAB_COMMENTS 和 ALL_COL_COMMENTS 视图中，
    PG 对应 COMMENT ON TABLE / COMMENT ON COLUMN。
    """
    try:
        # 表级注释
        oracle_cursor.execute(
            """
            SELECT COMMENTS FROM ALL_TAB_COMMENTS
            WHERE OWNER = :schema AND TABLE_NAME = :table_name
              AND COMMENTS IS NOT NULL
            """,
            {'schema': source_schema.upper(), 'table_name': table_name.upper()},
        )
        row = oracle_cursor.fetchone()
        if row and row[0]:
            comment = str(row[0]).replace("'", "''")
            tbl_ident = apply_identifier_case(table_name, id_case)
            qualified = build_qualified_table_name(target_schema, tbl_ident)
            try:
                pg_cursor.execute(f"COMMENT ON TABLE {qualified} IS '{comment}'")
                pg_conn.commit()
                log_list.append(f"已迁移表注释: {table_name}")
            except Exception as e:
                pg_conn.rollback()
                log_list.append(f"迁移表注释失败（可忽略）: {e}")

        # 列级注释
        oracle_cursor.execute(
            """
            SELECT COLUMN_NAME, COMMENTS FROM ALL_COL_COMMENTS
            WHERE OWNER = :schema AND TABLE_NAME = :table_name
              AND COMMENTS IS NOT NULL
            """,
            {'schema': source_schema.upper(), 'table_name': table_name.upper()},
        )
        col_count = 0
        for col_name, comment in oracle_cursor.fetchall():
            if not comment:
                continue
            comment = str(comment).replace("'", "''")
            col_ident = apply_identifier_case(col_name, id_case)
            tbl_ident = apply_identifier_case(table_name, id_case)
            qualified = build_qualified_table_name(target_schema, tbl_ident)
            try:
                pg_cursor.execute(
                    f"COMMENT ON COLUMN {qualified}.{quote_identifier(col_ident)} IS '{comment}'"
                )
                col_count += 1
            except Exception as e:
                pg_conn.rollback()
                log_list.append(f"迁移列注释失败 {col_name}（可忽略）: {e}")
        if col_count:
            pg_conn.commit()
            log_list.append(f"已迁移 {col_count} 个列注释: {table_name}")
    except Exception as e:
        # 注释迁移失败不应影响主流程
        log_list.append(f"注释迁移跳过（不影响数据）: {e}")


def fetch_foreign_keys_for_schema(oracle_cursor, source_schema: str) -> List[dict]:
    """读取 Schema 下全部外键约束（含引用表/列）。"""
    oracle_cursor.execute(
        """
        SELECT fk.CONSTRAINT_NAME, fk.TABLE_NAME,
               fkc.COLUMN_NAME, fkc.POSITION,
               pk.OWNER AS REF_OWNER, pk.TABLE_NAME AS REF_TABLE,
               pkc.COLUMN_NAME AS REF_COLUMN
        FROM ALL_CONSTRAINTS fk
        JOIN ALL_CONS_COLUMNS fkc
          ON fk.OWNER = fkc.OWNER AND fk.CONSTRAINT_NAME = fkc.CONSTRAINT_NAME
        JOIN ALL_CONSTRAINTS pk
          ON fk.R_OWNER = pk.OWNER AND fk.R_CONSTRAINT_NAME = pk.CONSTRAINT_NAME
        JOIN ALL_CONS_COLUMNS pkc
          ON pk.OWNER = pkc.OWNER AND pk.CONSTRAINT_NAME = pkc.CONSTRAINT_NAME
         AND fkc.POSITION = pkc.POSITION
        WHERE fk.OWNER = :schema AND fk.CONSTRAINT_TYPE = 'R' AND fk.STATUS = 'ENABLED'
        ORDER BY fk.TABLE_NAME, fk.CONSTRAINT_NAME, fkc.POSITION
        """,
        {'schema': source_schema.upper()},
    )
    fk_map: Dict[str, dict] = {}
    for row in oracle_cursor.fetchall():
        cname, tbl, col, _pos, ref_owner, ref_tbl, ref_col = row
        key = f'{source_schema.upper()}.{cname}'
        if key not in fk_map:
            fk_map[key] = {
                'name': cname,
                'table': tbl,
                'ref_owner': ref_owner,
                'ref_table': ref_tbl,
                'columns': [],
                'ref_columns': [],
            }
        fk_map[key]['columns'].append(col)
        fk_map[key]['ref_columns'].append(ref_col)
    return list(fk_map.values())


def _map_schema_name(source_schema: str, schema_mappings: List[dict], id_case: str) -> str:
    """Oracle Schema → 目标 Schema 映射。"""
    for m in schema_mappings or []:
        if m.get('source_schema', '').upper() == source_schema.upper():
            return m.get('target_schema') or apply_identifier_case(source_schema, id_case)
    return apply_identifier_case(source_schema, id_case)


def apply_foreign_keys_for_schema(
    oracle_cursor,
    pg_cursor,
    pg_conn,
    source_schema: str,
    target_schema: str,
    log_list: List[str],
    *,
    id_case: str = 'lower',
    schema_mappings: Optional[List[dict]] = None,
) -> int:
    """
    在目标库回放外键约束（需在表结构与数据导入完成后执行）。
    返回成功创建的外键数量。
    """
    fks = fetch_foreign_keys_for_schema(oracle_cursor, source_schema)
    if not fks:
        return 0
    created = 0
    for fk in fks:
        tbl = apply_identifier_case(fk['table'], id_case)
        ref_owner = fk['ref_owner']
        ref_tbl = apply_identifier_case(fk['ref_table'], id_case)
        ref_tgt_schema = _map_schema_name(ref_owner, schema_mappings or [], id_case)
        if ref_owner.upper() == source_schema.upper():
            ref_tgt_schema = target_schema

        child_qualified = build_qualified_table_name(target_schema, tbl)
        parent_qualified = build_qualified_table_name(ref_tgt_schema, ref_tbl)
        child_cols = ', '.join(
            quote_identifier(apply_identifier_case(c, id_case)) for c in fk['columns']
        )
        ref_cols = ', '.join(
            quote_identifier(apply_identifier_case(c, id_case)) for c in fk['ref_columns']
        )
        cname = apply_identifier_case(fk['name'], id_case)
        ddl = (
            f"ALTER TABLE {child_qualified} ADD CONSTRAINT {quote_identifier(cname)} "
            f"FOREIGN KEY ({child_cols}) REFERENCES {parent_qualified} ({ref_cols})"
        )
        try:
            pg_cursor.execute(ddl)
            pg_conn.commit()
            log_list.append(f"已创建外键 {fk['name']} 于表 {fk['table']}")
            created += 1
        except Exception as e:
            pg_conn.rollback()
            log_list.append(f"创建外键 {fk['name']} 失败（可人工补建）: {e}")
    return created


def apply_foreign_keys_batch(
    oracle_cursor,
    pg_cursor,
    pg_conn,
    schema_mappings: List[dict],
    log_list: List[str],
    *,
    id_case: str = 'lower',
) -> int:
    """对多个 Schema 映射批量回放外键。"""
    from .batch_config import get_enable_fk_replay

    if not get_enable_fk_replay():
        log_list.append('【外键回放】已在平台配置中关闭，跳过')
        return 0
    log_list.append('【外键回放】开始创建外键约束…')
    total = 0
    seen: set[str] = set()
    for mapping in schema_mappings or []:
        src = mapping.get('source_schema') or ''
        if not src or src in seen:
            continue
        seen.add(src)
        tgt = mapping.get('target_schema') or apply_identifier_case(src, id_case)
        total += apply_foreign_keys_for_schema(
            oracle_cursor, pg_cursor, pg_conn,
            src, tgt, log_list,
            id_case=id_case, schema_mappings=schema_mappings,
        )
    log_list.append(f'【外键回放】完成，成功 {total} 个外键')
    return total
