from django.contrib import admin
from .models import (
    OracleConnection, PostgresConnection, MigrationTask,
    MigrationTaskLog, PlatformConfig, AuditLog, UserProfile
)


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


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'action', 'target_type', 'target_id', 'ip_address', 'result', 'created_at')
    list_filter = ('action', 'target_type', 'result', 'created_at')
    search_fields = ('user__username', 'action', 'ip_address')
    readonly_fields = ('user', 'action', 'target_type', 'target_id', 'ip_address', 'user_agent', 'payload', 'result', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'created_at', 'updated_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username',)
    raw_id_fields = ('user',)
