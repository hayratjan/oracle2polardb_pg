"""
迁移任务创建和验证功能
"""
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import MigrationTask, OracleConnection, PostgresConnection

def validate_task_data(data):
    """验证任务数据的完整性和有效性"""
    errors = []
    
    # 检查必要字段
    required_fields = ['name', 'task_type', 'oracle_connection', 'source_schema']
    
    task_type = data.get('task_type')
    if task_type == 'view_to_sqlite':
        required_fields.extend(['sqlite_directory', 'sqlite_file_name'])
    else:
        required_fields.extend(['postgres_connection', 'postgres_database', 'target_schema'])
    
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"缺少必要字段: {field}")
    
    # SQLite任务的字段清理和默认值
    if task_type == 'view_to_sqlite':
        if data.get('sqlite_directory'):
            data['sqlite_directory'] = data['sqlite_directory'].strip()
        if data.get('sqlite_file_name'):
            file_name = data['sqlite_file_name'].strip()
            if not file_name.lower().endswith(('.sqlite', '.sqlite3', '.db')):
                file_name = f"{file_name}.sqlite3"
            data['sqlite_file_name'] = file_name
        data['target_schema'] = data.get('target_schema') or 'main'
    
    # 清理目标对象名称
    if data.get('target_object'):
        data['target_object'] = data['target_object'].strip()
        if not data['target_object']:
            data['target_object'] = None
    
    # 规范字段过滤配置
    selected_fields = data.get('selected_fields')
    if selected_fields:
        if isinstance(selected_fields, list):
            tokens = selected_fields
        else:
            normalized = str(selected_fields).replace('；', ',').replace(';', ',').replace('\n', ',')
            tokens = normalized.split(',')
        cleaned = [field.strip() for field in tokens if field and field.strip()]
        data['selected_fields'] = '\n'.join(cleaned) if cleaned else None
    
    # 验证标识符大小写策略
    valid_identifier_cases = ['lower', 'upper', 'preserve']
    identifier_case = data.get('identifier_case') or 'lower'
    if identifier_case not in valid_identifier_cases:
        errors.append(f"无效的标识符大小写策略: {identifier_case}")
    data['identifier_case'] = identifier_case
    
    # 检查source_object和source_objects字段
    if 'task_type' in data and data['task_type'] != 'all_tables':
        if data['task_type'] in ['view_to_table', 'view_to_sqlite']:
            # 对于多视图迁移类型，必须提供source_objects
            if 'source_objects' not in data or not data['source_objects'] or len(data['source_objects']) == 0:
                errors.append("对于该任务类型，必须提供至少一个视图名称")
            else:
                # 确保source_objects是一个数组
                if isinstance(data['source_objects'], str):
                    data['source_objects'] = [data['source_objects']]
                # 设置source_object为第一个视图名称
                data['source_object'] = data['source_objects'][0]
        else:
            # 对于其他类型，检查source_object
            if 'source_object' not in data or not data['source_object']:
                if 'source_objects' in data and data['source_objects'] and len(data['source_objects']) > 0:
                    # 如果有source_objects数组但没有source_object，使用第一个
                    data['source_object'] = data['source_objects'][0]
                else:
                    errors.append("对于非'all_tables'类型的任务，需要提供源对象名")
    
    # 检查冲突策略
    valid_strategies = ['error', 'replace', 'skip', 'append', 'truncate']
    if 'conflict_strategy' in data and data['conflict_strategy'] not in valid_strategies:
        errors.append(f"无效的冲突策略: {data['conflict_strategy']}")
    
    # 返回验证结果
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'data': data
    }

@csrf_exempt
def create_task_validated(request):
    """创建迁移任务，包含增强的验证逻辑"""
    if request.method == 'GET':
        # 获取所有可用的数据库连接
        oracle_connections = OracleConnection.objects.all()
        postgres_connections = PostgresConnection.objects.all()
        default_task_type = request.GET.get('task_type', '')
        
        return render(request, 'migration_app/create_task.html', {
            'oracle_connections': oracle_connections,
            'postgres_connections': postgres_connections,
            'default_task_type': default_task_type
        })
    
    elif request.method == 'POST':
        try:
            # 解析请求数据
            if request.content_type and 'application/json' in request.content_type:
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            # 验证数据
            validation = validate_task_data(data)
            if not validation['is_valid']:
                return {
                    'status': 'error',
                    'message': '任务数据验证失败',
                    'errors': validation['errors']
                }
            
            # 创建任务对象
            validated_data = validation['data']
            task = MigrationTask()
            task.name = validated_data['name']
            task.task_type = validated_data['task_type']
            task.oracle_connection = OracleConnection.objects.get(pk=validated_data['oracle_connection'])
            if task.task_type == 'view_to_sqlite':
                task.postgres_connection = None
            else:
                task.postgres_connection = PostgresConnection.objects.get(pk=validated_data['postgres_connection'])
            task.source_schema = validated_data['source_schema']
            task.target_schema = validated_data.get('target_schema') or ''
            task.target_object = validated_data.get('target_object') or None
            task.sqlite_directory = validated_data.get('sqlite_directory')
            task.sqlite_file_name = validated_data.get('sqlite_file_name')
            task.selected_fields = validated_data.get('selected_fields')
            task.identifier_case = validated_data.get('identifier_case') or 'lower'
            
            # 设置源对象（如果适用）
            if task.task_type != 'all_tables':
                task.source_object = validated_data['source_object']
                # 设置source_objects字段
                if 'source_objects' in validated_data and validated_data['source_objects']:
                    task.source_objects = ','.join(validated_data['source_objects'])
            
            # 设置冲突策略
            if 'conflict_strategy' in validated_data:
                task.conflict_strategy = validated_data['conflict_strategy']
            
            # 初始设置
            task.status = 'pending'
            if task.task_type == 'view_to_sqlite':
                task.log = f"SQLite文件: {task.sqlite_path or task.sqlite_file_name}"
            else:
                task.log = f"目标PostgreSQL数据库: {validated_data['postgres_database']}"
            task.save()
            
            return {
                'status': 'success',
                'message': '任务创建成功',
                'task_id': task.id
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'创建任务失败: {str(e)}'
            }
    
    return {
        'status': 'error',
        'message': 'Invalid request method'
    } 
