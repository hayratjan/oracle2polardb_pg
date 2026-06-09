"""
Oracle 11g → PolarDB/PostgreSQL 主键对齐增量同步（定时由 Celery Beat 触发）。

在单表行数不超过任务配置的 sync_max_pkey_rows 时，拉取两端主键集合做差集：
- 目标侧缺少的主键：从 Oracle 拉全行 INSERT；
- 目标侧多出的主键：在 PolarDB 上 DELETE。
仅支持带主键约束的表；Oracle 为数据权威源。
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, List, Sequence, Tuple


def _safe_oracle_ident(name: str) -> str:
    """校验 Oracle 未加引号标识符（大写字母、数字、下划线）。"""
    import re

    n = (name or "").strip().upper().replace('"', "")
    if not n or not re.match(r"^[A-Z][A-Z0-9_]*$", n):
        raise ValueError(f"非法 Oracle 标识符: {name}")
    return n


def _quote_pg_ident(name: str) -> str:
    """PostgreSQL 双引号标识符。"""
    s = str(name).replace('"', '""')
    return f'"{s}"'


def _norm_pk_cell(value: Any) -> Any:
    """将主键列值规范为可哈希、可跨 Oracle/PG 比较的形式。"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, bytes):
        return value.hex()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return value


def _pk_tuple(row: Sequence[Any]) -> Tuple[Any, ...]:
    return tuple(_norm_pk_cell(x) for x in row)


def fetch_oracle_pk_columns(oracle_cursor, owner: str, table_name: str) -> List[str]:
    """返回 Oracle 表主键列名列表（按约束列顺序，大写）。"""
    own = _safe_oracle_ident(owner)
    tab = _safe_oracle_ident(table_name)
    oracle_cursor.execute(
        """
        SELECT cc.column_name
        FROM all_cons_columns cc
        JOIN all_constraints c
          ON cc.owner = c.owner AND cc.constraint_name = c.constraint_name
        WHERE c.constraint_type = 'P'
          AND c.owner = :o AND c.table_name = :t
        ORDER BY cc.position
        """,
        {"o": own, "t": tab},
    )
    rows = [r[0] for r in oracle_cursor.fetchall()]
    if not rows:
        raise ValueError(
            f"表 {owner}.{table_name} 未定义主键约束，无法使用「主键对齐」增量。"
            "请先在 Oracle 上添加主键，或改用「按水位列」增量。"
        )
    return [_safe_oracle_ident(c) for c in rows]


def run_table_pk_mirror_flow(task, oracle_cursor, pg_conn, pg_cursor, log, source_table_name=None) -> None:
    """
    主键对齐同步入口：目标表不存在时先走全量建表+导数；已存在则只做主键差集增删。

    :param source_table_name: 可选，指定当前处理的 Oracle 表名；多表批量任务时传入，避免改写 task.source_object（
        否则 _migrate_single_table 内 refresh_from_db 会还原库中的单表字段）。
    """
    from .views import _migrate_single_table

    source_schema = task.source_schema
    target_schema = task.target_schema
    table_name = (source_table_name or task.source_object or "").strip()
    if not table_name:
        raise ValueError("主键对齐模式需要有效的源表名")
    from .pg_identifiers import apply_identifier_case
    id_case = getattr(task, 'identifier_case', 'lower') or 'lower'
    pg_table = apply_identifier_case(table_name, id_case)

    pg_cursor.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """,
        (target_schema, pg_table),
    )
    table_exists = pg_cursor.fetchone() is not None

    if not table_exists:
        log.append("【主键对齐】目标表不存在，先执行全量建表与导数（首次）。")
        ok, _rows = _migrate_single_table(
            oracle_cursor,
            pg_conn,
            pg_cursor,
            source_schema,
            target_schema,
            table_name,
            task.conflict_strategy,
            log,
            task=task,
            watermark_column=None,
            watermark_min_exclusive=None,
        )
        if not ok:
            raise RuntimeError(f"【主键对齐】首次全量迁移表 {table_name} 未成功完成")
        return

    pk_cols = fetch_oracle_pk_columns(oracle_cursor, source_schema, table_name)
    pk_cols_lower = [c.lower() for c in pk_cols]

    max_rows = int(getattr(task, "sync_max_pkey_rows", None) or 500_000)
    max_rows = max(1_000, min(10_000_000, max_rows))

    oracle_cursor.execute(
        f"SELECT COUNT(*) FROM {_safe_oracle_ident(source_schema)}.{_safe_oracle_ident(table_name)}"
    )
    n_ora = int(oracle_cursor.fetchone()[0])
    pg_ident_table = f'{_quote_pg_ident(target_schema)}.{_quote_pg_ident(pg_table)}'
    pg_cursor.execute(f"SELECT COUNT(*) FROM {pg_ident_table}")
    n_pg = int(pg_cursor.fetchone()[0])

    if n_ora > max_rows or n_pg > max_rows:
        raise ValueError(
            f"【主键对齐】源表 {n_ora} 行、目标表 {n_pg} 行，超过单次上限 {max_rows} 行。"
            "请调大任务字段 sync_max_pkey_rows，或对大表改用「按水位列」增量。"
        )

    log.append(
        f"【主键对齐】主键列 {', '.join(pk_cols)}；源 {n_ora} 行 / 目标 {n_pg} 行；开始对比…"
    )

    ora_sel = ", ".join(pk_cols)
    oracle_cursor.execute(
        f"SELECT {ora_sel} FROM {_safe_oracle_ident(source_schema)}.{_safe_oracle_ident(table_name)}"
    )
    # 规范化键用于差集；原始主键值用于 SQL 绑定（避免日期/数字类型与库表现不一致）
    oracle_pk_by_norm: dict[Tuple[Any, ...], Tuple[Any, ...]] = {}
    while True:
        batch = oracle_cursor.fetchmany(20000)
        if not batch:
            break
        for row in batch:
            nt = _pk_tuple(row)
            oracle_pk_by_norm[nt] = tuple(row)

    pg_sel = ", ".join(_quote_pg_ident(c) for c in pk_cols_lower)
    pg_cursor.execute(f"SELECT {pg_sel} FROM {pg_ident_table}")
    pg_pk_by_norm: dict[Tuple[Any, ...], Tuple[Any, ...]] = {}
    while True:
        batch = pg_cursor.fetchmany(20000)
        if not batch:
            break
        for row in batch:
            nt = _pk_tuple(row)
            pg_pk_by_norm[nt] = tuple(row)

    ora_keys = set(oracle_pk_by_norm)
    pg_keys = set(pg_pk_by_norm)
    to_delete_norm = pg_keys - ora_keys
    to_insert_norm = ora_keys - pg_keys

    log.append(f"【主键对齐】待删除 {len(to_delete_norm)} 行，待插入 {len(to_insert_norm)} 行。")

    del_chunk = 500
    if to_delete_norm:
        del_list = list(to_delete_norm)
        for i in range(0, len(del_list), del_chunk):
            chunk_norm = del_list[i : i + del_chunk]
            if len(pk_cols) == 1:
                col = _quote_pg_ident(pk_cols_lower[0])
                placeholders = ", ".join(["%s"] * len(chunk_norm))
                sql = f"DELETE FROM {pg_ident_table} WHERE {col} IN ({placeholders})"
                raw_vals = [pg_pk_by_norm[k][0] for k in chunk_norm]
                pg_cursor.execute(sql, raw_vals)
            else:
                cond_parts = []
                flat: List[Any] = []
                for nk in chunk_norm:
                    raw = pg_pk_by_norm[nk]
                    one = " AND ".join(
                        f"{_quote_pg_ident(pk_cols_lower[j])} = %s" for j in range(len(raw))
                    )
                    cond_parts.append(f"({one})")
                    flat.extend(raw)
                sql = f"DELETE FROM {pg_ident_table} WHERE " + " OR ".join(cond_parts)
                pg_cursor.execute(sql, flat)
            pg_conn.commit()

    if not to_insert_norm:
        log.append("【主键对齐】无新增行，同步完成。")
        return

    # 全列顺序与全量迁移一致：ALL_TAB_COLUMNS COLUMN_ID
    oracle_cursor.execute(
        """
        SELECT column_name, data_type FROM all_tab_columns
        WHERE owner = :o AND table_name = :t
        ORDER BY column_id
        """,
        {"o": _safe_oracle_ident(source_schema), "t": _safe_oracle_ident(table_name)},
    )
    col_meta = oracle_cursor.fetchall()
    all_cols = [_safe_oracle_ident(r[0]) for r in col_meta]
    column_oracle_types = [r[1] for r in col_meta]
    col_names_lower = [c.lower() for c in all_cols]
    quoted_cols = ", ".join(_quote_pg_ident(c) for c in col_names_lower)
    placeholders = ", ".join(["%s"] * len(all_cols))
    insert_sql = f"INSERT INTO {pg_ident_table} ({quoted_cols}) VALUES ({placeholders})"

    ins_chunk = 100
    to_insert_list = list(to_insert_norm)
    pk_count = len(pk_cols)

    for i in range(0, len(to_insert_list), ins_chunk):
        if task:
            try:
                task.refresh_from_db()
                if task.cancel_requested:
                    log.append("【主键对齐】用户取消，已中止插入。")
                    break
            except Exception:
                pass

        chunk_norm = to_insert_list[i : i + ins_chunk]
        if pk_count == 1:
            col = pk_cols[0]
            binds = {f"k{j}": oracle_pk_by_norm[chunk_norm[j]][0] for j in range(len(chunk_norm))}
            in_list = ", ".join(f":k{j}" for j in range(len(chunk_norm)))
            q = f"SELECT {', '.join(all_cols)} FROM {_safe_oracle_ident(source_schema)}.{_safe_oracle_ident(table_name)} WHERE {col} IN ({in_list})"
            oracle_cursor.execute(q, binds)
        else:
            or_parts = []
            bind: dict[str, Any] = {}
            bi = 0
            for nk in chunk_norm:
                raw = oracle_pk_by_norm[nk]
                ands = []
                for j, cname in enumerate(pk_cols):
                    key = f"b{bi}"
                    bind[key] = raw[j]
                    ands.append(f"{cname} = :{key}")
                    bi += 1
                or_parts.append("(" + " AND ".join(ands) + ")")
            wh = " OR ".join(or_parts)
            q = f"SELECT {', '.join(all_cols)} FROM {_safe_oracle_ident(source_schema)}.{_safe_oracle_ident(table_name)} WHERE {wh}"
            oracle_cursor.execute(q, bind)

        from .oracle_row_adapter import adapt_oracle_rows

        rows = oracle_cursor.fetchall()
        if rows:
            pg_cursor.executemany(insert_sql, adapt_oracle_rows(rows, column_oracle_types))
            pg_conn.commit()

    log.append(f"【主键对齐】本轮处理插入批次结束（计划插入 {len(to_insert_norm)} 行）。")
