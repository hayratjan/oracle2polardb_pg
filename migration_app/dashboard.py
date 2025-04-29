from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import MigrationTask
from django.views.decorators.csrf import csrf_exempt
import logging
import json
import threading
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
import psycopg2

logger = logging.getLogger(__name__)

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

def task_detail(request, task_id):
    """
    显示任务详情页面
    """
    task = get_object_or_404(MigrationTask, pk=task_id)
    subtasks = None
    
    if task.is_batch:
        subtasks = task.subtasks.all().order_by('-created_at')
    
    return render(request, 'migration_app/task_detail.html', {
        'task': task,
        'subtasks': subtasks
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

def task_status(request, task_id):
    """获取任务状态"""
    # 确保从数据库获取最新状态
    from django.db import connection
    connection.close()
    
    task = get_object_or_404(MigrationTask, pk=task_id)
    logger.debug(f"获取任务状态: 任务ID={task_id}, 当前状态={task.status}, 进度={task.progress}%")
    
    # 构建响应数据
    response_data = {
        'status': task.status,
        'progress': task.progress,
        'log': task.log,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    }
    
    # 添加视图进度信息
    if hasattr(task, 'view_progress') and task.view_progress:
        try:
            # 如果view_progress是字符串，尝试解析为JSON
            if isinstance(task.view_progress, str):
                view_progress = json.loads(task.view_progress)
            else:
                view_progress = task.view_progress
                
            # 确保view_progress是字典类型
            if isinstance(view_progress, dict):
                response_data['view_progress'] = view_progress
        except Exception as e:
            logger.error(f"解析视图进度数据失败: {str(e)}")
            response_data['view_progress'] = {}
    else:
        response_data['view_progress'] = {}
    
    return JsonResponse(response_data)

@csrf_exempt
def start_task(request, task_id):
    """启动迁移任务"""
    # 添加详细的请求调试日志
    logger.info(f"收到启动任务请求: 任务ID={task_id}")
    logger.info(f"请求方法: {request.method}")
    logger.info(f"请求头: {dict(request.headers)}")
    if request.body:
        logger.info(f"请求体: {request.body.decode('utf-8')}")
    logger.info(f"Content-Type: {request.content_type}")
    
    if request.method in ['POST', 'GET']:
        try:
            logger.info(f"开始处理启动任务: 任务ID={task_id}")
            task = get_object_or_404(MigrationTask, pk=task_id)
            logger.info(f"任务信息: {task.name}, 当前状态: {task.status}")
            
            # 从请求中获取参数，如果请求中未提供则使用任务原有设置
            new_conflict_strategy = None
            postgres_database = None
            try:
                if request.method == 'POST' and request.body:
                    data = json.loads(request.body)
                    new_conflict_strategy = data.get('conflict_strategy')
                    postgres_database = data.get('postgres_database')
            except:
                pass

            if new_conflict_strategy:
                task.conflict_strategy = new_conflict_strategy
                logger.info(f"更新冲突处理策略为: {new_conflict_strategy}")
            
            if not postgres_database:
                # 如果没有提供数据库名，尝试从任务日志中获取
                if task.log and "目标PostgreSQL数据库:" in task.log:
                    for line in task.log.split('\n'):
                        if line.startswith("目标PostgreSQL数据库:"):
                            postgres_database = line.split(":", 1)[1].strip()
                            logger.info(f"从任务日志中获取到PostgreSQL数据库: {postgres_database}")
                            break
            
            # 如果是view_to_table类型且source_object为空，尝试从source_objects获取
            if task.task_type == 'view_to_table' and (not task.source_object or task.source_object.strip() == ''):
                if task.source_objects and task.source_objects.strip():
                    source_objects = task.source_objects.split(',')
                    if source_objects and source_objects[0].strip():
                        task.source_object = source_objects[0].strip()
                        task.save()
                        logger.info(f"从多个源对象中选取第一个视图: {task.source_object}")
            
            # 重置任务状态
            task.status = 'pending'
            task.cancel_requested = False
            task.progress = 0
            
            # 如果有数据库名，添加到日志中
            if postgres_database:
                task.log = f"目标PostgreSQL数据库: {postgres_database}"
            else:
                task.log = ''
                
            task.started_at = None
            task.completed_at = None
            task.save()
            logger.info(f"任务状态已重置为待执行: 任务ID={task_id}")
            
            # 确保任务状态已被更新并可以被客户端查询到
            from django.db import connection
            connection.close()
            
            # 导入视图模块以调用迁移函数
            from . import views
            
            # 检查任务类型是否有效
            if task.task_type not in ['table', 'materialized_view', 'view', 'routine', 'all_tables', 'view_to_table']:
                logger.error(f"未知的任务类型: {task.task_type}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'未知的任务类型: {task.task_type}'
                }, status=400)
            
            # 获取全局线程池    
            try:
                executor = views.get_task_executor()
                
                # 提交任务到线程池
                if task.task_type == 'table':
                    logger.info(f"提交表迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(views.migrate_table, task.id, postgres_database)
                elif task.task_type == 'materialized_view':
                    logger.info(f"提交物化视图迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(views.migrate_materialized_view, task.id, postgres_database)
                elif task.task_type == 'view':
                    logger.info(f"提交视图迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(views.migrate_view, task.id, postgres_database)
                elif task.task_type == 'routine':
                    logger.info(f"提交存储过程/函数迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(views.migrate_routine, task.id, postgres_database)
                elif task.task_type == 'all_tables':
                    logger.info(f"提交全部表迁移任务: {task.source_schema}.*")
                    executor.submit(views.migrate_all_tables, task.id, postgres_database)
                elif task.task_type == 'view_to_table':
                    logger.info(f"提交视图数据迁移到表任务: {task.source_schema}.{task.source_object}")
                    # 直接在当前进程中执行，以便调试
                    logger.info("直接执行migrate_view_to_table函数进行调试")
                    migrate_view_to_table(task.id, postgres_database)
                    logger.info("migrate_view_to_table函数执行完毕")
                    # 不要使用线程池
                    # from migration_app.dashboard import migrate_view_to_table
                    # executor.submit(migrate_view_to_table, task.id, postgres_database)
                
                logger.info(f"任务已成功提交执行: 任务ID={task_id}")
            except (RuntimeError, AttributeError) as e:
                # 处理线程池已关闭或为None的情况
                logger.error(f"线程池不可用，将使用独立线程执行任务: {str(e)}")
                
                # 创建独立线程执行任务
                def run_task():
                    try:
                        if task.task_type == 'table':
                            logger.info(f"开始执行表迁移任务: {task.source_schema}.{task.source_object}")
                            views.migrate_table(task.id, postgres_database)
                        elif task.task_type == 'materialized_view':
                            logger.info(f"开始执行物化视图迁移任务: {task.source_schema}.{task.source_object}")
                            views.migrate_materialized_view(task.id, postgres_database)
                        elif task.task_type == 'view':
                            logger.info(f"开始执行视图迁移任务: {task.source_schema}.{task.source_object}")
                            views.migrate_view(task.id, postgres_database)
                        elif task.task_type == 'routine':
                            logger.info(f"开始执行存储过程/函数迁移任务: {task.source_schema}.{task.source_object}")
                            views.migrate_routine(task.id, postgres_database)
                        elif task.task_type == 'all_tables':
                            logger.info(f"开始执行全部表迁移任务: {task.source_schema}.*")
                            views.migrate_all_tables(task.id, postgres_database)
                        elif task.task_type == 'view_to_table':
                            logger.info(f"开始执行视图数据迁移到表任务: {task.source_schema}.{task.source_object}")
                            # 直接在当前进程中执行，以便调试
                            logger.info("直接执行migrate_view_to_table函数进行调试")
                            migrate_view_to_table(task.id, postgres_database)
                            logger.info("migrate_view_to_table函数执行完毕")
                            # 不要使用单独线程
                            # from migration_app.dashboard import migrate_view_to_table
                            # migrate_view_to_table(task.id, postgres_database)
                    except Exception as e:
                        logger.error(f"任务执行时发生异常: {str(e)}", exc_info=True)
                
                # 启动后台线程
                task_thread = threading.Thread(target=run_task)
                task_thread.daemon = True  # 设置为守护线程，不会阻止主程序退出
                task_thread.start()
                logger.info(f"任务已在独立线程中启动: 任务ID={task_id}")
            
            # 如果是GET请求，重定向到任务详情页
            if request.method == 'GET':
                return redirect('migration_app:task_detail', task_id=task_id)
            # 如果是POST请求，返回JSON响应
            else:
                return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"启动任务时发生错误: {str(e)}", exc_info=True)
            if request.method == 'GET':
                messages.error(request, f"启动任务失败: {str(e)}")
                return redirect('migration_app:task_detail', task_id=task_id)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)
    
    logger.warning(f"非法的请求方法: {request.method}")
    if request.method == 'GET':
        messages.error(request, "请求方法不支持")
        return redirect('migration_app:task_list')
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method'
        }, status=405)

@csrf_exempt
def cancel_task(request, task_id):
    """取消迁移任务"""
    # 添加详细的请求调试日志
    logger.info(f"收到取消任务请求: 任务ID={task_id}")
    logger.info(f"请求方法: {request.method}")
    logger.info(f"请求头: {dict(request.headers)}")
    
    if request.method in ['POST', 'GET']:
        try:
            task = get_object_or_404(MigrationTask, pk=task_id)
            logger.info(f"任务信息: {task.name}, 当前状态: {task.status}")
            
            if task.status == 'running':
                # 设置取消标志
                task.cancel_requested = True
                task.save()
                message = "任务已标记为取消，将在当前操作完成后终止"
                logger.info(f"已取消任务 {task_id}")
            else:
                message = f"无法取消处于 {task.status} 状态的任务"
                logger.warning(message)
            
            # 如果是GET请求，重定向到任务详情页
            if request.method == 'GET':
                if task.status == 'running':
                    messages.success(request, message)
                else:
                    messages.warning(request, message)
                return redirect('migration_app:task_detail', task_id=task_id)
            # 如果是POST请求，返回JSON响应
            else:
                status = 'success' if task.status == 'canceled' else 'warning'
                return JsonResponse({
                    'status': status,
                    'message': message
                })
            
        except Exception as e:
            error_message = f"取消任务失败: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            if request.method == 'GET':
                messages.error(request, error_message)
                return redirect('migration_app:task_list')
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': error_message
                }, status=500)
    
    logger.warning(f"非法的请求方法: {request.method}")
    if request.method == 'GET':
        messages.error(request, "请求方法不支持")
        return redirect('migration_app:task_list')
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method'
        }, status=405)

def task_detailed_info(request, task_id):
    """获取任务的详细信息"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    
    # 构建详细信息响应
    info = {
        'id': task.id,
        'name': task.name,
        'task_type': task.task_type,
        'task_type_display': task.get_task_type_display(),
        'status': task.status,
        'status_display': dict(MigrationTask.STATUS_CHOICES).get(task.status, task.status),
        'progress': task.progress,
        'source_schema': task.source_schema,
        'target_schema': task.target_schema,
        'source_object': task.source_object,
        'source_objects': task.source_objects.split(',') if task.source_objects else [],
        'conflict_strategy': task.conflict_strategy,
        'conflict_strategy_display': dict(MigrationTask.CONFLICT_STRATEGY_CHOICES).get(task.conflict_strategy, task.conflict_strategy),
        'oracle_connection': {
            'id': task.oracle_connection.id,
            'name': task.oracle_connection.name,
            'host': task.oracle_connection.host,
            'port': task.oracle_connection.port,
            'service_name': task.oracle_connection.service_name,
            'username': task.oracle_connection.username,
        },
        'postgres_connection': {
            'id': task.postgres_connection.id,
            'name': task.postgres_connection.name,
            'host': task.postgres_connection.host,
            'port': task.postgres_connection.port,
            'database': task.postgres_connection.database,
            'username': task.postgres_connection.username,
        },
        'is_batch': task.is_batch,
        'cancel_requested': task.cancel_requested,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
    }
    
    # 如果有父任务，添加父任务信息
    if task.parent_task:
        info['parent_task'] = {
            'id': task.parent_task.id,
            'name': task.parent_task.name,
            'status': task.parent_task.status
        }
    
    # 如果是批量任务，添加子任务信息
    if task.is_batch:
        subtasks = []
        for subtask in task.subtasks.all():
            subtasks.append({
                'id': subtask.id,
                'name': subtask.name,
                'task_type': subtask.task_type,
                'status': subtask.status,
                'progress': subtask.progress,
                'source_object': subtask.source_object,
                'created_at': subtask.created_at.isoformat() if subtask.created_at else None,
            })
        info['subtasks'] = subtasks
    
    return JsonResponse(info)

@csrf_exempt
def switch_postgres_database(request, task_id):
    """
    切换任务的目标PostgreSQL数据库
    """
    try:
        task = MigrationTask.objects.get(id=task_id)
        
        # 从请求中获取数据库名称
        data = json.loads(request.body)
        postgres_database = data.get('postgres_database')
        
        if not postgres_database:
            return JsonResponse({'status': 'error', 'message': '未提供PostgreSQL数据库名称'})
        
        # 记录请求
        log_message = f"收到切换目标数据库请求：{postgres_database}"
        task.log = (task.log or '') + f"\n{log_message}"
        task.save()
        
        return JsonResponse({
            'status': 'success', 
            'message': f'已设置目标数据库为 {postgres_database}',
            'postgres_database': postgres_database
        })
        
    except MigrationTask.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '任务不存在'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# 数据查询API函数
@csrf_exempt
def get_schemas(request):
    """获取数据库Schema列表"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            connection_id = data.get('connection_id')
            conn_type = data.get('type', 'oracle')  # 默认为oracle
            limit = data.get('limit', 1000)  # 默认显示1000个
            database = data.get('database')  # PostgreSQL数据库名称，Oracle不需要
            
            if not connection_id:
                return JsonResponse({'status': 'error', 'message': '未提供连接ID'})
            
            schemas = []
            
            if conn_type == 'oracle':
                from . import views
                # 使用视图函数中定义的Oracle连接函数
                connection = views.get_oracle_connection(connection_id)
                cursor = connection.cursor()
                
                # 查询Oracle的schema列表，使用更通用的查询
                query = """
                SELECT USERNAME 
                FROM ALL_USERS 
                WHERE USERNAME NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'AUDSYS', 'CTXSYS', 'DVSYS', 'GSMADMIN_INTERNAL', 'LBACSYS', 'MDSYS', 'OJVMSYS', 'OLAPSYS', 'ORDDATA', 'ORDSYS', 'REMOTE_SCHEDULER_AGENT', 'WMSYS', 'XDB')
                ORDER BY USERNAME
                """
                cursor.execute(query)
                schemas = [row[0] for row in cursor.fetchall()]
                
                # 关闭游标和连接
                cursor.close()
                connection.close()
                
            elif conn_type == 'postgres':
                from . import views
                from .models import PostgresConnection
                # 使用视图函数中定义的PostgreSQL连接函数
                connection = views.get_postgres_connection(connection_id, database)
                cursor = connection.cursor()
                
                # 查询PostgreSQL的schema列表
                query = """
                SELECT schema_name 
                FROM information_schema.schemata 
                ORDER BY schema_name
                """
                cursor.execute(query)
                all_schemas = [row[0] for row in cursor.fetchall()]
                
                # 关闭游标和连接
                cursor.close()
                connection.close()
                
                # 限制返回结果数量
                schemas = all_schemas[:limit]
                
                # 如果还有更多结果，设置has_more标志
                has_more = len(all_schemas) > limit
                
                return JsonResponse({
                    'status': 'success',
                    'schemas': schemas,
                    'count': len(schemas),
                    'total': len(all_schemas),
                    'has_more': has_more
                })
            
            return JsonResponse({
                'status': 'success',
                'schemas': schemas
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@csrf_exempt
def get_database_objects(request):
    """获取数据库对象列表"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            connection_id = data.get('connection_id')
            schema = data.get('schema')
            object_type = data.get('object_type')
            search_term = data.get('search_term', '').strip()
            
            if not connection_id or not schema or not object_type:
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少必要参数：connection_id, schema, object_type'
                })
            
            from . import views
            # 使用视图函数中定义的Oracle连接函数
            connection = views.get_oracle_connection(connection_id)
            cursor = connection.cursor()
            
            objects = []
            
            if object_type == 'table':
                # 查询表
                query = """
                SELECT TABLE_NAME 
                FROM ALL_TABLES 
                WHERE OWNER = :schema 
                ORDER BY TABLE_NAME
                """
                cursor.execute(query, schema=schema)
                objects = [row[0] for row in cursor.fetchall()]
                
            elif object_type == 'view' or object_type == 'view_to_table':
                # 查询视图
                query = """
                SELECT VIEW_NAME 
                FROM ALL_VIEWS 
                WHERE OWNER = :schema 
                ORDER BY VIEW_NAME
                """
                cursor.execute(query, schema=schema)
                objects = [row[0] for row in cursor.fetchall()]
                
            elif object_type == 'materialized_view':
                # 查询物化视图
                query = """
                SELECT MVIEW_NAME 
                FROM ALL_MVIEWS 
                WHERE OWNER = :schema 
                ORDER BY MVIEW_NAME
                """
                cursor.execute(query, schema=schema)
                objects = [row[0] for row in cursor.fetchall()]
                
            elif object_type == 'routine':
                # 查询存储过程和函数
                query = """
                SELECT DISTINCT OBJECT_NAME 
                FROM ALL_OBJECTS 
                WHERE OWNER = :schema 
                  AND OBJECT_TYPE IN ('PROCEDURE', 'FUNCTION') 
                ORDER BY OBJECT_NAME
                """
                cursor.execute(query, schema=schema)
                objects = [row[0] for row in cursor.fetchall()]
            
            # 如果提供了搜索词，进行过滤
            if search_term:
                objects = [obj for obj in objects if search_term.lower() in obj.lower()]
            
            # 关闭游标和连接
            cursor.close()
            connection.close()
            
            return JsonResponse({
                'status': 'success',
                'objects': objects
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@csrf_exempt
def get_postgres_databases(request):
    """获取PostgreSQL数据库列表"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            connection_id = data.get('connection_id')
            
            if not connection_id:
                return JsonResponse({'status': 'error', 'message': '未提供连接ID'})
            
            # 获取PostgreSQL连接信息
            from .models import PostgresConnection
            pg_conn = get_object_or_404(PostgresConnection, pk=connection_id)
            
            # 连接到PostgreSQL服务器的postgres数据库
            conn = psycopg2.connect(
                host=pg_conn.host,
                port=pg_conn.port,
                database='postgres',  # 使用默认数据库连接
                user=pg_conn.username,
                password=pg_conn.password
            )
            cursor = conn.cursor()
            
            # 查询所有非系统数据库
            cursor.execute("""
            SELECT datname FROM pg_database 
            WHERE datistemplate = false AND datname != 'postgres' 
            ORDER BY datname
            """)
            
            databases = [row[0] for row in cursor.fetchall()]
            
            # 添加默认连接的数据库到列表首位
            if pg_conn.database not in databases:
                databases.insert(0, pg_conn.database)
            else:
                databases.remove(pg_conn.database)
                databases.insert(0, pg_conn.database)
            
            # 关闭游标和连接
            cursor.close()
            conn.close()
            
            return JsonResponse({
                'status': 'success',
                'databases': databases
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

# 添加缺失的迁移函数
def migrate_view_to_table(task_id, postgres_database=None):
    """将视图数据迁移到表中"""
    # 避免循环导入
    from . import views
    from .views import convert_oracle_to_pg_type
    from django.utils import timezone
    
    logger.info(f"开始执行视图数据迁移到表任务: 任务ID={task_id}")
    task = get_object_or_404(MigrationTask, pk=task_id)
    logger.info(f"任务详情: 名称={task.name}, 源={task.source_schema}.{task.source_object}")
    
    # 在任务开始时初始化进度和日志
    task.status = 'running'
    task.started_at = timezone.now()
    task.progress = 0
    task.view_progress = json.dumps({})  # 初始化为空的JSON对象
    task.save()
    
    # 确保数据库提交已完成
    from django.db import connection
    connection.close()
    
    log = []
    
    # 记录数据库信息
    if postgres_database:
        log.append(f"目标PostgreSQL数据库: {postgres_database}")
        logger.info(f"使用指定的PostgreSQL数据库: {postgres_database}")
    else:
        # 如果未指定，使用默认数据库
        postgres_database = task.postgres_connection.database
        log.append(f"目标PostgreSQL数据库(默认): {postgres_database}")
        logger.info(f"使用默认PostgreSQL数据库: {postgres_database}")
    
    try:
        # 连接Oracle数据库
        logger.info(f"尝试连接Oracle数据库: {task.oracle_connection.name}")
        log.append(f"正在连接Oracle数据库: {task.oracle_connection.name}")
        
        try:
            oracle_conn = views.get_oracle_connection(task.oracle_connection.id)
            oracle_cursor = oracle_conn.cursor()
            log.append(f"已成功连接Oracle数据库")
            logger.info(f"已成功连接Oracle数据库")
        except Exception as ora_err:
            error_msg = f"连接Oracle数据库失败: {str(ora_err)}"
            logger.error(error_msg, exc_info=True)
            task.status = 'failed'
            task.log = '\n'.join(log + [error_msg])
            task.completed_at = timezone.now()
            task.save()
            return
        
        # 连接PostgreSQL数据库
        logger.info(f"尝试连接PostgreSQL数据库: {task.postgres_connection.name}, 数据库: {postgres_database}")
        log.append(f"正在连接PostgreSQL数据库: {task.postgres_connection.name}")
        
        try:
            pg_conn = views.get_postgres_connection(task.postgres_connection.id, postgres_database)
            pg_cursor = pg_conn.cursor()
            
            # 获取PostgreSQL数据库名
            pg_cursor.execute("SELECT current_database()")
            current_db = pg_cursor.fetchone()[0]
            log.append(f"已成功连接PostgreSQL数据库: {current_db}")
            logger.info(f"已成功连接PostgreSQL数据库: {current_db}")
        except Exception as pg_err:
            error_msg = f"连接PostgreSQL数据库失败: {str(pg_err)}"
            logger.error(error_msg, exc_info=True)
            oracle_cursor.close()
            oracle_conn.close()
            task.status = 'failed'
            task.log = '\n'.join(log + [error_msg])
            task.completed_at = timezone.now()
            task.save()
            return
        
        # 获取要迁移的视图列表
        views_to_migrate = []
        if task.source_objects and task.source_objects.strip():
            views_to_migrate = [v.strip() for v in task.source_objects.split(',') if v.strip()]
            log.append(f"将迁移以下视图数据到表: {', '.join(views_to_migrate)}")
            logger.info(f"将迁移 {len(views_to_migrate)} 个视图数据到表")
        elif task.source_object and task.source_object.strip():
            views_to_migrate = [task.source_object.strip()]
            log.append(f"将迁移视图 {task.source_object} 数据到表")
            logger.info(f"将迁移单个视图 {task.source_object} 数据到表")
        else:
            error_msg = "未指定要迁移的视图"
            logger.error(error_msg)
            oracle_cursor.close()
            oracle_conn.close()
            pg_cursor.close()
            pg_conn.close()
            task.status = 'failed'
            task.log = '\n'.join(log + [error_msg])
            task.completed_at = timezone.now()
            task.save()
            return
        
        # 处理每个视图
        successful_views = []
        failed_views = []
        total_views = len(views_to_migrate)
        
        for index, view_name in enumerate(views_to_migrate):
            # 检查是否请求了取消
            task.refresh_from_db()
            if task.cancel_requested:
                log.append(f"收到取消请求，停止处理后续视图")
                logger.info(f"任务 {task_id} 收到取消请求，停止处理")
                task.status = 'canceled'
                task.log = '\n'.join(log)
                task.completed_at = timezone.now()
                task.save()
                
                # 关闭数据库连接
                try:
                    oracle_cursor.close()
                    oracle_conn.close()
                    pg_cursor.close()
                    pg_conn.close()
                except Exception as close_err:
                    logger.error(f"关闭数据库连接出错: {str(close_err)}", exc_info=True)
                
                return
            
            # 更新进度
            current_progress = (index / total_views) * 100
            task.progress = current_progress
            task.view_progress = json.dumps({view_name: {'progress': 0, 'log': []}})
            task.save()
            
            view_log = []
            view_log.append(f"=== 开始处理视图 {view_name} ({index+1}/{total_views}) ===")
            logger.info(f"开始处理视图 {view_name} ({index+1}/{total_views})")
            
            try:
                # 获取视图定义
                query = """
                SELECT TEXT FROM ALL_VIEWS 
                WHERE OWNER = :schema AND VIEW_NAME = :view_name
                """
                logger.debug(f"执行SQL: {query}, 参数: schema={task.source_schema}, view_name={view_name}")
                oracle_cursor.execute(query, schema=task.source_schema, view_name=view_name)
                result = oracle_cursor.fetchone()
                
                if not result:
                    error_msg = f"找不到视图 {task.source_schema}.{view_name}"
                    logger.error(error_msg)
                    view_log.append(error_msg)
                    failed_views.append(view_name)
                    task.view_progress = json.dumps({view_name: {'progress': 0, 'log': view_log}})
                    task.save()
                    continue
                
                view_text = result[0]
                view_log.append(f"获取到视图定义: {view_text}")
                logger.info(f"获取到视图 {view_name} 的定义")
                
                # 获取视图列信息
                query = """
                SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE
                FROM ALL_TAB_COLUMNS
                WHERE OWNER = :schema AND TABLE_NAME = :view_name
                ORDER BY COLUMN_ID
                """
                logger.debug(f"执行SQL: {query}, 参数: schema={task.source_schema}, view_name={view_name}")
                oracle_cursor.execute(query, schema=task.source_schema, view_name=view_name)
                columns = oracle_cursor.fetchall()
                
                if not columns:
                    error_msg = f"找不到视图 {task.source_schema}.{view_name} 的列信息"
                    logger.error(error_msg)
                    view_log.append(error_msg)
                    failed_views.append(view_name)
                    task.view_progress = json.dumps({view_name: {'progress': 0, 'log': view_log}})
                    task.save()
                    continue
                
                # 创建PostgreSQL中的表
                create_table_sql = f"CREATE TABLE {task.target_schema}.{view_name} (\n"
                column_defs = []
                
                view_log.append(f"获取到视图列信息: 共 {len(columns)} 列")
                logger.info(f"获取到视图 {view_name} 的列信息: 共 {len(columns)} 列")
                
                for column in columns:
                    column_name, data_type, data_length, data_precision, data_scale, nullable = column
                    logger.debug(f"处理列: {column_name}, 类型: {data_type}, 长度: {data_length}, 精度: {data_precision}, 小数位: {data_scale}, 可空: {nullable}")
                    
                    try:
                        pg_type = convert_oracle_to_pg_type(data_type, data_length, data_precision, data_scale)
                        logger.debug(f"列 {column_name} 的Oracle类型 {data_type} 转换为PostgreSQL类型 {pg_type}")
                    except Exception as te:
                        logger.error(f"类型转换失败: {str(te)}", exc_info=True)
                        pg_type = "TEXT"  # 失败时使用TEXT作为默认类型
                        view_log.append(f"警告: 列 {column_name} 的类型转换失败，将使用TEXT: {str(te)}")
                    
                    if data_type == 'VARCHAR2' and (data_length is None or data_length == 0):
                        view_log.append(f"警告: 列 {column_name} 的VARCHAR长度为0，已自动调整为VARCHAR(255)")
                        logger.warning(f"列 {column_name} 的VARCHAR长度为0，已自动调整为VARCHAR(255)")
                        pg_type = "VARCHAR(255)"
                    
                    not_null = "" if nullable == 'Y' else " NOT NULL"
                    column_defs.append(f"    {column_name} {pg_type}{not_null}")
                
                create_table_sql += ",\n".join(column_defs)
                create_table_sql += "\n)"
                
                view_log.append(f"创建表SQL: \n{create_table_sql}")
                logger.info(f"生成创建表SQL: {view_name}")
                
                # 执行创建表
                try:
                    # 检查是否已存在表，如存在则根据冲突策略处理
                    pg_cursor.execute(f"SELECT to_regclass('{task.target_schema}.{view_name}')")
                    table_exists = pg_cursor.fetchone()[0] is not None
                    
                    if table_exists:
                        logger.info(f"表 {task.target_schema}.{view_name} 已存在，冲突策略: {task.conflict_strategy}")
                        if task.conflict_strategy == 'error':
                            error_msg = f"表 {task.target_schema}.{view_name} 已存在"
                            logger.error(error_msg)
                            raise Exception(error_msg)
                        elif task.conflict_strategy == 'replace':
                            logger.info(f"删除已存在的表 {task.target_schema}.{view_name}")
                            pg_cursor.execute(f"DROP TABLE IF EXISTS {task.target_schema}.{view_name}")
                            pg_conn.commit()
                            view_log.append(f"已删除已存在的表 {task.target_schema}.{view_name}")
                        elif task.conflict_strategy == 'skip':
                            logger.info(f"跳过已存在的表 {task.target_schema}.{view_name}")
                            view_log.append(f"表 {task.target_schema}.{view_name} 已存在，已跳过")
                            successful_views.append(view_name)
                            task.view_progress = json.dumps({view_name: {'progress': 100, 'log': view_log}})
                            task.save()
                            continue
                        elif task.conflict_strategy == 'truncate':
                            logger.info(f"清空表 {task.target_schema}.{view_name}")
                            pg_cursor.execute(f"TRUNCATE TABLE {task.target_schema}.{view_name}")
                            pg_conn.commit()
                            view_log.append(f"已清空表 {task.target_schema}.{view_name}")
                            # 继续执行数据导入部分
                        elif task.conflict_strategy == 'append':
                            logger.info(f"表 {task.target_schema}.{view_name} 已存在，将追加数据")
                            view_log.append(f"表 {task.target_schema}.{view_name} 已存在，将追加数据")
                            # 不创建表，只导入数据
                    
                    # 如果不是追加或清空数据，需要创建表
                    if not table_exists or (task.conflict_strategy not in ['append', 'truncate']):
                        logger.info(f"执行创建表: {task.target_schema}.{view_name}")
                        pg_cursor.execute(create_table_sql)
                        pg_conn.commit()
                        view_log.append(f"成功创建PostgreSQL表 {task.target_schema}.{view_name}")
                    
                    # 从Oracle视图查询数据并插入到PostgreSQL表中
                    oracle_query = f"SELECT * FROM {task.source_schema}.{view_name}"
                    view_log.append(f"查询视图数据SQL: {oracle_query}")
                    logger.info(f"从视图 {view_name} 查询数据")
                    
                    # 使用游标分批获取数据
                    oracle_cursor.arraysize = 5000  # 设置每次获取5000条记录
                    oracle_cursor.execute(oracle_query)
                    
                    # 获取列名（小写）
                    column_names = [col[0].lower() for col in oracle_cursor.description]
                    
                    # 创建INSERT语句
                    placeholders = ", ".join(["%s"] * len(column_names))
                    insert_sql = f"INSERT INTO {task.target_schema}.{view_name.lower()} ({', '.join(['\"' + col + '\"' for col in column_names])}) VALUES ({placeholders})"
                    
                    # 分批处理数据
                    total_rows = 0
                    while True:
                        rows = oracle_cursor.fetchmany()
                        if not rows:
                            break
                        
                        # 批量插入数据
                        pg_cursor.executemany(insert_sql, rows)
                        pg_conn.commit()
                        
                        total_rows += len(rows)
                        
                        # 更新视图进度
                        try:
                            # 获取当前视图进度数据
                            current_progress = json.loads(task.view_progress) if task.view_progress else {}
                            
                            # 计算当前视图的进度
                            view_progress = (total_rows / 1000000) * 100  # 假设最大100万条记录
                            if view_progress > 100:
                                view_progress = 100
                            
                            # 更新当前视图的进度和日志
                            current_progress[view_name] = {
                                'progress': view_progress,
                                'log': view_log
                            }
                            
                            # 保存更新后的进度
                            task.view_progress = json.dumps(current_progress)
                            task.save()
                            
                        except Exception as e:
                            logger.error(f"更新视图进度失败: {str(e)}")
                        
                        logger.info(f"已导入 {total_rows} 行数据到表 {task.target_schema}.{view_name}")
                    
                    view_log.append(f"成功从视图导入 {total_rows} 行数据到表 {task.target_schema}.{view_name}")
                    successful_views.append(view_name)
                    task.view_progress = json.dumps({view_name: {'progress': 100, 'log': view_log}})
                    task.save()
                    
                except Exception as table_err:
                    error_msg = f"创建表或导入数据时出错: {str(table_err)}"
                    logger.error(error_msg, exc_info=True)
                    view_log.append(error_msg)
                    failed_views.append(view_name)
                    task.view_progress = json.dumps({view_name: {'progress': 0, 'log': view_log}})
                    task.save()
                
            except Exception as view_err:
                error_msg = f"处理视图 {view_name} 时发生错误: {str(view_err)}"
                logger.error(error_msg, exc_info=True)
                view_log.append(error_msg)
                failed_views.append(view_name)
                task.view_progress = json.dumps({view_name: {'progress': 0, 'log': view_log}})
                task.save()
        
        # 关闭连接
        try:
            oracle_cursor.close()
            oracle_conn.close()
            pg_cursor.close()
            pg_conn.close()
            logger.info("数据库连接已关闭")
        except Exception as close_err:
            logger.error(f"关闭数据库连接出错: {str(close_err)}", exc_info=True)
            log.append(f"警告: 关闭数据库连接时出错: {str(close_err)}")
        
        # 检查是否请求了取消
        task.refresh_from_db()
        if task.cancel_requested:
            task.status = 'canceled'
            log.append(f"任务已取消")
            logger.info(f"任务 {task_id} 已标记为已取消")
        # 否则更新任务结果
        elif len(failed_views) == 0 and len(successful_views) > 0:
            task.status = 'completed'
            log.append(f"所有视图迁移成功: {', '.join(successful_views)}")
            logger.info(f"所有视图迁移成功: {', '.join(successful_views)}")
        elif len(successful_views) == 0 and len(failed_views) > 0:
            task.status = 'failed'
            log.append(f"所有视图迁移失败: {', '.join(failed_views)}")
            logger.error(f"所有视图迁移失败: {', '.join(failed_views)}")
        elif len(successful_views) > 0 and len(failed_views) > 0:
            task.status = 'partial'
            log.append(f"=== 部分视图迁移成功:")
            log.append(f"成功视图: {', '.join(successful_views)}")
            log.append(f"失败视图: {', '.join(failed_views)}")
            logger.warning(f"部分视图迁移成功: 成功={len(successful_views)}, 失败={len(failed_views)}")
        
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
        
        # 确保数据库提交已完成
        from django.db import connection
        connection.close()
        
    except Exception as e:
        logger.error(f"视图数据迁移到表任务执行失败: {str(e)}", exc_info=True)
        
        # 检查是否请求了取消
        task.refresh_from_db()
        if task.cancel_requested:
            task.status = 'canceled'
            log.append(f"任务已取消")
        else:
            task.status = 'failed'
            log.append(f"任务执行出错: {str(e)}")
            
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
        
        # 确保数据库提交已完成
        from django.db import connection
        connection.close()
    finally:
        logger.info(f"视图数据迁移到表任务结束: 状态={task.status}") 