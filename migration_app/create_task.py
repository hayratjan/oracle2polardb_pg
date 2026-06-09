"""
迁移任务创建和验证功能
"""
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import MigrationTask, OracleConnection, PostgresConnection
from .target_provisioning import prepare_target_env
from .platform_config import apply_task_creation_defaults


def validate_task_data(data):
    """验证任务数据的完整性和有效性"""
    # 合并平台默认策略（标识符大小写、冲突策略等）
    data = apply_task_creation_defaults(dict(data))
    errors = []
    
    # 检查必要字段
    required_fields = ['name', 'task_type', 'oracle_connection', 'source_schema']
    
    task_type = data.get('task_type')
    if task_type == 'view_to_sqlite':
        required_fields.extend(['sqlite_directory', 'sqlite_file_name'])
    else:
        required_fields.extend(['postgres_connection', 'target_schema'])
    
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
    
    # 规范化 source_objects：支持逗号分隔字符串或数组
    def _normalize_source_objects(val):
        if not val:
            return []
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        s = str(val).replace('；', ',').replace(';', ',').replace('\n', ',')
        return [x.strip() for x in s.split(',') if x.strip()]

    if 'source_objects' in data and data['source_objects']:
        data['source_objects'] = _normalize_source_objects(data['source_objects'])

    imode = data.get('incremental_mode') or 'none'
    if imode not in ('none', 'timestamp', 'pk_mirror'):
        errors.append(f"无效的增量模式: {imode}")
    data['incremental_mode'] = imode
    if imode == 'timestamp' and data.get('task_type') == 'table' and not (data.get('watermark_column') or '').strip():
        errors.append("增量模式为「按水位列」时，必须填写 watermark_column（源表列名）")
    if imode == 'pk_mirror' and data.get('task_type') == 'table':
        if (data.get('conflict_strategy') or 'error') != 'append':
            errors.append('主键对齐增量需将冲突策略设为「追加数据」，以便目标表已存在时只做差量同步。')
        sm = data.get('sync_max_pkey_rows')
        if sm is not None and str(sm).strip() != '':
            try:
                n = int(sm)
                if n < 1000 or n > 10_000_000:
                    errors.append('sync_max_pkey_rows 需在 1000～10000000 之间')
                else:
                    data['sync_max_pkey_rows'] = n
            except (TypeError, ValueError):
                errors.append('sync_max_pkey_rows 必须为整数')

    # 检查source_object和source_objects字段（view 与 view_to_table 均支持批量 source_objects）
    if 'task_type' in data and data['task_type'] not in ('all_tables', 'full_schema', 'full_database'):
        has_source_objects = bool(data.get('source_objects'))
        source_obj_val = data.get('source_object')
        has_source_object = bool(source_obj_val and str(source_obj_val).strip())
        if data['task_type'] in ['view', 'view_to_table', 'view_to_sqlite']:
            if not has_source_objects and not has_source_object:
                errors.append("对于该任务类型，必须提供至少一个视图名称")
            else:
                if has_source_objects:
                    data['source_object'] = data['source_objects'][0]
                elif not has_source_object:
                    errors.append("对于该任务类型，必须提供至少一个视图名称")
        else:
            if not has_source_object and not has_source_objects:
                errors.append("对于该任务类型，需要提供源对象名（表/视图/序列/触发器等）")
            elif has_source_objects and not has_source_object:
                data['source_object'] = data['source_objects'][0]
    
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
            task.view_migration_mode = validated_data.get('view_migration_mode') or 'materialize'
            task.is_batch = bool(validated_data.get('is_batch', False))
            
            # 设置目标 PolarDB 数据库名（可选，不填则用连接默认库）
            if task.task_type != 'view_to_sqlite' and task.postgres_connection:
                task.postgres_database = validated_data.get('postgres_database') or task.postgres_connection.database or None
            
            # 设置源对象（如果适用）
            if task.task_type not in ('all_tables', 'full_schema'):
                task.source_object = validated_data.get('source_object') or ''
                if 'source_objects' in validated_data and validated_data['source_objects']:
                    task.source_objects = ','.join(validated_data['source_objects'])
            else:
                task.source_object = ''
                task.source_objects = None

            task.incremental_mode = validated_data.get('incremental_mode') or 'none'
            task.watermark_column = (validated_data.get('watermark_column') or '').strip() or ''
            lw = validated_data.get('last_watermark')
            task.last_watermark = lw if lw not in (None, '') else None
            task.schedule_enabled = bool(validated_data.get('schedule_enabled', False))
            try:
                task.schedule_interval_minutes = max(1, int(validated_data.get('schedule_interval_minutes') or 60))
            except (TypeError, ValueError):
                task.schedule_interval_minutes = 60
            if validated_data.get('sync_max_pkey_rows') is not None:
                task.sync_max_pkey_rows = int(validated_data['sync_max_pkey_rows'])

            # 设置冲突策略
            if 'conflict_strategy' in validated_data:
                task.conflict_strategy = validated_data['conflict_strategy']
            if validated_data.get('target_provisioning') is not None:
                task.target_provisioning = validated_data['target_provisioning']
            
            # 初始设置
            task.status = 'pending'
            if task.task_type == 'view_to_sqlite':
                task.log = f"SQLite文件: {task.sqlite_path or task.sqlite_file_name}"
            else:
                postgres_db = task.postgres_database or (task.postgres_connection.database if task.postgres_connection else '')
                task.log = f"目标PostgreSQL数据库: {postgres_db}"
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


def _apply_task_fields(task: MigrationTask, validated_data: dict) -> None:
    """将校验后的数据写入 MigrationTask 实例（供多种创建入口复用）。"""
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
    task.view_migration_mode = validated_data.get('view_migration_mode') or 'materialize'
    task.is_batch = bool(validated_data.get('is_batch', False))

    if task.task_type != 'view_to_sqlite' and task.postgres_connection:
        task.postgres_database = validated_data.get('postgres_database') or task.postgres_connection.database or None

    if task.task_type not in ('all_tables', 'full_schema', 'full_database'):
        task.source_object = validated_data.get('source_object') or ''
        if validated_data.get('source_objects'):
            objs = validated_data['source_objects']
            task.source_objects = ','.join(objs) if isinstance(objs, list) else objs
    else:
        task.source_object = ''
        task.source_objects = None

    task.incremental_mode = validated_data.get('incremental_mode') or 'none'
    task.watermark_column = (validated_data.get('watermark_column') or '').strip() or ''
    lw = validated_data.get('last_watermark')
    task.last_watermark = lw if lw not in (None, '') else None
    task.schedule_enabled = bool(validated_data.get('schedule_enabled', False))
    try:
        task.schedule_interval_minutes = max(1, int(validated_data.get('schedule_interval_minutes') or 60))
    except (TypeError, ValueError):
        task.schedule_interval_minutes = 60
    if validated_data.get('sync_max_pkey_rows') is not None:
        task.sync_max_pkey_rows = int(validated_data['sync_max_pkey_rows'])
    if 'conflict_strategy' in validated_data:
        task.conflict_strategy = validated_data['conflict_strategy']
    if validated_data.get('target_provisioning') is not None:
        task.target_provisioning = validated_data['target_provisioning']


def create_table_migration_plan(data: dict) -> dict:
    """
    表级迁移向导：按表选择 + 增量 + 目标环境配置，创建迁移任务。
    """
    errors = []
    required = ['name', 'oracle_connection', 'postgres_connection', 'source_schema', 'target_schema']
    for field in required:
        if not data.get(field):
            errors.append(f'缺少必要字段: {field}')

    source_objects = data.get('source_objects') or []
    if isinstance(source_objects, str):
        source_objects = [x.strip() for x in source_objects.replace('；', ',').replace('\n', ',').split(',') if x.strip()]
    if not source_objects:
        errors.append('请至少选择一张表')

    if errors:
        return {'status': 'error', 'message': '任务数据验证失败', 'errors': errors}

    data['task_type'] = 'table'
    data['source_objects'] = source_objects
    data['source_object'] = source_objects[0]

    validation = validate_task_data(data)
    if not validation['is_valid']:
        return {'status': 'error', 'message': '任务数据验证失败', 'errors': validation['errors']}

    validated = validation['data']
    target_prov = validated.get('target_provisioning')

    # 可选：先准备目标环境
    if validated.get('prepare_target') and target_prov:
        prep_cfg = dict(target_prov)
        prep_cfg['connection_id'] = validated['postgres_connection']
        prep_result = prepare_target_env(prep_cfg)
        if prep_result.get('status') != 'success':
            return {
                'status': 'error',
                'message': prep_result.get('message', '目标环境准备失败'),
                'steps': prep_result.get('steps'),
            }
        resolved = prep_result.get('resolved') or {}
        if resolved.get('database'):
            validated['postgres_database'] = resolved['database']
        if resolved.get('schema'):
            validated['target_schema'] = resolved['schema']

    task = MigrationTask()
    _apply_task_fields(task, validated)
    task.status = 'pending'
    postgres_db = task.postgres_database or (task.postgres_connection.database if task.postgres_connection else '')
    task.log = f'【表级迁移】目标库: {postgres_db}，共 {len(source_objects)} 张表'
    task.save()

    return {'status': 'success', 'message': '表级迁移任务创建成功', 'task_id': task.id}


def create_full_database_migration_plan(data: dict) -> dict:
    """整库一键迁移：创建编排父任务。"""
    errors = []
    for field in ['name', 'oracle_connection', 'postgres_connection']:
        if not data.get(field):
            errors.append(f'缺少必要字段: {field}')
    if errors:
        return {'status': 'error', 'message': '任务数据验证失败', 'errors': errors}

    target_prov = data.get('target_provisioning') or {}
    data['task_type'] = 'full_database'
    data['source_schema'] = data.get('source_schema') or '_ALL_'
    data['target_schema'] = data.get('target_schema') or 'public'
    data['conflict_strategy'] = data.get('conflict_strategy') or 'error'
    data['identifier_case'] = data.get('identifier_case') or 'lower'
    data['target_provisioning'] = target_prov

    if data.get('prepare_target') and target_prov.get('prepare_config'):
        prep_cfg = dict(target_prov['prepare_config'])
        prep_cfg['connection_id'] = data['postgres_connection']
        prep_result = prepare_target_env(prep_cfg)
        if prep_result.get('status') != 'success':
            return {
                'status': 'error',
                'message': prep_result.get('message', '目标环境准备失败'),
                'steps': prep_result.get('steps'),
            }
        resolved = prep_result.get('resolved') or {}
        if resolved.get('database'):
            data['postgres_database'] = resolved['database']

    task = MigrationTask()
    _apply_task_fields(task, data)
    task.status = 'pending'
    task.log = '【整库一键迁移】任务已创建，等待启动'
    task.save()

    return {'status': 'success', 'message': '整库迁移任务创建成功', 'task_id': task.id}
