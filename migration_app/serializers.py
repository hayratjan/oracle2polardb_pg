from rest_framework import serializers
from .models import OracleConnection, PostgresConnection, MigrationTask


class OracleConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OracleConnection
        fields = ['id', 'name', 'host', 'port', 'service_name', 'username', 'password', 'created_at']
        read_only_fields = ['id', 'created_at']


class PostgresConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostgresConnection
        fields = ['id', 'user', 'name', 'host', 'port', 'database', 'username', 'password', 
                  'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class MigrationTaskSerializer(serializers.ModelSerializer):
    source_db = serializers.ReadOnlyField()
    target_db = serializers.ReadOnlyField()
    sqlite_path = serializers.ReadOnlyField()
    oracle_connection_name = serializers.CharField(source='oracle_connection.name', read_only=True)
    postgres_connection_name = serializers.CharField(source='postgres_connection.name', read_only=True)
    
    class Meta:
        model = MigrationTask
        fields = ['id', 'name', 'task_type', 'oracle_connection', 'postgres_connection', 
                  'source_schema', 'target_schema', 'target_object', 'source_object', 
                  'source_objects', 'selected_fields', 'identifier_case', 'is_batch', 
                  'parent_task', 'conflict_strategy', 'status', 'log', 'cancel_requested', 
                  'progress', 'created_at', 'started_at', 'completed_at', 'view_progress',
                  'sqlite_directory', 'sqlite_file_name', 'source_db', 'target_db', 
                  'sqlite_path', 'oracle_connection_name', 'postgres_connection_name']
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']


class MigrationTaskListSerializer(serializers.ModelSerializer):
    source_db = serializers.ReadOnlyField()
    target_db = serializers.ReadOnlyField()
    oracle_connection_name = serializers.CharField(source='oracle_connection.name', read_only=True)
    postgres_connection_name = serializers.CharField(source='postgres_connection.name', read_only=True)
    
    class Meta:
        model = MigrationTask
        fields = ['id', 'name', 'task_type', 'status', 'progress', 'created_at', 
                  'started_at', 'completed_at', 'source_db', 'target_db', 
                  'oracle_connection_name', 'postgres_connection_name']
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']