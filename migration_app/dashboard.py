from django.shortcuts import render
from .models import MigrationTask

def dashboard(request):
    """
    数据库迁移管理仪表盘
    """
    # 获取最近的迁移任务
    recent_tasks = MigrationTask.objects.all().order_by('-created_at')[:5]
    
    # 统计任务状态
    total_tasks = MigrationTask.objects.count()
    completed_tasks = MigrationTask.objects.filter(status='completed').count()
    failed_tasks = MigrationTask.objects.filter(status='failed').count()
    pending_tasks = MigrationTask.objects.filter(status='pending').count()
    running_tasks = MigrationTask.objects.filter(status='running').count()
    
    context = {
        'recent_tasks': recent_tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'failed_tasks': failed_tasks,
        'pending_tasks': pending_tasks,
        'running_tasks': running_tasks,
    }
    
    return render(request, 'migration_app/dashboard.html', context)

def task_list(request):
    """
    显示所有迁移任务
    """
    tasks = MigrationTask.objects.all().order_by('-created_at')
    
    return render(request, 'migration_app/task_list.html', {
        'tasks': tasks
    })

def database_info(request):
    """
    显示数据库连接信息
    """
    return render(request, 'migration_app/database_info.html')

# 新增数据库管理视图
def oracle_schemas(request):
    """
    Oracle数据库架构管理
    """
    return render(request, 'migration_app/oracle/schemas.html')

def oracle_tables(request):
    """
    Oracle数据库表管理
    """
    return render(request, 'migration_app/oracle/tables.html')

def oracle_users(request):
    """
    Oracle数据库用户管理
    """
    return render(request, 'migration_app/oracle/users.html')

def pg_schemas(request):
    """
    PolarDB-PG数据库架构管理
    """
    return render(request, 'migration_app/polardb/schemas.html')

def pg_tables(request):
    """
    PolarDB-PG数据库表管理
    """
    return render(request, 'migration_app/polardb/tables.html')

def pg_users(request):
    """
    PolarDB-PG数据库用户管理
    """
    return render(request, 'migration_app/polardb/users.html')

# 系统配置视图
def migration_settings(request):
    """
    迁移参数配置
    """
    return render(request, 'migration_app/config/migration_settings.html')

def system_settings(request):
    """
    系统参数配置
    """
    return render(request, 'migration_app/config/system_settings.html')

def migration_logs(request):
    """
    迁移日志
    """
    return render(request, 'migration_app/logs.html')

def help_docs(request):
    """
    帮助文档
    """
    return render(request, 'migration_app/help.html') 