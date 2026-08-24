"""
将 oracledb 查询结果中的 LOB 等特殊类型转为 PostgreSQL/psycopg2 可写入的 Python 值。
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from .migration_errors import MigrationDataError

logger = logging.getLogger(__name__)

# LOB 读取/解码失败策略：strict=抛错中止（默认，防静默数据丢失）；warn=旧旧行为（置 NULL/替换字符）
LOB_ERROR_POLICY = 'strict'

# Oracle 二进制类列：LOB 读入后保持 bytes
_BINARY_ORACLE_TYPES = frozenset({
    'BLOB', 'RAW', 'LONG RAW', 'BFILE',
})


def _is_oracledb_lob(value: Any) -> bool:
    """判断是否为 oracledb LOB 对象（CLOB/BLOB/NCLOB）。"""
    if value is None:
        return False
    t = type(value)
    # v2.5: cx_Oracle → oracledb,兼容两者(过渡期可能混用)
    if t.__name__ == 'LOB' and ((t.__module__ or '').startswith('oracledb') or (t.__module__ or '').startswith('cx_Oracle')):
        return True
    mod = getattr(t, '__module__', '') or ''
    return (mod.startswith('oracledb') or mod.startswith('cx_Oracle')) and hasattr(value, 'read') and callable(value.read)

# 向后兼容:保留旧函数名
_is_cx_oracle_lob = _is_oracledb_lob


def _lob_is_binary(value: Any, oracle_type: Optional[str]) -> bool:
    """根据列类型或 LOB 元数据判断是否为二进制 BLOB。"""
    if oracle_type and oracle_type.upper() in _BINARY_ORACLE_TYPES:
        return True
    try:
        import oracledb
        lob_type = getattr(value, 'type', None)
        if lob_type is not None:
            if hasattr(oracledb, 'DB_TYPE_BLOB') and lob_type == oracledb.DB_TYPE_BLOB:
                return True
            name = getattr(lob_type, 'name', str(lob_type))
            if 'BLOB' in str(name).upper():
                return True
    except Exception:
        pass
    return False


def adapt_oracle_value_for_postgres(value: Any, oracle_type: Optional[str] = None) -> Any:
    """
    单单元格：LOB 读入内存；BLOB 保持 bytes，CLOB/NCLOB 转为 str。

    v2.4.3: LOB 读取失败不再静默置 NULL —— 该行为会写入内容为 NULL 的行，
    行数校验照样通过，数据损坏完全不可见。现在默认抛 MigrationDataError
    中止迁移；确需容错的场景可将 LOB_ERROR_POLICY 置为 'warn' 恢复旧行为。
    """
    if value is None:
        return None

    if _is_oracledb_lob(value):
        try:
            content = value.read()
        except Exception as e:
            if LOB_ERROR_POLICY == 'warn':
                logger.warning('读取 Oracle LOB 失败，已置为 NULL（warn 策略）: %s', e)
                return None
            raise MigrationDataError(f'读取 Oracle LOB 失败（列类型 {oracle_type}）: {e}') from e
        if content is None:
            return None
        if _lob_is_binary(value, oracle_type):
            if isinstance(content, bytes):
                return content
            if isinstance(content, str):
                return content.encode('latin-1')
            return bytes(content)
        # 文本类 LOB：解码失败同样按策略处理（不再 errors='replace' 静默替换字符）
        if isinstance(content, bytes):
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError as e:
                if LOB_ERROR_POLICY == 'warn':
                    logger.warning('CLOB UTF-8 解码失败，已替换损坏字符（warn 策略）: %s', e)
                    return content.decode('utf-8', errors='replace')
                raise MigrationDataError(
                    f'CLOB UTF-8 解码失败（列类型 {oracle_type}），'
                    f'请检查源库字符集配置: {e}'
                ) from e
        return str(content)

    if isinstance(value, (datetime, date, Decimal, int, float, str, bytes, bool)):
        return value

    mod = type(value).__module__ or ''
    if mod.startswith('oracledb') or mod.startswith('cx_Oracle'):
        try:
            if hasattr(value, 'read') and callable(value.read):
                return adapt_oracle_value_for_postgres(value, oracle_type)
        except Exception:
            pass
        return str(value)

    return value


def adapt_oracle_rows(
    rows: Iterable[Sequence[Any]],
    column_oracle_types: Optional[Sequence[str]] = None,
) -> List[Tuple[Any, ...]]:
    """批量转换 fetchmany/fetchall 得到的行。"""
    types = list(column_oracle_types) if column_oracle_types else []
    out: List[Tuple[Any, ...]] = []
    for row in rows:
        adapted = []
        for i, cell in enumerate(row):
            ot = types[i] if i < len(types) else None
            adapted.append(adapt_oracle_value_for_postgres(cell, ot))
        out.append(tuple(adapted))
    return out
