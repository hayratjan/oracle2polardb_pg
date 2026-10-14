"""PolarDB-PG 目标库运行指标采集（供"数据库信息"面板使用）。

设计约束（与 Oracle 侧 oracle_info.py 同形状，但有三点 PostgreSQL 特有差异）：
- 失败必回滚：psycopg2 里一条语句报错后事务进入 aborted 状态，不回滚会让同一
  连接上的后续查询全部失败，因此降级不能只吞异常。
- 版本自适应：pg_shmem_allocations 的分配列在 PolarDB 是 allocated_size，社区版
  是 allocated_bytes；先查 pg_attribute 拿到实际列名，再按白名单拼进求和语句。
- 口径标注：PG 的系统目录不跨库，表/角色/Schema 数量只统计当前连接的数据库，
  所以返回值带 database_name，前端据此标注。
- 每条 SQL 带 /* o2p:marker */ 注释，便于测试路由与线上定位。
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Sequence

from .migration_errors import rollback_quietly

# 面板为只读探测：单条查询实测均 ≤250ms，5s 上限足够兜住异常，
# 又不至于让十几个探测点串起来拖死 worker。
STATEMENT_TIMEOUT_MS = 5_000

_TOP_DATABASES = 5

_SQL_PING = "select /* o2p:ping */ 1"
_SQL_VERSION = "select /* o2p:pgver */ version()"
# 社区版 PostgreSQL 没有该函数，查不到属预期缺失，不计入 errors
_SQL_POLAR_VERSION = "select /* o2p:polarver */ polar_version()"
_SQL_INSTANCE = (
    "select /* o2p:inst */ current_database(), "
    "to_char(pg_postmaster_start_time(), 'YYYY-MM-DD HH24:MI:SS'), "
    "extract(epoch from now() - pg_postmaster_start_time())"
)
_SQL_SETTINGS = (
    "select /* o2p:settings */ name, setting, unit from pg_settings "
    "where name in ('shared_buffers', 'work_mem', 'effective_cache_size', "
    "'max_connections', 'superuser_reserved_connections')"
)
_SQL_COUNTS = (
    "select /* o2p:counts */ "
    "(select count(*) from pg_database), "
    "(select count(*) from pg_roles), "
    r"(select count(*) from pg_roles where not rolsuper and rolname not like 'pg\_%'), "
    r"(select count(*) from pg_namespace "
    r"where nspname not like 'pg\_%' and nspname <> 'information_schema'), "
    "(select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace "
    r"where c.relkind = 'r' and n.nspname not in ('pg_catalog', 'information_schema') "
    r"and n.nspname not like 'pg\_toast%')"
)
# 排除自身后端：面板连接会把"当前会话数"多算 1
_SQL_SESSIONS = (
    "select /* o2p:sessions */ count(*), "
    "count(*) filter (where state = 'active'), "
    "count(*) filter (where state = 'idle') "
    "from pg_stat_activity "
    "where pid <> pg_backend_pid() and backend_type = 'client backend'"
)
_SQL_DB_SIZE = "select /* o2p:dbsize */ pg_database_size(current_database())"
# pg_database_size 对无权限的库会报错并中止事务；模板库与禁止连接的库先排除
_SQL_DB_LIST = (
    "select /* o2p:dblist */ datname, pg_database_size(datname) from pg_database "
    "where datallowconn and not datistemplate"
)
_SQL_SHMEM_COLUMN = (
    "select /* o2p:shmemcol */ attname from pg_attribute "
    "where attrelid = 'pg_shmem_allocations'::regclass "
    "and attname in ('allocated_bytes', 'allocated_size') "
    "order by attnum limit 1"
)
_SHMEM_COLUMNS = ('allocated_bytes', 'allocated_size')
_SQL_SHMEM_SUM = (
    "select /* o2p:shmemsum */ coalesce(sum({column}), 0) from pg_shmem_allocations"
)

_SERVER_VERSION_RE = re.compile(r'PostgreSQL\s+([\d.]+)')
_POLAR_VERSION_RE = re.compile(r'PolarDB\s+([\d.]+)')
# pg_settings 的内存类 GUC 以块或字节为单位返回，需按 unit 换算
_UNIT_FACTOR = {
    'B': 1, 'kB': 1024, '8kB': 8192, '16kB': 16384, '32kB': 32768,
    '64kB': 65536, 'MB': 1048576, 'GB': 1073741824, 'TB': 1099511627776,
}


def _error_reason(exc: BaseException) -> str:
    """降级原因取 SQLSTATE（如 42501 权限不足），拿不到则退化为异常类名。"""
    pgcode = getattr(exc, 'pgcode', None)
    if pgcode:
        return f'PG-{pgcode}'
    return exc.__class__.__name__


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class _Reader:
    """执行单条查询；失败时回滚并记录降级原因，返回 None 而不抛出。"""

    def __init__(self, connection, errors: Dict[str, str]):
        self.connection = connection
        self.cursor = connection.cursor()
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
            # 不回滚的话，同一连接上的后续查询会全部撞上
            # "current transaction is aborted"
            rollback_quietly(self.connection)
            if error_key:
                self.errors[error_key] = _error_reason(exc)
            return None

    def scalar(self, sql, params=None, *, error_key=None):
        rows = self.rows(sql, params, error_key=error_key)
        if not rows or not rows[0]:
            return None
        return rows[0][0]


def _setting_bytes(value: Any, unit: Any) -> Optional[int]:
    number = _as_int(value)
    if number is None:
        return None
    return number * _UNIT_FACTOR.get(unit, 1)


def collect_database_info(connection) -> Dict[str, Any]:
    """在已有连接上采集一版运行指标。调用方负责连接、语句超时与关闭。

    Args:
        connection: psycopg2.connection（或池代理）
    """
    errors: Dict[str, str] = {}
    reader = _Reader(connection, errors)

    # ping：一次最小往返的墙钟耗时（池命中时接近 0）
    started = time.monotonic()
    reader.rows(_SQL_PING)
    ping_ms = int((time.monotonic() - started) * 1000)

    banner = reader.scalar(_SQL_VERSION, error_key='version')
    version_out: Dict[str, Any] = {'banner': None, 'server_version': None,
                                   'polar_version': None}
    if banner:
        version_out['banner'] = str(banner).strip()
        match = _SERVER_VERSION_RE.search(version_out['banner'])
        version_out['server_version'] = match.group(1) if match else None
    polar = reader.scalar(_SQL_POLAR_VERSION)
    if not polar:
        # 线上实测：PolarDB 17 并不一定提供 polar_version()，但 version() 的
        # banner 里有 "(PolarDB 17.9.1.0 build ...)"，据此回退解析。
        polar = _POLAR_VERSION_RE.search(version_out['banner'] or '')
        polar = polar.group(1) if polar else None
    else:
        polar = str(polar).strip()
    if polar:
        version_out['polar_version'] = polar

    instance_out: Dict[str, Any] = {}
    rows = reader.rows(_SQL_INSTANCE, error_key='instance')
    if rows and rows[0]:
        instance_out = dict(zip(
            ('database_name', 'start_time', 'uptime_seconds'), rows[0]))
        instance_out['uptime_seconds'] = _as_int(instance_out['uptime_seconds'])

    settings: Dict[str, tuple] = {}
    for row in reader.rows(_SQL_SETTINGS, error_key='settings') or []:
        if row and row[0]:
            settings[row[0]] = (row[1] if len(row) > 1 else None,
                                row[2] if len(row) > 2 else None)

    shmem_allocated = None
    column = reader.scalar(_SQL_SHMEM_COLUMN)
    if column in _SHMEM_COLUMNS:
        # 列名来自白名单常量，不做字符串拼接注入
        shmem_allocated = _as_int(reader.scalar(
            _SQL_SHMEM_SUM.format(column=column), error_key='memory.shmem_allocated'))

    memory = {
        'shared_buffers_bytes': _setting_bytes(*settings.get('shared_buffers', (None, None))),
        'work_mem_bytes': _setting_bytes(*settings.get('work_mem', (None, None))),
        'effective_cache_size_bytes': _setting_bytes(
            *settings.get('effective_cache_size', (None, None))),
        'shmem_allocated_bytes': shmem_allocated,
    }

    sessions = {'total': None, 'active': None, 'idle': None,
                'max': _as_int(settings.get('max_connections', (None, None))[0]),
                'superuser_reserved': _as_int(
                    settings.get('superuser_reserved_connections', (None, None))[0])}
    sess_rows = reader.rows(_SQL_SESSIONS, error_key='sessions')
    if sess_rows and sess_rows[0]:
        total, active, idle = sess_rows[0]
        sessions.update({'total': _as_int(total), 'active': _as_int(active),
                         'idle': _as_int(idle)})

    counts = {'database_name': instance_out.get('database_name')}
    count_rows = reader.rows(_SQL_COUNTS, error_key='counts')
    if count_rows and count_rows[0]:
        counts.update(dict(zip(
            ('databases', 'roles', 'non_system_roles', 'schemas', 'tables'),
            (_as_int(v) for v in count_rows[0]))))

    storage: Dict[str, Any] = {
        'current_database_bytes': _as_int(
            reader.scalar(_SQL_DB_SIZE, error_key='storage.current_database_bytes')),
        'instance_total_bytes': None,
        'top_databases': [],
    }
    db_rows = reader.rows(_SQL_DB_LIST, error_key='storage.top_databases')
    if db_rows:
        sized = [(_as_int(size) or 0, name) for name, size in db_rows
                 if name and len(name) > 0]
        storage['instance_total_bytes'] = sum(size for size, _ in sized)
        # 服务端无序返回，占用降序在采集端排：面板只展示 Top 5
        storage['top_databases'] = [
            {'name': name, 'size_bytes': size}
            for size, name in sorted(sized, reverse=True)[:_TOP_DATABASES]
        ]

    return {
        'ping_ms': ping_ms,
        'version': version_out,
        'instance': instance_out,
        'memory': memory,
        'sessions': sessions,
        'counts': counts,
        'storage': storage,
        'errors': errors,
    }


def apply_statement_timeout(connection, timeout_ms: int = STATEMENT_TIMEOUT_MS) -> None:
    """设置会话级语句超时；只接受整数毫秒，不做参数绑定以便审计留痕。"""
    connection.cursor().execute(f"set statement_timeout = {int(timeout_ms)}")


def clear_statement_timeout(connection) -> None:
    """撤销会话级超时。池连接会被其他迁移任务复用，残留超时会让大表批量写入
    在半途被杀，因此必须在归还前执行。"""
    if connection is None:
        return
    try:
        connection.cursor().execute("reset statement_timeout")
    except Exception as exc:
        rollback_quietly(connection)
        raise
