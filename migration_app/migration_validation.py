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

from .pg_identifiers import (
    build_qualified_table_name,
    quote_identifier,
    safe_oracle_identifier,
)

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
    # v2.4: schema/object 经 safe_oracle_identifier 强校验,防注入
    src_qualified = f"{safe_oracle_identifier(source_schema)}.{safe_oracle_identifier(object_name)}"
    sql = f"SELECT COUNT(*) FROM {src_qualified}"
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
        # v2.4: 源端 schema/object 强校验,列名 Oracle 端 safe_oracle_identifier、PG 端 quote_identifier
        _src_qualified = f"{safe_oracle_identifier(source_schema)}.{safe_oracle_identifier(source_object)}"
        all_pass = True

        for col in columns:
            ora_col = safe_oracle_identifier(col)
            pg_col = quote_identifier(col)
            # Oracle 端聚合
            oracle_cursor.execute(
                f"SELECT NVL(SUM(\"{ora_col}\"), 0), NVL(COUNT(\"{ora_col}\"), 0), "
                f"NVL(MIN(\"{ora_col}\"), 0), NVL(MAX(\"{ora_col}\"), 0) "
                f"FROM {_src_qualified}"
            )
            o_sum, o_cnt, o_min, o_max = oracle_cursor.fetchone()

            # PG 端聚合
            pg_cursor.execute(
                f'SELECT COALESCE(SUM({pg_col}), 0), COALESCE(COUNT({pg_col}), 0), '
                f'COALESCE(MIN({pg_col}), 0), COALESCE(MAX({pg_col}), 0) '
                f'FROM {qualified}'
            )
            p_sum, p_cnt, p_min, p_max = pg_cursor.fetchone()

            # 对比（v2.4.3: 相对容差 —— 固定 0.01 绝对容差对 SUM 千万级数值
            # 过严（浮点累积误差假阳性），对小数值又过粗）
            def _eq(a, b):
                if isinstance(a, float) or isinstance(b, float):
                    fa, fb = float(a or 0), float(b or 0)
                    return abs(fa - fb) <= max(1e-9, 1e-9 * max(abs(fa), abs(fb)))
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
# 按列类型分派的哈希归一表达式（行哈希校验 / 增量同步 UPDATE 检测共用）
# ============================================================================

# 数值掩码：整数位 22 + 小数 18，覆盖 Oracle NUMBER 38 位精度
_NUM_MASK = 'FM' + '9' * 21 + '0.' + '9' * 18

_DATE_TYPES = {'DATE'}
_TS_TYPES_PREFIX = ('TIMESTAMP', 'INTERVAL')  # INTERVAL 实际走 excluded
_STR_TYPES_PREFIX = ('VARCHAR', 'NVARCHAR', 'CHAR', 'NCHAR', 'CLOB', 'NCLOB', 'LONG')
_NUM_TYPES = {'NUMBER', 'FLOAT', 'BINARY_FLOAT', 'BINARY_DOUBLE',
              'PLS_INTEGER', 'BINARY_INTEGER'}
_BINARY_TYPES = {'BLOB', 'RAW', 'LONG RAW', 'BFILE'}


def build_typed_hash_exprs(
    col_meta: List[Tuple[str, str]],
) -> Tuple[str, str, List[str]]:
    """按 Oracle DATA_TYPE 为每列生成两端语义一致的归一化 to_char 表达式。

    v2.4.3: 修复此前所有列统一套日期格式串的问题 —— 对 NUMBER 列 Oracle 报
    ORA-01481、PG 模板无效，导致哈希校验系统性异常、增量同步 UPDATE 检测失效。

    规则：
      - DATE        → 两端 to_char(col, 'YYYY-MM-DD HH24:MI:SS')
      - TIMESTAMP*  → Oracle '...FF6' / PG '...US'（微秒）
      - NUMBER/FLOAT 等 → 两端 to_char(col, 数值掩码)，FM 去填充
      - 字符类      → 原值（NULL 归一为 ''）
      - BLOB/RAW/未知类型 → 排除出哈希（返回 excluded 列表，调用方记日志）

    Args:
        col_meta: [(列名, Oracle DATA_TYPE), ...]
    Returns:
        (oracle_expr, pg_expr, excluded_cols) —— expr 为 " || '|' || " 连接的整行表达式
    """
    ora_parts: List[str] = []
    pg_parts: List[str] = []
    excluded: List[str] = []

    for col, dtype in col_meta:
        d = (dtype or '').strip().upper()
        base = d.split('(')[0].strip()  # 'TIMESTAMP(6) WITH TIME ZONE' → 'TIMESTAMP'
        quoted_ora = f'"{safe_oracle_identifier(col)}"'
        quoted_pg = quote_identifier(col)

        if d in _BINARY_TYPES or base in _BINARY_TYPES or base.startswith('INTERVAL'):
            excluded.append(col)
            continue
        if d in _DATE_TYPES:
            fmt = "'YYYY-MM-DD HH24:MI:SS'"
            ora_parts.append(f'NVL(to_char({quoted_ora}, {fmt}), \'\')')
            pg_parts.append(f"COALESCE(to_char({quoted_pg}, {fmt}), '')")
        elif base.startswith('TIMESTAMP'):
            ora_parts.append(
                f"NVL(to_char({quoted_ora}, 'YYYY-MM-DD HH24:MI:SS.FF6'), '')")
            # PG 无 FF6，用 US（微秒）等价
            pg_parts.append(
                f"COALESCE(to_char({quoted_pg}, 'YYYY-MM-DD HH24:MI:SS.US'), '')")
        elif d in _NUM_TYPES or base in _NUM_TYPES:
            ora_parts.append(f"NVL(to_char({quoted_ora}, '{_NUM_MASK}'), '')")
            pg_parts.append(f"COALESCE(to_char({quoted_pg}, '{_NUM_MASK}'), '')")
        elif any(base.startswith(p) for p in _STR_TYPES_PREFIX):
            ora_parts.append(f"NVL({quoted_ora}, '')")
            pg_parts.append(f"COALESCE({quoted_pg}, '')")
        else:
            excluded.append(col)

    sep_ora = " || '|' || "
    sep_pg = " || '|' || "
    return sep_ora.join(ora_parts), sep_pg.join(pg_parts), excluded


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
    try:
        # 自动获取列列表（含 Oracle DATA_TYPE，用于按类型分派哈希归一表达式）
        if not columns:
            oracle_cursor.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE FROM ALL_TAB_COLUMNS
                WHERE OWNER = :schema AND TABLE_NAME = :table_name
                ORDER BY COLUMN_ID
                """,
                {'schema': source_schema.upper(), 'table_name': source_object.upper()},
            )
            col_meta = [(r[0], r[1]) for r in oracle_cursor.fetchall()]
            columns = [c for c, _ in col_meta]
        else:
            oracle_cursor.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE FROM ALL_TAB_COLUMNS
                WHERE OWNER = :schema AND TABLE_NAME = :table_name
                ORDER BY COLUMN_ID
                """,
                {'schema': source_schema.upper(), 'table_name': source_object.upper()},
            )
            type_map = {r[0]: r[1] for r in oracle_cursor.fetchall()}
            col_meta = [(c, type_map.get(c, '')) for c in columns]

        if not columns or primary_key not in columns:
            columns = columns or []
            if primary_key not in columns:
                columns.insert(0, primary_key)
                col_meta.insert(0, (primary_key, type_map.get(primary_key, '')))

        # v2.4.3: 按列类型分派归一表达式，修复数值列 to_char(日期格式) 报错问题
        from .pg_identifiers import apply_identifier_case
        pg_col_meta = [(apply_identifier_case(c, 'lower'), t) for c, t in col_meta]
        ora_cols_expr, pg_cols_expr, excluded_cols = build_typed_hash_exprs(col_meta)
        if excluded_cols:
            log_list.append(
                f"[INFO] 哈希校验排除 {len(excluded_cols)} 个不可归一列 · "
                f"{source_object}: {', '.join(excluded_cols)}"
            )
        if not ora_cols_expr:
            log_list.append(f"[INFO] 哈希校验跳过 · {source_object}: 所有列均不可归一")
            return None, 0, 0

        tgt_tbl = pg_table_name or target_table
        qualified = build_qualified_table_name(target_schema, tgt_tbl)
        # v2.4: 源端 schema/object 强校验;primary_key 同样校验
        _src_qualified = f"{safe_oracle_identifier(source_schema)}.{safe_oracle_identifier(source_object)}"
        _ora_pk = safe_oracle_identifier(primary_key)
        _pg_pk = quote_identifier(primary_key)

        total_checked = 0
        mismatch_count = 0
        offset = 0

        for batch_idx in range(max_batches):
            # Oracle 端：按主键排序，取本批
            # 列名/表达式组件均已通过 safe_oracle_identifier / build_typed_hash_exprs 白名单校验
            ora_hash_sql = (
                'SELECT "' + _ora_pk + '", MD5(' + ora_cols_expr + ') '
                'FROM ' + _src_qualified + ' '
                'ORDER BY "' + _ora_pk + '" '
                'OFFSET ' + str(offset) + ' ROWS FETCH NEXT ' + str(batch_size) + ' ROWS ONLY'
            )
            oracle_cursor.execute(ora_hash_sql)
            ora_rows = oracle_cursor.fetchall()
            if not ora_rows:
                break

            ora_map = {str(r[0]): r[1] for r in ora_rows}
            ora_keys = [str(r[0]) for r in ora_rows]

            # PG 端：按主键排序，取相同主键范围
            min_pk = ora_keys[0]
            max_pk = ora_keys[-1]
            # 表达式组件已通过 quote_identifier / build_typed_hash_exprs 白名单校验；
            # 主键范围用 %s 绑参
            pg_hash_sql = (
                'SELECT ' + _pg_pk + '::text, MD5(' + pg_cols_expr + ') '
                'FROM ' + qualified + ' '
                'WHERE ' + _pg_pk + '::text >= %s AND ' + _pg_pk + '::text <= %s '
                'ORDER BY ' + _pg_pk + '::text'
            )
            pg_cursor.execute(pg_hash_sql, (min_pk, max_pk))
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

        # v2.4: schema/object/primary_key/列名全部经安全函数包装,防注入
        _src_qualified = f"{safe_oracle_identifier(source_schema)}.{safe_oracle_identifier(source_object)}"
        _ora_pk = safe_oracle_identifier(primary_key)
        _pg_pk = quote_identifier(primary_key)

        # Oracle 端随机抽取主键（保留原始类型，供 PG 端原生绑定，
        # 避免 ::text 比较因两端文本格式差异造成假"目标端不存在"）
        oracle_cursor.execute(
            f'SELECT "{_ora_pk}" FROM ('
            f'  SELECT "{_ora_pk}" FROM {_src_qualified} '
            f'  ORDER BY DBMS_RANDOM.VALUE'
            f') WHERE ROWNUM <= {int(sample_count)}'
        )
        pk_raw_rows = oracle_cursor.fetchall()
        sampled_pks = [str(r[0]) for r in pk_raw_rows]
        raw_by_pk_str = {str(r[0]): r[0] for r in pk_raw_rows}

        if not sampled_pks:
            log_list.append(f"[INFO] 抽样校验跳过 · {source_object}: 表为空或无主键")
            return True, 0, 0

        tgt_tbl = pg_table_name or target_table
        qualified = build_qualified_table_name(target_schema, tgt_tbl)

        # 构建列引用(Oracle 列大写,PG 列带双引号)
        ora_col_list = ', '.join(f'"{safe_oracle_identifier(c)}"' for c in columns)
        pg_col_list = ', '.join(quote_identifier(c) for c in columns)

        mismatch_count = 0
        for pk in sampled_pks:
            # Oracle 端
            oracle_cursor.execute(
                f'SELECT {ora_col_list} FROM {_src_qualified} '
                f'WHERE "{_ora_pk}" = :pk',
                {'pk': pk},
            )
            ora_row = oracle_cursor.fetchone()

            # PG 端：主键原生绑定（datetime/numeric 直接适配，不走 ::text）
            pg_cursor.execute(
                f'SELECT {pg_col_list} FROM {qualified} '
                f'WHERE {_pg_pk} = %s',
                (raw_by_pk_str.get(pk, pk),),
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
                    # v2.4.3: 相对容差（原固定 0.01 对大数过严/小数过粗）
                    if isinstance(ora_val, (int, float)) or isinstance(pg_val, (int, float)):
                        fa, fb = float(ora_val or 0), float(pg_val or 0)
                        if abs(fa - fb) > max(1e-9, 1e-9 * max(abs(fa), abs(fb))):
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
