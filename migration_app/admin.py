from django.contrib import admin
from .models import OracleConnection, PostgresConnection, MigrationTask, MigrationTaskLog, PlatformConfig


@admin.register(MigrationTaskLog)
class MigrationTaskLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'level', 'created_at')
    list_filter = ('level', 'created_at')
    search_fields = ('message',)
    raw_id_fields = ('task',)


@admin.register(OracleConnection)
class OracleConnectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'host', 'port', 'service_name', 'username', 'created_at')
    search_fields = ('name', 'host', 'service_name')
    list_filter = ('created_at',)

@admin.register(PostgresConnection)
class PostgresConnectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'host', 'port', 'database', 'username', 'created_at')
    search_fields = ('name', 'host', 'database')
    list_filter = ('created_at',)

@admin.register(MigrationTask)
class MigrationTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'task_type', 'source_schema', 'target_schema', 'source_object', 'identifier_case', 'status', 'created_at')
    list_filter = ('task_type', 'identifier_case', 'status', 'created_at')
    search_fields = ('name', 'source_schema', 'target_schema', 'source_object')
    readonly_fields = ('log', 'created_at', 'started_at', 'completed_at', 'migration_report')


@admin.register(PlatformConfig)
class PlatformConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'default_conflict_strategy', 'batch_size', 'max_concurrent_tasks', 'updated_at')
