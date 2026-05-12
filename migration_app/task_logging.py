"""
任务日志：同步写入 MigrationTask.log 与 MigrationTaskLog 表，并做脱敏。
"""
from django.db import transaction
from .log_sanitize import redact_sensitive_text
from .models import MigrationTask, MigrationTaskLog

# 单任务内存日志上限，避免 SQLite TextField 过大
_MAX_TASK_LOG_CHARS = 200_000


def append_migration_log(task: MigrationTask, message: str, level: str = 'INFO') -> None:
    """
    追加一行日志到任务主日志与结构化日志表。
    message 会先经脱敏处理。
    """
    safe = redact_sensitive_text(message)
    safe_level = (level or 'INFO')[:16]
    with transaction.atomic():
        task.refresh_from_db()
        prev = task.log or ''
        chunk = ('\n' if prev else '') + safe
        if len(prev) + len(chunk) > _MAX_TASK_LOG_CHARS:
            trim = len(prev) + len(chunk) - _MAX_TASK_LOG_CHARS
            prev = prev[trim:]
            if not prev.startswith('...'):
                prev = '...(日志已截断)\n' + prev
        task.log = prev + chunk
        task.save(update_fields=['log'])
        MigrationTaskLog.objects.create(
            task=task,
            level=safe_level,
            message=safe,
        )

