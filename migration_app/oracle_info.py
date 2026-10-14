"""Oracle 源库运行指标采集（供"数据库信息"面板使用）。

设计约束：
- 逐项降级：单个动态视图无权限（ORA-00942/01031）只影响该格，面板整体仍可用；
  已记录的降级原因返回给前端 errors 字段。
- 11g 方言：v$sga 的列名是 VALUE（12c 起才叫 CURRENT_SIZE）；不支持
  `fetch first n rows only`，取前 N 行需外层 rownum。
- 每条 SQL 带 /* o2p:marker */ 注释，便于测试路由与线上定位。
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Sequence

_TOP_TABLESPACES = 5

_SQL_VERSION = (
    "select /* o2p:version */ banner from v$version "
    "where banner like 'Oracle%' and rownum = 1"
)
_SQL_INSTANCE = (
    "select /* o2p:instance */ instance_name, host_name, version, status, "
    "database_status, to_char(startup_time, 'YYYY-MM-DD HH24:MI:SS') "
    "from v$instance"
)
_SQL_PING = "select /* o2p:ping */ 1 from dual"
_SQL_SGA = "select /* o2p:sga_components */ name, value from v$sga"
_SQL_SGA_TARGET = "select /* o2p:sga_target */ value from v$parameter where name = 'sga_target'"
_SQL_PGA_TARGET = "select /* o2p:pga_target */ value from v$parameter where name = 'pga_aggregate_target'"
_SQL_PGA_ALLOC = "select /* o2p:pga_alloc */ value from v$pgastat where name = 'total PGA allocated'"
_SQL_DATAFILES = "select /* o2p:datafiles */ count(*), nvl(sum(bytes), 0) from dba_data_files"
_SQL_TS_SIZE = (
    "select /* o2p:ts_size */ tablespace_name, sum(bytes) "
    "from dba_data_files group by tablespace_name"
)
# 已用空间取 dba_segments 而非 dba_free_space：后者在大库上实测 6.7s（且按单个
# 表空间过滤更慢到 9.5s），dba_segments 全表聚合实测 0.84s，两者数值差仅为段头/未用区。
_SQL_TS_USED = (
    "select /* o2p:ts_used */ tablespace_name, sum(bytes) "
    "from dba_segments group by tablespace_name"
)
_SQL_TS_USED_ALL = (
    "select /* o2p:all_segments */ tablespace_name, sum(bytes) "
    "from all_segments group by tablespace_name"
)
_SQL_TS_COUNT = "select /* o2p:ts_count */ count(*) from dba_tablespaces"
_SQL_RESOURCE = (
    "select /* o2p:resource */ to_char(current_utilization), to_char(max_utilization), "
    "to_char(limit_value) from v$resource_limit where resource_name = 'processes'"
)
_SQL_SESSIONS = (
    "select /* o2p:sessions */ count(*), "
    "nvl(sum(case when status = 'ACTIVE' and type = 'USER' then 1 else 0 end), 0), "
    "nvl(sum(case when type = 'BACKGROUND' then 1 else 0 end), 0) from v$session"
)
_SQL_USERS_DBA = "select /* o2p:users */ count(*) from dba_users"
_SQL_USERS_ALL = "select /* o2p:all_users */ count(distinct username) from all_users"
_SQL_TABLES_DBA = "select /* o2p:tables */ count(*) from dba_tables"
_SQL_TABLES_ALL = "select /* o2p:all_tables */ count(*) from all_tables"
_SQL_TABLES_SCHEMA = (
    "select /* o2p:owner_tables */ count(*) from dba_tables where owner = UPPER(:1)"
)
_SQL_DATABASE = "select /* o2p:database */ name from v$database"
_SQL_PDBS = "select /* o2p:pdbs */ count(*) from v$pdbs"

_RELEASE_RE = re.compile(r'Release\s+([\d.]+)')
_CODE_RE = re.compile(r'\b(ORA|DPY|DPI)-\d+', re.I)


def _error_code(exc: BaseException) -> str:
    """提取 ORA-/DPY-/DPI- 错误码作为简短降级原因。"""
    text = str(exc)
    for arg in getattr(exc, 'args', ()):
        text = f'{getattr(arg, "message", None) or text} {text}'
    match = _CODE_RE.search(text)
    if match:
        return match.group(0).upper()
    return exc.__class__.__name__


class _Reader:
    """执行单条查询；失败时记录降级原因，返回 None 而不抛出。"""

    def __init__(self, cursor, errors: Dict[str, str]):
        self.cursor = cursor
        self.errors = errors

    def rows(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
        *,
        error_key: Optional[str] = None,
    ) -> Optional[List[Any]]:
        try:
            if params:
                self.cursor.execute(sql, list(params))
            else:
                self.cursor.execute(sql)
            return list(self.cursor.fetchall())
        except Exception as exc:
            if error_key:
                self.errors[error_key] = _error_code(exc)
            return None

    def scalar(self, sql, params=None, *, error_key=None):
        rows = self.rows(sql, params, error_key=error_key)
        if not rows or not rows[0]:
            return None
        return rows[0][0]


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def collect_database_info(connection, *, schema: Optional[str] = None) -> Dict[str, Any]:
    """在已有连接上采集一版运行指标。调用方负责连接与关闭。

    Args:
        connection: oracledb.Connection
        schema: 若提供，则表数量仅统计该 Schema（全库 dba_tables 在十万级表时可达秒级）
    """
    errors: Dict[str, str] = {}
    cursor = connection.cursor()
    reader = _Reader(cursor, errors)

    # ping：一次最小往返的墙钟耗时（Oracle 无 ICMP 语义，握手后以查询往返衡量）
    started = time.monotonic()
    reader.rows(_SQL_PING)
    ping_ms = int((time.monotonic() - started) * 1000)

    version_out: Dict[str, Any] = {'banner': None, 'release': None}
    banner = reader.scalar(_SQL_VERSION, error_key='version')
    if banner:
        version_out['banner'] = str(banner).strip()
        match = _RELEASE_RE.search(version_out['banner'])
        version_out['release'] = match.group(1) if match else None

    instance_out: Dict[str, Any] = {}
    rows = reader.rows(_SQL_INSTANCE, error_key='instance')
    if rows and rows[0]:
        keys = ('instance_name', 'host_name', 'version', 'status',
                'database_status', 'startup_time')
        instance_out = dict(zip(keys, rows[0]))

    sga_used = None
    comp_rows = reader.rows(_SQL_SGA, error_key='sga_used')
    if comp_rows:
        sga_used = sum(_as_int(r[1]) or 0 for r in comp_rows if r and len(r) > 1)
    if sga_used is None:
        # 退化：拿不到分项时以 sga_target 近似内存规模
        sga_used = _as_int(reader.scalar(_SQL_SGA_TARGET))

    memory = {
        'sga_used_bytes': sga_used,
        'sga_target_bytes': _as_int(reader.scalar(_SQL_SGA_TARGET, error_key='sga_target')),
        'pga_allocated_bytes': _as_int(reader.scalar(_SQL_PGA_ALLOC, error_key='pga_allocated')),
        'pga_target_bytes': _as_int(reader.scalar(_SQL_PGA_TARGET, error_key='pga_target')),
    }

    tablespaces: List[Dict[str, Any]] = []
    size_rows = reader.rows(_SQL_TS_SIZE, error_key='tablespaces')
    used_rows = reader.rows(_SQL_TS_USED, error_key='tablespaces') if size_rows else None
    if size_rows and used_rows is None:
        # dba_segments 需要更宽的字典权限，退到当前用户可见的 all_segments
        used_rows = reader.rows(_SQL_TS_USED_ALL)
    if used_rows:
        used_map = {r[0]: (_as_int(r[1]) or 0) for r in used_rows if r and r[0]}
        for name, size in ((r[0], _as_int(r[1]) or 0) for r in size_rows if r and r[0]):
            used = used_map.get(name, 0)
            tablespaces.append({
                'name': name,
                'size_bytes': size,
                'used_bytes': used,
                'used_pct': round(used / size * 100, 1) if size else None,
            })
        tablespaces.sort(key=lambda t: t['used_bytes'], reverse=True)

    tablespace_count = _as_int(reader.scalar(_SQL_TS_COUNT, error_key='tablespace_count'))
    if tablespace_count is None:
        tablespace_count = len(size_rows) if size_rows else None

    storage = {
        'datafile_count': None,
        'datafile_bytes': None,
        'tablespace_count': tablespace_count,
        'tablespaces': tablespaces[:_TOP_TABLESPACES],
    }
    df_rows = reader.rows(_SQL_DATAFILES, error_key='datafiles')
    if df_rows and df_rows[0]:
        storage['datafile_count'] = _as_int(df_rows[0][0])
        storage['datafile_bytes'] = _as_int(df_rows[0][1])

    sessions = {'total': None, 'active_user': None, 'background': None}
    sess_rows = reader.rows(_SQL_SESSIONS, error_key='sessions')
    if sess_rows and sess_rows[0]:
        total, active, bg = sess_rows[0]
        sessions = {'total': _as_int(total), 'active_user': _as_int(active),
                    'background': _as_int(bg)}

    processes = {'current': None, 'peak': None, 'limit': None}
    res_rows = reader.rows(_SQL_RESOURCE, error_key='processes')
    if res_rows and res_rows[0]:
        cur, peak, limit = res_rows[0]
        processes = {'current': _as_int(cur), 'peak': _as_int(peak), 'limit': _as_int(limit)}

    # 主查询失败即记录降级原因；回退查询成功时保留该原因，前端据此标注数据来源
    users = _as_int(reader.scalar(_SQL_USERS_DBA, error_key='users'))
    if users is None:
        users = _as_int(reader.scalar(_SQL_USERS_ALL, error_key='users'))

    if schema:
        tables = _as_int(reader.scalar(_SQL_TABLES_SCHEMA, params=[schema], error_key='tables'))
    else:
        tables = _as_int(reader.scalar(_SQL_TABLES_DBA, error_key='tables'))
        if tables is None:
            tables = _as_int(reader.scalar(_SQL_TABLES_ALL, error_key='tables'))

    counts = {
        'users': users,
        'tables': tables,
        'database_name': reader.scalar(_SQL_DATABASE, error_key='database_name'),
    }
    if schema:
        counts['schema'] = schema
    # 12c+ 多租户才有的视图；查不到属正常，不计入 errors
    pdb_count = _as_int(reader.scalar(_SQL_PDBS))
    if pdb_count:
        counts['pdb_count'] = pdb_count

    return {
        'ping_ms': ping_ms,
        'version': version_out,
        'instance': instance_out,
        'memory': memory,
        'storage': storage,
        'sessions': sessions,
        'processes': processes,
        'counts': counts,
        'errors': errors,
    }
