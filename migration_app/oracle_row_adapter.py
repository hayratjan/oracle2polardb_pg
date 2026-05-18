"""
将 cx_Oracle 查询结果中的 LOB 等特殊类型转为 PostgreSQL/psycopg2 可写入的 Python 值。
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# Oracle 二进制类列：LOB 读入后保持 bytes
_BINARY_ORACLE_TYPES = frozenset({
    'BLOB', 'RAW', 'LONG RAW', 'BFILE',
})


def _is_cx_oracle_lob(value: Any) -> bool:
    """判断是否为 cx_Oracle LOB 对象（CLOB/BLOB/NCLOB）。"""
    if value is None:
        return False
    t = type(value)
    if t.__name__ == 'LOB' and (t.__module__ or '').startswith('cx_Oracle'):
        return True
    mod = getattr(t, '__module__', '') or ''
    return mod.startswith('cx_Oracle') and hasattr(value, 'read') and callable(value.read)


def _lob_is_binary(value: Any, oracle_type: Optional[str]) -> bool:
    """根据列类型或 LOB 元数据判断是否为二进制 BLOB。"""
    if oracle_type and oracle_type.upper() in _BINARY_ORACLE_TYPES:
        return True
    try:
        import cx_Oracle
        lob_type = getattr(value, 'type', None)
        if lob_type is not None:
            if hasattr(cx_Oracle, 'DB_TYPE_BLOB') and lob_type == cx_Oracle.DB_TYPE_BLOB:
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
    """
    if value is None:
        return None

    if _is_cx_oracle_lob(value):
        try:
            content = value.read()
        except Exception as e:
            logger.warning('读取 Oracle LOB 失败，将置为 NULL: %s', e)
            return None
        if content is None:
            return None
        if _lob_is_binary(value, oracle_type):
            if isinstance(content, bytes):
                return content
            if isinstance(content, str):
                return content.encode('latin-1')
            return bytes(content)
        # 文本类 LOB
        if isinstance(content, bytes):
            return content.decode('utf-8', errors='replace')
        return str(content)

    if isinstance(value, (datetime, date, Decimal, int, float, str, bytes, bool)):
        return value

    mod = type(value).__module__ or ''
    if mod.startswith('cx_Oracle'):
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
