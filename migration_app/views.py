from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from .models import OracleConnection, PostgresConnection, MigrationTask, AuditLog
from .batch_config import (
    MIGRATION_COMMIT_EVERY_BATCHES,
    MIGRATION_FETCH_BATCH_SIZE,
    MIGRATION_PARALLEL_TABLE_WORKERS,
    MIGRATION_PROGRESS_SAVE_ROWS,
)
from .parallel_tables import run_parallel_table_migrations
from .resume import (
    build_batch_view_progress,
    filter_pending_tables,
    get_completed_tables,
    mark_table_completed,
    normalize_view_progress,
)
from .oracle_row_adapter import adapt_oracle_rows
from .data_writer import insert_rows_batch
from .migration_validation import validate_row_counts
from .schema_converter import apply_post_table_schema, pg_table_exists
from .oracle_sql_converter import (
    convert_oracle_to_pg_mview as _convert_mview_sql,
    convert_oracle_to_pg_routine as _convert_routine_sql,
    convert_oracle_to_pg_view,
    is_routine_safe_to_execute as _is_routine_safe,
)
from .pg_identifiers import (
    apply_identifier_case,
    build_pg_column_definition,
    build_qualified_table_name,
    quote_identifier,
)
import cx_Oracle
import psycopg2
import logging
import json
import traceback
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import os
from django.conf import settings
import io
import re
import datetime
from io import StringIO
from django.core.paginator import Paginator
import atexit
from django.contrib.auth.decorators import login_required
from django.db import models

# 配置日志
logger = logging.getLogger(__name__)

# 全局线程池
_task_executor = None


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

def get_task_executor():
    """获取全局任务执行器"""
    global _task_executor
    
    if _task_executor is None:
        logger.info("初始化任务执行线程池")
        
        # 创建一个有5个工作线程的线程池
        _task_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="migration_task_")
        
    return _task_executor

# 在模块初始化时预热线程池
try:
    executor = get_task_executor()
    logger.info("任务执行线程池已初始化")
except Exception as e:
    logger.error(f"初始化任务执行线程池失败: {str(e)}")

# 注册应用退出时的清理函数
def cleanup_executor():
    """在应用退出时关闭线程池"""
    global _task_executor
    try:
        if _task_executor:
            logger.info("关闭线程池")
            _task_executor.shutdown(wait=False)
    except Exception as e:
        logger.warning(f"关闭线程池时出错: {e}")
    finally:
        _task_executor = None

# 注册清理函数
atexit.register(cleanup_executor)

@login_required
def index(request):
    """首页视图"""
    tasks = MigrationTask.objects.all().order_by('-created_at')[:10]
    oracle_connections = OracleConnection.objects.all()
    postgres_connections = PostgresConnection.objects.all()
    
    context = {
        'tasks': tasks,
        'oracle_connections': oracle_connections,
        'postgres_connections': postgres_connections,
    }
    return render(request, 'migration_app/index.html', context)

def _connection_plain_password(stored):
    """返回连接配置中的明文密码（兼容未加密旧数据）；密文解密失败时抛出 PasswordDecryptError。"""
    from .credentials import require_plain_connection_password
    return require_plain_connection_password(stored)


def _get_oracle_connection_direct(connection_id, *, call_timeout_ms: int = 30000):
    """直接创建 Oracle 连接（不使用连接池，保留供特殊场景）。

    Args:
        connection_id: OracleConnection 主键
        call_timeout_ms: 单条 SQL 执行超时（毫秒），默认 30 秒。
            cx_Oracle 7.1+ 的 callTimeout，超时后查询自动中断并抛
            DPI-1067 或 ORA-01013。设为 0 表示不限制。
    """
    conn_obj = get_object_or_404(OracleConnection, pk=connection_id)
    dsn = cx_Oracle.makedsn(conn_obj.host, conn_obj.port, service_name=conn_obj.service_name)
    pwd = _connection_plain_password(conn_obj.password)
    connection = cx_Oracle.connect(
        user=conn_obj.username,
        password=pwd,
        dsn=dsn
    )
    # 设置单条 SQL 执行超时，避免查询卡死导致 HTTP 请求永不返回
    if call_timeout_ms and hasattr(connection, 'callTimeout'):
        connection.callTimeout = call_timeout_ms
    return connection


def get_oracle_connection(connection_id, *, call_timeout_ms: int = 30000, use_pool: bool = True):
    """创建或获取 Oracle 连接（支持连接池）。

    Args:
        connection_id: OracleConnection 主键
        call_timeout_ms: 单条 SQL 执行超时（毫秒），默认 30 秒。
        use_pool: 是否使用连接池，默认 True（可通过 settings.MIGRATION_USE_CONNECTION_POOL 控制）

    Returns:
        cx_Oracle.Connection: 连接对象（从池获取或新建，使用池时返回代理对象）

    注意：
        - 使用连接池时，返回代理对象，调用 connection.close() 会自动归还到池
        - 不使用连接池时，直接关闭连接即可（connection.close()）
    """
    # 从 settings 读取全局配置，如果未启用池，则强制 use_pool=False
    if use_pool and hasattr(settings, 'MIGRATION_USE_CONNECTION_POOL'):
        use_pool = settings.MIGRATION_USE_CONNECTION_POOL

    if use_pool:
        from .connection_pool import get_oracle_pooled_connection, OracleConnectionProxy
        conn = get_oracle_pooled_connection(connection_id, call_timeout_ms=call_timeout_ms)
        # 返回代理对象，拦截 close() 调用并归还到池
        return OracleConnectionProxy(conn, connection_id)
    else:
        return _get_oracle_connection_direct(connection_id, call_timeout_ms=call_timeout_ms)

def _pg_connect_kwargs(conn_obj, database=None, *, connect_timeout: int = 30):
    """从 PostgresConnection 构建 psycopg2.connect 参数字典（含连接超时）。"""
    db_name = database if database else conn_obj.database
    pwd = _connection_plain_password(conn_obj.password)
    kwargs = {
        'host': conn_obj.host,
        'port': conn_obj.port,
        'database': db_name,
        'user': conn_obj.username,
        'password': pwd,
        'connect_timeout': max(5, int(connect_timeout)),
    }
    sslmode = (getattr(conn_obj, 'sslmode', None) or '').strip()
    if sslmode:
        kwargs['sslmode'] = sslmode
    return kwargs

def get_postgres_connection(connection_id, database=None, *, use_pool: bool = True):
    """创建或获取 PostgreSQL 连接（支持连接池）。

    Args:
        connection_id: PostgresConnection 主键
        database: 可选的数据库名（默认使用连接配置中的数据库）
        use_pool: 是否使用连接池，默认 True（可通过 settings.MIGRATION_USE_CONNECTION_POOL 控制）

    Returns:
        psycopg2.connection: 连接对象（从池获取或新建，使用池时返回代理对象）

    注意：
        - 使用连接池时，返回代理对象，调用 connection.close() 会自动归还到池
        - 不使用连接池时，直接关闭连接即可（connection.close()）
    """
    # 从 settings 读取全局配置，如果未启用池，则强制 use_pool=False
    if use_pool and hasattr(settings, 'MIGRATION_USE_CONNECTION_POOL'):
        use_pool = settings.MIGRATION_USE_CONNECTION_POOL

    if use_pool:
        from .connection_pool import get_postgres_pooled_connection, PostgresConnectionProxy
        conn = get_postgres_pooled_connection(connection_id, database)
        # 返回代理对象，拦截 close() 调用并归还到池
        return PostgresConnectionProxy(conn, connection_id, database)
    else:
        conn_obj = get_object_or_404(PostgresConnection, pk=connection_id)
        connection = psycopg2.connect(**_pg_connect_kwargs(conn_obj, database))
        return connection

@login_required
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

def migrate_materialized_view(task_id, postgres_database=None):
    """迁移物化视图"""
    task = get_object_or_404(MigrationTask, pk=task_id)

    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()

    from .task_logging import (
        build_log_line, make_step_log, make_info_log, make_ok_log,
        make_warn_log, make_error_log, make_meta_log, make_sql_log,
    )

    log = []
    make_step_log(log, f'物化视图迁移任务 #{task_id} 启动')
    if postgres_database:
        make_info_log(log, f'目标 PostgreSQL 数据库: {postgres_database}')

    oracle_conn = oracle_cursor = pg_conn = pg_cursor = None
    try:
        # 连接Oracle数据库
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()

        # 连接PostgreSQL数据库
        pg_conn = get_postgres_connection(task.postgres_connection.id, postgres_database)
        pg_cursor = pg_conn.cursor()

        # 获取PostgreSQL数据库名
        pg_cursor.execute("SELECT current_database()")
        current_db = pg_cursor.fetchone()[0]
        make_ok_log(log, f'已连接 PostgreSQL 数据库: {current_db}')
        make_ok_log(log, '已连接 Oracle 源端')

        # 优先使用 QUERY 列（纯查询体），回退 TEXT
        oracle_cursor.execute(
            """
            SELECT QUERY, TEXT FROM ALL_MVIEWS
            WHERE OWNER = :schema AND MVIEW_NAME = :mview_name
            """,
            schema=task.source_schema,
            mview_name=task.source_object,
        )
        result = oracle_cursor.fetchone()
        if not result:
            make_error_log(log, f'找不到物化视图 {task.source_schema}.{task.source_object}')
            raise Exception(f"找不到物化视图 {task.source_schema}.{task.source_object}")

        mview_text = result[0] or result[1]
        make_meta_log(log, f'物化视图定义 (前500字符): {str(mview_text)[:500]}')

        pg_mview_text, manual_items = convert_oracle_to_pg_mview(mview_text)
        make_meta_log(log, f'转换后 PG 查询体 (前500字符): {pg_mview_text[:500]}')
        if manual_items:
            make_warn_log(log, f'需人工审查 ({len(manual_items)} 项): {", ".join(manual_items)}')

        id_case = getattr(task, 'identifier_case', 'lower') or 'lower'
        target_schema = (task.target_schema or 'public').strip()
        mview_name = apply_identifier_case(task.source_object, id_case)
        qualified_mview = build_qualified_table_name(target_schema, mview_name)
        strategy = task.conflict_strategy or 'error'
        make_info_log(log, f'目标: {target_schema}.{mview_name} | 冲突策略: {strategy} | 大小写: {id_case}')

        pg_cursor.execute(
            """
            SELECT 1 FROM pg_matviews
            WHERE schemaname = %s AND matviewname = %s
            """,
            (target_schema, apply_identifier_case(mview_name, id_case)),
        )
        if pg_cursor.fetchone():
            if strategy == 'skip':
                make_ok_log(log, f'物化视图 {target_schema}.{mview_name} 已存在，跳过')
                task.status = 'completed'
                task.log = '\n'.join(log)
                task.completed_at = timezone.now()
                task.save()
                return
            if strategy == 'error':
                make_error_log(log, f'物化视图 {target_schema}.{mview_name} 已存在')
                raise Exception(f"物化视图 {target_schema}.{mview_name} 已存在")
            make_warn_log(log, f'冲突策略 replace，DROP 已存在的物化视图 {target_schema}.{mview_name}')
            pg_cursor.execute(f"DROP MATERIALIZED VIEW IF EXISTS {qualified_mview} CASCADE")
            pg_conn.commit()

        create_mview_sql = f"CREATE MATERIALIZED VIEW {qualified_mview} AS\n{pg_mview_text}"
        make_sql_log(log, f'执行 DDL: {create_mview_sql[:300]}{"..." if len(create_mview_sql) > 300 else ""}')
        pg_cursor.execute(create_mview_sql)
        pg_conn.commit()

        make_ok_log(log, f'成功创建物化视图 {target_schema}.{mview_name}')

        # 更新任务状态
        task.status = 'completed'
        task.progress = 100
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

    except Exception as e:
        from .migration_errors import format_db_error, rollback_quietly
        rollback_quietly(pg_conn)
        error_msg = format_db_error(e)
        trace = traceback.format_exc()
        make_error_log(log, f'物化视图迁移失败: {error_msg}')
        make_error_log(log, f'详细错误: {trace}')
        task.status = 'failed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
    finally:
        from .migration_errors import safe_close_db_resources
        safe_close_db_resources(oracle_cursor, oracle_conn, pg_cursor, pg_conn)

def migrate_view(task_id, postgres_database=None):
    """
    迁移视图。
    - definition 模式：转换 Oracle 视图 SQL 并在目标库 CREATE VIEW
    - materialize 模式（默认）：将视图数据物化到目标表（与 view_to_table 共用实现）
    """
    task = get_object_or_404(MigrationTask, pk=task_id)
    view_mode = getattr(task, 'view_migration_mode', None) or 'materialize'
    if view_mode == 'definition':
        _migrate_view_definition(task_id, postgres_database)
        return
    from .view_materialization import run_view_materialization_task
    run_view_materialization_task(
        task_id,
        postgres_database,
        get_oracle_connection=get_oracle_connection,
        get_postgres_connection=get_postgres_connection,
        convert_oracle_to_pg_type=convert_oracle_to_pg_type,
    )


def _migrate_view_definition(task_id, postgres_database=None):
    """在目标库创建 CREATE VIEW（Oracle 语法经 convert_oracle_to_pg_view 转换）。"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()

    from .task_logging import (
        make_step_log, make_info_log, make_ok_log,
        make_warn_log, make_error_log, make_meta_log, make_sql_log,
    )

    log = []
    make_step_log(log, f'视图定义迁移任务 #{task_id} 启动')
    if postgres_database:
        make_info_log(log, f'目标 PostgreSQL 数据库: {postgres_database}')

    try:
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        pg_conn = get_postgres_connection(task.postgres_connection.id, postgres_database)
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute("SELECT current_database()")
        make_ok_log(log, f'已连接 PostgreSQL: {pg_cursor.fetchone()[0]}')
        make_ok_log(log, '已连接 Oracle 源端')

        if task.source_objects and task.source_objects.strip():
            views = [v.strip() for v in task.source_objects.split(',') if v.strip()]
        else:
            views = [task.source_object.strip()] if task.source_object else []
        if not views:
            raise Exception("未指定要迁移的视图")
        make_info_log(log, f'待迁移视图数: {len(views)}')

        id_case = getattr(task, 'identifier_case', 'lower') or 'lower'
        target_schema = (task.target_schema or 'public').strip()
        strategy = task.conflict_strategy or 'error'
        failed, manual_review_all = [], []

        for idx, view_name in enumerate(views):
            make_step_log(log, f'创建视图定义 {task.source_schema}.{view_name}',
                          total=len(views), index=idx)
            oracle_cursor.execute(
                "SELECT TEXT FROM ALL_VIEWS WHERE OWNER = :schema AND VIEW_NAME = :view_name",
                schema=task.source_schema,
                view_name=view_name,
            )
            row = oracle_cursor.fetchone()
            if not row:
                failed.append(view_name)
                make_error_log(log, f'找不到视图 {task.source_schema}.{view_name}')
                continue

            pg_query, manual_items = convert_oracle_to_pg_view(row[0])
            if manual_items:
                manual_review_all.extend(manual_items)
                make_warn_log(log, f'需人工审查 ({len(manual_items)} 项): {", ".join(manual_items)}')

            target_view = apply_identifier_case(
                (task.target_object or view_name).strip() if len(views) == 1
                else apply_identifier_case(f"{(task.target_object or 'v')}_{view_name}", id_case),
                id_case,
            )
            qualified_view = build_qualified_table_name(target_schema, target_view)

            pg_cursor.execute(
                """
                SELECT 1 FROM information_schema.views
                WHERE table_schema = %s AND table_name = %s
                """,
                (target_schema, apply_identifier_case(target_view, id_case)),
            )
            exists = pg_cursor.fetchone() is not None
            if exists:
                if strategy == 'skip':
                    make_ok_log(log, f'视图 {target_schema}.{target_view} 已存在，跳过')
                    continue
                if strategy == 'error':
                    make_error_log(log, f'视图 {target_schema}.{target_view} 已存在')
                    raise Exception(f"视图 {target_schema}.{target_view} 已存在")
                make_warn_log(log, f'冲突策略 replace，DROP 视图 {target_schema}.{target_view}')
                pg_cursor.execute(f"DROP VIEW IF EXISTS {qualified_view} CASCADE")
                pg_conn.commit()

            create_sql = f"CREATE VIEW {qualified_view} AS\n{pg_query}"
            make_sql_log(log, f'CREATE VIEW SQL (前300字符): {create_sql[:300]}{"..." if len(create_sql) > 300 else ""}')
            try:
                pg_cursor.execute(create_sql)
                pg_conn.commit()
                make_ok_log(log, f'成功创建视图 {target_schema}.{target_view}')
            except Exception as ddl_err:
                pg_conn.rollback()
                failed.append(view_name)
                make_error_log(log, f'创建视图失败: {ddl_err}')

        oracle_cursor.close()
        oracle_conn.close()
        pg_cursor.close()
        pg_conn.close()

        make_step_log(log, '任务结束')
        if manual_review_all:
            make_warn_log(log, f'共 {len(manual_review_all)} 项 Oracle 专有语法需人工复核后再投入生产')
        if failed:
            task.status = 'partial' if len(failed) < len(views) else 'failed'
            make_error_log(log, f'失败 ({len(failed)}): {", ".join(failed)}')
        else:
            task.status = 'completed'
            task.progress = 100
            make_ok_log(log, f'全部视图创建成功 ({len(views) - len(failed)}/{len(views)})')
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
    except Exception as e:
        make_error_log(log, f'任务异常: {e}')
        make_error_log(log, traceback.format_exc())
        task.status = 'failed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()


def migrate_routine(task_id, postgres_database=None):
    """迁移例程（存储过程、函数）"""
    task = get_object_or_404(MigrationTask, pk=task_id)

    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()

    from .task_logging import (
        make_step_log, make_info_log, make_ok_log,
        make_warn_log, make_error_log, make_meta_log, make_sql_log,
    )

    log = []
    make_step_log(log, f'例程迁移任务 #{task_id} 启动')
    if postgres_database:
        make_info_log(log, f'目标 PostgreSQL 数据库: {postgres_database}')

    try:
        # 连接Oracle数据库
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()

        # 连接PostgreSQL数据库
        pg_conn = get_postgres_connection(task.postgres_connection.id, postgres_database)
        pg_cursor = pg_conn.cursor()

        # 获取PostgreSQL数据库名
        pg_cursor.execute("SELECT current_database()")
        current_db = pg_cursor.fetchone()[0]
        make_ok_log(log, f'已连接 PostgreSQL 数据库: {current_db}')
        make_ok_log(log, '已连接 Oracle 源端')

        # 获取存储过程或函数定义
        query = """
        SELECT TEXT FROM ALL_SOURCE
        WHERE OWNER = :schema AND NAME = :routine_name
        ORDER BY LINE
        """
        oracle_cursor.execute(query, schema=task.source_schema, routine_name=task.source_object)
        results = oracle_cursor.fetchall()

        if not results:
            make_error_log(log, f'找不到例程 {task.source_schema}.{task.source_object}')
            raise Exception(f"找不到例程 {task.source_schema}.{task.source_object}")

        routine_text = '\n'.join([row[0] for row in results])
        line_count = len(results)
        make_meta_log(log, f'例程定义: {line_count} 行 / {len(routine_text)} 字符')
        make_meta_log(log, f'前 300 字符预览: {routine_text[:300]}')

        # 转换为 PostgreSQL 函数语法（基础替换，完整 PL/SQL 需人工）
        pg_routine_text, manual_items = _convert_routine_sql(routine_text)
        make_meta_log(log, f'转换后 PG 定义 (前 300 字符): {pg_routine_text[:300]}')
        if manual_items:
            make_warn_log(log, f'需人工审查 ({len(manual_items)} 项): {", ".join(manual_items)}')

        # 安全校验：检测是否仍含 Oracle 专有语法（PROCEDURE/%TYPE 等），避免直接 execute 导致语法错误
        if not _is_routine_safe(pg_routine_text, manual_items):
            make_warn_log(log, '检测到 Oracle 专有语法（CREATE PROCEDURE / %TYPE / 缺少 LANGUAGE plpgsql 包装等），未自动执行，仅导出源码供人工改写')
            make_sql_log(log, '【Oracle 源码 / 需人工改写为 PG plpgsql】')
            make_sql_log(log, routine_text)
            make_ok_log(log, f'例程 {task.source_object} 源码已导出，需人工改写后在 PG 中创建（语法不兼容，未自动执行以避免失败）')
        else:
            # 创建PostgreSQL函数
            make_sql_log(log, f'执行 CREATE FUNCTION: {pg_routine_text[:200]}{"..." if len(pg_routine_text) > 200 else ""}')
            pg_cursor.execute(pg_routine_text)
            pg_conn.commit()
            make_ok_log(log, f'成功创建 PostgreSQL 函数 {task.target_schema}.{task.source_object}')

        # 关闭连接
        oracle_cursor.close()
        oracle_conn.close()
        pg_cursor.close()
        pg_conn.close()

        # 更新任务状态
        task.status = 'completed'
        task.progress = 100
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

    except Exception as e:
        error_msg = str(e)
        trace = traceback.format_exc()
        make_error_log(log, f'例程迁移失败: {error_msg}')
        make_error_log(log, f'详细错误: {trace}')

        # 更新任务状态
        task.status = 'failed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()


def _safe_oracle_identifier(name: str) -> str:
    """校验 Oracle 未加引号标识符（大写字母、数字、下划线）。"""
    n = (name or '').strip().upper().replace('"', '')
    if not n or not re.match(r'^[A-Z][A-Z0-9_]*$', n):
        raise ValueError(f'非法 Oracle 标识符: {name}')
    return n


def _topological_sort_tables_by_fk(oracle_cursor, owner: str, table_names):
    """
    按外键依赖排序表名：父表在前、子表在后；无法解析的边或环则按字母序追加并记日志。
    table_names 为 ALL_TABLES 返回的名称列表（通常大写）。
    """
    if not table_names:
        return []
    # 去重且保持首次出现顺序
    seen = set()
    ordered_unique = []
    for t in table_names:
        u = t[0] if isinstance(t, (list, tuple)) else t
        u = str(u).strip()
        if not u or u in seen:
            continue
        seen.add(u)
        ordered_unique.append(u)
    if len(ordered_unique) <= 1:
        return ordered_unique
    upper_list = [x.upper() for x in ordered_unique]
    name_set = set(upper_list)
    orig_by_upper = {x.upper(): x for x in ordered_unique}

    # 不在 SQL 中使用 IN (表名列表)：Oracle 限制 IN 最多 1000 项（ORA-01795）
    query = """
    SELECT DISTINCT c.table_name AS child_tab, pk.table_name AS parent_tab
    FROM all_constraints c
    JOIN all_constraints pk
      ON c.r_owner = pk.owner AND c.r_constraint_name = pk.constraint_name
    WHERE c.constraint_type = 'R'
      AND c.owner = :owner
    """
    oracle_cursor.execute(query, {'owner': owner.upper()})
    rows = [
        (child_tab, parent_tab)
        for child_tab, parent_tab in oracle_cursor.fetchall()
        if child_tab and parent_tab
        and child_tab.upper() in name_set
        and parent_tab.upper() in name_set
    ]
    from collections import defaultdict
    from heapq import heappush, heappop

    indegree = defaultdict(int)
    children = defaultdict(list)
    nodes = set(upper_list)
    for child_tab, parent_tab in rows:
        if not child_tab or not parent_tab:
            continue
        cu, pu = child_tab.upper(), parent_tab.upper()
        if cu not in name_set or pu not in name_set:
            continue
        children[pu].append(cu)
        indegree[cu] += 1

    heap = []
    for n in nodes:
        if indegree[n] == 0:
            heappush(heap, n)
    result_upper = []
    while heap:
        n = heappop(heap)
        result_upper.append(n)
        for ch in sorted(children[n]):
            indegree[ch] -= 1
            if indegree[ch] == 0:
                heappush(heap, ch)

    remaining = [n for n in nodes if n not in result_upper]
    if remaining:
        result_upper.extend(sorted(remaining))
    return [orig_by_upper[u] for u in result_upper]


def _persist_running_task_log(task, log_list, extra_update_fields=None):
    """运行中将日志写回数据库，便于前端轮询展示分批进度。"""
    if task is None:
        return
    task.log = '\n'.join(log_list)
    fields = {'log'}
    if extra_update_fields:
        fields.update(extra_update_fields)
    task.save(update_fields=list(fields))


def _migrate_single_table(oracle_cursor, pg_conn, pg_cursor, source_schema, target_schema, table_name,
                          conflict_strategy, log_list, task=None, all_tables_context=None,
                          watermark_column=None, watermark_min_exclusive=None):
    """
    迁移单张表的结构和数据（不创建子任务，供 migrate_table 与 migrate_all_tables 复用）。
    使用已打开的 oracle_cursor / pg_conn / pg_cursor，结果追加到 log_list。
    task 可选，用于取消检查和进度回调（view_progress）。
    all_tables_context 可选，格式 {'total_tables': N, 'table_index': idx, 'failed_count': n}，
        用于「所有表」任务时在单表迁移过程中更新总进度 task.progress，避免首张表很大时进度一直为 0。
    返回 (成功与否, 迁移行数)。
    """
    strategy = conflict_strategy or 'error'
    id_case = (getattr(task, 'identifier_case', None) or 'lower') if task else 'lower'
    # 按 identifier_case 检查目标表是否已存在
    table_exists = pg_table_exists(pg_cursor, target_schema, table_name, id_case)

    if table_exists:
        if strategy == 'error':
            raise Exception(f"表 {target_schema}.{table_name} 已存在")
        if strategy == 'skip':
            log_list.append(f"表 {target_schema}.{table_name} 已存在，跳过")
            return True, 0
        if strategy == 'replace':
            log_list.append(f"冲突策略为 replace，删除已存在的表 {target_schema}.{table_name}")
            pg_cursor.execute(f"DROP TABLE IF EXISTS {target_schema}.{table_name}")
            pg_conn.commit()
            table_exists = False
        elif strategy == 'truncate':
            log_list.append(f"冲突策略为 truncate，清空表 {target_schema}.{table_name}")
            pg_cursor.execute(f"TRUNCATE TABLE {target_schema}.{table_name}")
            pg_conn.commit()
        # append 或 truncate 后继续走下面的建表（仅当表不存在时）或直接导数据

    # 获取表结构
    # v2.3: 增加 IDENTITY_COLUMN/VIRTUAL_COLUMN/HIDDEN_COLUMN/DATA_DEFAULT 字段
    # 用于识别 Oracle 12c+ 自增列、虚拟列、不可见列并生成对应的 PG DDL
    column_query = """
    SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE, COLUMN_ID,
           IDENTITY_COLUMN, VIRTUAL_COLUMN, HIDDEN_COLUMN, DATA_DEFAULT
    FROM ALL_TAB_COLUMNS
    WHERE OWNER = :schema AND TABLE_NAME = :table_name
    ORDER BY COLUMN_ID
    """
    oracle_cursor.execute(column_query, schema=source_schema, table_name=table_name)
    columns = oracle_cursor.fetchall()
    if not columns:
        raise Exception(f"找不到表 {source_schema}.{table_name}")

    # 仅当目标表不存在或刚被 replace 掉时创建表；列名加双引号，避免 ISNULL 等与 PG 关键字冲突
    pg_table = apply_identifier_case(table_name, id_case)
    qualified_table = build_qualified_table_name(target_schema, pg_table)

    if not table_exists or strategy == 'replace':
        create_table_sql = f"CREATE TABLE {qualified_table} (\n"
        column_definitions = []
        identity_columns = []  # v2.3: 记录自增列，用于日志提示
        virtual_columns = []   # v2.3: 记录虚拟列，用于日志提示
        
        for column in columns:
            # 解包 11 个字段（v2.3 新增 4 个）
            col_name, data_type, data_length, data_precision, data_scale, nullable, column_id = (
                column[0], column[1], column[2], column[3], column[4], column[5], column[6]
            )
            identity_column = column[7] if len(column) > 7 else 'NO'  # YES/NO
            virtual_column_flag = column[8] if len(column) > 8 else 'NO'
            hidden_column = column[9] if len(column) > 9 else 'NO'
            data_default = column[10] if len(column) > 10 else None
            
            pg_type = convert_oracle_to_pg_type(data_type, data_length, data_precision, data_scale)
            if pg_type.startswith('VARCHAR('):
                match = re.search(r'VARCHAR\((\d+)\)', pg_type)
                if match and int(match.group(1)) < 1:
                    pg_type = 'VARCHAR(255)'
                    log_list.append(f"警告: 列 {col_name} 的 VARCHAR 长度为0，已调整为 VARCHAR(255)")
            
            # v2.3: 处理 Oracle 12c+ 自增列 IDENTITY
            if identity_column == 'YES':
                identity_columns.append(col_name)
                # 自增列必须是 NOT NULL（PG 要求）
                col_def = build_pg_column_definition(col_name, pg_type, 'N', id_case=id_case)
                col_def += ' GENERATED BY DEFAULT AS IDENTITY'  # 使用 BY DEFAULT 允许手动插入
                column_definitions.append(col_def)
                continue
            
            # v2.3: 处理虚拟列 GENERATED ALWAYS AS
            if virtual_column_flag == 'YES' and data_default:
                virtual_columns.append(col_name)
                expr = str(data_default).strip()
                # 尝试转换 Oracle 表达式为 PG 表达式
                from .oracle_sql_converter import convert_oracle_to_pg_sql
                pg_expr, manual_items = convert_oracle_to_pg_sql(expr)
                col_def = build_pg_column_definition(col_name, pg_type, nullable, id_case=id_case)
                col_def += f' GENERATED ALWAYS AS ({pg_expr}) STORED'
                if manual_items:
                    log_list.append(f"[WARN] 虚拟列 {col_name} 表达式需人工复核: {', '.join(manual_items)}")
                column_definitions.append(col_def)
                continue
            
            # v2.3: 处理不可见列 INVISIBLE（PG 无原生支持，建成普通列并告警）
            if hidden_column == 'YES':
                log_list.append(f"[WARN] 列 {col_name} 在 Oracle 中为 INVISIBLE，PG 无原生支持，建成普通列")
            
            column_definitions.append(
                build_pg_column_definition(col_name, pg_type, nullable, id_case=id_case)
            )
        
        create_table_sql += ",\n".join(column_definitions) + "\n)"
        try:
            pg_cursor.execute(create_table_sql)
        except Exception as create_err:
            log_list.append(f"建表 SQL 失败:\n{create_table_sql}")
            raise create_err
        pg_conn.commit()
        log_list.append(f"成功创建表 {target_schema}.{table_name}")
        
        if identity_columns:
            log_list.append(f"[INFO] 表含 {len(identity_columns)} 个自增列(IDENTITY): {', '.join(identity_columns)}")
        if virtual_columns:
            log_list.append(f"[INFO] 表含 {len(virtual_columns)} 个虚拟列(GENERATED ALWAYS AS): {', '.join(virtual_columns)}")

    # 获取总行数（Oracle 中未加引号的标识符为大写）；支持按水位列增量统计
    wm_sql_fragment = ""
    if watermark_column and watermark_min_exclusive is not None and str(watermark_min_exclusive).strip() != '':
        try:
            wm_col_sql = _safe_oracle_identifier(watermark_column)
        except ValueError as e:
            raise Exception(str(e))
        wm_sql_fragment = f" WHERE {wm_col_sql} > :wmv "
        log_list.append(f"使用增量条件: {wm_col_sql} > 上一水位值")

    total_count = 0
    try:
        if wm_sql_fragment:
            oracle_cursor.execute(
                f"SELECT COUNT(*) FROM {source_schema}.{table_name}{wm_sql_fragment}",
                wmv=watermark_min_exclusive,
            )
        else:
            oracle_cursor.execute(f"SELECT COUNT(*) FROM {source_schema}.{table_name}")
        total_count = int(oracle_cursor.fetchone()[0])
        log_list.append(f"表 {source_schema}.{table_name} 总行数: {total_count}")
    except Exception as count_err:
        err_str = str(count_err).upper()
        if "ORA-00942" in err_str or "TABLE OR VIEW DOES NOT EXIST" in err_str or "00942" in err_str:
            raise Exception(
                f"无法访问源表 {source_schema}.{table_name}（表或视图不存在或无 SELECT 权限）。错误: {count_err}"
            )
        logger.warning(f"获取总行数失败: {count_err}，进度将按已迁移行数估算")

    fetch_batch_size = MIGRATION_FETCH_BATCH_SIZE
    commit_every_batches = MIGRATION_COMMIT_EVERY_BATCHES
    if total_count > 0:
        rows_per_commit = fetch_batch_size * commit_every_batches
        log_list.append(
            f"【开始迁移】{source_schema}.{table_name}，共 {total_count} 行，"
            f"每批读取 {fetch_batch_size} 行，每 {commit_every_batches} 批提交一次"
            f"（约 {rows_per_commit} 行/事务）"
        )
    else:
        log_list.append(f"【开始迁移】{source_schema}.{table_name}，源表无数据行")
    if task and all_tables_context:
        _persist_running_task_log(task, log_list)

    oracle_cursor.arraysize = fetch_batch_size
    if wm_sql_fragment:
        oracle_cursor.execute(
            f"SELECT * FROM {source_schema}.{table_name}{wm_sql_fragment}",
            wmv=watermark_min_exclusive,
        )
    else:
        oracle_cursor.execute(f"SELECT * FROM {source_schema}.{table_name}")
    column_names = [apply_identifier_case(col[0], id_case) for col in oracle_cursor.description]
    # 与 SELECT * 列顺序一致，供 LOB 按列类型转换（BLOB 保持 bytes，CLOB 转 str）
    column_oracle_types = [col[1] for col in columns]
    placeholders = ", ".join(["%s"] * len(column_names))
    quoted_cols = [quote_identifier(c) for c in column_names]
    insert_sql = f"INSERT INTO {qualified_table} ({', '.join(quoted_cols)}) VALUES ({placeholders})"

    total_rows = 0
    last_saved_pct = -1
    last_saved_rows = 0
    progress_save_interval_rows = MIGRATION_PROGRESS_SAVE_ROWS
    batches_since_commit = 0
    user_cancelled = False

    while True:
        if task:
            try:
                task.refresh_from_db()
                if task.cancel_requested:
                    user_cancelled = True
                    log_list.append(f"用户取消，已迁移表 {table_name} 共 {total_rows} 行（未提交批次将回滚）")
                    break
            except Exception:
                pass
        rows = oracle_cursor.fetchmany()
        if not rows:
            break
        insert_rows_batch(
            pg_cursor,
            pg_conn,
            qualified_table,
            quoted_cols,
            rows,
            column_oracle_types,
            total_rows_hint=total_count,
        )
        total_rows += len(rows)
        batches_since_commit += 1
        if batches_since_commit >= commit_every_batches:
            pg_conn.commit()
            batches_since_commit = 0

        progress_pct = min(100.0, (total_rows / total_count) * 100) if total_count > 0 else (100.0 if total_rows == 0 else 0.0)
        should_save = (
            int(progress_pct) > last_saved_pct
            or (total_rows - last_saved_rows) >= progress_save_interval_rows
        )
        if should_save and task:
            try:
                ctx = all_tables_context or {}
                total_tables = ctx.get('total_tables')
                table_index = ctx.get('table_index', 0)
                failed_count = ctx.get('failed_count', 0)
                if total_count > 0:
                    log_list.append(
                        f"【分批】表 {table_name} 已成功迁移 {total_rows}/{total_count} 行"
                        f"（{progress_pct:.1f}%）"
                    )
                else:
                    log_list.append(f"【分批】表 {table_name} 已迁移 {total_rows} 行")
                if total_tables and total_tables > 0:
                    # 「所有表」任务：保留 current/current_table/total/failed_count，并合并当前表明细；同时更新总进度
                    task.view_progress = {
                        'current_table': table_name,
                        'current': table_index,
                        'total': total_tables,
                        'failed_count': failed_count,
                        table_name: {'progress': progress_pct, 'total_rows': total_count, 'migrated_rows': total_rows},
                    }
                    # 总进度 = (已完成表数 + 当前表内进度) / 总表数 * 100
                    overall_pct = (table_index + progress_pct / 100.0) / total_tables * 100.0
                    task.progress = min(100.0, overall_pct)
                    _persist_running_task_log(
                        task, log_list, extra_update_fields={'view_progress', 'progress'}
                    )
                else:
                    task.view_progress = {
                        table_name: {'progress': progress_pct, 'total_rows': total_count, 'migrated_rows': total_rows}
                    }
                    _persist_running_task_log(task, log_list, extra_update_fields={'view_progress'})
                last_saved_pct = int(progress_pct)
                last_saved_rows = total_rows
            except Exception as save_err:
                logger.warning(f"更新进度失败: {save_err}")

    if user_cancelled:
        from .migration_errors import MigrationCancelledError, rollback_quietly
        rollback_quietly(pg_conn, log_list=log_list)
        raise MigrationCancelledError(f'用户取消表 {table_name} 的数据迁移')

    if batches_since_commit > 0:
        pg_conn.commit()

    if total_rows == 0:
        log_list.append(f"【完成】表 {source_schema}.{table_name} 无数据，跳过数据导入")
    else:
        log_list.append(
            f"【完成】表 {table_name} 迁移成功，共导入 {total_rows} 行到 {target_schema}.{table_name}"
        )

    # 迁移后行数校验
    wm_where = wm_sql_fragment.strip() if wm_sql_fragment else ''
    wm_params = {'wmv': watermark_min_exclusive} if wm_where else None
    count_ok, src_row_count, tgt_row_count = validate_row_counts(
        oracle_cursor,
        pg_cursor,
        source_schema,
        table_name,
        target_schema,
        table_name,
        log_list,
        pg_table_name=pg_table,
        watermark_where=wm_where,
        watermark_params=wm_params,
    )

    # Schema 扩展：默认值、约束、索引（导数完成后执行）
    try:
        apply_post_table_schema(
            oracle_cursor,
            pg_cursor,
            pg_conn,
            source_schema,
            target_schema,
            table_name,
            log_list,
            id_case=id_case,
        )
    except Exception as schema_err:
        log_list.append(f"【Schema 扩展】表 {table_name} 部分对象未创建: {schema_err}")

    if not count_ok:
        from .migration_errors import MigrationValidationError
        raise MigrationValidationError(
            f'表 {source_schema}.{table_name} 行数校验未通过，'
            f'源端 {src_row_count} 行 ≠ 目标端 {tgt_row_count} 行'
        )
    return True, total_rows


def _parse_task_source_object_names(task):
    """
    解析「表」类任务要迁移的源对象名列表：优先 source_objects（逗号/中文逗号分隔），否则使用 source_object。
    """
    raw = (getattr(task, "source_objects", None) or "").strip()
    names = []
    if raw:
        normalized = raw.replace("，", ",")
        for chunk in normalized.split(","):
            s = chunk.strip()
            if s:
                names.append(s)
    if not names:
        one = (getattr(task, "source_object", None) or "").strip()
        if one:
            names.append(one)
    return names


def _update_task_last_watermark_max(task, oracle_cursor, log, oracle_table_name):
    """按水位列增量：根据指定源表刷新任务上的 last_watermark（Oracle MAX）。"""
    wm_col = (getattr(task, "watermark_column", None) or "").strip()
    if not wm_col:
        return
    try:
        safe_wm = _safe_oracle_identifier(wm_col)
        oracle_cursor.execute(
            f"SELECT MAX({safe_wm}) FROM {task.source_schema}.{oracle_table_name}"
        )
        mx = oracle_cursor.fetchone()[0]
        if mx is not None:
            task.last_watermark = str(mx)
            task.save(update_fields=["last_watermark"])
            log.append(f"表 {oracle_table_name} 已更新水位 last_watermark={task.last_watermark}")
    except Exception as wm_err:
        log.append(f"表 {oracle_table_name} 更新水位失败（可忽略）: {wm_err}")


def migrate_table(task_id, postgres_database=None):
    """迁移表结构和数据（分批读取；支持 source_objects 多表顺序迁移，与「所有表」任务类似的进度展示）。"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    table_names = _parse_task_source_object_names(task)

    vp_init = normalize_view_progress(task.view_progress)
    resume_mode = bool(vp_init.pop('resume', False))
    completed_set = get_completed_tables(task) if resume_mode else set()

    task.status = 'running'
    if not task.started_at:
        task.started_at = timezone.now()
    if resume_mode:
        if not task.progress:
            task.progress = min(100.0, (len(completed_set) / max(len(table_names), 1)) * 100)
    else:
        task.progress = 0
        task.view_progress = {}
    task.save()

    if resume_mode:
        log = [ln for ln in (task.log or '').split('\n') if ln is not None]
    else:
        log = []
    if postgres_database:
        log.append(f"目标PostgreSQL数据库: {postgres_database}")

    if not table_names:
        task.status = 'failed'
        task.log = "未配置源表名：请在创建任务时选择表，或填写 source_object / source_objects。"
        task.completed_at = timezone.now()
        task.save()
        return

    oracle_conn = None
    oracle_cursor = None
    pg_conn = None
    pg_cursor = None

    try:
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        pg_conn = get_postgres_connection(task.postgres_connection.id, postgres_database)
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute("SELECT current_database()")
        log.append(f"已连接到PostgreSQL数据库: {pg_cursor.fetchone()[0]}")

        imode = getattr(task, 'incremental_mode', 'none') or 'none'
        all_table_names = list(table_names)
        if resume_mode and len(all_table_names) > 1:
            table_names = filter_pending_tables(all_table_names, completed_set)
            log.append(
                f"【继续迁移】共 {len(all_table_names)} 张表，已完成 {len(completed_set)} 张，"
                f"剩余 {len(table_names)} 张"
            )
        total_tables = len(all_table_names)
        base_done = len(completed_set) if resume_mode else 0

        if resume_mode and not table_names:
            log.append("【继续迁移】所选表均已迁移完成")
            task.status = 'completed'
            task.progress = 100.0
            task.view_progress = build_batch_view_progress(
                current_table='',
                current_index=total_tables,
                total_tables=total_tables,
                failed_count=0,
                completed_tables=sorted(completed_set),
            )
            task.log = '\n'.join(log)
            task.completed_at = timezone.now()
            task.save()
            if oracle_cursor:
                oracle_cursor.close()
            if oracle_conn:
                oracle_conn.close()
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()
            return

        if imode == 'pk_mirror':
            from .incremental_sync import run_table_pk_mirror_flow

            log.append("增量模式: 主键对齐（Oracle 为权威源，PolarDB 补插缺失行、删除多余行）")
            if total_tables > 1:
                log.append(f"主键对齐批量：共 {total_tables} 张表，将依次处理。")
            failed_tables = []
            first_table = table_names[0]
            task.progress = 0.0
            task.view_progress = {
                'current': 0,
                'total': total_tables,
                'current_table': first_table,
                'failed_count': 0,
            }
            task.log = '\n'.join(log)
            task.save(update_fields=['progress', 'view_progress', 'log'])

            for loop_idx, tn in enumerate(table_names):
                idx = base_done + loop_idx
                task.refresh_from_db()
                if task.cancel_requested:
                    log.append(f"用户取消，已处理 {idx}/{total_tables} 张表（主键对齐）")
                    task.status = 'partial'
                    break
                task.view_progress = build_batch_view_progress(
                    current_table=tn,
                    current_index=idx,
                    total_tables=total_tables,
                    failed_count=len(failed_tables),
                    completed_tables=sorted(completed_set),
                )
                task.save(update_fields=['view_progress'])
                try:
                    run_table_pk_mirror_flow(
                        task, oracle_cursor, pg_conn, pg_cursor, log, source_table_name=tn
                    )
                    mark_table_completed(completed_set, tn)
                except Exception as pk_err:
                    err_msg = str(pk_err)
                    log.append(f"表 {tn} 主键对齐失败: {err_msg}")
                    failed_tables.append((tn, err_msg))
                done = idx + 1
                task.progress = min(100.0, (done / total_tables) * 100)
                task.view_progress = build_batch_view_progress(
                    current_table=tn,
                    current_index=done,
                    total_tables=total_tables,
                    failed_count=len(failed_tables),
                    completed_tables=sorted(completed_set),
                )
                task.log = '\n'.join(log)
                task.save(update_fields=['progress', 'view_progress', 'log'])

            if task.cancel_requested:
                pass
            elif failed_tables:
                task.status = 'partial'
                log.append(f"部分完成：主键对齐 {total_tables} 张表中失败 {len(failed_tables)} 张")
                for tname, err in failed_tables:
                    log.append(f"  - {tname}: {err}")
            else:
                task.status = 'completed'
                task.progress = 100
                if total_tables > 1:
                    log.append(f"全部完成：主键对齐共 {total_tables} 张表")

        else:
            wm_col = (getattr(task, 'watermark_column', None) or '').strip()
            wm_after = getattr(task, 'last_watermark', None)
            use_wm = (
                imode == 'timestamp'
                and wm_col
                and wm_after is not None
                and str(wm_after).strip() != ''
            )
            if use_wm:
                log.append(f"增量模式: 水位列 {wm_col}")

            failed_tables = []
            if total_tables > 1 and not resume_mode:
                log.append(f"批量迁移表：共 {total_tables} 张，按任务中的顺序依次迁移。")
                task.progress = 0.0
                task.view_progress = build_batch_view_progress(
                    current_table=table_names[0] if table_names else '',
                    current_index=base_done,
                    total_tables=total_tables,
                    failed_count=0,
                    completed_tables=sorted(completed_set),
                )
                task.log = '\n'.join(log)
                task.save(update_fields=['progress', 'view_progress', 'log'])

            for loop_idx, table_name in enumerate(table_names):
                idx = base_done + loop_idx
                task.refresh_from_db()
                if task.cancel_requested:
                    log.append(f"用户取消，已完成 {idx}/{total_tables} 张表")
                    task.status = 'partial'
                    break
                if total_tables > 1:
                    log.append(f"【开始】第 {idx + 1}/{total_tables} 张表: {table_name}")
                    task.view_progress = build_batch_view_progress(
                        current_table=table_name,
                        current_index=idx,
                        total_tables=total_tables,
                        failed_count=len(failed_tables),
                        completed_tables=sorted(completed_set),
                    )
                    _persist_running_task_log(task, log, extra_update_fields={'view_progress'})
                try:
                    ctx = None
                    if total_tables > 1:
                        ctx = {
                            'total_tables': total_tables,
                            'table_index': idx,
                            'failed_count': len(failed_tables),
                        }
                    _migrate_single_table(
                        oracle_cursor, pg_conn, pg_cursor,
                        task.source_schema, task.target_schema, table_name,
                        task.conflict_strategy, log, task=task,
                        all_tables_context=ctx,
                        watermark_column=wm_col if use_wm else None,
                        watermark_min_exclusive=wm_after if use_wm else None,
                    )
                    if use_wm:
                        _update_task_last_watermark_max(task, oracle_cursor, log, table_name)
                    if total_tables > 1:
                        mark_table_completed(completed_set, table_name)
                except Exception as table_err:
                    from .migration_errors import MigrationCancelledError, format_db_error
                    err_msg = format_db_error(table_err)
                    log.append(f"表 {table_name} 迁移失败: {err_msg}")
                    if not isinstance(table_err, MigrationCancelledError):
                        log.append(traceback.format_exc())
                    failed_tables.append((table_name, err_msg))

                if total_tables > 1:
                    done = idx + 1
                    task.progress = min(100.0, (done / total_tables) * 100)
                    task.view_progress = build_batch_view_progress(
                        current_table=table_name,
                        current_index=done,
                        total_tables=total_tables,
                        failed_count=len(failed_tables),
                        completed_tables=sorted(completed_set),
                    )
                    task.log = '\n'.join(log)
                    task.save(update_fields=['progress', 'view_progress', 'log'])

            if task.cancel_requested:
                task.status = 'partial'
                log.append(f"用户取消，已完成 {len(completed_set)}/{total_tables} 张表")
            elif total_tables > 1:
                if failed_tables:
                    task.status = 'partial'
                    log.append(f"部分完成：共 {total_tables} 张表，失败 {len(failed_tables)} 张")
                    for tname, err in failed_tables:
                        log.append(f"  - {tname}: {err}")
                else:
                    task.status = 'completed'
                    task.progress = 100
                    log.append(f"全部完成：共迁移 {total_tables} 张表")
            else:
                if failed_tables:
                    task.status = 'failed'
                else:
                    task.status = 'completed'
                    task.progress = 100

        if oracle_cursor:
            oracle_cursor.close()
        if oracle_conn:
            oracle_conn.close()
        if pg_cursor:
            pg_cursor.close()
        if pg_conn:
            pg_conn.close()

        if task.status == 'completed':
            task.progress = 100
        final_vp = normalize_view_progress(task.view_progress)
        final_vp.pop('resume', None)
        if total_tables > 1:
            final_vp['completed_tables'] = sorted(completed_set)
        task.view_progress = final_vp
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

    except Exception as e:
        from .migration_errors import MigrationCancelledError, format_db_error, rollback_quietly, safe_close_db_resources
        rollback_quietly(pg_conn)
        error_msg = format_db_error(e)
        log.append(f"迁移任务发生错误: {error_msg}")
        if not isinstance(e, MigrationCancelledError):
            log.append(f"详细错误: {traceback.format_exc()}")
        safe_close_db_resources(oracle_cursor, oracle_conn, pg_cursor, pg_conn)
        task.status = 'partial' if isinstance(e, MigrationCancelledError) else 'failed'
        try:
            final_vp = normalize_view_progress(task.view_progress)
            final_vp.pop('resume', None)
            if total_tables > 1:
                final_vp['completed_tables'] = sorted(completed_set)
            task.view_progress = final_vp
        except NameError:
            pass
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

def convert_oracle_to_pg_type(oracle_type, data_length=None, data_precision=None, data_scale=None):
    """将Oracle数据类型转换为PostgreSQL数据类型"""
    logger.debug(f"转换数据类型: {oracle_type}, 长度={data_length}, 精度={data_precision}, 小数位={data_scale}")
    
    oracle_type = oracle_type.upper()
    
    # 基本数据类型映射
    type_map = {
        'NUMBER': 'NUMERIC',
        'VARCHAR2': 'VARCHAR',
        'CHAR': 'CHAR',
        # Oracle DATE 含时分秒，映射为 TIMESTAMP(0) 避免 PG DATE 截断
        'DATE': 'TIMESTAMP(0)',
        'TIMESTAMP WITH TIME ZONE': 'TIMESTAMPTZ',
        'TIMESTAMP WITH LOCAL TIME ZONE': 'TIMESTAMP',
        'TIMESTAMP': 'TIMESTAMP',
        'CLOB': 'TEXT',
        'NCLOB': 'TEXT',
        'BLOB': 'BYTEA',
        'NVARCHAR2': 'VARCHAR',
        'NCHAR': 'CHAR',
        'FLOAT': 'REAL',
        'BINARY_FLOAT': 'REAL',
        'BINARY_DOUBLE': 'DOUBLE PRECISION',
        'RAW': 'BYTEA',
        'LONG RAW': 'BYTEA',
        'LONG': 'TEXT',
        # ===== v2.1 新增类型映射 =====
        # XML 类型：PG 原生支持 XML（需启用 xml 模块或直接用 TEXT）
        'XMLTYPE': 'XML',
        # ROWID/UROWID：Oracle 物理行标识，PG 无直接对应，用 CHAR(18) 保留
        'ROWID': 'CHAR(18)',
        'UROWID': 'CHAR(40)',
        # BFILE：Oracle 外部文件指针，PG 无对应，用 TEXT 记录路径
        'BFILE': 'TEXT',
        # INTERVAL 类型：PG 原生支持 INTERVAL
        'INTERVAL YEAR TO MONTH': 'INTERVAL',
        'INTERVAL DAY TO SECOND': 'INTERVAL',
        # BINARY_FLOAT/DOUBLE 已在上面映射
        # Oracle BOOLEAN（PL/SQL 中使用，表列不直接支持但兼容）
        'BOOLEAN': 'BOOLEAN',
    }
    
    if oracle_type == 'NUMBER':
        # 根据精度和小数位处理NUMBER类型
        if data_precision is not None:
            if data_scale is not None and data_scale > 0:
                return f"NUMERIC({data_precision}, {data_scale})"
            else:
                # 如果精度小于等于10且没有小数位，使用INTEGER或BIGINT
                if data_precision <= 4:
                    return "SMALLINT"
                elif data_precision <= 9:
                    return "INTEGER"
                elif data_precision <= 18:
                    return "BIGINT"
                else:
                    return f"NUMERIC({data_precision})"
        else:
            # 未指定精度的NUMBER，使用NUMERIC
            return "NUMERIC"
    elif oracle_type == 'VARCHAR2' or oracle_type == 'NVARCHAR2':
        # 处理字符串类型，添加长度限制
        if data_length is not None and data_length > 0:
            # PostgreSQL的VARCHAR限制为10485760
            if data_length > 10485760:
                return "TEXT"
            else:
                return f"VARCHAR({data_length})"
        else:
            # 如果没有指定长度或长度为0，使用VARCHAR(255)
            return "VARCHAR(255)"
    elif oracle_type == 'CHAR' or oracle_type == 'NCHAR':
        # 处理定长字符串
        if data_length is not None and data_length > 0:
            return f"CHAR({data_length})"
        else:
            return "CHAR(1)"
    elif oracle_type == 'TIMESTAMP' and data_scale is not None:
        # 处理带精度的TIMESTAMP
        return f"TIMESTAMP({data_scale})"
    elif oracle_type.startswith('INTERVAL'):
        # 处理 INTERVAL YEAR TO MONTH / INTERVAL DAY TO SECOND
        # 可能带精度如 INTERVAL YEAR(2) TO MONTH / INTERVAL DAY(2) TO SECOND(6)
        import re
        m = re.match(r'INTERVAL\s+YEAR\s*(?:\((\d+)\))?\s*TO\s*MONTH', oracle_type)
        if m:
            precision = m.group(1) or '2'
            return f"INTERVAL YEAR TO MONTH"  # PG 不接受精度参数，用默认
        m = re.match(r'INTERVAL\s+DAY\s*(?:\((\d+)\))?\s*TO\s*SECOND\s*(?:\((\d+)\))?', oracle_type)
        if m:
            second_precision = m.group(2)
            if second_precision:
                return f"INTERVAL DAY TO SECOND({second_precision})"
            return "INTERVAL DAY TO SECOND"
        # 兜底
        return "INTERVAL"
    elif oracle_type in type_map:
        # 使用映射表中的对应类型
        return type_map[oracle_type]
    else:
        # 对于未知类型，记录警告并返回TEXT
        logger.warning(f"未知的Oracle数据类型: {oracle_type}，将使用TEXT代替")
        return "TEXT"

def convert_oracle_to_sqlite_type(oracle_type, data_length=None, data_precision=None, data_scale=None):
    """将Oracle数据类型转换为SQLite数据类型"""
    oracle_type = (oracle_type or '').upper()
    
    if oracle_type in ['VARCHAR2', 'NVARCHAR2', 'CHAR', 'NCHAR', 'CLOB', 'NCLOB', 'LONG', 'XMLTYPE']:
        return "TEXT"
    if oracle_type in ['DATE', 'TIMESTAMP', 'TIMESTAMP WITH LOCAL TIME ZONE', 'TIMESTAMP WITH TIME ZONE']:
        return "TEXT"
    if oracle_type in ['BLOB', 'BYTEA', 'RAW', 'LONG RAW']:
        return "BLOB"
    if oracle_type in ['FLOAT', 'BINARY_FLOAT', 'BINARY_DOUBLE']:
        return "REAL"
    if oracle_type == 'NUMBER':
        if data_scale and data_scale > 0:
            return "REAL"
        if data_precision and data_precision <= 10:
            return "INTEGER"
        return "NUMERIC"
    if oracle_type == 'INTEGER':
        return "INTEGER"
    if oracle_type == 'DECIMAL':
        return "NUMERIC"
    
    return "TEXT"

def convert_oracle_to_pg_mview(oracle_mview_text):
    """将 Oracle 物化视图定义转换为 PostgreSQL 查询体。"""
    return _convert_mview_sql(oracle_mview_text)


def convert_oracle_to_pg_routine(oracle_routine_text):
    """将 Oracle 存储过程/函数源码做基础语法转换。"""
    return _convert_routine_sql(oracle_routine_text)

def migrate_all_tables(task_id, postgres_database=None):
    """迁移指定 schema 的所有表。在当前任务中依次迁移每张表，不创建子任务、不调用线程池，避免 interpreter shutdown 时 submit 报错。"""
    task = get_object_or_404(MigrationTask, pk=task_id)

    vp_init = normalize_view_progress(task.view_progress)
    resume_mode = bool(vp_init.pop('resume', False))
    completed_set = get_completed_tables(task) if resume_mode else set()

    # 更新任务状态
    task.status = 'running'
    if not task.started_at:
        task.started_at = timezone.now()
    task.save()

    if resume_mode:
        log = [ln for ln in (task.log or '').split('\n') if ln is not None]
    else:
        log = []
    if MIGRATION_PARALLEL_TABLE_WORKERS > 1:
        log.append(
            f"【所有表迁移】并行模式，最多同时 {MIGRATION_PARALLEL_TABLE_WORKERS} 张表；"
            f"不创建子任务记录。"
        )
    else:
        log.append("【所有表迁移】顺序模式，不创建子任务。")
    # 记录数据库信息
    if postgres_database:
        log.append(f"目标PostgreSQL数据库: {postgres_database}")

    oracle_conn = oracle_cursor = pg_conn = pg_cursor = None
    try:
        # 连接Oracle数据库
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        
        # 连接PostgreSQL数据库
        pg_conn = get_postgres_connection(task.postgres_connection.id, postgres_database)
        pg_cursor = pg_conn.cursor()
        
        # 获取PostgreSQL数据库名
        pg_cursor.execute("SELECT current_database()")
        current_db = pg_cursor.fetchone()[0]
        log.append(f"已连接到PostgreSQL数据库: {current_db}")
        
        # 获取源schema中的所有表
        query = """
        SELECT TABLE_NAME FROM ALL_TABLES 
        WHERE OWNER = :schema
        ORDER BY TABLE_NAME
        """
        oracle_cursor.execute(query, schema=task.source_schema)
        table_rows = oracle_cursor.fetchall()
        raw_names = [row[0] for row in table_rows]
        try:
            sorted_names = _topological_sort_tables_by_fk(oracle_cursor, task.source_schema, raw_names)
        except Exception as sort_err:
            logger.warning(f"外键拓扑排序失败，使用数据库原始顺序: {sort_err}")
            sorted_names = raw_names
        if raw_names and [x.upper() for x in raw_names] != [x.upper() for x in sorted_names]:
            log.append("已根据外键依赖对表迁移顺序进行拓扑排序（父表优先）；存在环时剩余表按名字追加。")
        all_tables_sorted = sorted_names

        if not all_tables_sorted:
            log.append(f"源schema '{task.source_schema}'中没有找到表")
            task.status = 'completed'
            task.log = '\n'.join(log)
            task.completed_at = timezone.now()
            task.save()
            oracle_cursor.close()
            oracle_conn.close()
            pg_cursor.close()
            pg_conn.close()
            return

        total_tables = len(all_tables_sorted)
        base_done = len(completed_set)
        if resume_mode:
            tables = filter_pending_tables(all_tables_sorted, completed_set)
            log.append(
                f"【继续迁移】源 schema 共 {total_tables} 张表，已完成 {base_done} 张，"
                f"剩余 {len(tables)} 张待迁移"
            )
            if not tables:
                log.append("【继续迁移】所有表均已迁移完成")
                task.status = 'completed'
                task.progress = 100.0
                task.view_progress = build_batch_view_progress(
                    current_table='',
                    current_index=total_tables,
                    total_tables=total_tables,
                    failed_count=0,
                    completed_tables=sorted(completed_set),
                )
                task.log = '\n'.join(log)
                task.completed_at = timezone.now()
                task.save()
                oracle_cursor.close()
                oracle_conn.close()
                pg_cursor.close()
                pg_conn.close()
                return
        else:
            tables = all_tables_sorted
            completed_set = set()
            base_done = 0
            log.append(
                f"在源schema '{task.source_schema}'中找到 {total_tables} 个表，"
                f"将在当前任务中依次迁移（不创建子任务）"
            )

        first_table = tables[0] if tables else ''
        if not resume_mode:
            task.progress = 0.0
        task.view_progress = build_batch_view_progress(
            current_table=first_table,
            current_index=base_done,
            total_tables=total_tables,
            failed_count=0,
            completed_tables=sorted(completed_set),
        )
        task.log = '\n'.join(log)
        task.save(update_fields=['progress', 'view_progress', 'log'])

        failed_tables = []
        # 可重入：parallel_tables 持锁调用本函数时避免死锁
        state_lock = threading.RLock()
        running_tables: set = set()

        def _flush_parallel_progress() -> None:
            with state_lock:
                done = len(completed_set)
                # 快照，避免迭代 set 时与其它线程 add/discard 交错
                rt = sorted(set(running_tables))
                if rt:
                    hint = rt[0] if len(rt) == 1 else f"{rt[0]} 等 {len(rt)} 张"
                elif completed_set:
                    hint = sorted(completed_set)[-1]
                else:
                    hint = ''
                task.progress = min(100.0, (done / total_tables) * 100)
                task.view_progress = build_batch_view_progress(
                    current_table=hint,
                    current_index=done,
                    total_tables=total_tables,
                    failed_count=len(failed_tables),
                    completed_tables=sorted(completed_set),
                    running_tables=rt,
                    parallel_workers=MIGRATION_PARALLEL_TABLE_WORKERS,
                )
                task.log = '\n'.join(log)
            task.save(update_fields=['progress', 'view_progress', 'log'])

        def _should_cancel() -> bool:
            task.refresh_from_db()
            return bool(task.cancel_requested)

        use_parallel = MIGRATION_PARALLEL_TABLE_WORKERS > 1 and len(tables) > 1

        if use_parallel:
            oracle_cursor.close()
            oracle_conn.close()
            pg_cursor.close()
            pg_conn.close()
            oracle_cursor = oracle_conn = pg_cursor = pg_conn = None

            run_parallel_table_migrations(
                task=task,
                tables=tables,
                total_tables=total_tables,
                base_done=base_done,
                completed_set=completed_set,
                log=log,
                failed_tables=failed_tables,
                running_tables=running_tables,
                postgres_database=postgres_database,
                on_progress=_flush_parallel_progress,
                should_cancel=_should_cancel,
                state_lock=state_lock,
            )
            if _should_cancel():
                task.status = 'partial'
                log.append(f"用户取消，已完成 {len(completed_set)}/{total_tables} 张表")
        else:
            for loop_idx, table_name in enumerate(tables):
                idx = base_done + loop_idx
                log.append(f"【开始】第 {idx + 1}/{total_tables} 张表: {table_name}")
                task.view_progress = build_batch_view_progress(
                    current_table=table_name,
                    current_index=idx,
                    total_tables=total_tables,
                    failed_count=len(failed_tables),
                    completed_tables=sorted(completed_set),
                )
                _persist_running_task_log(task, log, extra_update_fields={'view_progress'})

                task.refresh_from_db()
                if task.cancel_requested:
                    log.append(f"用户取消，已完成 {idx}/{total_tables} 张表")
                    task.status = 'partial'
                    break
                try:
                    _migrate_single_table(
                        oracle_cursor, pg_conn, pg_cursor,
                        task.source_schema, task.target_schema, table_name,
                        task.conflict_strategy, log, task=task,
                        all_tables_context={
                            'total_tables': total_tables,
                            'table_index': idx,
                            'failed_count': len(failed_tables),
                        },
                    )
                    completed_list = mark_table_completed(completed_set, table_name)
                except Exception as table_err:
                    from .migration_errors import format_db_error
                    err_msg = format_db_error(table_err)
                    log.append(f"表 {table_name} 迁移失败: {err_msg}")
                    failed_tables.append((table_name, err_msg))
                    completed_list = sorted(completed_set)
                done = idx + 1
                task.progress = min(100.0, (done / total_tables) * 100)
                task.view_progress = build_batch_view_progress(
                    current_table=table_name,
                    current_index=done,
                    total_tables=total_tables,
                    failed_count=len(failed_tables),
                    completed_tables=completed_list,
                )
                task.log = '\n'.join(log)
                task.save(update_fields=['progress', 'view_progress', 'log'])

            from .migration_errors import safe_close_db_resources
            safe_close_db_resources(oracle_cursor, oracle_conn, pg_cursor, pg_conn)
            oracle_cursor = oracle_conn = pg_cursor = pg_conn = None

        # 根据是否有失败表设置最终状态
        if task.cancel_requested:
            pass  # 已在上面设为 partial
        elif failed_tables:
            task.status = 'partial'
            log.append(f"部分完成：共 {total_tables} 张表，失败 {len(failed_tables)} 张")
            for tname, err in failed_tables:
                log.append(f"  - {tname}: {err}")
        else:
            task.status = 'completed'
            log.append(f"全部完成：共迁移 {total_tables} 张表")
        final_vp = normalize_view_progress(task.view_progress)
        final_vp.pop('resume', None)
        final_vp['completed_tables'] = sorted(completed_set)
        task.view_progress = final_vp
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

    except Exception as e:
        from .migration_errors import format_db_error, safe_close_db_resources
        error_msg = format_db_error(e)
        trace = traceback.format_exc()
        log.append(f"错误: {error_msg}")
        log.append(f"详细错误: {trace}")
        safe_close_db_resources(oracle_cursor, oracle_conn, pg_cursor, pg_conn)
        task.status = 'failed'
        final_vp = normalize_view_progress(task.view_progress)
        final_vp.pop('resume', None)
        final_vp['completed_tables'] = sorted(completed_set) if completed_set else final_vp.get('completed_tables', [])
        task.view_progress = final_vp
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

def _migrate_one_sequence(oracle_cursor, pg_conn, pg_cursor, source_schema, target_schema, seq_name,
                          conflict_strategy, log_list, id_case='lower'):
    """
    根据 ALL_SEQUENCES 在 PolarDB/PostgreSQL 中创建等价序列（常见属性映射）。

    注意：PostgreSQL 中一条 SQL 失败后事务进入 aborted 状态，后续所有查询
    都会报「当前事务被终止」。本函数内任何异常都会先 rollback 再向上抛出，
    保证批量迁移时一个序列失败不影响下一个。

    Oracle NUMBER 最大 38 位，但 PostgreSQL bigint 最大 9223372036854775807
    （19 位）。当 Oracle 序列的 MAX_VALUE/LAST_NUMBER 超过 bigint 范围时，
    自动截断到 bigint 最大值，避免 CREATE SEQUENCE 失败。
    """
    # PostgreSQL bigint 范围上限
    PG_BIGINT_MAX = 9223372036854775807
    PG_BIGINT_MIN = -9223372036854775808

    strategy = conflict_strategy or 'error'
    try:
        # 确保目标 schema 存在，否则 CREATE SEQUENCE 会报「模式不存在」
        pg_cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = %s",
            (target_schema,),
        )
        if not pg_cursor.fetchone():
            pg_cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}"')
            pg_conn.commit()
            log_list.append(f'  自动创建 schema: {target_schema}')

        oracle_cursor.execute("""
            SELECT MIN_VALUE, MAX_VALUE, INCREMENT_BY, CYCLE_FLAG, ORDER_FLAG, CACHE_SIZE, LAST_NUMBER
            FROM ALL_SEQUENCES
            WHERE SEQUENCE_OWNER = :o AND SEQUENCE_NAME = :n
        """, {'o': source_schema.upper(), 'n': seq_name.upper()})
        row = oracle_cursor.fetchone()
        if not row:
            raise Exception(f"找不到序列 {source_schema}.{seq_name}")
        min_v, max_v, inc_by, cycle_f, _order_f, cache_sz, last_num = (
            int(row[0]), int(row[1]), int(row[2]), row[3], row[4],
            int(row[5]) if row[5] is not None else 20,
            int(row[6]) if row[6] is not None else 1,
        )
        # 关键：Oracle 序列值可能超过 PostgreSQL bigint 范围，需截断
        clamped = False
        if min_v < PG_BIGINT_MIN:
            min_v = PG_BIGINT_MIN
            clamped = True
        if max_v > PG_BIGINT_MAX:
            max_v = PG_BIGINT_MAX
            clamped = True
        if last_num > PG_BIGINT_MAX:
            last_num = PG_BIGINT_MAX
            clamped = True
        if inc_by > PG_BIGINT_MAX:
            inc_by = 1
            clamped = True

        cycle_sql = 'CYCLE' if (cycle_f or 'N') == 'Y' else 'NO CYCLE'
        cache_n = max(1, int(cache_sz) if cache_sz else 1)
        seq_ident = apply_identifier_case(seq_name, id_case)
        pg_cursor.execute(
            """
            SELECT 1 FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'S' AND n.nspname = %s AND c.relname = %s
            """,
            (target_schema, seq_ident),
        )
        exists = pg_cursor.fetchone() is not None
        if exists:
            if strategy == 'skip':
                log_list.append(f"序列 {target_schema}.{seq_ident} 已存在，跳过")
                return
            if strategy == 'error':
                raise Exception(f"序列 {target_schema}.{seq_ident} 已存在")
            pg_cursor.execute(f"DROP SEQUENCE IF EXISTS {target_schema}.{seq_ident} CASCADE")
            pg_conn.commit()
        sql = (
            f"CREATE SEQUENCE {target_schema}.{seq_ident} "
            f"INCREMENT BY {inc_by} MINVALUE {min_v} MAXVALUE {max_v} "
            f"START WITH {last_num} CACHE {cache_n} {cycle_sql}"
        )
        pg_cursor.execute(sql)
        pg_conn.commit()
        if clamped:
            log_list.append(f"已创建序列: {target_schema}.{seq_ident}（注：原值超出 bigint 范围，已截断）")
        else:
            log_list.append(f"已创建序列: {target_schema}.{seq_ident}")
    except Exception:
        # 关键：失败时必须 rollback，否则事务留在 aborted 状态，
        # 后续所有 SQL 都会报「当前事务被终止, 事务块结束之前的查询被忽略」
        try:
            pg_conn.rollback()
        except Exception:
            pass
        raise


def migrate_sequence(task_id, postgres_database=None):
    """迁移单个 Oracle 序列至 PostgreSQL。"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    log = []
    if postgres_database:
        log.append(f"目标PostgreSQL数据库: {postgres_database}")
    oracle_conn = oracle_cursor = pg_conn = pg_cursor = None
    try:
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        pg_conn = get_postgres_connection(task.postgres_connection.id, postgres_database)
        pg_cursor = pg_conn.cursor()
        _migrate_one_sequence(
            oracle_cursor, pg_conn, pg_cursor,
            task.source_schema, task.target_schema, task.source_object,
            task.conflict_strategy, log,
            id_case=getattr(task, 'identifier_case', 'lower') or 'lower',
        )
        task.status = 'completed'
        task.progress = 100
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
    except Exception as e:
        from .migration_errors import format_db_error, rollback_quietly
        rollback_quietly(pg_conn)
        task.status = 'failed'
        log.append(format_db_error(e))
        log.append(traceback.format_exc())
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
    finally:
        from .migration_errors import safe_close_db_resources
        safe_close_db_resources(oracle_cursor, oracle_conn, pg_cursor, pg_conn)


def migrate_trigger(task_id, postgres_database=None):
    """
    导出 Oracle 触发器源码并生成 PL/pgSQL 改写模板。
    不向目标库自动下发 DDL；任务状态为 exported（已导出待人工处理）。
    支持 source_objects 批量导出。
    """
    from .task_logging import (
        make_step_log, make_info_log, make_ok_log,
        make_warn_log, make_error_log,
    )
    from .trigger_export import export_one_trigger, parse_trigger_names

    task = get_object_or_404(MigrationTask, pk=task_id)
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    log = []
    make_step_log(log, f'触发器导出任务 #{task_id} 启动')
    make_info_log(log, '本任务仅导出 Oracle 源码与 PL/pgSQL 改写模板，不会在目标库自动创建触发器')
    make_info_log(log, '请在任务日志中复制模板，人工完成业务逻辑改写后在 PolarDB-PG 执行')
    if postgres_database:
        make_info_log(log, f'参考目标 PostgreSQL 数据库: {postgres_database}')

    try:
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        make_ok_log(log, '已连接 Oracle 源端')

        trigger_names = parse_trigger_names(task)
        if not trigger_names:
            make_error_log(log, '未指定要导出的触发器')
            raise Exception("未指定要导出的触发器")
        make_info_log(log, f'待导出触发器数: {len(trigger_names)}')

        exported, failed = 0, []
        for idx, tname in enumerate(trigger_names):
            make_step_log(log, f'导出触发器 {task.source_schema}.{tname}',
                          total=len(trigger_names), index=idx)
            meta, _body, export_log = export_one_trigger(
                oracle_cursor, task.source_schema, tname,
            )
            if meta:
                log.append(export_log)
                exported += 1
            else:
                failed.append(tname)
                log.append(export_log)

        oracle_cursor.close()
        oracle_conn.close()

        make_step_log(log, '任务结束')
        if exported == 0:
            task.status = 'failed'
            make_error_log(log, f'全部导出失败 ({len(failed)}): {", ".join(failed)}')
        elif failed:
            task.status = 'partial'
            make_ok_log(log, f'部分导出成功 ({exported}/{len(trigger_names)})')
            make_error_log(log, f'失败 ({len(failed)}): {", ".join(failed)}')
        else:
            task.status = 'exported'
            make_ok_log(log, f'已成功导出 {exported} 个触发器，状态为「已导出待人工处理」')
        task.progress = 100
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
    except Exception as e:
        task.status = 'failed'
        make_error_log(log, f'任务异常: {e}')
        make_error_log(log, traceback.format_exc())
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()


def _replay_schema_foreign_keys(task, postgres_database=None) -> None:
    """全 Schema 编排：表数据导入完成后回放外键。"""
    from .batch_config import get_enable_fk_replay
    from .schema_converter import apply_foreign_keys_for_schema

    if not get_enable_fk_replay():
        append_line = '【外键回放】已在平台配置中关闭，跳过'
        task.log = (task.log or '') + '\n' + append_line
        task.save(update_fields=['log'])
        return
    if not task.postgres_connection_id:
        return
    oracle_conn = oracle_cursor = pg_conn = pg_cursor = None
    fk_log: list[str] = []
    try:
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        pgdb = postgres_database or task.postgres_database or task.postgres_connection.database
        pg_conn = get_postgres_connection(task.postgres_connection.id, pgdb)
        pg_cursor = pg_conn.cursor()
        id_case = getattr(task, 'identifier_case', 'lower') or 'lower'
        apply_foreign_keys_for_schema(
            oracle_cursor, pg_cursor, pg_conn,
            task.source_schema, task.target_schema or task.source_schema,
            fk_log, id_case=id_case,
        )
        if fk_log:
            task.log = (task.log or '') + '\n' + '\n'.join(fk_log)
            task.save(update_fields=['log'])
    except Exception as e:
        task.log = (task.log or '') + f'\n【外键回放】失败: {e}'
        task.save(update_fields=['log'])
    finally:
        from .migration_errors import safe_close_db_resources
        safe_close_db_resources(oracle_cursor, oracle_conn, pg_cursor, pg_conn)


def migrate_schema_orchestration(task_id, postgres_database=None):
    """
    全 Schema 编排：先迁移序列，再复用「所有表」逻辑迁移全部表；其余对象请单独建任务。
    继续迁移时保留 resume 标记与已完成表，跳过序列阶段直接进入迁表。
    """
    from .resume import get_completed_tables, normalize_view_progress
    from .task_logging import append_migration_log

    task = get_object_or_404(MigrationTask, pk=task_id)
    vp_init = normalize_view_progress(task.view_progress)
    resume_mode = bool(vp_init.pop('resume', False))
    completed_set = get_completed_tables(task) if resume_mode else set()
    # 已有表级进度或日志中已完成表 → 续传时跳过序列阶段
    skip_sequences = resume_mode and (
        bool(completed_set)
        or vp_init.get('current') is not None
        or vp_init.get('total') is not None
        or vp_init.get('phase') in ('all_tables', 'done')
        or int(vp_init.get('phase_index') or 0) >= 1
    )

    task.status = 'running'
    if not task.started_at:
        task.started_at = timezone.now()
    phases = ['sequences', 'all_tables', 'foreign_keys', 'done']
    if not resume_mode:
        task.progress = 0
    if resume_mode:
        vp_init['resume'] = True
        if completed_set:
            vp_init['completed_tables'] = sorted(completed_set)
        task.view_progress = vp_init
    else:
        task.view_progress = {
            'orchestration': True,
            'phase': phases[0],
            'phase_index': 0,
            'phases': phases,
        }
    task.save()

    phase1_log = []
    try:
        if skip_sequences:
            phase1_log.append(
                f"【继续迁移】【编排】跳过序列阶段，直接进入迁表（已完成 {len(completed_set)} 张表）"
            )
            task.view_progress = {
                'orchestration': True,
                'phase': phases[1],
                'phase_index': 1,
                'phases': phases,
                'resume': True,
                **({} if not completed_set else {'completed_tables': sorted(completed_set)}),
            }
            task.save(update_fields=['view_progress'])
            if phase1_log:
                task.refresh_from_db()
                head = '\n'.join(phase1_log)
                task.log = f"{head}\n{task.log}" if task.log else head
                task.save(update_fields=['log'])
            migrate_all_tables(task_id, postgres_database)
            task.refresh_from_db()
            if task.status != 'failed':
                _replay_schema_foreign_keys(task, postgres_database)
                task.refresh_from_db()
            if task.status == 'failed':
                task.view_progress = {
                    'orchestration': True,
                    'phase': phases[1],
                    'phase_index': 1,
                    'phases': phases,
                    'tables_phase_failed': True,
                }
            else:
                task.view_progress = {
                    'orchestration': True,
                    'phase': phases[-1],
                    'phase_index': len(phases) - 1,
                    'phases': phases,
                }
            task.save(update_fields=['view_progress'])
            try:
                append_migration_log(
                    task,
                    '【编排】物化视图、普通视图、例程、触发器请通过对应任务类型分别迁移。',
                )
            except Exception:
                task.refresh_from_db()
                task.log = (task.log or '') + '\n【编排】物化视图、普通视图、例程、触发器请通过对应任务类型分别迁移。'
                task.save(update_fields=['log'])
            return

        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        pg_conn = get_postgres_connection(task.postgres_connection.id, postgres_database)
        pg_cursor = pg_conn.cursor()

        phase1_log.append("【编排】阶段一：迁移序列")
        oracle_cursor.execute("""
            SELECT SEQUENCE_NAME FROM ALL_SEQUENCES
            WHERE SEQUENCE_OWNER = :s ORDER BY SEQUENCE_NAME
        """, {'s': task.source_schema.upper()})
        seq_rows = [r[0] for r in oracle_cursor.fetchall()]
        phase1_log.append(f"共 {len(seq_rows)} 个序列")
        for sn in seq_rows:
            try:
                _migrate_one_sequence(
                    oracle_cursor, pg_conn, pg_cursor,
                    task.source_schema, task.target_schema, sn,
                    task.conflict_strategy, phase1_log,
                    id_case=getattr(task, 'identifier_case', 'lower') or 'lower',
                )
            except Exception as se:
                phase1_log.append(f"序列 {sn} 失败: {se}")

        oracle_cursor.close()
        oracle_conn.close()
        pg_cursor.close()
        pg_conn.close()

        task.view_progress = {
            'orchestration': True,
            'phase': phases[1],
            'phase_index': 1,
            'phases': phases,
        }
        task.save(update_fields=['view_progress'])

        migrate_all_tables(task_id, postgres_database)

        task.refresh_from_db()
        if task.status != 'failed':
            _replay_schema_foreign_keys(task, postgres_database)
            task.refresh_from_db()
        merged = '\n'.join(phase1_log) + '\n\n' + (task.log or '')
        task.log = merged
        # 全表阶段失败时不把编排进度标为 done，避免界面误以为编排已成功收尾
        if task.status == 'failed':
            task.view_progress = {
                'orchestration': True,
                'phase': phases[1],
                'phase_index': 1,
                'phases': phases,
                'tables_phase_failed': True,
            }
        else:
            task.view_progress = {
                'orchestration': True,
                'phase': phases[-1],
                'phase_index': len(phases) - 1,
                'phases': phases,
            }
        task.save(update_fields=['log', 'view_progress'])
        try:
            append_migration_log(
                task,
                '【编排】物化视图、普通视图、例程、触发器请通过对应任务类型分别迁移。',
            )
        except Exception:
            task.refresh_from_db()
            task.log = (task.log or '') + '\n【编排】物化视图、普通视图、例程、触发器请通过对应任务类型分别迁移。'
            task.save(update_fields=['log'])
    except Exception as e:
        task.status = 'failed'
        task.log = (task.log or '') + f"\n编排任务失败: {e}\n{traceback.format_exc()}"
        task.completed_at = timezone.now()
        task.save()


@login_required
def oracle_database_management(request):
    """Oracle数据库管理视图"""
    # 获取所有Oracle连接
    oracle_connections = OracleConnection.objects.all()
    
    context = {
        'oracle_connections': oracle_connections,
    }
    return render(request, 'migration_app/oracle/database_management.html', context)

def _test_oracle_connect_with_params(host, port, service_name, username, password):
    """使用给定参数测试 Oracle 连接，返回 (success, error_message)。"""
    try:
        port = int(port) if port is not None else 1521
    except (TypeError, ValueError):
        return False, '端口格式无效'
    try:
        dsn = cx_Oracle.makedsn(host, port, service_name=service_name)
        # cx_Oracle.connect() 不支持 connect_timeout 参数，需通过 DSN 或 Oracle 客户端配置超时
        connection = cx_Oracle.connect(
            user=username,
            password=password or '',
            dsn=dsn
        )
        connection.close()
        return True, None
    except cx_Oracle.DatabaseError as e:
        error_obj, = e.args
        if error_obj.code == 12170 or 'timeout' in str(e).lower():
            return False, '无法连接到数据库，连接超时'
        return False, str(e)
    except Exception as e:
        return False, str(e)


@login_required
@csrf_exempt
def test_oracle_connection(request):
    """测试Oracle数据库连接。支持仅传 connection_id（用已保存配置），或传 host/port/service_name/username/password（用前端未保存的输入）"""
    if request.method == 'POST':
        try:
            if request.content_type and 'application/json' in request.content_type:
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({'status': 'error', 'message': '无效的JSON数据'})
            else:
                data = dict(request.POST.items())

            connection_id = data.get('connection_id')
            use_form_params = all(
                data.get(k) is not None and data.get(k) != ''
                for k in ('host', 'port', 'service_name', 'username')
            )
            if use_form_params:
                host = (data.get('host') or '').strip()
                port = data.get('port', 1521)
                service_name = (data.get('service_name') or '').strip()
                username = (data.get('username') or '').strip()
                if not host or not service_name or not username:
                    return JsonResponse({'status': 'error', 'message': '请填写主机、服务名和用户名'})
                if connection_id:
                    try:
                        conn_obj = OracleConnection.objects.get(pk=connection_id)
                        password = (data.get('password') or '').strip() or _connection_plain_password(conn_obj.password)
                    except (OracleConnection.DoesNotExist, ValueError):
                        password = (data.get('password') or '').strip()
                        if not password:
                            return JsonResponse({'status': 'error', 'message': '请填写密码'})
                else:
                    password = (data.get('password') or '').strip()
                    if not password:
                        return JsonResponse({'status': 'error', 'message': '请填写密码'})
                success, err_msg = _test_oracle_connect_with_params(host, port, service_name, username, password)
                if success:
                    return JsonResponse({'status': 'success'})
                return JsonResponse({'status': 'error', 'message': err_msg or '连接测试失败'})

            if not connection_id:
                return JsonResponse({'status': 'error', 'message': '未提供连接ID'})

            conn_obj = get_object_or_404(OracleConnection, pk=connection_id)
            success, err_msg = _test_oracle_connect_with_params(
                conn_obj.host, conn_obj.port, conn_obj.service_name,
                conn_obj.username, _connection_plain_password(conn_obj.password)
            )
            if success:
                return JsonResponse({'status': 'success'})
            return JsonResponse({'status': 'error', 'message': err_msg or '连接测试失败'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

@login_required
@csrf_exempt
def save_oracle_connection(request):
    """保存Oracle数据库连接"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            host = request.POST.get('host')
            port = request.POST.get('port')
            service_name = request.POST.get('service_name')
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            if not all([name, host, port, service_name, username, password]):
                return JsonResponse({'status': 'error', 'message': '请填写所有必填字段'})
            
            # 创建新的连接
            connection = OracleConnection.objects.create(
                name=name,
                host=host,
                port=port,
                service_name=service_name,
                username=username,
                password=password
            )
            
            # 记录审计日志
            record_audit(
                request,
                action='create_oracle_connection',
                target_type='connection',
                target_id=connection.id,
                payload={'name': name, 'host': host, 'service_name': service_name},
                result='success'
            )
            
            return JsonResponse({'status': 'success', 'message': '连接保存成功'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

@login_required
@csrf_exempt
def delete_oracle_connection(request):
    """删除Oracle数据库连接"""
    if request.method == 'POST':
        try:
            connection_id = request.POST.get('connection_id')
            if not connection_id:
                return JsonResponse({'status': 'error', 'message': '未提供连接ID'})
            
            connection = OracleConnection.objects.get(id=connection_id)
            connection.delete()
            
            # 记录审计日志
            record_audit(
                request,
                action='delete_oracle_connection',
                target_type='connection',
                target_id=connection_id,
                result='success'
            )
            
            return JsonResponse({'status': 'success', 'message': '连接删除成功'})
        except OracleConnection.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '连接不存在'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

@login_required
@csrf_exempt
def edit_oracle_connection(request):
    """编辑Oracle数据库连接"""
    if request.method == 'POST':
        try:
            # 支持JSON和表单数据
            if request.content_type and 'application/json' in request.content_type:
                try:
                    data = json.loads(request.body)
                    connection_id = data.get('connection_id')
                    name = data.get('name')
                    host = data.get('host')
                    port = data.get('port')
                    service_name = data.get('service_name')
                    username = data.get('username')
                    password = data.get('password')
                except json.JSONDecodeError:
                    return JsonResponse({'status': 'error', 'message': '无效的JSON数据'})
            else:
                connection_id = request.POST.get('connection_id')
                name = request.POST.get('name')
                host = request.POST.get('host')
                port = request.POST.get('port')
                service_name = request.POST.get('service_name')
                username = request.POST.get('username')
                password = request.POST.get('password')
            
            if not connection_id:
                return JsonResponse({'status': 'error', 'message': '未提供连接ID'})
            
            try:
                connection = OracleConnection.objects.get(id=connection_id)
            except (OracleConnection.DoesNotExist, ValueError):
                return JsonResponse({'status': 'error', 'message': f'找不到ID为 {connection_id} 的连接'})
            
            if not all([name, host, port, service_name, username]):
                return JsonResponse({'status': 'error', 'message': '请填写所有必填字段'})
            
            # 更新连接信息
            connection.name = name
            connection.host = host
            connection.port = port
            connection.service_name = service_name
            connection.username = username
            
            # 如果提供了新密码，则更新密码
            if password:
                connection.password = password
            
            connection.save()
            
            # 记录审计日志
            record_audit(
                request,
                action='edit_oracle_connection',
                target_type='connection',
                target_id=connection_id,
                payload={'name': name, 'host': host},
                result='success'
            )
            
            return JsonResponse({'status': 'success', 'message': '连接更新成功'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

# PolarDB-PG数据库连接管理

@login_required
def pg_database_management(request):
    return render(request, 'migration_app/postgres/database_management.html')


@login_required
def get_pg_connections(request):
    try:
        # 获取当前用户的连接和没有指定用户的连接
        connections = PostgresConnection.objects.filter(
            models.Q(user=request.user) | models.Q(user__isnull=True)
        )
        data = [{
            'id': conn.id,
            'name': conn.name,
            'host': conn.host,
            'port': conn.port,
            'database': conn.database,
            'username': conn.username,
            'status': conn.status,
            'created_at': conn.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for conn in connections]
        return JsonResponse({'status': 'success', 'connections': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def add_pg_connection(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            host = request.POST.get('host')
            port = request.POST.get('port')
            database = request.POST.get('database')
            username = request.POST.get('username')
            password = request.POST.get('password')
            sslmode = (request.POST.get('sslmode') or '').strip()
            connection = PostgresConnection.objects.create(
                name=name,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                sslmode=sslmode,
                status='active'
            )
            
            # 记录审计日志
            record_audit(
                request,
                action='create_postgres_connection',
                target_type='connection',
                target_id=connection.id,
                payload={'name': name, 'host': host, 'database': database},
                result='success'
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

from django.views.decorators.csrf import csrf_exempt

def _test_pg_connect_with_params(host, port, database, user, password, sslmode=None):
    """使用给定参数测试 PG 连接，返回 (success, error_message)。"""
    try:
        port = int(port) if port is not None else 5432
    except (TypeError, ValueError):
        return False, '端口格式无效'

    def _connect(ssl_mode):
        kwargs = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password or '',
            'connect_timeout': 5
        }
        if ssl_mode:
            kwargs['sslmode'] = ssl_mode
        return psycopg2.connect(**kwargs)

    last_error = None
    # PolarDB 公网连接通常需要 SSL，优先尝试 sslmode=require
    ssl_try_order = [sslmode] if sslmode else []
    if not sslmode and host and ('aliyuncs.com' in host or 'polardb' in host.lower()):
        ssl_try_order = ['require', 'prefer', 'disable']
    elif not ssl_try_order:
        ssl_try_order = [None]

    for ssl_mode in ssl_try_order:
        try:
            conn = _connect(ssl_mode)
            conn.close()
            return True, None
        except psycopg2.OperationalError as e:
            last_error = e
            error_msg = str(e).lower()
            # SSL 相关错误时尝试其他模式
            if 'ssl' in error_msg or 'certificate' in error_msg:
                continue
            if 'timeout' in error_msg or 'could not connect' in error_msg or 'connection timed out' in error_msg:
                return False, '无法连接到数据库，连接超时。请检查：1) 主机地址和端口是否正确；2) PolarDB 控制台是否已添加当前 IP 到白名单。'
            if 'does not exist' in error_msg or ('database' in error_msg and 'fatal' in error_msg):
                return False, f'数据库 "{database}" 不存在，请先在该 PolarDB 实例上创建该数据库，或将连接配置中的数据库名改为已存在的库（如 postgres）。'
            if 'password authentication failed' in error_msg or 'authentication failed' in error_msg:
                raw_err = str(e).strip()
                hint = (
                    '用户名或密码错误。请检查：\n'
                    '1) 在 PolarDB 控制台「账号管理」中确认账号和密码正确；\n'
                    '2) 确认该账号已授权访问目标数据库；\n'
                    '3) 若使用公网连接，请确认已添加 IP 白名单；\n'
                    '4) 可尝试在连接配置中切换 SSL 模式（需要/禁用）。'
                )
                if raw_err:
                    hint += f'\n\n原始错误: {raw_err}'
                return False, hint
            return False, str(e)
        except Exception as e:
            last_error = e
            if ssl_mode != ssl_try_order[-1]:
                continue
            return False, str(e)

    if last_error:
        err_str = str(last_error).lower()
        if 'password authentication failed' in err_str or 'authentication failed' in err_str:
            raw_err = str(last_error).strip()
            return False, (
                '用户名或密码错误。请检查 PolarDB 控制台中的账号密码，确认已添加 IP 白名单。'
                f'\n\n原始错误: {raw_err}'
            )
        return False, str(last_error)
    return False, '连接测试失败'


@login_required
@csrf_exempt
def test_pg_connection(request):
    if request.method == 'POST':
        try:
            # 支持JSON和表单数据
            if request.content_type and 'application/json' in request.content_type:
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({'status': 'error', 'message': '无效的JSON数据'})
            else:
                data = dict(request.POST.items())

            connection_id = data.get('connection_id')
            # 若前端传入完整连接参数（编辑弹窗未保存即测试），则用当前输入值测试，不更新库里的连接状态
            use_form_params = all(
                data.get(k) is not None and data.get(k) != ''
                for k in ('host', 'port', 'database', 'username')
            )
            if use_form_params:
                host = data.get('host', '').strip()
                port = data.get('port', 5432)
                database = (data.get('database') or '').strip()
                username = (data.get('username') or '').strip()
                if not host or not database or not username:
                    return JsonResponse({'status': 'error', 'message': '请填写主机、数据库名和用户名'})
                if connection_id:
                    try:
                        connection = PostgresConnection.objects.get(id=connection_id)
                        password = (data.get('password') or '').strip() or _connection_plain_password(connection.password)
                    except (PostgresConnection.DoesNotExist, ValueError):
                        password = (data.get('password') or '').strip()
                        if not password:
                            return JsonResponse({'status': 'error', 'message': '请填写密码'})
                else:
                    password = (data.get('password') or '').strip()
                    if not password:
                        return JsonResponse({'status': 'error', 'message': '请填写密码'})
                sslmode = (data.get('sslmode') or '').strip() or None
                success, err_msg = _test_pg_connect_with_params(host, port, database, username, password, sslmode)
                if success:
                    return JsonResponse({'status': 'success'})
                return JsonResponse({'status': 'error', 'message': err_msg or '连接测试失败'})

            if not connection_id:
                return JsonResponse({'status': 'error', 'message': '未提供连接ID'})

            try:
                connection = PostgresConnection.objects.get(id=connection_id)
            except (PostgresConnection.DoesNotExist, ValueError):
                return JsonResponse({'status': 'error', 'message': f'找不到ID为 {connection_id} 的连接'})

            # 更新连接状态为测试中
            connection.status = 'testing'
            connection.save()

            try:
                sslmode = (getattr(connection, 'sslmode', None) or '').strip() or None
                success, err_msg = _test_pg_connect_with_params(
                    connection.host, connection.port, connection.database,
                    connection.username, _connection_plain_password(connection.password),
                    sslmode=sslmode
                )
                if success:
                    connection.status = 'active'
                    connection.save()
                    return JsonResponse({'status': 'success'})
                connection.status = 'inactive'
                connection.save()
                return JsonResponse({'status': 'error', 'message': err_msg or '连接测试失败'})
            except Exception as e:
                connection.status = 'inactive'
                connection.save()
                return JsonResponse({'status': 'error', 'message': f'连接测试失败: {str(e)}'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'测试连接时发生错误: {str(e)}'})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

@login_required
def delete_pg_connection(request):
    if request.method == 'POST':
        try:
            connection_id = request.POST.get('connection_id')
            connection = PostgresConnection.objects.get(id=connection_id, user=request.user)
            connection.delete()
            
            # 记录审计日志
            record_audit(
                request,
                action='delete_postgres_connection',
                target_type='connection',
                target_id=connection_id,
                result='success'
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def edit_pg_connection(request):
    if request.method == 'POST':
        try:
            # 支持JSON和表单数据
            if request.content_type and 'application/json' in request.content_type:
                try:
                    data = json.loads(request.body)
                    connection_id = data.get('connection_id')
                    name = data.get('name')
                    host = data.get('host')
                    port = data.get('port')
                    database = data.get('database')
                    username = data.get('username')
                    password = data.get('password')
                    sslmode = data.get('sslmode')
                except json.JSONDecodeError:
                    return JsonResponse({'status': 'error', 'message': '无效的JSON数据'})
            else:
                connection_id = request.POST.get('connection_id')
                name = request.POST.get('name')
                host = request.POST.get('host')
                port = request.POST.get('port')
                database = request.POST.get('database')
                username = request.POST.get('username')
                password = request.POST.get('password')
                sslmode = request.POST.get('sslmode')
            
            if not connection_id:
                return JsonResponse({'status': 'error', 'message': '未提供连接ID'})
            
            try:
                connection = PostgresConnection.objects.get(id=connection_id)
            except (PostgresConnection.DoesNotExist, ValueError):
                return JsonResponse({'status': 'error', 'message': f'找不到ID为 {connection_id} 的连接'})
            
            # 更新连接信息
            connection.name = name
            connection.host = host
            connection.port = port
            connection.database = database
            connection.username = username
            
            if password:
                connection.password = password
            if sslmode is not None:
                connection.sslmode = (sslmode or '').strip()
            
            connection.save()
            
            # 记录审计日志
            record_audit(
                request,
                action='edit_postgres_connection',
                target_type='connection',
                target_id=connection_id,
                payload={'name': name, 'host': host, 'database': database},
                result='success'
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})
