"""
迁移任务运行时生命周期：本进程内活跃任务登记、孤儿 running 状态修正（异常停止）。
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional, TypeVar

from django.utils import timezone

logger = logging.getLogger(__name__)

_lock = threading.Lock()
# 本 Django/Celery 进程内正在执行的任务 ID
_active_task_ids: set[int] = set()

T = TypeVar('T')

# 写入任务日志的异常停止说明
ABORTED_LOG_MARKER = '【异常停止】'
ABORTED_LOG_MESSAGE = (
    f'{ABORTED_LOG_MARKER}迁移进程已中断，任务未正常结束。'
    '可能原因：服务重启、进程被终止、Worker 崩溃、开发服务器热重载等。'
)


def mark_task_active(task_id: int) -> None:
    """登记任务在本进程内开始执行。"""
    with _lock:
        _active_task_ids.add(int(task_id))


def mark_task_inactive(task_id: int) -> None:
    """任务执行结束（成功/失败/取消）后注销。"""
    with _lock:
        _active_task_ids.discard(int(task_id))


def is_task_active_locally(task_id: int) -> bool:
    """当前进程是否仍有该任务的执行线程/Worker。"""
    with _lock:
        return int(task_id) in _active_task_ids


def run_with_lifecycle(task_id: int, fn: Callable[..., T], *args, **kwargs) -> T:
    """包装迁移入口：自动登记/注销本进程活跃任务。"""
    mark_task_active(task_id)
    try:
        return fn(*args, **kwargs)
    finally:
        mark_task_inactive(task_id)


def _append_aborted_log(task) -> None:
    prev = task.log or ''
    if ABORTED_LOG_MARKER in prev:
        return
    chunk = ('\n' if prev else '') + ABORTED_LOG_MESSAGE
    task.log = prev + chunk


def mark_task_aborted(task, *, reason: str = '') -> bool:
    """
    将任务标记为异常停止。若已不是 running 则不做修改。
    返回是否发生了状态变更。
    """
    if task.status != 'running':
        return False
    task.status = 'aborted'
    task.cancel_requested = False
    if not task.completed_at:
        task.completed_at = timezone.now()
    _append_aborted_log(task)
    if reason:
        task.log = (task.log or '') + f'\n{reason}'
    task.save(update_fields=['status', 'cancel_requested', 'completed_at', 'log'])
    logger.warning('任务 %s 已标记为异常停止', task.id)
    return True


def reconcile_orphan_running_task(task) -> bool:
    """
    数据库状态为 running，但本进程无对应执行线程时，修正为 aborted。
    用于显式 reconcile=1 或完整 status 查询；轻量轮询（light=1）不应调用，以免误杀仍在执行的任务。
    """
    if task.status != 'running':
        return False
    if is_task_active_locally(task.id):
        return False
    return mark_task_aborted(task)


def reconcile_all_orphan_running_on_startup() -> int:
    """
    服务启动时将遗留的 running 任务全部标为异常停止（典型于重启后）。
    返回修正条数。
    """
    from .models import MigrationTask

    qs = MigrationTask.objects.filter(status='running')
    count = 0
    for task in qs:
        if mark_task_aborted(task, reason='【异常停止】检测到服务启动时任务仍处于执行中，已自动标记。'):
            count += 1
    if count:
        logger.warning('启动时已修正 %s 个遗留 running 任务为异常停止', count)
    return count
