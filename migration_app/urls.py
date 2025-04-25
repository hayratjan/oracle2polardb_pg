from django.urls import path
from . import views
from . import dashboard

app_name = 'migration_app'

urlpatterns = [
    # 基本视图
    path('', dashboard.dashboard, name='dashboard'),
    path('index/', views.index, name='index'),
    
    # 任务管理
    path('task/create/', views.create_task, name='create_task'),
    path('task/<int:task_id>/', views.task_detail, name='task_detail'),
    path('task/<int:task_id>/status/', views.task_status, name='task_status'),
    path('task/<int:task_id>/start/', views.start_task, name='start_task'),
    path('task/<int:task_id>/cancel/', views.cancel_task, name='cancel_task'),
    path('tasks/', dashboard.task_list, name='task_list'),
    
    # 数据查询API
    path('schemas/', views.get_schemas, name='get_schemas'),
    path('database-objects/', views.get_database_objects, name='get_database_objects'),
    
    # 数据库管理
    path('database-info/', dashboard.database_info, name='database_info'),
    
    # Oracle数据库管理
    path('oracle/schemas/', dashboard.oracle_schemas, name='oracle_schemas'),
    path('oracle/tables/', dashboard.oracle_tables, name='oracle_tables'),
    path('oracle/users/', dashboard.oracle_users, name='oracle_users'),
    
    # PolarDB-PG数据库管理
    path('polardb/schemas/', dashboard.pg_schemas, name='pg_schemas'),
    path('polardb/tables/', dashboard.pg_tables, name='pg_tables'),
    path('polardb/users/', dashboard.pg_users, name='pg_users'),
    
    # 系统配置
    path('config/migration/', dashboard.migration_settings, name='migration_settings'),
    path('config/system/', dashboard.system_settings, name='system_settings'),
    path('logs/', dashboard.migration_logs, name='migration_logs'),
    path('help/', dashboard.help_docs, name='help'),
] 