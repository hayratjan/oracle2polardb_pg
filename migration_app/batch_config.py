"""
表数据迁移分批参数（Oracle 读取 ↔ PostgreSQL/PolarDB 写入）。
优先读取 PlatformConfig 持久化配置，无 DB 时回退默认值。
"""
from __future__ import annotations

# 静态默认值（PlatformConfig 不可用时）
_DEFAULT_FETCH_BATCH_SIZE = 5000
_DEFAULT_COMMIT_EVERY_BATCHES = 2
_DEFAULT_PROGRESS_SAVE_ROWS = 10000
_DEFAULT_PARALLEL_TABLE_WORKERS = 16
_DEFAULT_COPY_ROW_THRESHOLD = 100_000


def _runtime():
    try:
        from .platform_config import get_migration_runtime
        return get_migration_runtime()
    except Exception:
        return {}


def get_fetch_batch_size() -> int:
    return int(_runtime().get('fetch_batch_size', _DEFAULT_FETCH_BATCH_SIZE))


def get_commit_every_batches() -> int:
    return int(_runtime().get('commit_every_batches', _DEFAULT_COMMIT_EVERY_BATCHES))


def get_progress_save_rows() -> int:
    return int(_runtime().get('progress_save_rows', _DEFAULT_PROGRESS_SAVE_ROWS))


def get_parallel_table_workers() -> int:
    return int(_runtime().get('parallel_table_workers', _DEFAULT_PARALLEL_TABLE_WORKERS))


def get_copy_row_threshold() -> int:
    return int(_runtime().get('copy_row_threshold', _DEFAULT_COPY_ROW_THRESHOLD))


def get_enable_fk_replay() -> bool:
    return bool(_runtime().get('enable_fk_replay', True))


# 为现有 import MIGRATION_* 提供兼容——使用 __getattr__ 延迟解析
def __getattr__(name: str):
    if name == 'MIGRATION_FETCH_BATCH_SIZE':
        return get_fetch_batch_size()
    if name == 'MIGRATION_COMMIT_EVERY_BATCHES':
        return get_commit_every_batches()
    if name == 'MIGRATION_PROGRESS_SAVE_ROWS':
        return get_progress_save_rows()
    if name == 'MIGRATION_PARALLEL_TABLE_WORKERS':
        return get_parallel_table_workers()
    if name == 'MIGRATION_COPY_ROW_THRESHOLD':
        return get_copy_row_threshold()
    raise AttributeError(name)
