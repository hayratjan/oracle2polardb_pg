from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import MigrationTask, AuditLog
from .batch_config import (
    MIGRATION_COMMIT_EVERY_BATCHES,
    MIGRATION_FETCH_BATCH_SIZE,
    MIGRATION_PROGRESS_SAVE_ROWS,
)
from .oracle_row_adapter import adapt_oracle_rows
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import logging
import json
import threading
import importlib
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
import psycopg2
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def record_audit(request, action, target_type='', target_id=None, payload=None, result='success'):
    """记录审计日志"""
    try:
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            payload=payload,
            result=result,
        )
    except Exception as e:
        logger.error(f'记录审计日志失败: {e}', exc_info=True)

SQLITE_ALLOWED_SUFFIXES = ('.sqlite', '.sqlite3', '.db')

@login_required
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

@login_required
def task_list(request):
    """
    显示所有迁移任务
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    # 获取查询参数
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    
    # 构建查询
    tasks = MigrationTask.objects.all().order_by('-created_at')
    
    # 搜索过滤
    if search:
        from django.db.models import Q
        tasks = tasks.filter(
            Q(name__icontains=search) |
            Q(oracle_connection__name__icontains=search) |
            Q(postgres_connection__name__icontains=search) |
            Q(source_schema__icontains=search) |
            Q(target_schema__icontains=search)
        )
    
    # 状态过滤
    if status_filter and status_filter != 'all':
        tasks = tasks.filter(status=status_filter)
    
    # 分页
    paginator = Paginator(tasks, 20)  # 每页显示20条
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    return render(request, 'migration_app/task_list.html', {
        'tasks': page_obj,
        'search': search,
        'status_filter': status_filter
    })

@login_required
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

@login_required
def database_info(request):
    """
    显示数据库连接信息
    """
    return render(request, 'migration_app/database_info.html')

# 新增数据库管理视图
@login_required
def oracle_schemas(request):
    """
    Oracle数据库架构管理
    """
    return render(request, 'migration_app/oracle/schemas.html')

@login_required
def oracle_tables(request):
    """
    Oracle数据库表管理
    """
    return render(request, 'migration_app/oracle/tables.html')

@login_required
def oracle_users(request):
    """
    Oracle数据库用户管理
    """
    return render(request, 'migration_app/oracle/users.html')

@login_required
def pg_schemas(request):
    """
    PolarDB-PG数据库架构管理
    """
    return render(request, 'migration_app/polardb/schemas.html')

@login_required
def pg_tables(request):
    """
    PolarDB-PG数据库表管理
    """
    return render(request, 'migration_app/polardb/tables.html')

@login_required
def pg_users(request):
    """
    PolarDB-PG数据库用户管理
    """
    return render(request, 'migration_app/polardb/users.html')

# 系统配置视图
@login_required
def migration_settings(request):
    """
    迁移参数配置
    """
    return render(request, 'migration_app/config/migration_settings.html')

@login_required
def system_settings(request):
    """
    系统参数配置
    """
    return render(request, 'migration_app/config/system_settings.html')

@login_required
def migration_logs(request):
    """
    迁移日志
    """
    return render(request, 'migration_app/logs.html')

@login_required
def help_docs(request):
    """
    帮助文档
    """
    return render(request, 'migration_app/help.html')

@login_required
def task_status(request, task_id):
    """获取任务状态。支持 ?light=1 轻量轮询：不返回 log，view_progress 仅含 progress/total_rows/migrated_rows，减少响应体积。"""
    # 确保从数据库获取最新状态
    from django.db import connection
    connection.close()
    
    task = get_object_or_404(MigrationTask, pk=task_id)
    light = request.GET.get('light') == '1'
    # 轻量轮询仅读进度，不做孤儿修正（避免多 Worker/跨进程时误标 aborted 导致前端停止刷新）
    if not light:
        from .task_lifecycle import reconcile_orphan_running_task
        if reconcile_orphan_running_task(task):
            task.refresh_from_db()
    logger.debug(f"获取任务状态: 任务ID={task_id}, 当前状态={task.status}, 进度={task.progress}%, light={light}")
    
    # 构建响应数据
    response_data = {
        'status': task.status,
        'progress': task.progress,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'cancel_requested': getattr(task, 'cancel_requested', False),
    }
    if not light:
        response_data['log'] = task.log
    elif task.status == 'running' and task.log:
        # 轻量轮询仍返回日志尾部，便于展示分批迁移进度
        response_data['log'] = task.log[-12000:]
    
    # 添加视图进度信息；light 模式下不包含 log，减小响应体积
    if hasattr(task, 'view_progress') and task.view_progress:
        try:
            if isinstance(task.view_progress, str):
                view_progress = json.loads(task.view_progress)
            else:
                view_progress = task.view_progress
            if isinstance(view_progress, dict):
                if light:
                    # 「所有表」任务：汇总字段 + 当前表行级进度（供进度条展示）
                    if 'current' in view_progress and 'total' in view_progress:
                        response_data['view_progress'] = {
                            k: v for k, v in view_progress.items()
                            if k in (
                                'current_table', 'current', 'total', 'failed_count',
                                'completed_tables', 'running_tables', 'parallel_workers',
                            )
                        }
                        ct = view_progress.get('current_table')
                        if ct and isinstance(view_progress.get(ct), dict):
                            response_data['view_progress'][ct] = {
                                kk: vv for kk, vv in view_progress[ct].items()
                                if kk in ('progress', 'total_rows', 'migrated_rows')
                            }
                    else:
                        # 表/视图级进度：只保留 progress、total_rows、migrated_rows
                        response_data['view_progress'] = {
                            k: {kk: vv for kk, vv in (v.items() if isinstance(v, dict) else []) if kk in ('progress', 'total_rows', 'migrated_rows')}
                            for k, v in view_progress.items() if isinstance(v, dict)
                        }
                else:
                    response_data['view_progress'] = view_progress
            else:
                response_data['view_progress'] = {}
        except Exception as e:
            logger.error(f"解析视图进度数据失败: {str(e)}")
            response_data['view_progress'] = {}
    else:
        response_data['view_progress'] = {}
    
    return JsonResponse(response_data)

@login_required
@csrf_exempt
def start_task(request, task_id):
    """启动迁移任务"""
    # v2.4: 移除请求头/体调试日志(含 Cookie/Authorization/密码字段,泄露敏感信息)
    # 仅保留必要审计信息
    logger.info(f"收到启动任务请求: 任务ID={task_id} 方法={request.method} 用户={request.user.username if request.user.is_authenticated else 'anon'}")

    if request.method == 'POST':
        try:
            logger.info(f"开始处理启动任务: 任务ID={task_id}")
            task = get_object_or_404(MigrationTask, pk=task_id)
            logger.info(f"任务信息: {task.name}, 当前状态: {task.status}")

            if task.status == 'running':
                return JsonResponse({
                    'status': 'error',
                    'message': '任务已在执行中',
                }, status=400)

            from .platform_config import can_start_new_task
            allowed, limit_msg = can_start_new_task()
            if not allowed:
                return JsonResponse({'status': 'error', 'message': limit_msg}, status=400)
            
            # 从请求中获取参数，如果请求中未提供则使用任务原有设置
            new_conflict_strategy = None
            postgres_database = None
            resume = False
            try:
                if request.method == 'POST' and request.body:
                    data = json.loads(request.body)
                    new_conflict_strategy = data.get('conflict_strategy')
                    postgres_database = data.get('postgres_database')
                    resume = bool(data.get('resume', False))
            except Exception:
                pass

            if new_conflict_strategy:
                task.conflict_strategy = new_conflict_strategy
                logger.info(f"更新冲突处理策略为: {new_conflict_strategy}")

            from .resume import can_resume_task, get_completed_tables, normalize_view_progress

            if resume and not can_resume_task(task):
                return JsonResponse({
                    'status': 'error',
                    'message': f'当前状态 {task.status} 不支持继续迁移，请使用重新运行',
                }, status=400)
            
            if task.task_type != 'view_to_sqlite':
                if not postgres_database:
                    # 优先使用任务保存的目标数据库字段
                    postgres_database = getattr(task, 'postgres_database', None) or (task.postgres_connection.database if task.postgres_connection else None)
                    if not postgres_database and task.log and "目标PostgreSQL数据库:" in task.log:
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
            
            # 继续迁移：保留进度、日志与已完成表；重新运行：清空后从头执行
            task.status = 'pending'
            task.cancel_requested = False
            task.completed_at = None

            if resume:
                vp = normalize_view_progress(task.view_progress)
                completed = get_completed_tables(task)
                vp['resume'] = True
                vp['completed_tables'] = sorted(completed)
                task.view_progress = vp
                if not task.started_at:
                    task.started_at = timezone.now()
                prev_log = (task.log or '').strip()
                resume_head = (
                    f"\n---\n【继续迁移】从断点恢复，已完成 {len(completed)} 张表，"
                    f"进度 {task.progress:.1f}%"
                )
                task.log = (prev_log + resume_head) if prev_log else resume_head.strip()
                logger.info(f"继续迁移任务: 任务ID={task_id}, 已完成表数={len(completed)}")
            else:
                task.progress = 0
                if task.task_type == 'view_to_sqlite':
                    task.log = f"SQLite文件: {task.sqlite_path or '未配置'}"
                elif postgres_database:
                    task.log = f"目标PostgreSQL数据库: {postgres_database}"
                else:
                    task.log = ''
                task.started_at = None
                task.view_progress = {}
                logger.info(f"重新运行任务（从头开始）: 任务ID={task_id}")

            task.save()
            logger.info(f"任务状态已置为待执行: 任务ID={task_id}, resume={resume}")
            
            # 记录审计日志
            record_audit(
                request,
                action='start_task',
                target_type='task',
                target_id=task_id,
                payload={'resume': resume, 'postgres_database': postgres_database},
                result='success'
            )
            
            # 确保任务状态已被更新并可以被客户端查询到
            from django.db import connection
            connection.close()
            
            # 导入视图模块以调用迁移函数
            from . import views
            from .task_lifecycle import run_with_lifecycle
            from django.conf import settings as dj_settings

            valid_task_types = [
                'table', 'materialized_view', 'view', 'routine', 'all_tables',
                'view_to_table', 'view_to_sqlite', 'trigger', 'sequence', 'full_schema',
                'table_batch', 'full_database',
            ]
            if task.task_type not in valid_task_types:
                logger.error(f"未知的任务类型: {task.task_type}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'未知的任务类型: {task.task_type}'
                }, status=400)

            # 若配置了 Celery Broker，则交由 Worker 执行（企业部署推荐）
            broker = (getattr(dj_settings, 'CELERY_BROKER_URL', None) or '').strip()
            if broker:
                from migration_app.tasks import celery_run_migration_task
                celery_run_migration_task.delay(task.id, postgres_database)
                logger.info(f"任务已提交 Celery 队列: 任务ID={task_id}")
                if request.method == 'GET':
                    return redirect('migration_app:task_detail', task_id=task_id)
                return JsonResponse({'status': 'success', 'queued': 'celery'})

            # 获取全局线程池（未配置 Celery 时）
            try:
                executor = views.get_task_executor()

                # 提交任务到线程池
                if task.task_type == 'table':
                    logger.info(f"提交表迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(run_with_lifecycle, task.id, views.migrate_table, task.id, postgres_database)
                elif task.task_type == 'materialized_view':
                    logger.info(f"提交物化视图迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(run_with_lifecycle, task.id, views.migrate_materialized_view, task.id, postgres_database)
                elif task.task_type == 'view':
                    logger.info(f"提交视图迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(run_with_lifecycle, task.id, views.migrate_view, task.id, postgres_database)
                elif task.task_type == 'routine':
                    logger.info(f"提交存储过程/函数迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(run_with_lifecycle, task.id, views.migrate_routine, task.id, postgres_database)
                elif task.task_type == 'trigger':
                    logger.info(f"提交触发器迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(run_with_lifecycle, task.id, views.migrate_trigger, task.id, postgres_database)
                elif task.task_type == 'sequence':
                    logger.info(f"提交序列迁移任务: {task.source_schema}.{task.source_object}")
                    executor.submit(run_with_lifecycle, task.id, views.migrate_sequence, task.id, postgres_database)
                elif task.task_type == 'full_schema':
                    logger.info(f"提交全 Schema 编排任务: {task.source_schema}")
                    def run_full_schema():
                        try:
                            # v2.4: 移除 importlib.reload(v) — 在线程内重载模块会影响所有线程,
                            # 导致其它线程持有的旧引用进入半重载状态,引发 NameError/AttributeError
                            import migration_app.views as v
                            v.migrate_schema_orchestration(task.id, postgres_database)
                        except Exception as ex:
                            logger.error(f"编排迁移异常: {str(ex)}", exc_info=True)
                    t2 = threading.Thread(target=lambda: run_with_lifecycle(task.id, run_full_schema))
                    t2.daemon = True
                    t2.start()
                elif task.task_type == 'full_database':
                    logger.info(f"提交整库一键迁移任务: {task.name}")
                    def run_full_db():
                        try:
                            from migration_app import full_database as fd
                            fd.migrate_full_database(task.id, postgres_database)
                        except Exception as ex:
                            logger.error(f"整库迁移异常: {str(ex)}", exc_info=True)
                    t3 = threading.Thread(target=lambda: run_with_lifecycle(task.id, run_full_db))
                    t3.daemon = True
                    t3.start()
                elif task.task_type == 'table_batch':
                    logger.info(f"提交表级批量迁移任务: {task.source_schema}")
                    executor.submit(run_with_lifecycle, task.id, views.migrate_table, task.id, postgres_database)
                elif task.task_type == 'all_tables':
                    # 所有表迁移不使用线程池，避免 interpreter shutdown 时 submit 报错；用独立线程并重载 views 确保跑最新逻辑
                    logger.info(f"提交全部表迁移任务（独立线程）: {task.source_schema}.*")
                    def run_all_tables():
                        try:
                            import migration_app.views as v
                            importlib.reload(v)
                            v.migrate_all_tables(task.id, postgres_database)
                        except Exception as e:
                            logger.error(f"全部表迁移任务异常: {str(e)}", exc_info=True)
                    t = threading.Thread(target=lambda: run_with_lifecycle(task.id, run_all_tables))
                    t.daemon = True
                    t.start()
                elif task.task_type == 'view_to_table':
                    logger.info(f"提交视图数据迁移到表任务（线程池异步）: {task.source_schema}.{task.source_object}")
                    executor.submit(run_with_lifecycle, task.id, migrate_view_to_table, task.id, postgres_database)
                elif task.task_type == 'view_to_sqlite':
                    logger.info(f"提交视图迁移到SQLite任务: {task.source_schema}")
                    run_with_lifecycle(task.id, migrate_view_to_sqlite, task.id)

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
                        elif task.task_type == 'trigger':
                            logger.info(f"开始执行触发器迁移任务: {task.source_schema}.{task.source_object}")
                            views.migrate_trigger(task.id, postgres_database)
                        elif task.task_type == 'sequence':
                            logger.info(f"开始执行序列迁移任务: {task.source_schema}.{task.source_object}")
                            views.migrate_sequence(task.id, postgres_database)
                        elif task.task_type == 'full_schema':
                            logger.info(f"开始执行全 Schema 编排任务: {task.source_schema}")
                            import migration_app.views as v
                            importlib.reload(v)
                            v.migrate_schema_orchestration(task.id, postgres_database)
                        elif task.task_type == 'full_database':
                            logger.info(f"开始执行整库一键迁移: {task.name}")
                            from migration_app import full_database as fd
                            fd.migrate_full_database(task.id, postgres_database)
                        elif task.task_type == 'table_batch':
                            logger.info(f"开始执行表级批量迁移: {task.source_schema}")
                            views.migrate_table(task.id, postgres_database)
                        elif task.task_type == 'all_tables':
                            logger.info(f"开始执行全部表迁移任务（重载 views 后执行）: {task.source_schema}.*")
                            import migration_app.views as v
                            importlib.reload(v)
                            v.migrate_all_tables(task.id, postgres_database)
                        elif task.task_type == 'view_to_table':
                            logger.info(f"开始执行视图数据迁移到表任务: {task.source_schema}.{task.source_object}")
                            migrate_view_to_table(task.id, postgres_database)
                        elif task.task_type == 'view_to_sqlite':
                            logger.info("开始执行视图迁移到SQLite任务")
                            migrate_view_to_sqlite(task.id)
                    except Exception as e:
                        logger.error(f"任务执行时发生异常: {str(e)}", exc_info=True)

                # 启动后台线程
                task_thread = threading.Thread(target=lambda: run_with_lifecycle(task.id, run_task))
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

@login_required
@csrf_exempt
def cancel_task(request, task_id):
    """取消迁移任务"""
    # v2.4: 移除请求头调试日志(含 Cookie 等敏感信息),仅保留必要审计信息
    logger.info(f"收到取消任务请求: 任务ID={task_id} 方法={request.method} 用户={request.user.username if request.user.is_authenticated else 'anon'}")

    if request.method == 'POST':
        try:
            task = get_object_or_404(MigrationTask, pk=task_id)
            logger.info(f"任务信息: {task.name}, 当前状态: {task.status}")
            
            if task.status == 'running':
                # 标记取消并立即更新状态，前端可以立刻看到“已取消”
                task.cancel_requested = True
                task.status = 'canceled'
                task.completed_at = timezone.now()
                log_message = "任务已被用户请求取消"
                task.log = (task.log or "") + ("\n" if task.log else "") + log_message
                task.save()
                message = "任务已取消"
                logger.info(f"任务 {task_id} 已标记为取消")
                
                # 记录审计日志
                record_audit(
                    request,
                    action='cancel_task',
                    target_type='task',
                    target_id=task_id,
                    result='success'
                )
            else:
                message = f"无法取消处于 {task.status} 状态的任务"
                logger.warning(message)
            
            # 如果是GET请求，重定向到任务详情页
            if request.method == 'GET':
                if task.status == 'canceled':
                    messages.success(request, message)
                else:
                    messages.warning(request, message)
                return redirect('migration_app:task_detail', task_id=task_id)
            # 如果是POST请求，返回JSON响应
            else:
                return JsonResponse({
                    'status': 'success' if task.status == 'canceled' else 'warning',
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

@login_required
@csrf_exempt
def delete_task(request, task_id):
    """删除迁移任务（仅允许删除非运行中的任务）"""
    logger.info(f"收到删除任务请求: 任务ID={task_id}, 方法={request.method}")
    
    if request.method in ['POST', 'DELETE']:
        try:
            task = get_object_or_404(MigrationTask, pk=task_id)
            
            if task.status == 'running':
                message = "正在运行的任务无法删除，请先取消任务"
                logger.warning(message)
                return JsonResponse({'status': 'error', 'message': message}, status=400)
            
            task.delete()
            logger.info(f"任务 {task_id} 已删除")
            
            # 记录审计日志
            record_audit(
                request,
                action='delete_task',
                target_type='task',
                target_id=task_id,
                result='success'
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            error_message = f"删除任务失败: {str(e)}"
            logger.error(error_message, exc_info=True)
            return JsonResponse({'status': 'error', 'message': error_message}, status=500)
    
    logger.warning(f"非法的请求方法: {request.method}")
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
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
        'sqlite_directory': task.sqlite_directory,
        'sqlite_file_name': task.sqlite_file_name,
        'sqlite_path': task.sqlite_path,
        'postgres_connection': None,
        'is_batch': task.is_batch,
        'cancel_requested': task.cancel_requested,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
    }
    
    if task.postgres_connection:
        info['postgres_connection'] = {
            'id': task.postgres_connection.id,
            'name': task.postgres_connection.name,
            'host': task.postgres_connection.host,
            'port': task.postgres_connection.port,
            'database': task.postgres_connection.database,
            'username': task.postgres_connection.username,
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

@login_required
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
        
        # 更新任务保存的目标数据库名
        task.postgres_database = postgres_database
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
        # v2.4: 脱敏后再返回前端,避免泄露数据库错误细节/路径/密码字段
        from .migration_errors import format_db_error
        return JsonResponse({'status': 'error', 'message': format_db_error(e)})

# 数据查询API函数
@login_required
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

@login_required
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
            
            if object_type == 'view_to_sqlite':
                # 同时查询表和视图
                cursor.execute("""
                SELECT TABLE_NAME 
                FROM ALL_TABLES 
                WHERE OWNER = :schema 
                ORDER BY TABLE_NAME
                """, schema=schema)
                table_rows = cursor.fetchall()
                
                cursor.execute("""
                SELECT VIEW_NAME 
                FROM ALL_VIEWS 
                WHERE OWNER = :schema 
                ORDER BY VIEW_NAME
                """, schema=schema)
                view_rows = cursor.fetchall()
                
                table_objects = [{'name': row[0], 'object_type': 'TABLE'} for row in table_rows]
                view_objects = [{'name': row[0], 'object_type': 'VIEW'} for row in view_rows]
                objects = table_objects + view_objects
                
                if search_term:
                    objects = [
                        obj for obj in objects 
                        if search_term.lower() in (obj['name'] or '').lower()
                    ]
                
                objects.sort(key=lambda obj: (obj['object_type'], obj['name']))
                
                cursor.close()
                connection.close()
                
                return JsonResponse({
                    'status': 'success',
                    'objects': objects,
                    'total': len(objects),
                    'has_more': False
                })
            
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
                
            elif object_type in ('view', 'view_to_table'):
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

@login_required
@csrf_exempt
def get_postgres_databases(request):
    """获取PostgreSQL数据库列表"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            connection_id = data.get('connection_id')
            
            if not connection_id:
                return JsonResponse({'status': 'error', 'message': '未提供连接ID'})
            
            from .models import PostgresConnection
            from .views import _pg_connect_kwargs
            pg_conn = get_object_or_404(PostgresConnection, pk=connection_id)
            conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn, 'postgres'))
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

@login_required
@csrf_exempt
def browse_directories(request):
    """列出服务器上的目录，便于选择SQLite输出位置"""
    raw_path = request.GET.get('path')
    if request.method == 'POST':
        raw_path = raw_path or request.POST.get('path')
    raw_path = (raw_path or '').strip()
    explicit_request = bool(raw_path)
    base_path = Path.home().resolve()
    
    if not raw_path:
        raw_path = str(base_path)
    
    try:
        target = Path(raw_path).expanduser().resolve()
    except Exception as resolve_err:
        return JsonResponse({'status': 'error', 'message': f'路径解析失败: {resolve_err}'}, status=400)
    
    try:
        if explicit_request and (not target.exists() or not target.is_dir()):
            return JsonResponse({'status': 'error', 'message': '目标路径不存在或不是目录'}, status=400)
        if not target.exists() or not target.is_dir():
            target = base_path
        
        # 限制在用户主目录范围内，避免意外曝光其它路径
        if target != base_path:
            try:
                target.relative_to(base_path)
            except ValueError:
                return JsonResponse({'status': 'error', 'message': '不允许访问该目录'}, status=403)
        
        if not os.access(target, os.R_OK | os.X_OK):
            return JsonResponse({'status': 'error', 'message': '没有权限访问该目录'}, status=403)
        
        directories = []
        files = []
        for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if child.is_dir():
                accessible = os.access(child, os.R_OK | os.X_OK)
                directories.append({
                    'name': child.name,
                    'path': str(child),
                    'is_hidden': child.name.startswith('.'),
                    'accessible': accessible
                })
            elif child.is_file() and child.suffix.lower() in SQLITE_ALLOWED_SUFFIXES:
                readable = os.access(child, os.R_OK)
                file_size = None
                modified = None
                try:
                    stat = child.stat()
                    file_size = stat.st_size
                    modified = stat.st_mtime
                except Exception:
                    pass
                files.append({
                    'name': child.name,
                    'path': str(child),
                    'size': file_size,
                    'modified': modified,
                    'readable': readable
                })
        
        parent = str(target.parent) if target.parent != target else None
        if parent and not parent.startswith(str(base_path)):
            parent = None
        
        return JsonResponse({
            'status': 'success',
            'current': str(target),
            'parent': parent,
            'directories': directories,
            'files': files
        })
    except PermissionError:
        return JsonResponse({'status': 'error', 'message': '没有权限访问该目录'}, status=403)
    except Exception as e:
        from .migration_errors import format_db_error
        return JsonResponse({'status': 'error', 'message': format_db_error(e)}, status=500)

# 添加缺失的迁移函数
def migrate_view_to_table(task_id, postgres_database=None):
    """将视图数据迁移到表中（与 migrate_view 物化模式共用 view_materialization 实现）。"""
    from . import views
    from .view_materialization import run_view_materialization_task

    logger.info(f"开始执行视图数据迁移到表任务: 任务ID={task_id}")
    run_view_materialization_task(
        task_id,
        postgres_database,
        get_oracle_connection=views.get_oracle_connection,
        get_postgres_connection=views.get_postgres_connection,
        convert_oracle_to_pg_type=views.convert_oracle_to_pg_type,
    )


def migrate_view_to_sqlite(task_id):
    """将Oracle表或视图导出至SQLite数据库文件"""
    from . import views
    from .views import convert_oracle_to_sqlite_type
    from django.utils import timezone
    
    task = get_object_or_404(MigrationTask, pk=task_id)
    logger.info(f"开始执行SQLite导出任务: 任务ID={task_id}")
    
    sqlite_path = task.sqlite_path
    if not sqlite_path:
        error_msg = "未配置SQLite输出路径"
        logger.error(error_msg)
        task.status = 'failed'
        task.log = error_msg
        task.completed_at = timezone.now()
        task.save()
        return
    
    sqlite_directory = os.path.dirname(sqlite_path)
    task.status = 'running'
    task.started_at = timezone.now()
    task.progress = 0
    task.view_progress = {}
    task.log = f"SQLite文件: {sqlite_path}"
    task.save()
    
    log = [f"SQLite文件: {sqlite_path}"]
    oracle_cursor = oracle_conn = sqlite_cursor = sqlite_conn = None
    
    try:
        os.makedirs(sqlite_directory, exist_ok=True)
    except Exception as e:
        error_msg = f"创建SQLite目录失败: {e}"
        logger.error(error_msg, exc_info=True)
        task.status = 'failed'
        task.log = ''.join(log + [error_msg])
        task.completed_at = timezone.now()
        task.save()
        return
    
    try:
        oracle_conn = views.get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        log.append("已连接Oracle数据库")
    except Exception as e:
        error_msg = f"连接Oracle数据库失败: {e}"
        logger.error(error_msg, exc_info=True)
        task.status = 'failed'
        task.log = ''.join(log + [error_msg])
        task.completed_at = timezone.now()
        task.save()
        return
    
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        log.append("已连接SQLite数据库")
    except Exception as e:
        error_msg = f"连接SQLite数据库失败: {e}"
        logger.error(error_msg, exc_info=True)
        oracle_cursor.close()
        oracle_conn.close()
        task.status = 'failed'
        task.log = ''.join(log + [error_msg])
        task.completed_at = timezone.now()
        task.save()
        return
    
    try:
        object_names = []
        if task.source_objects and task.source_objects.strip():
            object_names = [obj.strip() for obj in task.source_objects.split(',') if obj.strip()]
        elif task.source_object:
            object_names = [task.source_object.strip()]
        
        if not object_names:
            raise ValueError("未指定需要迁移的对象")
        
        total_objects = len(object_names)
        success, failed = [], []
        progress_data = {}
        
        for index, object_name in enumerate(object_names):
            task.refresh_from_db()
            if task.cancel_requested:
                log.append("任务被请求取消")
                task.status = 'canceled'
                break
            
            task.progress = (index / total_objects) * 100
            task.save(update_fields=['progress'])
            
            obj_log = [f"开始处理对象 {object_name} ({index+1}/{total_objects})"]
            logger.info(obj_log[0])
            
            try:
                oracle_cursor.execute("""
                    SELECT OBJECT_TYPE 
                    FROM ALL_OBJECTS 
                    WHERE OWNER = :schema 
                      AND OBJECT_NAME = :object_name 
                      AND OBJECT_TYPE IN ('TABLE', 'VIEW')
                """, schema=task.source_schema, object_name=object_name)
                obj_info = oracle_cursor.fetchone()
                object_type = obj_info[0] if obj_info else 'VIEW'
                obj_log.append(f"对象类型: {object_type}")
                
                oracle_cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE
                    FROM ALL_TAB_COLUMNS
                    WHERE OWNER = :schema AND TABLE_NAME = :object_name
                    ORDER BY COLUMN_ID
                """, schema=task.source_schema, object_name=object_name)
                columns = oracle_cursor.fetchall()
                
                if not columns:
                    raise ValueError(f"{object_name} 未找到列定义")
                
                column_defs = []
                for column in columns:
                    column_name, data_type, data_length, data_precision, data_scale, nullable = column
                    sqlite_type = convert_oracle_to_sqlite_type(data_type, data_length, data_precision, data_scale)
                    not_null = "" if nullable == 'Y' else " NOT NULL"
                    column_defs.append(f'"{column_name}" {sqlite_type}{not_null}')
                
                create_table_sql = f'CREATE TABLE IF NOT EXISTS "{object_name}" (' + ",".join(column_defs) + ")"
                
                sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (object_name,))
                table_exists = sqlite_cursor.fetchone() is not None
                
                if table_exists:
                    if task.conflict_strategy == 'error':
                        raise ValueError(f'SQLite表 "{object_name}" 已存在')
                    elif task.conflict_strategy == 'replace':
                        sqlite_cursor.execute(f'DROP TABLE IF EXISTS "{object_name}"')
                        sqlite_conn.commit()
                        table_exists = False
                        obj_log.append("已删除已存在的表")
                    elif task.conflict_strategy == 'skip':
                        obj_log.append("表已存在，跳过")
                        success.append(object_name)
                        continue
                    elif task.conflict_strategy == 'truncate':
                        sqlite_cursor.execute(f'DELETE FROM "{object_name}"')
                        sqlite_conn.commit()
                        obj_log.append("已清空目标表")
                    elif task.conflict_strategy == 'append':
                        obj_log.append("将追加数据到现有表")
                
                if not table_exists or task.conflict_strategy in ['replace', 'error']:
                    sqlite_cursor.execute(create_table_sql)
                    sqlite_conn.commit()
                    obj_log.append("已创建SQLite表结构")
                
                oracle_query = f"SELECT * FROM {task.source_schema}.{object_name}"
                oracle_cursor.arraysize = 5000
                oracle_cursor.execute(oracle_query)
                column_names = [col[0] for col in oracle_cursor.description]
                column_oracle_types_sqlite = [col[1] for col in columns]
                placeholders = ", ".join(["?"] * len(column_names))
                quoted_columns = ", ".join([f'"{col}"' for col in column_names])
                insert_sql = f'INSERT INTO "{object_name}" ({quoted_columns}) VALUES ({placeholders})'
                
                batch_total = 0
                conflict_insert_sql = None
                conflict_notice_logged = False
                while True:
                    rows = oracle_cursor.fetchmany()
                    if not rows:
                        break
                    rows = adapt_oracle_rows(rows, column_oracle_types_sqlite)
                    try:
                        sqlite_cursor.executemany(insert_sql, rows)
                    except sqlite3.IntegrityError as integrity_err:
                        if 'UNIQUE constraint failed' in str(integrity_err):
                            if conflict_insert_sql is None:
                                conflict_insert_sql = insert_sql.replace('INSERT INTO', 'INSERT OR REPLACE INTO', 1)
                            sqlite_cursor.executemany(conflict_insert_sql, rows)
                            if not conflict_notice_logged:
                                obj_log.append("检测到唯一键冲突，已自动使用INSERT OR REPLACE覆盖SQLite中已有记录")
                                conflict_notice_logged = True
                        else:
                            raise
                    sqlite_conn.commit()
                    batch_total += len(rows)
                
                obj_log.append(f"已写入 {batch_total} 行数据")
                success.append(object_name)
            
            except Exception as obj_err:
                error_msg = f"对象 {object_name} 迁移失败: {obj_err}"
                logger.error(error_msg, exc_info=True)
                obj_log.append(error_msg)
                failed.append(object_name)
            
            progress_data = task.view_progress if isinstance(task.view_progress, dict) else {}
            progress_data[object_name] = {
                'progress': 100 if object_name in success else 0,
                'log': obj_log,
                'object_type': object_type
            }
            task.view_progress = progress_data
            task.save(update_fields=['view_progress'])
        
        if task.status != 'canceled':
            if success and failed:
                task.status = 'partial'
                log.append(f"部分成功: 成功 {len(success)} 个，失败 {len(failed)} 个")
            elif failed and not success:
                task.status = 'failed'
                log.append("所有对象迁移失败")
            else:
                task.status = 'completed'
                log.append("所有对象迁移完成")
            task.progress = 100
        
        if success:
            log.append(f"成功: {', '.join(success)}")
        if failed:
            log.append(f"失败: {', '.join(failed)}")
    
    except Exception as e:
        error_msg = f"执行SQLite迁移任务失败: {e}"
        logger.error(error_msg, exc_info=True)
        log.append(error_msg)
        task.status = 'failed'
    finally:
        try:
            if oracle_cursor:
                oracle_cursor.close()
            if oracle_conn:
                oracle_conn.close()
        except Exception:
            pass
        try:
            if sqlite_cursor:
                sqlite_cursor.close()
            if sqlite_conn:
                sqlite_conn.close()
        except Exception:
            pass
        
        task.completed_at = timezone.now()
        task.log = ''.join(log)
        task.save()
        logger.info(f"SQLite导出任务结束: 任务ID={task_id}, 状态={task.status}")
