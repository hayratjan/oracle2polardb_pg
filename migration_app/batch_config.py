"""
表数据迁移分批参数（Oracle 读取 ↔ PostgreSQL/PolarDB 写入）。
在内存占用、网络往返与事务大小之间折中，供 views / dashboard 共用。
"""

# 每批从 Oracle 拉取行数（过大易占内存、单批插入慢；过小往返次数多）
MIGRATION_FETCH_BATCH_SIZE = 5000

# 每 N 批提交一次 PostgreSQL，约 FETCH * N 行/事务
MIGRATION_COMMIT_EVERY_BATCHES = 2

# 进度与【分批】日志写库间隔（行），与提交粒度接近便于界面刷新
MIGRATION_PROGRESS_SAVE_ROWS = 10000
