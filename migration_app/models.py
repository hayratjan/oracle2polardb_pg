from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os


class OracleConnection(models.Model):
    name = models.CharField(max_length=100, verbose_name="连接名称")
    host = models.CharField(max_length=100, verbose_name="主机")
    port = models.IntegerField(default=1521, verbose_name="端口")
    service_name = models.CharField(max_length=100, verbose_name="服务名")
    username = models.CharField(max_length=50, verbose_name="用户名")
    # 加密后变长，预留长度（enc: + Fernet）
    password = models.CharField(max_length=512, verbose_name="密码")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def save(self, *args, **kwargs):
        from .credentials import maybe_encrypt_password
        if self.password:
            self.password = maybe_encrypt_password(self.password)
        super().save(*args, **kwargs)
        # v2.4: 保存后失效旧连接池,确保密码/主机修改后下次获取用新配置重建池
        try:
            from .connection_pool import invalidate_oracle_pool
            invalidate_oracle_pool(self.pk)
        except Exception:
            # 连接池失效失败不应阻止保存,下次重启时池会自然重建
            pass

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Oracle连接"
        verbose_name_plural = "Oracle连接"


class PostgresConnection(models.Model):
    STATUS_CHOICES = [
        ('active', '正常'),
        ('inactive', '异常'),
        ('testing', '测试中')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='用户')
    name = models.CharField(max_length=100, verbose_name='连接名称')
    host = models.CharField(max_length=100, verbose_name='主机地址')
    port = models.IntegerField(default=5432, verbose_name='端口')
    database = models.CharField(max_length=100, verbose_name='数据库名')
    username = models.CharField(max_length=100, verbose_name='用户名')
    password = models.CharField(max_length=512, verbose_name='密码')
    sslmode = models.CharField(max_length=20, blank=True, default='', verbose_name='SSL模式',
                               help_text='留空自动检测；require=需要SSL；prefer=优先SSL；disable=禁用SSL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def save(self, *args, **kwargs):
        from .credentials import maybe_encrypt_password
        if self.password:
            self.password = maybe_encrypt_password(self.password)
        super().save(*args, **kwargs)
        # v2.4: 保存后失效旧连接池,确保密码/主机修改后下次获取用新配置重建池
        try:
            from .connection_pool import invalidate_postgres_pool
            invalidate_postgres_pool(self.pk)
        except Exception:
            pass

    class Meta:
        verbose_name = 'PostgreSQL连接'
        verbose_name_plural = 'PostgreSQL连接'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.host}:{self.port})"


class MigrationTask(models.Model):
    TASK_TYPE_CHOICES = [
        ('table', '表'),
        ('materialized_view', '物化视图'),
        ('view', '视图'),
        ('routine', '例程'),
        ('all_tables', '所有表'),
        ('view_to_table', '视图数据迁移到表'),
        ('view_to_sqlite', '视图数据迁移到SQLite'),
        ('trigger', '触发器'),
        ('sequence', '序列'),
        ('full_schema', '全Schema编排迁移'),
        ('table_batch', '表级批量迁移'),
        ('full_database', '整库一键迁移'),
    ]

    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('partial', '部分完成'),
        ('canceled', '已取消'),
        ('aborted', '异常停止'),
        ('exported', '已导出待人工处理'),
    ]

    VIEW_MIGRATION_MODE_CHOICES = [
        ('materialize', '物化到表（快照）'),
        ('definition', '创建视图定义'),
    ]

    CONFLICT_STRATEGY_CHOICES = [
        ('error', '遇到冲突时报错'),
        ('replace', '删除并替换已存在对象'),
        ('skip', '跳过已存在对象'),
        ('append', '追加数据（仅适用于表）'),
        ('truncate', '清空表并重新加载数据'),
    ]
    IDENTIFIER_CASE_CHOICES = [
        ('lower', '全部小写'),
        ('upper', '全部大写'),
        ('preserve', '保持原样'),
    ]
    INCREMENTAL_MODE_CHOICES = [
        ('none', '全量'),
        ('timestamp', '按水位列增量'),
        ('pk_mirror', '主键对齐增量(定时增删)'),
    ]

    name = models.CharField(max_length=100, verbose_name="任务名称")
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name="任务类型")
    oracle_connection = models.ForeignKey(OracleConnection, on_delete=models.CASCADE, verbose_name="Oracle连接")
    postgres_connection = models.ForeignKey(
        PostgresConnection,
        on_delete=models.CASCADE,
        verbose_name="PostgreSQL连接",
        null=True,
        blank=True
    )
    source_schema = models.CharField(max_length=50, verbose_name="源Schema")
    target_schema = models.CharField(max_length=50, verbose_name="目标Schema", blank=True, null=True)
    target_object = models.CharField(max_length=100, blank=True, null=True, verbose_name="目标对象名称")
    source_object = models.CharField(max_length=100, verbose_name="源对象名称", blank=True, null=True)
    source_objects = models.TextField(verbose_name="多个源对象", blank=True, null=True, help_text="用逗号分隔的多个源对象名称")
    selected_fields = models.TextField(blank=True, null=True, verbose_name="字段过滤", help_text="逗号或换行分隔的字段名，可选")
    identifier_case = models.CharField(max_length=10, choices=IDENTIFIER_CASE_CHOICES, default='lower', verbose_name="标识符大小写策略")
    view_migration_mode = models.CharField(
        max_length=20,
        choices=VIEW_MIGRATION_MODE_CHOICES,
        default='materialize',
        blank=True,
        verbose_name="视图迁移模式",
        help_text="materialize=将视图数据写入目标表；definition=在目标库创建 CREATE VIEW",
    )
    is_batch = models.BooleanField(default=False, verbose_name="批量迁移")
    parent_task = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtasks', verbose_name="父任务")
    conflict_strategy = models.CharField(max_length=20, choices=CONFLICT_STRATEGY_CHOICES, default='error', verbose_name="冲突处理策略")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    log = models.TextField(blank=True, null=True, verbose_name="日志")
    cancel_requested = models.BooleanField(default=False, verbose_name="请求取消")
    progress = models.FloatField(default=0, verbose_name="进度百分比")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    view_progress = models.JSONField(verbose_name="视图迁移进度", blank=True, null=True, help_text="存储每个视图的迁移进度")
    sqlite_directory = models.CharField(max_length=255, blank=True, null=True, verbose_name="SQLite目录")
    sqlite_file_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="SQLite文件名")
    postgres_database = models.CharField(max_length=255, blank=True, null=True, verbose_name="目标数据库")
    # 增量与定时（与 Celery Beat 扫描配合）
    incremental_mode = models.CharField(
        max_length=20, choices=INCREMENTAL_MODE_CHOICES, default='none',
        verbose_name="增量模式"
    )
    watermark_column = models.CharField(max_length=128, blank=True, default='', verbose_name="水位列名")
    last_watermark = models.TextField(blank=True, null=True, verbose_name="上次水位值")
    schedule_enabled = models.BooleanField(default=False, verbose_name="启用定时增量")
    schedule_interval_minutes = models.PositiveIntegerField(default=60, verbose_name="调度最小间隔(分钟)")
    last_schedule_run = models.DateTimeField(null=True, blank=True, verbose_name="上次定时触发时间")
    # 主键对齐增量：单次在内存中对比主键的最大行数（源、目标两侧均不得超过）
    sync_max_pkey_rows = models.PositiveIntegerField(
        default=500_000,
        verbose_name="主键对齐单次最大行数",
        help_text="超过则拒绝执行主键对齐，避免 OOM；大表请用水位列增量或调大该值",
    )
    # 目标环境配置（库/表空间/用户/Schema 创建或选择信息）
    target_provisioning = models.JSONField(
        null=True, blank=True, verbose_name="目标环境配置",
        help_text="表级/整库迁移向导中的目标库、表空间、用户、Schema 配置",
    )
    # 任务完成后结构化迁移报告（成功/失败对象、行数校验、需人工审查项）
    migration_report = models.JSONField(
        null=True, blank=True, verbose_name="迁移报告",
    )

    def __str__(self):
        return self.name

    @property
    def sqlite_path(self):
        if self.sqlite_directory and self.sqlite_file_name:
            directory = os.path.expanduser(self.sqlite_directory)
            return os.path.abspath(os.path.join(directory, self.sqlite_file_name))
        return None

    @property
    def source_db(self):
        if self.oracle_connection:
            return f"{self.oracle_connection.name} ({self.source_schema})"
        return f"Oracle ({self.source_schema})"

    @property
    def target_db(self):
        if self.task_type == 'view_to_sqlite':
            if self.sqlite_file_name:
                return f"SQLite ({self.sqlite_file_name})"
            return "SQLite"
        if self.postgres_connection:
            target_info = f"{self.postgres_connection.name}"
            db_name = self.postgres_database or self.postgres_connection.database
            if db_name:
                target_info += f" / {db_name}"
            if self.target_schema:
                target_info += f" ({self.target_schema})"
            return target_info
        if self.target_schema:
            return f"PostgreSQL ({self.target_schema})"
        return "PostgreSQL"

    class Meta:
        verbose_name = "迁移任务"
        verbose_name_plural = "迁移任务"


class MigrationTaskLog(models.Model):
    """结构化任务日志，支持分页查询。"""
    task = models.ForeignKey(MigrationTask, on_delete=models.CASCADE, related_name='log_entries', verbose_name="任务")
    level = models.CharField(max_length=16, default='INFO', verbose_name="级别")
    message = models.TextField(verbose_name="消息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="时间")

    class Meta:
        verbose_name = "迁移任务日志行"
        verbose_name_plural = "迁移任务日志行"
        ordering = ['-id']
        indexes = [
            models.Index(fields=['task', '-id']),
        ]

    def __str__(self):
        return f"{self.task_id} {self.level} {self.created_at}"


class PlatformConfig(models.Model):
    """平台全局配置单例（pk 固定为 1）。"""

    IDENTIFIER_CASE_CHOICES = MigrationTask.IDENTIFIER_CASE_CHOICES
    CONFLICT_STRATEGY_CHOICES = MigrationTask.CONFLICT_STRATEGY_CHOICES

    # 迁移默认策略
    default_identifier_case = models.CharField(
        max_length=10, choices=IDENTIFIER_CASE_CHOICES, default='lower',
        verbose_name="默认标识符大小写",
    )
    default_conflict_strategy = models.CharField(
        max_length=20, choices=CONFLICT_STRATEGY_CHOICES, default='error',
        verbose_name="默认冲突策略",
    )
    enable_batch_migration = models.BooleanField(default=True, verbose_name="启用分批迁移")
    batch_size = models.PositiveIntegerField(default=5000, verbose_name="每批拉取行数")
    commit_every_batches = models.PositiveIntegerField(default=2, verbose_name="每N批提交一次")
    progress_save_rows = models.PositiveIntegerField(default=10000, verbose_name="进度写库间隔(行)")
    parallel_table_workers = models.PositiveIntegerField(default=16, verbose_name="多表并行线程数")
    copy_row_threshold = models.PositiveIntegerField(default=100_000, verbose_name="快速写入行数阈值")
    enable_fk_replay = models.BooleanField(default=True, verbose_name="启用外键约束回放")

    # 系统参数
    log_level = models.CharField(max_length=16, default='INFO', verbose_name="日志级别")
    max_concurrent_tasks = models.PositiveIntegerField(default=5, verbose_name="最大并发任务数")
    task_timeout = models.PositiveIntegerField(default=3600, verbose_name="任务超时(秒)")
    enable_auto_retry = models.BooleanField(default=False, verbose_name="启用自动重试")
    max_retry_count = models.PositiveIntegerField(default=3, verbose_name="最大重试次数")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "平台配置"
        verbose_name_plural = "平台配置"

    def __str__(self):
        return "平台全局配置"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class UserRole(models.TextChoices):
    """用户角色枚举"""
    ADMIN = 'admin', '管理员'
    OPERATOR = 'operator', '操作员'
    VIEWER = 'viewer', '只读用户'


class UserProfile(models.Model):
    """用户角色配置（一对一关联 User，兼容性好）"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='用户'
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.VIEWER,
        verbose_name='角色'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'migration_user_profile'
        verbose_name = '用户角色配置'
        verbose_name_plural = '用户角色配置'

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class AuditLog(models.Model):
    """审计日志模型"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='操作用户'
    )
    action = models.CharField(
        max_length=50,
        verbose_name='操作类型'
    )  # start_task, cancel_task, delete_task, create_connection, update_settings 等
    target_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='目标类型'
    )  # task, connection, settings
    target_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='目标 ID'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP 地址'
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='User Agent'
    )
    payload = models.JSONField(
        null=True,
        blank=True,
        verbose_name='操作参数'
    )
    result = models.CharField(
        max_length=20,
        default='success',
        verbose_name='结果'
    )  # success, failed, denied
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='操作时间'
    )

    class Meta:
        db_table = 'migration_audit_log'
        ordering = ['-created_at']
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'

    def __str__(self):
        username = self.user.username if self.user else '匿名'
        return f"[{self.created_at}] {username} - {self.action} ({self.result})"
