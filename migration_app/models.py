from django.db import models

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
    name = models.CharField(max_length=100, verbose_name="连接名称")
    host = models.CharField(max_length=100, verbose_name="主机")
    port = models.IntegerField(default=5432, verbose_name="端口")
    database = models.CharField(max_length=100, verbose_name="数据库名")
    username = models.CharField(max_length=50, verbose_name="用户名")
    password = models.CharField(max_length=50, verbose_name="密码")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "PostgreSQL连接"
        verbose_name_plural = "PostgreSQL连接"

class MigrationTask(models.Model):
    TASK_TYPE_CHOICES = [
        ('table', '表'),
        ('materialized_view', '物化视图'),
        ('view', '视图'),
        ('routine', '例程'),
        ('all_tables', '所有表'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('partial', '部分完成'),
        ('canceled', '已取消'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="任务名称")
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, verbose_name="任务类型")
    oracle_connection = models.ForeignKey(OracleConnection, on_delete=models.CASCADE, verbose_name="Oracle连接")
    postgres_connection = models.ForeignKey(PostgresConnection, on_delete=models.CASCADE, verbose_name="PostgreSQL连接")
    source_schema = models.CharField(max_length=50, verbose_name="源Schema")
    target_schema = models.CharField(max_length=50, verbose_name="目标Schema")
    source_object = models.CharField(max_length=100, verbose_name="源对象名称", blank=True, null=True)
    is_batch = models.BooleanField(default=False, verbose_name="批量迁移")
    parent_task = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtasks', verbose_name="父任务")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    log = models.TextField(blank=True, null=True, verbose_name="日志")
    cancel_requested = models.BooleanField(default=False, verbose_name="请求取消")
    progress = models.FloatField(default=0, verbose_name="进度百分比")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "迁移任务"
        verbose_name_plural = "迁移任务"