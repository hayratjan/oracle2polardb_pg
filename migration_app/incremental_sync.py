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

from .pg_identifiers import quote_identifier as _quote_pg_ident
from .pg_identifiers import safe_oracle_identifier as _safe_oracle_ident


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


def preview_table_diff(task, oracle_cursor, pg_conn, pg_cursor, source_table_name=None) -> dict:
    """v2.4: 只读对比源/目标差异,不执行任何写操作。

    用于「对比预览」API,让用户在同步前了解差异规模(待插入/待删除/共存行数)。
    UPDATE 检测需逐行哈希对比(开销大),此处不执行,仅在同步时做;
    返回 sampled_updates=None,由调用方提示用户。

    Returns:
        dict: 差异统计,含 source_count/target_count/to_insert/to_delete/common/pk_columns 等
    """
    from .pg_identifiers import apply_identifier_case

    source_schema = task.source_schema
    target_schema = task.target_schema
    table_name = (source_table_name or task.source_object or "").strip()
    if not table_name:
        raise ValueError("对比预览需要有效的源表名")

    id_case = getattr(task, 'identifier_case', 'lower') or 'lower'
    pg_table = apply_identifier_case(table_name, id_case)

    # 检查目标表是否存在
    pg_cursor.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
        (target_schema, pg_table),
    )
    target_exists = pg_cursor.fetchone() is not None

    # 源行数
    oracle_cursor.execute(
        f"SELECT COUNT(*) FROM {_safe_oracle_ident(source_schema)}.{_safe_oracle_ident(table_name)}"
    )
    n_ora = int(oracle_cursor.fetchone()[0])

    if not target_exists:
        return {
            'source_schema': source_schema, 'table_name': table_name,
            'target_schema': target_schema, 'pg_table': pg_table,
            'target_exists': False,
            'source_count': n_ora, 'target_count': 0,
            'to_insert': n_ora, 'to_delete': 0, 'common': 0,
            'sampled_updates': None, 'pk_columns': [],
            'note': '目标表不存在,需先执行全量迁移(首次同步将自动建表导数)',
        }

    pg_ident_table = f'{_quote_pg_ident(target_schema)}.{_quote_pg_ident(pg_table)}'
    pg_cursor.execute(f"SELECT COUNT(*) FROM {pg_ident_table}")
    n_pg = int(pg_cursor.fetchone()[0])

    pk_cols = fetch_oracle_pk_columns(oracle_cursor, source_schema, table_name)
    if not pk_cols:
        return {
            'source_schema': source_schema, 'table_name': table_name,
            'target_schema': target_schema, 'pg_table': pg_table,
            'target_exists': True,
            'source_count': n_ora, 'target_count': n_pg,
            'to_insert': None, 'to_delete': None, 'common': None,
            'sampled_updates': None, 'pk_columns': [],
            'note': '源表无主键,无法主键对齐;仅返回行数差,建议改用水位列增量',
        }

    # 行数超限保护(与 run_table_pk_mirror_flow 一致)
    max_rows = int(getattr(task, "sync_max_pkey_rows", None) or 500_000)
    if n_ora > max_rows or n_pg > max_rows:
        return {
            'source_schema': source_schema, 'table_name': table_name,
            'target_schema': target_schema, 'pg_table': pg_table,
            'target_exists': True,
            'source_count': n_ora, 'target_count': n_pg,
            'to_insert': None, 'to_delete': None, 'common': None,
            'sampled_updates': None, 'pk_columns': pk_cols,
            'note': f'行数超过单次上限 {max_rows},请调大 sync_max_pkey_rows 或改用水位列增量',
        }

    # 拉取两端主键做差集
    ora_sel = ", ".join(pk_cols)
    oracle_cursor.execute(
        f"SELECT {ora_sel} FROM {_safe_oracle_ident(source_schema)}.{_safe_oracle_ident(table_name)}"
    )
    oracle_pk_by_norm: dict[Tuple[Any, ...], Tuple[Any, ...]] = {}
    while True:
        batch = oracle_cursor.fetchmany(20000)
        if not batch:
            break
        for row in batch:
            oracle_pk_by_norm[_pk_tuple(row)] = tuple(row)

    pk_cols_lower = [c.lower() for c in pk_cols]
    pg_sel = ", ".join(_quote_pg_ident(c) for c in pk_cols_lower)
    pg_cursor.execute(f"SELECT {pg_sel} FROM {pg_ident_table}")
    pg_pk_by_norm: dict[Tuple[Any, ...], Tuple[Any, ...]] = {}
    while True:
        batch = pg_cursor.fetchmany(20000)
        if not batch:
            break
        for row in batch:
            pg_pk_by_norm[_pk_tuple(row)] = tuple(row)

    ora_keys = set(oracle_pk_by_norm)
    pg_keys = set(pg_pk_by_norm)

    return {
        'source_schema': source_schema, 'table_name': table_name,
        'target_schema': target_schema, 'pg_table': pg_table,
        'target_exists': True,
        'source_count': n_ora, 'target_count': n_pg,
        'to_insert': len(ora_keys - pg_keys),
        'to_delete': len(pg_keys - ora_keys),
        'common': len(ora_keys & pg_keys),
        'sampled_updates': None, 'pk_columns': pk_cols,
        'note': 'UPDATE 检测需逐行哈希对比(开销大),将在同步时执行;此处仅统计主键差集',
    }


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
    # 两端都存在的主键：可能存在 UPDATE 变更，需逐行哈希对比
    common_keys = ora_keys & pg_keys

    log.append(
        f"【主键对齐】待删除 {len(to_delete_norm)} 行，待插入 {len(to_insert_norm)} 行，"
        f"两端共存 {len(common_keys)} 行（需检测 UPDATE）。"
    )

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

    if to_insert_norm:
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

    # ============================================================================
    # UPDATE 检测：对两端都存在的主键，按主键分批做行哈希对比，发现差异行做 UPDATE
    # 修复之前"主键对齐只处理 INSERT/DELETE，漏掉 UPDATE 导致数据静默丢失"的致命缺陷
    # ============================================================================
    if not common_keys:
        log.append("【主键对齐】两端无共存主键，UPDATE 检测跳过。")
        return

    updated_count = _detect_and_apply_updates(
        oracle_cursor=oracle_cursor,
        pg_conn=pg_conn,
        pg_cursor=pg_cursor,
        source_schema=_safe_oracle_ident(source_schema),
        table_name=_safe_oracle_ident(table_name),
        pg_ident_table=pg_ident_table,
        all_cols=all_cols,
        col_names_lower=col_names_lower,
        pk_cols=pk_cols,
        pk_cols_lower=pk_cols_lower,
        common_keys=list(common_keys),
        oracle_pk_by_norm=oracle_pk_by_norm,
        task=task,
        log=log,
    )
    log.append(
        f"【主键对齐】UPDATE 检测完成，共更新 {updated_count} 行（两端共存 {len(common_keys)} 行）。"
    )


def _detect_and_apply_updates(
    *,
    oracle_cursor,
    pg_conn,
    pg_cursor,
    source_schema: str,
    table_name: str,
    pg_ident_table: str,
    all_cols: List[str],
    col_names_lower: List[str],
    pk_cols: List[str],
    pk_cols_lower: List[str],
    common_keys: List[Tuple[Any, ...]],
    oracle_pk_by_norm: dict,
    task,
    log: List[str],
) -> int:
    """对两端都存在的主键，分批做行哈希对比，发现差异行做 UPDATE。

    为避免全表逐行对比耗时过大，采用分批策略：
    1. 每批取 500 个主键，Oracle 端计算 MD5(全列拼接)
    2. PG 端取相同主键范围计算 MD5
    3. 对比不一致的主键，从 Oracle 拉全行数据做 UPDATE
    """
    import hashlib

    if not common_keys:
        return 0

    # v2.4: 修复哈希格式不一致问题
    # 原实现: Oracle TO_CHAR(date) → '22-JUL-26',PG date::text → '2026-07-22'
    # 相同数据哈希必不等,触发无意义 UPDATE
    # 修复: 两端统一使用 to_char(col, 'YYYY-MM-DD HH24:MI:SS') 格式化
    _ORA_FMT = "'YYYY-MM-DD HH24:MI:SS'"
    _PG_FMT = "'YYYY-MM-DD HH24:MI:SS'"
    ora_hash_expr = " || '|' || ".join(
        f"NVL(to_char(\"{c}\", {_ORA_FMT}), '')" for c in all_cols
    )
    pg_hash_expr = " || '|' || ".join(
        f'COALESCE(to_char("{c}", {_PG_FMT}), \'\')' for c in col_names_lower
    )

    batch_size = 500
    max_update_rows = 50000  # 单轮最多更新 5 万行，防止超大表长时间锁表
    updated_count = 0
    skipped_update = 0

    set_clause = ", ".join(
        f'"{c}" = %s' for c in col_names_lower if c not in pk_cols_lower
    )
    where_clause = " AND ".join(
        f'"{c}" = %s' for c in pk_cols_lower
    )
    update_sql = f"UPDATE {pg_ident_table} SET {set_clause} WHERE {where_clause}"

    for i in range(0, len(common_keys), batch_size):
        if updated_count + skipped_update >= max_update_rows * 2:
            log.append(
                f"【主键对齐】UPDATE 检测达到安全上限（{updated_count + skipped_update} 行），停止后续扫描。"
            )
            break

        if task:
            try:
                task.refresh_from_db()
                if task.cancel_requested:
                    log.append("【主键对齐】用户取消，已中止 UPDATE 检测。")
                    break
            except Exception:
                pass

        chunk = common_keys[i : i + batch_size]
        if not chunk:
            break

        # Oracle 端：取这批主键的 (主键, 行哈希)
        if len(pk_cols) == 1:
            binds = {f"k{j}": oracle_pk_by_norm[chunk[j]][0] for j in range(len(chunk))}
            in_list = ", ".join(f":k{j}" for j in range(len(chunk)))
            q = (
                f'SELECT "{pk_cols[0]}", MD5({ora_hash_expr}) '
                f"FROM {source_schema}.{table_name} "
                f"WHERE {pk_cols[0]} IN ({in_list})"
            )
            oracle_cursor.execute(q, binds)
        else:
            or_parts = []
            bind: dict[str, Any] = {}
            bi = 0
            for nk in chunk:
                raw = oracle_pk_by_norm[nk]
                ands = []
                for j, cname in enumerate(pk_cols):
                    key = f"b{bi}"
                    bind[key] = raw[j]
                    ands.append(f'"{cname}" = :{key}')
                    bi += 1
                or_parts.append("(" + " AND ".join(ands) + ")")
            wh = " OR ".join(or_parts)
            pk_sel = ", ".join(f'"{c}"' for c in pk_cols)
            q = (
                f"SELECT {pk_sel}, MD5({ora_hash_expr}) "
                f"FROM {source_schema}.{table_name} WHERE {wh}"
            )
            oracle_cursor.execute(q, bind)

        ora_rows = oracle_cursor.fetchall()
        if not ora_rows:
            continue

        # 构建 Oracle 端 主键 → 哈希 映射
        ora_hash_map: dict[Tuple[Any, ...], str] = {}
        for row in ora_rows:
            pk_vals = tuple(_norm_pk_cell(x) for x in row[: len(pk_cols)])
            hash_val = str(row[-1]) if row[-1] else ""
            ora_hash_map[pk_vals] = hash_val

        # PG 端：取相同主键的 (主键, 行哈希)
        if len(pk_cols) == 1:
            col = _quote_pg_ident(pk_cols_lower[0])
            placeholders = ", ".join(["%s"] * len(chunk))
            pg_q = (
                f"SELECT {col}, MD5({pg_hash_expr}) "
                f"FROM {pg_ident_table} "
                f"WHERE {col} IN ({placeholders})"
            )
            pg_cursor.execute(pg_q, [oracle_pk_by_norm[k][0] for k in chunk])
        else:
            cond_parts = []
            flat: List[Any] = []
            for nk in chunk:
                raw = oracle_pk_by_norm[nk]
                one = " AND ".join(
                    f"{_quote_pg_ident(pk_cols_lower[j])} = %s" for j in range(len(raw))
                )
                cond_parts.append(f"({one})")
                flat.extend(raw)
            pg_sel = ", ".join(_quote_pg_ident(c) for c in pk_cols_lower)
            pg_q = (
                f"SELECT {pg_sel}, MD5({pg_hash_expr}) "
                f"FROM {pg_ident_table} WHERE " + " OR ".join(cond_parts)
            )
            pg_cursor.execute(pg_q, flat)

        pg_rows = pg_cursor.fetchall()
        pg_hash_map: dict[Tuple[Any, ...], str] = {}
        for row in pg_rows:
            pk_vals = tuple(_norm_pk_cell(x) for x in row[: len(pk_cols)])
            hash_val = str(row[-1]) if row[-1] else ""
            pg_hash_map[pk_vals] = hash_val

        # 对比哈希，找出差异主键
        diff_pks: List[Tuple[Any, ...]] = []
        for pk_norm, ora_hash in ora_hash_map.items():
            pg_hash = pg_hash_map.get(pk_norm)
            if pg_hash is None:
                continue  # PG 端不存在该主键（理论上不会，因为 common_keys 已过滤）
            if ora_hash != pg_hash:
                diff_pks.append(pk_norm)

        if not diff_pks:
            continue  # 本批无差异

        # 对差异主键，从 Oracle 拉全行数据做 UPDATE
        if len(pk_cols) == 1:
            binds2 = {f"k{j}": oracle_pk_by_norm[diff_pks[j]][0] for j in range(len(diff_pks))}
            in_list2 = ", ".join(f":k{j}" for j in range(len(diff_pks)))
            q2 = (
                f"SELECT {', '.join(all_cols)} "
                f"FROM {source_schema}.{table_name} "
                f"WHERE {pk_cols[0]} IN ({in_list2})"
            )
            oracle_cursor.execute(q2, binds2)
        else:
            or_parts2 = []
            bind2: dict[str, Any] = {}
            bi2 = 0
            for nk in diff_pks:
                raw = oracle_pk_by_norm[nk]
                ands2 = []
                for j, cname in enumerate(pk_cols):
                    key = f"b{bi2}"
                    bind2[key] = raw[j]
                    ands2.append(f'"{cname}" = :{key}')
                    bi2 += 1
                or_parts2.append("(" + " AND ".join(ands2) + ")")
            wh2 = " OR ".join(or_parts2)
            q2 = (
                f"SELECT {', '.join(all_cols)} "
                f"FROM {source_schema}.{table_name} WHERE {wh2}"
            )
            oracle_cursor.execute(q2, bind2)

        from .oracle_row_adapter import adapt_oracle_rows

        diff_rows = oracle_cursor.fetchall()
        if not diff_rows:
            continue

        adapted = adapt_oracle_rows(diff_rows, column_oracle_types)
        # 列顺序：all_cols（与 SELECT 顺序一致），但 UPDATE 时需排除 PK 列
        non_pk_idx = [i for i, c in enumerate(col_names_lower) if c not in pk_cols_lower]
        pk_idx = [i for i, c in enumerate(col_names_lower) if c in pk_cols_lower]

        update_batch: List[Tuple[Any, ...]] = []
        for row in adapted:
            # SET 子句参数（非主键列）+ WHERE 子句参数（主键列）
            params = tuple(row[i] for i in non_pk_idx) + tuple(row[i] for i in pk_idx)
            update_batch.append(params)

        try:
            pg_cursor.executemany(update_sql, update_batch)
            pg_conn.commit()
            updated_count += len(update_batch)
        except Exception as e:
            pg_conn.rollback()
            log.append(f"【主键对齐】UPDATE 批次失败（{len(update_batch)} 行），已跳过: {e}")
            skipped_update += len(update_batch)

    if skipped_update:
        log.append(f"【主键对齐】UPDATE 检测有 {skipped_update} 行因异常跳过，请人工核查。")
    return updated_count
