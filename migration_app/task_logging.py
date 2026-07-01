"""
任务日志：同步写入 MigrationTask.log 与 MigrationTaskLog 表，并做脱敏。

提供两类日志写入接口：
1. `append_migration_log(task, message, level)` —— 同时写入 task.log 与结构化日志表
2. `build_log_line(...)` / `make_step_log(...)` 等纯函数 —— 在内存 list[str] 中追加
   带级别前缀的日志行（不写库），最后由调用方一次性 '\n'.join(log) 赋给 task.log

内存日志行约定使用统一前缀格式：`[LEVEL] message`，便于前端解析并着色：
  [INFO] / [OK] / [WARN] / [ERROR] / [STEP] / [DATA] / [SQL] / [META]
"""
from __future__ import annotations

from typing import List

from django.db import transaction

from .log_sanitize import redact_sensitive_text
from .models import MigrationTask, MigrationTaskLog

# 单任务内存日志上限，避免 SQLite TextField 过大
_MAX_TASK_LOG_CHARS = 200_000

# 日志级别常量（与 MigrationTaskLog.level 对齐，前端按 level 着色）
LEVEL_INFO = 'INFO'
LEVEL_OK = 'OK'           # 视为 INFO 子类，前端高亮绿色
LEVEL_WARN = 'WARN'
LEVEL_ERROR = 'ERROR'
LEVEL_STEP = 'STEP'       # 阶段性步骤标记
LEVEL_DATA = 'DATA'       # 数据导入相关
LEVEL_SQL = 'SQL'         # SQL DDL/DML 相关
LEVEL_META = 'META'       # 元数据/对象信息


def _prefix(level: str) -> str:
    """规范化日志前缀，例如 `INFO` -> `[INFO]`。"""
    return f'[{(level or LEVEL_INFO).upper()}]'


def build_log_line(level: str, message: str) -> str:
    """
    生成一行带级别前缀的日志文本（不写库）。
    前端通过正则匹配 `[LEVEL]` 来着色与过滤。
    """
    msg = (message or '').strip().replace('\n', '\n    ')  # 多行时缩进续行
    return f'{_prefix(level)} {msg}' if msg else _prefix(level)


def make_step_log(log: List[str], step_name: str, *, total: int | None = None,
                  index: int | None = None) -> None:
    """向内存日志列表追加一个阶段步骤标记行。"""
    if total is not None and index is not None:
        log.append(build_log_line(LEVEL_STEP, f'━━ {step_name} ({index + 1}/{total}) ━━'))
    else:
        log.append(build_log_line(LEVEL_STEP, f'━━ {step_name} ━━'))


def make_info_log(log: List[str], message: str) -> None:
    log.append(build_log_line(LEVEL_INFO, message))


def make_ok_log(log: List[str], message: str) -> None:
    log.append(build_log_line(LEVEL_OK, message))


def make_warn_log(log: List[str], message: str) -> None:
    log.append(build_log_line(LEVEL_WARN, message))


def make_error_log(log: List[str], message: str) -> None:
    log.append(build_log_line(LEVEL_ERROR, message))


def make_data_log(log: List[str], message: str) -> None:
    log.append(build_log_line(LEVEL_DATA, message))


def make_sql_log(log: List[str], message: str) -> None:
    log.append(build_log_line(LEVEL_SQL, message))


def make_meta_log(log: List[str], message: str) -> None:
    log.append(build_log_line(LEVEL_META, message))


def append_migration_log(task: MigrationTask, message: str, level: str = 'INFO') -> None:
    """
    追加一行日志到任务主日志与结构化日志表。
    message 会先经脱敏处理。

    level 接受 INFO/OK/WARN/ERROR/STEP/DATA/SQL/META 七类（兼容旧调用），写入
    MigrationTaskLog.level 时会做规整：OK/STEP/DATA/SQL/META 归并为 INFO，
    WARN/ERROR 原样保留，便于按严重级别过滤。
    """
    safe = redact_sensitive_text(message)
    raw_level = (level or LEVEL_INFO).upper()
    # 库表 level 仅保留语义级别，避免前端展示过多颜色类
    db_level = raw_level if raw_level in ('WARN', 'ERROR', 'INFO') else 'INFO'
    safe_level = db_level[:16]
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

