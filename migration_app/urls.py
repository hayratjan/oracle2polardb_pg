from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import dashboard
from . import create_task
from . import api

app_name = 'migration_app'

router = DefaultRouter()
router.register(r'oracle-connections', api.OracleConnectionViewSet, basename='oracle-connection')
router.register(r'postgres-connections', api.PostgresConnectionViewSet, basename='postgres-connection')
router.register(r'tasks', api.MigrationTaskViewSet, basename='task')

urlpatterns = [
    # REST API 路由 - 不需要加 /api/ 前缀，因为主urls.py已经加了
    path('', include(router.urls)),
    
    # REST API 端点
    path('schemas/', api.SchemasAPIView.as_view(), name='api_schemas'),
    path('database-objects/', api.DatabaseObjectsAPIView.as_view(), name='api_database_objects'),
    path('postgres-databases/', api.PostgresDatabasesAPIView.as_view(), name='api_postgres_databases'),
    path('filesystem/directories/', api.BrowseDirectoriesAPIView.as_view(), name='api_browse_directories'),
    path('database-info/', api.DatabaseInfoAPIView.as_view(), name='api_database_info'),
    path('oracle/schemas/', api.OracleSchemasAPIView.as_view(), name='api_oracle_schemas'),
    path('oracle/tables/', api.OracleTablesAPIView.as_view(), name='api_oracle_tables'),
    path('oracle/users/', api.OracleUsersAPIView.as_view(), name='api_oracle_users'),
    path('oracle/test-connection/', views.test_oracle_connection, name='api_test_oracle_connection'),
    path('oracle/save-connection/', views.save_oracle_connection, name='api_save_oracle_connection'),
    path('oracle/delete-connection/', views.delete_oracle_connection, name='api_delete_oracle_connection'),
    path('oracle/edit-connection/', views.edit_oracle_connection, name='api_edit_oracle_connection'),
    path('polardb/schemas/', api.PgSchemasAPIView.as_view(), name='api_pg_schemas'),
    path('polardb/tables/', api.PgTablesAPIView.as_view(), name='api_pg_tables'),
    path('polardb/users/', api.PgUsersAPIView.as_view(), name='api_pg_users'),
    path('postgres/test-connection/', views.test_pg_connection, name='api_test_pg_connection'),
    path('postgres/save-connection/', views.add_pg_connection, name='api_save_pg_connection'),
    path('postgres/delete-connection/', views.delete_pg_connection, name='api_delete_pg_connection'),
    path('postgres/edit-connection/', views.edit_pg_connection, name='api_edit_pg_connection'),
    path('config/migration/', api.MigrationSettingsAPIView.as_view(), name='api_migration_settings'),
    path('config/system/', api.SystemSettingsAPIView.as_view(), name='api_system_settings'),
    path('logs/', api.MigrationLogsAPIView.as_view(), name='api_migration_logs'),
    path('help/', api.HelpDocsAPIView.as_view(), name='api_help'),
    path('create-task/', api.CreateTaskAPIView.as_view(), name='api_create_task'),
    
    # 保留旧的HTML视图路由（用于向后兼容，使用 /app/ 前缀）
    path('app/', include([
        path('', dashboard.dashboard, name='dashboard'),
        path('index/', views.index, name='index'),
        path('task/create/', create_task.create_task_validated, name='create_task'),
        path('task/<int:task_id>/', dashboard.task_detail, name='task_detail'),
        path('task/<int:task_id>/status/', dashboard.task_status, name='task_status'),
        path('task/<int:task_id>/start/', dashboard.start_task, name='start_task'),
        path('task/<int:task_id>/cancel/', dashboard.cancel_task, name='cancel_task'),
        path('task/<int:task_id>/delete/', dashboard.delete_task, name='delete_task'),
        path('task/<int:task_id>/info/', dashboard.task_detailed_info, name='task_detailed_info'),
        path('task/<int:task_id>/switch_database/', dashboard.switch_postgres_database, name='switch_postgres_database'),
        path('tasks/', dashboard.task_list, name='task_list'),
        path('schemas/', dashboard.get_schemas, name='get_schemas'),
        path('database-objects/', dashboard.get_database_objects, name='get_database_objects'),
        path('postgres-databases/', dashboard.get_postgres_databases, name='get_postgres_databases'),
        path('filesystem/directories/', dashboard.browse_directories, name='browse_directories'),
        path('database-info/', dashboard.database_info, name='database_info'),
        path('oracle/schemas/', dashboard.oracle_schemas, name='oracle_schemas'),
        path('oracle/tables/', dashboard.oracle_tables, name='oracle_tables'),
        path('oracle/users/', dashboard.oracle_users, name='oracle_users'),
        path('oracle/database/', views.oracle_database_management, name='oracle_database_management'),
        path('oracle/test_connection/', views.test_oracle_connection, name='test_oracle_connection'),
        path('oracle/save_connection/', views.save_oracle_connection, name='save_oracle_connection'),
        path('oracle/delete_connection/', views.delete_oracle_connection, name='delete_oracle_connection'),
        path('oracle/edit_connection/', views.edit_oracle_connection, name='edit_oracle_connection'),
        path('polardb/schemas/', dashboard.pg_schemas, name='pg_schemas'),
        path('polardb/tables/', dashboard.pg_tables, name='pg_tables'),
        path('polardb/users/', dashboard.pg_users, name='pg_users'),
        path('postgres/connections/', views.pg_database_management, name='pg_database_management'),
        path('postgres/connections/get/', views.get_pg_connections, name='get_pg_connections'),
        path('postgres/connections/add/', views.add_pg_connection, name='add_pg_connection'),
        path('postgres/connections/test/', views.test_pg_connection, name='test_pg_connection'),
        path('postgres/connections/delete/', views.delete_pg_connection, name='delete_pg_connection'),
        path('postgres/connections/edit/', views.edit_pg_connection, name='edit_pg_connection'),
        path('config/migration/', dashboard.migration_settings, name='migration_settings'),
        path('config/system/', dashboard.system_settings, name='system_settings'),
        path('logs/', dashboard.migration_logs, name='migration_logs'),
        path('help/', dashboard.help_docs, name='help'),
        path('create_task_validated/', create_task.create_task_validated, name='create_task_validated'),
    ])),
] 
