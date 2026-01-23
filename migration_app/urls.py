from django.urls import path
from . import views
from . import dashboard
from . import create_task

app_name = 'migration_app'

urlpatterns = [
    # 基本视图
    path('', dashboard.dashboard, name='dashboard'),
    path('index/', views.index, name='index'),
    
    # 任务管理
    path('task/create/', create_task.create_task_validated, name='create_task'),
    path('task/<int:task_id>/', dashboard.task_detail, name='task_detail'),
    path('task/<int:task_id>/status/', dashboard.task_status, name='task_status'),
    path('task/<int:task_id>/start/', dashboard.start_task, name='start_task'),
    path('task/<int:task_id>/cancel/', dashboard.cancel_task, name='cancel_task'),
    path('task/<int:task_id>/delete/', dashboard.delete_task, name='delete_task'),
    path('task/<int:task_id>/info/', dashboard.task_detailed_info, name='task_detailed_info'),
    path('task/<int:task_id>/switch_database/', dashboard.switch_postgres_database, name='switch_postgres_database'),
    path('tasks/', dashboard.task_list, name='task_list'),
    
    # 数据查询API
    path('schemas/', dashboard.get_schemas, name='get_schemas'),
    path('database-objects/', dashboard.get_database_objects, name='get_database_objects'),
    path('postgres-databases/', dashboard.get_postgres_databases, name='get_postgres_databases'),
    path('filesystem/directories/', dashboard.browse_directories, name='browse_directories'),
    
    # 数据库管理
    path('database-info/', dashboard.database_info, name='database_info'),
    
    # Oracle数据库管理
    path('oracle/schemas/', dashboard.oracle_schemas, name='oracle_schemas'),
    path('oracle/tables/', dashboard.oracle_tables, name='oracle_tables'),
    path('oracle/users/', dashboard.oracle_users, name='oracle_users'),
    path('oracle/database/', views.oracle_database_management, name='oracle_database_management'),
    path('oracle/test_connection/', views.test_oracle_connection, name='test_oracle_connection'),
    path('oracle/save_connection/', views.save_oracle_connection, name='save_oracle_connection'),
    path('oracle/delete_connection/', views.delete_oracle_connection, name='delete_oracle_connection'),
    
    # PolarDB-PG数据库管理
    path('polardb/schemas/', dashboard.pg_schemas, name='pg_schemas'),
    path('polardb/tables/', dashboard.pg_tables, name='pg_tables'),
    path('polardb/users/', dashboard.pg_users, name='pg_users'),
    
    # 系统配置
    path('config/migration/', dashboard.migration_settings, name='migration_settings'),
    path('config/system/', dashboard.system_settings, name='system_settings'),
    path('logs/', dashboard.migration_logs, name='migration_logs'),
    path('help/', dashboard.help_docs, name='help'),
    
    # 新增带验证的任务创建接口
    path('create_task_validated/', create_task.create_task_validated, name='create_task_validated'),
    
    # PolarDB-PG数据库连接管理
    path('postgres/connections/', views.pg_database_management, name='pg_database_management'),
    path('postgres/connections/get/', views.get_pg_connections, name='get_pg_connections'),
    path('postgres/connections/add/', views.add_pg_connection, name='add_pg_connection'),
    path('postgres/connections/test/', views.test_pg_connection, name='test_pg_connection'),
    path('postgres/connections/delete/', views.delete_pg_connection, name='delete_pg_connection'),
    path('postgres/connections/edit/', views.edit_pg_connection, name='edit_pg_connection'),
] 
