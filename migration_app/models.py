from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class OracleConnection(models.Model):
    name = models.CharField(max_length=100, verbose_name="连接名称")
    host = models.CharField(max_length=100, verbose_name="主机")
    port = models.IntegerField(default=1521, verbose_name="端口")
    service_name = models.CharField(max_length=100, verbose_name="服务名")
    username = models.CharField(max_length=50, verbose_name="用户名")
    password = models.CharField(max_length=50, verbose_name="密码")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
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
    password = models.CharField(max_length=100, verbose_name='密码')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
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
    ]
    
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('partial', '部分完成'),
        ('canceled', '已取消'),
    ]
    
    CONFLICT_STRATEGY_CHOICES = [
        ('error', '遇到冲突时报错'),
        ('replace', '删除并替换已存在对象'),
        ('skip', '跳过已存在对象'),
        ('append', '追加数据（仅适用于表）'),
        ('truncate', '清空表并重新加载数据'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="任务名称")
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, verbose_name="任务类型")
    oracle_connection = models.ForeignKey(OracleConnection, on_delete=models.CASCADE, verbose_name="Oracle连接")
    postgres_connection = models.ForeignKey(PostgresConnection, on_delete=models.CASCADE, verbose_name="PostgreSQL连接")
    source_schema = models.CharField(max_length=50, verbose_name="源Schema")
    target_schema = models.CharField(max_length=50, verbose_name="目标Schema")
    source_object = models.CharField(max_length=100, verbose_name="源对象名称", blank=True, null=True)
    source_objects = models.TextField(verbose_name="多个源对象", blank=True, null=True, help_text="用逗号分隔的多个源对象名称")
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
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "迁移任务"
        verbose_name_plural = "迁移任务"