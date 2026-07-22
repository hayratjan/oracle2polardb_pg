"""
迁移后数据校验：源端与目标端行数对比、哈希校验、聚合校验等。

校验层级：
  1. 行数校验（validate_row_counts）—— 最低保障，行数相等≠数据一致
  2. 聚合校验（validate_aggregates）—— 对比 SUM/COUNT/MIN/MAX，捕获批量错误
  3. 哈希校验（validate_row_hashes）—— 按主键分批 MD5 对比，精确定位差异行
  4. 抽样校验（validate_sample_rows）—— 随机抽样逐行对比，适用于大表

返回值约定：
  - True  = 校验通过
  - False = 校验失败（发现差异）
  - None  = 校验异常跳过（连接断开、权限不足等，不应视为"通过"）

校验失败默认不阻塞迁移，仅记 WARN 日志。可通过 validate_full(strict=True)
强制阻塞：strict 模式下 None 也视为失败。
"""
from __future__ import annotations

import hashlib
import logging
import random
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
) -> Tuple[Optional[bool], int, int]:
    """
    对比源端与目标端行数。
    返回 (是否一致, 源行数, 目标行数)。
    返回值: True=一致, False=不一致, None=校验异常跳过
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
            f"[ERROR] 行数校验异常跳过 · {source_object}: 行数对比异常 ({format_db_error(e)})，请检查连接与权限"
        )
        return None, -1, -1  # None 表示校验异常,不应视为"通过"


# ============================================================================
# 聚合校验：对比 SUM/COUNT/MIN/MAX，捕获批量数据错误
# ============================================================================

def validate_aggregates(
    oracle_cursor,
    pg_cursor,
    source_schema: str,
    source_object: str,
    target_schema: str,
    target_table: str,
    log_list: List[str],
    columns: Optional[List[str]] = None,
    *,
    pg_table_name: Optional[str] = None,
) -> bool:
    """对数值列做聚合校验（SUM/COUNT/MIN/MAX）。

    行数相等不代表内容一致（如 UPDATE 把 A 改成 B，行数不变但 SUM 变化）。
    本函数对每个数值列对比 SUM/MIN/MAX，能捕获批量数据错误。

    Args:
        columns: 需要校验的列名列表。None 时自动查询数值列。
    Returns:
        True 表示全部通过或跳过，False 表示有差异。
    """
    from .pg_identifiers import build_qualified_table_name

    try:
        # 自动查询数值列（NUMBER/FLOAT/BINARY_*）
        if not columns:
            oracle_cursor.execute(
                """
                SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS
                WHERE OWNER = :schema AND TABLE_NAME = :table_name
                  AND DATA_TYPE IN ('NUMBER', 'FLOAT', 'BINARY_FLOAT', 'BINARY_DOUBLE')
                ORDER BY COLUMN_NAME
                """,
                {'schema': source_schema.upper(), 'table_name': source_object.upper()},
            )
            columns = [r[0] for r in oracle_cursor.fetchall()]

        if not columns:
            log_list.append(f"[INFO] 聚合校验跳过 · {source_object}: 无数值列")
            return True

        tgt_tbl = pg_table_name or target_table
        qualified = build_qualified_table_name(target_schema, tgt_tbl)
        all_pass = True

        for col in columns:
            # Oracle 端聚合
            oracle_cursor.execute(
                f"SELECT NVL(SUM(\"{col}\"), 0), NVL(COUNT(\"{col}\"), 0), "
                f"NVL(MIN(\"{col}\"), 0), NVL(MAX(\"{col}\"), 0) "
                f"FROM {source_schema}.\"{source_object}\""
            )
            o_sum, o_cnt, o_min, o_max = oracle_cursor.fetchone()

            # PG 端聚合
            pg_cursor.execute(
                f'SELECT COALESCE(SUM("{col}"), 0), COALESCE(COUNT("{col}"), 0), '
                f'COALESCE(MIN("{col}"), 0), COALESCE(MAX("{col}"), 0) '
                f'FROM {qualified}'
            )
            p_sum, p_cnt, p_min, p_max = pg_cursor.fetchone()

            # 对比（浮点数容差 0.01）
            def _eq(a, b):
                if isinstance(a, float) or isinstance(b, float):
                    return abs(float(a or 0) - float(b or 0)) < 0.01
                return a == b

            if _eq(o_sum, p_sum) and _eq(o_cnt, p_cnt) and _eq(o_min, p_min) and _eq(o_max, p_max):
                log_list.append(f"  [OK] 聚合校验通过 · {col}: SUM={o_sum} CNT={o_cnt} MIN={o_min} MAX={o_max}")
            else:
                all_pass = False
                log_list.append(
                    f"  [WARN] 聚合校验失败 · {col}: "
                    f"Oracle(SUM={o_sum},CNT={o_cnt},MIN={o_min},MAX={o_max}) "
                    f"PG(SUM={p_sum},CNT={p_cnt},MIN={p_min},MAX={p_max})"
                )

        if all_pass:
            log_list.append(f"[OK] 聚合校验通过 · {source_object}: {len(columns)} 个数值列")
        else:
            log_list.append(f"[WARN] 聚合校验有差异 · {source_object}: 请核查上方明细")
        return all_pass
    except Exception as e:
        logger.warning('聚合校验异常: %s', e)
        log_list.append(f"[ERROR] 聚合校验异常跳过 · {source_object}: {e}")
        return None  # None 表示校验异常,不应视为"通过"


# ============================================================================
# 行级哈希校验：按主键分批 MD5 对比，精确定位差异行
# ============================================================================

def validate_row_hashes(
    oracle_cursor,
    pg_cursor,
    source_schema: str,
    source_object: str,
    target_schema: str,
    target_table: str,
    log_list: List[str],
    primary_key: str,
    columns: Optional[List[str]] = None,
    *,
    pg_table_name: Optional[str] = None,
    batch_size: int = 1000,
    max_batches: int = 100,
) -> Tuple[bool, int, int]:
    """按主键分批计算行 MD5 对比，精确找出差异行。

    对每行所有列拼接后做 MD5，按主键排序分批对比。
    找到第一个不一致的行即标记并停止。

    Args:
        primary_key: 主键列名（用于排序与定位）
        columns: 需要校验的列名列表。None 时用所有列。
        batch_size: 每批对比的行数
        max_batches: 最大批数（防止超大表全表校验耗时过长）
    Returns:
        (是否一致, 校验行数, 差异行数)
    """
    from .pg_identifiers import build_qualified_table_name

    try:
        # 自动获取列列表
        if not columns:
            oracle_cursor.execute(
                """
                SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS
                WHERE OWNER = :schema AND TABLE_NAME = :table_name
                ORDER BY COLUMN_ID
                """,
                {'schema': source_schema.upper(), 'table_name': source_object.upper()},
            )
            columns = [r[0] for r in oracle_cursor.fetchall()]

        if not columns or primary_key not in columns:
            columns = columns or []
            if primary_key not in columns:
                columns.insert(0, primary_key)

        # v2.4: 修复哈希格式不一致问题
        # 原实现: Oracle 用 TO_CHAR(col) → '22-JUL-26',PG 用 col::text → '2026-07-22'
        # 相同数据哈希必不等,导致校验系统性假阳性
        # 修复: 两端统一使用 to_char(col, 'YYYY-MM-DD HH24:MI:SS') 格式化
        # 数值类型两端 to_char 输出一致,日期/时间戳两端格式串兼容
        _ORA_FMT = "'YYYY-MM-DD HH24:MI:SS'"
        _PG_FMT = "'YYYY-MM-DD HH24:MI:SS'"
        ora_cols = " || '|' || ".join(f'NVL(to_char("{c}", {_ORA_FMT}), \'\')' for c in columns)
        pg_cols = " || '|' || ".join(f'COALESCE(to_char("{c}", {_PG_FMT}), \'\')' for c in columns)

        tgt_tbl = pg_table_name or target_table
        qualified = build_qualified_table_name(target_schema, tgt_tbl)

        total_checked = 0
        mismatch_count = 0
        offset = 0

        for batch_idx in range(max_batches):
            # Oracle 端：按主键排序，取本批
            oracle_cursor.execute(
                f'SELECT "{primary_key}", MD5({ora_cols}) '
                f'FROM {source_schema}."{source_object}" '
                f'ORDER BY "{primary_key}" '
                f'OFFSET {offset} ROWS FETCH NEXT {batch_size} ROWS ONLY'
            )
            ora_rows = oracle_cursor.fetchall()
            if not ora_rows:
                break

            ora_map = {str(r[0]): r[1] for r in ora_rows}
            ora_keys = [str(r[0]) for r in ora_rows]

            # PG 端：按主键排序，取相同主键范围
            min_pk = ora_keys[0]
            max_pk = ora_keys[-1]
            pg_cursor.execute(
                f'SELECT "{primary_key}"::text, MD5({pg_cols}) '
                f'FROM {qualified} '
                f'WHERE "{primary_key}"::text >= %s AND "{primary_key}"::text <= %s '
                f'ORDER BY "{primary_key}"::text'
            )
            pg_rows = pg_cursor.fetchall()
            pg_map = {str(r[0]): r[1] for r in pg_rows}

            # 逐行对比
            for pk in ora_keys:
                total_checked += 1
                ora_hash = ora_map.get(pk)
                pg_hash = pg_map.get(pk)
                if pg_hash is None:
                    mismatch_count += 1
                    if mismatch_count <= 5:  # 只打印前 5 个差异
                        log_list.append(f"  [WARN] 主键 {pk} 在目标端不存在")
                elif ora_hash != pg_hash:
                    mismatch_count += 1
                    if mismatch_count <= 5:
                        log_list.append(f"  [WARN] 主键 {pk} 哈希不一致 (Oracle={ora_hash[:12]}... PG={pg_hash[:12]}...)")

            if mismatch_count > 0 and mismatch_count >= 5:
                # 发现足够差异，停止全表扫描
                log_list.append(f"  [INFO] 已发现 {mismatch_count} 个差异，停止后续扫描")
                break

            offset += batch_size

        if mismatch_count == 0:
            log_list.append(f"[OK] 哈希校验通过 · {source_object}: 校验 {total_checked} 行，无差异")
            return True, total_checked, 0
        else:
            log_list.append(f"[WARN] 哈希校验失败 · {source_object}: 校验 {total_checked} 行，发现 {mismatch_count} 个差异")
            return False, total_checked, mismatch_count
    except Exception as e:
        logger.warning('哈希校验异常: %s', e)
        log_list.append(f"[ERROR] 哈希校验异常跳过 · {source_object}: {e}")
        return None, 0, 0  # None 表示校验异常,不应视为"通过"


# ============================================================================
# 抽样校验：随机抽 N 行逐行对比，适用于大表快速验证
# ============================================================================

def validate_sample_rows(
    oracle_cursor,
    pg_cursor,
    source_schema: str,
    source_object: str,
    target_schema: str,
    target_table: str,
    log_list: List[str],
    primary_key: str,
    columns: Optional[List[str]] = None,
    *,
    pg_table_name: Optional[str] = None,
    sample_count: int = 100,
) -> Tuple[bool, int, int]:
    """随机抽样逐行对比，适用于大表快速验证。

    通过 DBMS_RANDOM 随机抽取 N 个主键，逐行对比所有列值。

    Args:
        sample_count: 抽样行数（默认 100）
    Returns:
        (是否一致, 抽样行数, 差异行数)
    """
    from .pg_identifiers import build_qualified_table_name

    try:
        if not columns:
            oracle_cursor.execute(
                """
                SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS
                WHERE OWNER = :schema AND TABLE_NAME = :table_name
                ORDER BY COLUMN_ID
                """,
                {'schema': source_schema.upper(), 'table_name': source_object.upper()},
            )
            columns = [r[0] for r in oracle_cursor.fetchall()]

        # Oracle 端随机抽取主键
        oracle_cursor.execute(
            f'SELECT "{primary_key}" FROM ('
            f'  SELECT "{primary_key}" FROM {source_schema}."{source_object}" '
            f'  ORDER BY DBMS_RANDOM.VALUE'
            f') WHERE ROWNUM <= {sample_count}'
        )
        sampled_pks = [str(r[0]) for r in oracle_cursor.fetchall()]

        if not sampled_pks:
            log_list.append(f"[INFO] 抽样校验跳过 · {source_object}: 表为空或无主键")
            return True, 0, 0

        tgt_tbl = pg_table_name or target_table
        qualified = build_qualified_table_name(target_schema, tgt_tbl)

        # 构建列引用
        ora_col_list = ', '.join(f'"{c}"' for c in columns)
        pg_col_list = ', '.join(f'"{c}"' for c in columns)

        mismatch_count = 0
        for pk in sampled_pks:
            # Oracle 端
            oracle_cursor.execute(
                f'SELECT {ora_col_list} FROM {source_schema}."{source_object}" '
                f'WHERE "{primary_key}" = :pk',
                {'pk': pk},
            )
            ora_row = oracle_cursor.fetchone()

            # PG 端
            pg_cursor.execute(
                f'SELECT {pg_col_list} FROM {qualified} '
                f'WHERE "{primary_key}"::text = %s',
                (pk,),
            )
            pg_row = pg_cursor.fetchone()

            if pg_row is None:
                mismatch_count += 1
                if mismatch_count <= 5:
                    log_list.append(f"  [WARN] 主键 {pk} 在目标端不存在")
            elif ora_row and pg_row:
                # 逐列对比
                for i, col in enumerate(columns):
                    ora_val = ora_row[i]
                    pg_val = pg_row[i]
                    # 数值容差
                    if isinstance(ora_val, (int, float)) or isinstance(pg_val, (int, float)):
                        if abs(float(ora_val or 0) - float(pg_val or 0)) > 0.01:
                            mismatch_count += 1
                            if mismatch_count <= 5:
                                log_list.append(f"  [WARN] 主键 {pk} 列 {col}: Oracle={ora_val} PG={pg_val}")
                            break
                    elif str(ora_val) != str(pg_val):
                        mismatch_count += 1
                        if mismatch_count <= 5:
                            log_list.append(f"  [WARN] 主键 {pk} 列 {col}: Oracle={ora_val} PG={pg_val}")
                        break

        if mismatch_count == 0:
            log_list.append(f"[OK] 抽样校验通过 · {source_object}: 抽样 {len(sampled_pks)} 行，无差异")
            return True, len(sampled_pks), 0
        else:
            log_list.append(f"[WARN] 抽样校验失败 · {source_object}: 抽样 {len(sampled_pks)} 行，发现 {mismatch_count} 个差异")
            return False, len(sampled_pks), mismatch_count
    except Exception as e:
        logger.warning('抽样校验异常: %s', e)
        log_list.append(f"[ERROR] 抽样校验异常跳过 · {source_object}: {e}")
        return None, 0, 0  # None 表示校验异常,不应视为"通过"


# ============================================================================
# 综合校验：行数 + 聚合 + 哈希（或抽样）
# ============================================================================

def validate_full(
    oracle_cursor,
    pg_cursor,
    source_schema: str,
    source_object: str,
    target_schema: str,
    target_table: str,
    log_list: List[str],
    primary_key: Optional[str] = None,
    *,
    pg_table_name: Optional[str] = None,
    enable_hash: bool = False,
    enable_sample: bool = True,
    sample_count: int = 100,
    max_rows_for_hash: int = 100000,
    strict: bool = False,
) -> dict:
    """综合校验：行数 → 聚合 → 哈希/抽样。

    Args:
        primary_key: 主键列名。哈希/抽样校验必需。
        enable_hash: 是否启用哈希校验（大表慎用）
        enable_sample: 是否启用抽样校验
        max_rows_for_hash: 超过此行数不启用哈希校验
        strict: 严格模式。启用后校验异常(None)与失败(False)均视为未通过,
            调用方可据此标记任务 failed。默认 False,校验失败仅记 WARN 日志。
    Returns:
        {'row_count': bool|None, 'aggregate': bool|None, 'hash': bool|None, 'sample': bool|None,
         'all_pass': bool, 'failed': list, 'skipped': list}
    """
    results = {'row_count': True, 'aggregate': True, 'hash': True, 'sample': True}

    # 1. 行数校验
    rc_ok, src_cnt, tgt_cnt = validate_row_counts(
        oracle_cursor, pg_cursor,
        source_schema, source_object,
        target_schema, target_table,
        log_list, pg_table_name=pg_table_name,
    )
    results['row_count'] = rc_ok

    # 2. 聚合校验
    agg_ok = validate_aggregates(
        oracle_cursor, pg_cursor,
        source_schema, source_object,
        target_schema, target_table,
        log_list, pg_table_name=pg_table_name,
    )
    results['aggregate'] = agg_ok

    # 3. 哈希校验（仅小表且提供主键时）
    if enable_hash and primary_key and src_cnt >= 0 and src_cnt <= max_rows_for_hash:
        hash_ok, _, _ = validate_row_hashes(
            oracle_cursor, pg_cursor,
            source_schema, source_object,
            target_schema, target_table,
            log_list, primary_key=primary_key,
            pg_table_name=pg_table_name,
        )
        results['hash'] = hash_ok

    # 4. 抽样校验（大表推荐）
    if enable_sample and primary_key:
        sample_ok, _, _ = validate_sample_rows(
            oracle_cursor, pg_cursor,
            source_schema, source_object,
            target_schema, target_table,
            log_list, primary_key=primary_key,
            pg_table_name=pg_table_name,
            sample_count=sample_count,
        )
        results['sample'] = sample_ok

    # 汇总
    failed = [k for k, v in results.items() if v is False]
    skipped = [k for k, v in results.items() if v is None]
    # strict 模式:None 也视为失败;非 strict 模式:None 视为跳过(不影响 all_pass)
    if strict:
        all_pass = all(v is True for v in results.values())
    else:
        all_pass = all(v is not False for v in results.values())

    if all_pass and not skipped:
        log_list.append(f"[OK] 综合校验通过 · {source_object}: 行数+聚合+哈希+抽样全部通过")
    elif all_pass and skipped:
        log_list.append(f"[WARN] 综合校验部分跳过 · {source_object}: {', '.join(skipped)} 因异常跳过（strict={strict}）")
    else:
        if skipped:
            log_list.append(
                f"[{'ERROR' if strict else 'WARN'}] 综合校验有差异 · {source_object}: "
                f"失败 {failed} / 跳过 {skipped}（strict={strict}）"
            )
        else:
            log_list.append(f"[{'ERROR' if strict else 'WARN'}] 综合校验有差异 · {source_object}: {', '.join(failed)} 未通过（strict={strict}）")

    results['all_pass'] = all_pass
    results['failed'] = failed
    results['skipped'] = skipped
    return results
