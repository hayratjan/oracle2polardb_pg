"""
平台全局配置（单例）：迁移参数、系统参数持久化与读取。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = 'platform_config_singleton'
CACHE_TTL = 30

# 与 batch_config 默认值保持一致
DEFAULT_MIGRATION: Dict[str, Any] = {
    'default_identifier_case': 'lower',
    'default_conflict_strategy': 'error',
    'enable_batch_migration': True,
    'batch_size': 5000,
    'commit_every_batches': 2,
    'progress_save_rows': 10000,
    'parallel_table_workers': 16,
    'copy_row_threshold': 100_000,
    'enable_fk_replay': True,
}

DEFAULT_SYSTEM: Dict[str, Any] = {
    'log_level': 'INFO',
    'max_concurrent_tasks': 5,
    'task_timeout': 3600,
    'enable_auto_retry': False,
    'max_retry_count': 3,
}


def _invalidate_cache() -> None:
    cache.delete(CACHE_KEY)


def get_config_row():
    """获取或创建 PlatformConfig 单例（pk=1）。"""
    from .models import PlatformConfig

    obj, _ = PlatformConfig.objects.get_or_create(pk=1)
    return obj


def get_migration_settings() -> Dict[str, Any]:
    """返回迁移配置扁平字典（供 API / 前端）。"""
    row = get_config_row()
    return {
        'default_identifier_case': row.default_identifier_case,
        'default_conflict_strategy': row.default_conflict_strategy,
        'enable_batch_migration': row.enable_batch_migration,
        'batch_size': row.batch_size,
        'commit_every_batches': row.commit_every_batches,
        'progress_save_rows': row.progress_save_rows,
        'parallel_table_workers': row.parallel_table_workers,
        'copy_row_threshold': row.copy_row_threshold,
        'enable_fk_replay': row.enable_fk_replay,
    }


def get_system_settings() -> Dict[str, Any]:
    """返回系统配置扁平字典。"""
    row = get_config_row()
    return {
        'log_level': row.log_level,
        'max_concurrent_tasks': row.max_concurrent_tasks,
        'task_timeout': row.task_timeout,
        'enable_auto_retry': row.enable_auto_retry,
        'max_retry_count': row.max_retry_count,
    }


def get_migration_runtime() -> Dict[str, int]:
    """迁移引擎运行时参数（batch_config 调用）。"""
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached
    s = get_migration_settings()
    runtime = {
        'fetch_batch_size': max(1, int(s['batch_size'])),
        'commit_every_batches': max(1, int(s['commit_every_batches'])),
        'progress_save_rows': max(1000, int(s['progress_save_rows'])),
        'parallel_table_workers': max(1, int(s['parallel_table_workers'])),
        'copy_row_threshold': max(1000, int(s['copy_row_threshold'])),
        'enable_fk_replay': bool(s.get('enable_fk_replay', True)),
    }
    cache.set(CACHE_KEY, runtime, CACHE_TTL)
    return runtime


def save_migration_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """校验并保存迁移配置，返回归一化后的字典。"""
    row = get_config_row()
    valid_cases = {'lower', 'upper', 'preserve'}
    valid_conflicts = {'error', 'replace', 'skip', 'append', 'truncate'}

    if 'default_identifier_case' in data:
        v = data['default_identifier_case']
        if v in valid_cases:
            row.default_identifier_case = v
    if 'default_conflict_strategy' in data:
        v = data['default_conflict_strategy']
        if v in valid_conflicts:
            row.default_conflict_strategy = v
    if 'enable_batch_migration' in data:
        row.enable_batch_migration = bool(data['enable_batch_migration'])
    if 'batch_size' in data:
        row.batch_size = max(100, min(int(data['batch_size']), 50000))
    if 'commit_every_batches' in data:
        row.commit_every_batches = max(1, min(int(data['commit_every_batches']), 20))
    if 'progress_save_rows' in data:
        row.progress_save_rows = max(1000, int(data['progress_save_rows']))
    if 'parallel_table_workers' in data:
        row.parallel_table_workers = max(1, min(int(data['parallel_table_workers']), 64))
    if 'copy_row_threshold' in data:
        row.copy_row_threshold = max(1000, int(data['copy_row_threshold']))
    if 'enable_fk_replay' in data:
        row.enable_fk_replay = bool(data['enable_fk_replay'])

    row.save()
    _invalidate_cache()
    _apply_log_level()
    return get_migration_settings()


def save_system_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """校验并保存系统配置。"""
    row = get_config_row()
    if 'log_level' in data:
        lvl = str(data['log_level']).upper()
        if lvl in ('DEBUG', 'INFO', 'WARNING', 'ERROR'):
            row.log_level = lvl
    if 'max_concurrent_tasks' in data:
        row.max_concurrent_tasks = max(1, min(int(data['max_concurrent_tasks']), 100))
    if 'task_timeout' in data:
        row.task_timeout = max(60, int(data['task_timeout']))
    if 'enable_auto_retry' in data:
        row.enable_auto_retry = bool(data['enable_auto_retry'])
    if 'max_retry_count' in data:
        row.max_retry_count = max(0, min(int(data['max_retry_count']), 10))
    row.save()
    _apply_log_level()
    return get_system_settings()


def apply_task_creation_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    """创建任务时合并平台默认策略（仅当调用方未显式传入）。"""
    mig = get_migration_settings()
    if not data.get('identifier_case'):
        data['identifier_case'] = mig['default_identifier_case']
    if not data.get('conflict_strategy'):
        data['conflict_strategy'] = mig['default_conflict_strategy']
    return data


def count_running_tasks() -> int:
    """当前 running 状态任务数。"""
    from .models import MigrationTask

    return MigrationTask.objects.filter(status='running').count()


def can_start_new_task() -> tuple[bool, str]:
    """是否允许再启动一个迁移任务（受 max_concurrent_tasks 限制）。"""
    sys_cfg = get_system_settings()
    limit = int(sys_cfg['max_concurrent_tasks'])
    running = count_running_tasks()
    if running >= limit:
        return False, f'已达最大并发任务数 {limit}（当前 {running} 个执行中）'
    return True, ''


def get_celery_status() -> Dict[str, Any]:
    """检测 Celery Broker / Beat 配置状态（供前端提示）。"""
    from django.conf import settings as dj_settings

    broker = (getattr(dj_settings, 'CELERY_BROKER_URL', None) or '').strip()
    beat_installed = 'django_celery_beat' in dj_settings.INSTALLED_APPS
    return {
        'broker_configured': bool(broker),
        'broker_url_hint': 'redis://127.0.0.1:6379/0' if not broker else '(已配置)',
        'beat_app_installed': beat_installed,
        'incremental_requires_celery': True,
        'message': (
            '未配置 CELERY_BROKER_URL：迁移任务将在 Django 进程内执行，定时增量不可用。'
            if not broker
            else '已配置 Celery Broker；请同时启动 Worker 与 Beat 以支持定时增量。'
        ),
    }


def _apply_log_level() -> None:
    """将平台 log_level 应用到根 logger（尽力而为）。"""
    try:
        lvl = get_system_settings()['log_level']
        logging.getLogger().setLevel(getattr(logging, lvl, logging.INFO))
    except Exception:
        pass
