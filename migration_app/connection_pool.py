"""
数据库连接池管理模块

提供 Oracle 和 PostgreSQL 连接池功能，解决频繁新建连接的性能问题。
使用线程安全的连接池实现，支持按 connection_id 缓存池。
"""

import threading
import atexit
import logging
import cx_Oracle
import psycopg2
from psycopg2 import pool as pg_pool
from django.shortcuts import get_object_or_404
from django.conf import settings

from .models import OracleConnection, PostgresConnection
from .credentials import require_plain_connection_password

logger = logging.getLogger(__name__)

# ============================================================================
# 全局连接池字典与线程锁
# ============================================================================
_oracle_pools = {}  # {connection_id: cx_Oracle.SessionPool}
_pg_pools = {}      # {connection_id: psycopg2.pool.ThreadedConnectionPool}

_oracle_pool_lock = threading.Lock()
_pg_pool_lock = threading.Lock()

# 池配置参数
POOL_MIN_CONNECTIONS = 2
POOL_MAX_CONNECTIONS = 10
POOL_INCREMENT = 1
POOL_TIMEOUT = 30  # Oracle SessionPool timeout (seconds)


def get_oracle_pooled_connection(connection_id, *, call_timeout_ms: int = 30000):
    """
    从 Oracle 连接池获取连接。

    Args:
        connection_id: OracleConnection 主键
        call_timeout_ms: 单条 SQL 执行超时（毫秒），默认 30 秒

    Returns:
        cx_Oracle.Connection: 池中的连接对象

    Raises:
        Exception: 连接池创建或获取连接失败时抛出异常
    """
    with _oracle_pool_lock:
        # 检查池是否已存在
        if connection_id not in _oracle_pools:
            logger.info(f"创建 Oracle 连接池: connection_id={connection_id}")
            conn_obj = get_object_or_404(OracleConnection, pk=connection_id)

            # 构建 DSN
            dsn = cx_Oracle.makedsn(
                conn_obj.host,
                conn_obj.port,
                service_name=conn_obj.service_name
            )

            # 获取明文密码
            pwd = require_plain_connection_password(conn_obj.password)

            # 创建 SessionPool
            try:
                session_pool = cx_Oracle.SessionPool(
                    user=conn_obj.username,
                    password=pwd,
                    dsn=dsn,
                    min=POOL_MIN_CONNECTIONS,
                    max=POOL_MAX_CONNECTIONS,
                    increment=POOL_INCREMENT,
                    threaded=True,
                    getmode=cx_Oracle.SPOOL_ATTRVAL_WAIT,
                    timeout=POOL_TIMEOUT
                )
                _oracle_pools[connection_id] = session_pool
                logger.info(
                    f"Oracle 连接池已创建: min={POOL_MIN_CONNECTIONS}, "
                    f"max={POOL_MAX_CONNECTIONS}, increment={POOL_INCREMENT}"
                )
            except Exception as e:
                logger.error(f"创建 Oracle 连接池失败: {e}")
                raise Exception(f"创建 Oracle 连接池失败: {str(e)}")

        # 从池中获取连接
        pool = _oracle_pools[connection_id]

    # 在锁外获取连接，避免死锁
    try:
        connection = pool.acquire()
        # 设置单条 SQL 执行超时
        if call_timeout_ms and hasattr(connection, 'callTimeout'):
            connection.callTimeout = call_timeout_ms
        logger.debug(f"从 Oracle 连接池获取连接成功: connection_id={connection_id}")
        return connection
    except Exception as e:
        logger.error(f"从 Oracle 连接池获取连接失败: {e}")
        raise Exception(f"从 Oracle 连接池获取连接失败: {str(e)}")


def release_oracle_connection(connection_id, connection):
    """
    将 Oracle 连接归还到池中。

    Args:
        connection_id: OracleConnection 主键
        connection: 要归还的连接对象
    """
    try:
        with _oracle_pool_lock:
            if connection_id in _oracle_pools:
                pool = _oracle_pools[connection_id]
                pool.release(connection)
                logger.debug(f"Oracle 连接已归还到池: connection_id={connection_id}")
    except Exception as e:
        logger.warning(f"归还 Oracle 连接失败: {e}")
        # 归还失败时尝试直接关闭
        try:
            connection.close()
        except Exception:
            pass


def get_postgres_pooled_connection(connection_id, database=None, *, connect_timeout: int = 30):
    """
    从 PostgreSQL 连接池获取连接。

    Args:
        connection_id: PostgresConnection 主键
        database: 可选的数据库名（默认使用连接配置中的数据库）
        connect_timeout: 连接超时（秒），默认 30 秒

    Returns:
        psycopg2.connection: 池中的连接对象

    Raises:
        Exception: 连接池创建或获取连接失败时抛出异常
    """
    db_name = database or None
    pool_key = (connection_id, db_name)  # 按 (connection_id, database) 缓存池

    with _pg_pool_lock:
        # 检查池是否已存在
        if pool_key not in _pg_pools:
            logger.info(f"创建 PostgreSQL 连接池: connection_id={connection_id}, database={db_name}")
            conn_obj = get_object_or_404(PostgresConnection, pk=connection_id)

            # 构建连接参数
            db_to_use = db_name if db_name else conn_obj.database
            pwd = require_plain_connection_password(conn_obj.password)

            kwargs = {
                'host': conn_obj.host,
                'port': conn_obj.port,
                'database': db_to_use,
                'user': conn_obj.username,
                'password': pwd,
                'connect_timeout': max(5, int(connect_timeout)),
            }

            # 添加 SSL 模式（如果配置了）
            sslmode = (getattr(conn_obj, 'sslmode', None) or '').strip()
            if sslmode:
                kwargs['sslmode'] = sslmode

            # 创建 ThreadedConnectionPool
            try:
                pg_pool_obj = pg_pool.ThreadedConnectionPool(
                    minconn=POOL_MIN_CONNECTIONS,
                    maxconn=POOL_MAX_CONNECTIONS,
                    **kwargs
                )
                _pg_pools[pool_key] = pg_pool_obj
                logger.info(
                    f"PostgreSQL 连接池已创建: min={POOL_MIN_CONNECTIONS}, "
                    f"max={POOL_MAX_CONNECTIONS}, database={db_to_use}"
                )
            except Exception as e:
                logger.error(f"创建 PostgreSQL 连接池失败: {e}")
                raise Exception(f"创建 PostgreSQL 连接池失败: {str(e)}")

        # 从池中获取连接
        pool = _pg_pools[pool_key]

    # 在锁外获取连接，避免死锁
    try:
        connection = pool.getconn()
        logger.debug(
            f"从 PostgreSQL 连接池获取连接成功: "
            f"connection_id={connection_id}, database={db_to_use}"
        )
        return connection
    except Exception as e:
        logger.error(f"从 PostgreSQL 连接池获取连接失败: {e}")
        raise Exception(f"从 PostgreSQL 连接池获取连接失败: {str(e)}")


def release_postgres_connection(connection_id, connection, database=None):
    """
    将 PostgreSQL 连接归还到池中。

    Args:
        connection_id: PostgresConnection 主键
        connection: 要归还的连接对象
        database: 可选的数据库名
    """
    db_name = database or None
    pool_key = (connection_id, db_name)

    try:
        with _pg_pool_lock:
            if pool_key in _pg_pools:
                pool = _pg_pools[pool_key]
                pool.putconn(connection)
                logger.debug(
                    f"PostgreSQL 连接已归还到池: "
                    f"connection_id={connection_id}, database={db_name}"
                )
    except Exception as e:
        logger.warning(f"归还 PostgreSQL 连接失败: {e}")
        # 归还失败时尝试直接关闭
        try:
            connection.close()
        except Exception:
            pass


def close_all_pools():
    """
    关闭所有连接池，在应用退出时调用。
    """
    logger.info("开始关闭所有数据库连接池...")

    # 关闭 Oracle 连接池
    with _oracle_pool_lock:
        for connection_id, pool in list(_oracle_pools.items()):
            try:
                pool.close()
                logger.info(f"Oracle 连接池已关闭: connection_id={connection_id}")
            except Exception as e:
                logger.warning(f"关闭 Oracle 连接池失败 (connection_id={connection_id}): {e}")
        _oracle_pools.clear()

    # 关闭 PostgreSQL 连接池
    with _pg_pool_lock:
        for pool_key, pool in list(_pg_pools.items()):
            try:
                pool.closeall()
                logger.info(f"PostgreSQL 连接池已关闭: pool_key={pool_key}")
            except Exception as e:
                logger.warning(f"关闭 PostgreSQL 连接池失败 (pool_key={pool_key}): {e}")
        _pg_pools.clear()

    logger.info("所有数据库连接池已关闭")


def get_pool_stats():
    """
    获取连接池统计信息（用于监控）。

    Returns:
        dict: 包含 Oracle 和 PostgreSQL 连接池状态的字典
    """
    stats = {
        'oracle': {},
        'postgres': {}
    }

    with _oracle_pool_lock:
        for conn_id, pool in _oracle_pools.items():
            try:
                stats['oracle'][conn_id] = {
                    'busy': pool.busy,
                    'open': pool.open,
                    'max': pool.max,
                }
            except Exception as e:
                logger.warning(f"获取 Oracle 池统计失败: {e}")

    with _pg_pool_lock:
        for pool_key, pool in _pg_pools.items():
            try:
                # psycopg2 的池没有直接的 busy/open 统计，需估算
                stats['postgres'][pool_key] = {
                    'min': POOL_MIN_CONNECTIONS,
                    'max': POOL_MAX_CONNECTIONS,
                    'pools_count': len(_pg_pools),
                }
            except Exception as e:
                logger.warning(f"获取 PostgreSQL 池统计失败: {e}")

    return stats


# ============================================================================
# 注册应用退出时的清理函数
# ============================================================================
atexit.register(close_all_pools)


# ============================================================================
# 上下文管理器（简化使用）
# ============================================================================
class OraclePooledConnection:
    """
    Oracle 连接池上下文管理器，自动归还连接。

    使用示例:
        with OraclePooledConnection(connection_id) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
    """
    def __init__(self, connection_id, *, call_timeout_ms=30000):
        self.connection_id = connection_id
        self.call_timeout_ms = call_timeout_ms
        self.connection = None

    def __enter__(self):
        self.connection = get_oracle_pooled_connection(
            self.connection_id,
            call_timeout_ms=self.call_timeout_ms
        )
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            release_oracle_connection(self.connection_id, self.connection)
        return False  # 不抑制异常


class PostgresPooledConnection:
    """
    PostgreSQL 连接池上下文管理器，自动归还连接。

    使用示例:
        with PostgresPooledConnection(connection_id, database='mydb') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
    """
    def __init__(self, connection_id, database=None, *, connect_timeout=30):
        self.connection_id = connection_id
        self.database = database
        self.connect_timeout = connect_timeout
        self.connection = None

    def __enter__(self):
        self.connection = get_postgres_pooled_connection(
            self.connection_id,
            database=self.database,
            connect_timeout=self.connect_timeout
        )
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            release_postgres_connection(
                self.connection_id,
                self.connection,
                database=self.database
            )
        return False  # 不抑制异常


# ============================================================================
# 连接代理类（用于兼容原有代码的 close() 调用）
# ============================================================================
class OracleConnectionProxy:
    """
    Oracle 连接代理类，拦截 close() 调用并归还连接到池。

    用于兼容现有代码中使用 connection.close() 的场景，
    将 close() 转换为归还到池而不是真正关闭连接。
    """
    def __init__(self, connection, connection_id):
        self._connection = connection
        self._connection_id = connection_id
        self._released = False

    def __getattr__(self, name):
        """代理所有其他属性和方法到真实连接对象"""
        return getattr(self._connection, name)

    def close(self):
        """拦截 close() 调用，归还连接到池"""
        if not self._released:
            release_oracle_connection(self._connection_id, self._connection)
            self._released = True

    def __del__(self):
        """析构时自动归还连接（防止泄漏）"""
        if not self._released:
            try:
                release_oracle_connection(self._connection_id, self._connection)
                self._released = True
            except Exception:
                pass


class PostgresConnectionProxy:
    """
    PostgreSQL 连接代理类，拦截 close() 调用并归还连接到池。

    用于兼容现有代码中使用 connection.close() 的场景，
    将 close() 转换为归还到池而不是真正关闭连接。
    """
    def __init__(self, connection, connection_id, database=None):
        self._connection = connection
        self._connection_id = connection_id
        self._database = database
        self._released = False

    def __getattr__(self, name):
        """代理所有其他属性和方法到真实连接对象"""
        return getattr(self._connection, name)

    def close(self):
        """拦截 close() 调用，归还连接到池"""
        if not self._released:
            release_postgres_connection(
                self._connection_id,
                self._connection,
                database=self._database
            )
            self._released = True

    def __del__(self):
        """析构时自动归还连接（防止泄漏）"""
        if not self._released:
            try:
                release_postgres_connection(
                    self._connection_id,
                    self._connection,
                    database=self._database
                )
                self._released = True
            except Exception:
                pass