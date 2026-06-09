"""
迁移过程异常分类、连接安全关闭与错误消息脱敏。
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 可重试的瞬断错误关键词（Oracle / PostgreSQL）
_RETRYABLE_PATTERNS = (
    r'ORA-03113', r'ORA-03114', r'ORA-12170', r'ORA-12541', r'ORA-12543',
    r'connection.*closed', r'connection.*lost', r'connection.*reset',
    r'timeout', r'timed out', r'could not connect', r'connection refused',
    r'server closed the connection', r'broken pipe', r'network',
)


class MigrationError(Exception):
    """迁移业务异常基类"""


class MigrationValidationError(MigrationError):
    """行数校验或数据一致性校验失败"""


class MigrationCancelledError(MigrationError):
    """用户取消迁移"""


class MigrationDataError(MigrationError):
    """数据写入失败（约束、类型、网络等）"""


def format_db_error(exc: BaseException, *, max_len: int = 500) -> str:
    """将数据库异常转为用户可读且脱敏的简短消息。"""
    raw = str(exc).strip() or exc.__class__.__name__
    # 隐藏密码等敏感片段
    raw = re.sub(r'(password\s*[=:]\s*)\S+', r'\1***', raw, flags=re.I)
    raw = re.sub(r'PWD\s*=\s*\S+', 'PWD=***', raw, flags=re.I)
    if len(raw) > max_len:
        raw = raw[: max_len - 3] + '...'
    return raw


def is_transient_db_error(exc: BaseException) -> bool:
    """判断是否为可重试的瞬断类数据库错误。"""
    text = f'{exc.__class__.__name__} {exc}'.lower()
    return any(re.search(p, text, re.I) for p in _RETRYABLE_PATTERNS)


def safe_close_db_resources(*resources: Any) -> None:
    """安全关闭 cursor / connection，忽略关闭时的次级异常。"""
    for obj in resources:
        if obj is None:
            continue
        try:
            obj.close()
        except Exception as close_err:
            logger.debug('关闭数据库资源时忽略异常: %s', close_err)


def rollback_quietly(pg_conn, *, log_list: Optional[list] = None) -> None:
    """回滚 PostgreSQL 事务，失败时仅记日志。"""
    if pg_conn is None:
        return
    try:
        pg_conn.rollback()
    except Exception as rb_err:
        msg = f'回滚事务失败: {format_db_error(rb_err)}'
        logger.warning(msg)
        if log_list is not None:
            log_list.append(msg)
