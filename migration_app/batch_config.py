"""
表数据迁移分批参数（Oracle 读取 ↔ PostgreSQL/PolarDB 写入）。
优先读取 PlatformConfig 持久化配置，无 DB 时回退默认值。
"""
from __future__ import annotations

# 静态默认值（PlatformConfig 不可用时）
_DEFAULT_FETCH_BATCH_SIZE = 5000
_DEFAULT_COMMIT_EVERY_BATCHES = 2
_DEFAULT_PROGRESS_SAVE_ROWS = 10000
# v2.3: 并行度默认降至 8，避免 16 路并发写入对目标库造成过大压力
_DEFAULT_PARALLEL_TABLE_WORKERS = 8
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
    workers = int(_runtime().get('parallel_table_workers', _DEFAULT_PARALLEL_TABLE_WORKERS))
    # v2.4.3: 与连接池上限联动 —— 每张并行表占 1 个 Oracle + 1 个 PG 池连接，
    # 超过池上限会耗尽池/长时间等待。上限放宽到池 max + 2（主流程自身占用）。
    try:
        from .connection_pool import POOL_MAX_CONNECTIONS
        cap = int(POOL_MAX_CONNECTIONS) + 2
        if workers > cap:
            workers = cap
    except Exception:
        pass
    return workers


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


def get_enable_advanced_validation() -> bool:
    """v2.4.3: 迁移后综合校验（聚合+抽样/哈希）开关，默认开启。"""
    return bool(_runtime().get('enable_advanced_validation', True))


def get_validation_hash_max_rows() -> int:
    """v2.4.3: 启用哈希校验的表行数上限（超过走抽样校验）。"""
    return int(_runtime().get('validation_hash_max_rows', 100_000))
