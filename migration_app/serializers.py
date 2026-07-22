from rest_framework import serializers
from django.core.validators import RegexValidator
from .models import OracleConnection, PostgresConnection, MigrationTask, MigrationTaskLog

# v2.4: 纵深防御 —— 在 API 入口拦截非法标识符,避免依赖每个 SQL 拼接点
# 仅放行 [A-Za-z_][A-Za-z0-9_]* ,杜绝分号/引号/空格等注入字符穿透
_IDENTIFIER_VALIDATOR = RegexValidator(
    r'^[A-Za-z_][A-Za-z0-9_]*$',
    message='标识符仅允许字母/数字/下划线,且不能以数字开头',
    code='invalid_identifier',
)
# 可空字段用此(允许空字符串通过,非空时才校验)
_OPTIONAL_IDENTIFIER_VALIDATOR = RegexValidator(
    r'^([A-Za-z_][A-Za-z0-9_]*)?$',
    message='标识符仅允许字母/数字/下划线,且不能以数字开头(可为空)',
    code='invalid_identifier',
)


class OracleConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OracleConnection
        fields = ['id', 'name', 'host', 'port', 'service_name', 'username', 'password', 'created_at']
        read_only_fields = ['id', 'created_at']
        # 密码字段仅写入,不通过 API 返回(避免 enc: 密文泄露到前端)
        extra_kwargs = {
            'password': {'write_only': True, 'required': False, 'allow_blank': True},
        }


class PostgresConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostgresConnection
        fields = ['id', 'user', 'name', 'host', 'port', 'database', 'username', 'password',
                  'sslmode', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        # 密码字段仅写入,不通过 API 返回(避免 enc: 密文泄露到前端)
        extra_kwargs = {
            'password': {'write_only': True, 'required': False, 'allow_blank': True},
        }


class MigrationTaskLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrationTaskLog
        fields = ['id', 'level', 'message', 'created_at']


class MigrationTaskSerializer(serializers.ModelSerializer):
    source_db = serializers.ReadOnlyField()
    target_db = serializers.ReadOnlyField()
    sqlite_path = serializers.ReadOnlyField()
    oracle_connection_name = serializers.CharField(source='oracle_connection.name', read_only=True)
    postgres_connection_name = serializers.CharField(source='postgres_connection.name', read_only=True)
    # v2.4: 标识符字段入口正则校验(纵深防御,SQL 拼接点另有 safe_oracle_identifier/quote_identifier 兜底)
    source_schema = serializers.CharField(max_length=50, validators=[_IDENTIFIER_VALIDATOR])
    target_schema = serializers.CharField(
        max_length=50, required=False, allow_blank=True, allow_null=True,
        validators=[_OPTIONAL_IDENTIFIER_VALIDATOR],
    )
    source_object = serializers.CharField(
        max_length=100, required=False, allow_blank=True, allow_null=True,
        validators=[_OPTIONAL_IDENTIFIER_VALIDATOR],
    )
    target_object = serializers.CharField(
        max_length=100, required=False, allow_blank=True, allow_null=True,
        validators=[_OPTIONAL_IDENTIFIER_VALIDATOR],
    )
    watermark_column = serializers.CharField(
        max_length=128, required=False, allow_blank=True,
        validators=[_OPTIONAL_IDENTIFIER_VALIDATOR],
    )

    class Meta:
        model = MigrationTask
        fields = ['id', 'name', 'task_type', 'oracle_connection', 'postgres_connection',
                  'postgres_database', 'source_schema', 'target_schema', 'target_object', 'source_object',
                  'source_objects', 'selected_fields', 'identifier_case', 'is_batch',
                  'parent_task', 'conflict_strategy', 'status', 'log', 'cancel_requested',
                  'progress', 'created_at', 'started_at', 'completed_at', 'view_progress',
                  'sqlite_directory', 'sqlite_file_name', 'source_db', 'target_db',
                  'sqlite_path', 'oracle_connection_name', 'postgres_connection_name',
                  'incremental_mode', 'watermark_column', 'last_watermark',
                  'schedule_enabled', 'schedule_interval_minutes', 'last_schedule_run',
                  'sync_max_pkey_rows', 'view_migration_mode', 'target_provisioning', 'migration_report']
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at', 'last_schedule_run']


class MigrationTaskListSerializer(serializers.ModelSerializer):
    source_db = serializers.ReadOnlyField()
    target_db = serializers.ReadOnlyField()
    oracle_connection_name = serializers.CharField(source='oracle_connection.name', read_only=True)
    postgres_connection_name = serializers.CharField(source='postgres_connection.name', read_only=True)

    class Meta:
        model = MigrationTask
        fields = ['id', 'name', 'task_type', 'status', 'progress', 'created_at',
                  'started_at', 'completed_at', 'source_db', 'target_db',
                  'oracle_connection_name', 'postgres_connection_name', 'postgres_database', 'target_schema',
                  'incremental_mode', 'schedule_enabled']
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']
