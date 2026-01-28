from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from .models import OracleConnection, PostgresConnection, MigrationTask
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

def get_oracle_connection(connection_id):
    """创建Oracle连接"""
    conn_obj = get_object_or_404(OracleConnection, pk=connection_id)
    dsn = cx_Oracle.makedsn(conn_obj.host, conn_obj.port, service_name=conn_obj.service_name)
    connection = cx_Oracle.connect(
        user=conn_obj.username,
        password=conn_obj.password,
        dsn=dsn
    )
    return connection

def get_postgres_connection(connection_id, database=None):
    """创建PostgreSQL连接"""
    conn_obj = get_object_or_404(PostgresConnection, pk=connection_id)
    
    # 如果指定了数据库，使用指定的数据库名
    db_name = database if database else conn_obj.database
    
    connection = psycopg2.connect(
        host=conn_obj.host,
        port=conn_obj.port,
        database=db_name,
        user=conn_obj.username,
        password=conn_obj.password
    )
    return connection

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
    
    log = []
    
    # 记录数据库信息
    if postgres_database:
        log.append(f"目标PostgreSQL数据库: {postgres_database}")
    
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
        
        # 获取物化视图定义
        query = """
        SELECT TEXT FROM ALL_MVIEWS 
        WHERE OWNER = :schema AND MVIEW_NAME = :mview_name
        """
        oracle_cursor.execute(query, schema=task.source_schema, mview_name=task.source_object)
        result = oracle_cursor.fetchone()
        
        if not result:
            raise Exception(f"找不到物化视图 {task.source_schema}.{task.source_object}")
        
        mview_text = result[0]
        log.append(f"获取到物化视图定义: {mview_text}")
        
        # 转换为PostgreSQL物化视图语法
        pg_mview_text = convert_oracle_to_pg_mview(mview_text)
        log.append(f"转换后的PostgreSQL物化视图定义: {pg_mview_text}")
        
        # 创建PostgreSQL物化视图
        create_mview_sql = f"""
        CREATE MATERIALIZED VIEW {task.target_schema}.{task.source_object} AS
        {pg_mview_text}
        """
        
        pg_cursor.execute(create_mview_sql)
        pg_conn.commit()
        
        log.append(f"成功创建PostgreSQL物化视图 {task.target_schema}.{task.source_object}")
        
        # 关闭连接
        oracle_cursor.close()
        oracle_conn.close()
        pg_cursor.close()
        pg_conn.close()
        
        # 更新任务状态
        task.status = 'completed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
        
    except Exception as e:
        error_msg = str(e)
        trace = traceback.format_exc()
        log.append(f"错误: {error_msg}")
        log.append(f"详细错误: {trace}")
        
        # 更新任务状态
        task.status = 'failed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

def migrate_view(task_id, postgres_database=None):
    """迁移视图"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    
    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    
    log = []
   
    # 记录数据库信息
    if postgres_database:
        log.append(f"目标PostgreSQL数据库: {postgres_database}")
    
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
        
        # 获取视图定义
        query = """
        SELECT TEXT FROM ALL_VIEWS 
        WHERE OWNER = :schema AND VIEW_NAME = :view_name
        """
        oracle_cursor.execute(query, schema=task.source_schema, view_name=task.source_object)
        result = oracle_cursor.fetchone()
        
        if not result:
            raise Exception(f"找不到视图 {task.source_schema}.{task.source_object}")
        
        view_text = result[0]
        log.append(f"获取到视图定义: {view_text}")
        
        # 获取视图列信息
        query = """
        SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE
        FROM ALL_TAB_COLUMNS
        WHERE OWNER = :schema AND TABLE_NAME = :view_name
        ORDER BY COLUMN_ID
        """
        oracle_cursor.execute(query, schema=task.source_schema, view_name=task.source_object)
        columns = oracle_cursor.fetchall()

        if not columns:
            raise Exception(f"找不到视图 {task.source_schema}.{task.source_object} 的列信息")
        
        # 解析字段过滤配置
        selected_fields = []
        if task.selected_fields:
            raw_fields = re.split(r"[,\n;，；]+", task.selected_fields)
            selected_fields = [field.strip().upper() for field in raw_fields if field and field.strip()]
            if selected_fields:
                log.append(f"用户选择字段: {', '.join(selected_fields)}")
        
        if selected_fields:
            column_lookup = {col[0].upper(): col for col in columns}
            filtered_columns = []
            missing_columns = []
            for field in selected_fields:
                column = column_lookup.get(field)
                if column:
                    filtered_columns.append(column)
                else:
                    missing_columns.append(field)
            if missing_columns:
                raise Exception(f"以下字段在视图中不存在: {', '.join(missing_columns)}")
            columns = filtered_columns
        
        if not columns:
            raise Exception("字段列表为空，无法创建目标表")
        
        log.append(f"获取到视图列信息: 共 {len(columns)} 列")
        identifier_case = getattr(task, 'identifier_case', 'lower') or 'lower'
        target_schema = (task.target_schema or 'public').strip()
        derived_table_name = (task.target_object or task.source_object or '').strip()
        if not derived_table_name:
            raise Exception("未指定目标视图/表名称")
        if not task.target_object:
            derived_table_name = apply_identifier_case(derived_table_name, identifier_case)
        target_table = derived_table_name
        qualified_table_name = build_qualified_table_name(target_schema, target_table)
        display_table_name = f"{target_schema}.{target_table}"
        log.append(f"目标PostgreSQL表: {display_table_name}")
        
        # 创建PostgreSQL中的表而不是视图
        column_defs = []
        for column in columns:
            column_name, data_type, data_length, data_precision, data_scale, nullable = column
            pg_type = convert_oracle_to_pg_type(data_type, data_length, data_precision, data_scale)
            if data_type == 'VARCHAR2' and (data_length is None or data_length == 0):
                log.append(f"警告: 列 {column_name} 的VARCHAR长度为0，已自动调整为VARCHAR(255)")
                pg_type = "VARCHAR(255)"
            target_column_name = apply_identifier_case(column_name, identifier_case)
            nullable_str = " NOT NULL" if nullable == 'N' else ""
            column_defs.append(f"    {quote_identifier(target_column_name)} {pg_type}{nullable_str}")
        create_table_sql = f"CREATE TABLE {qualified_table_name} (\n" + ",\n".join(column_defs) + "\n)"
        log.append(f"创建表SQL: \n{create_table_sql}")
        
        conflict_strategy = task.conflict_strategy or 'error'
        pg_cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            )
            """,
            (target_schema, target_table)
        )
        table_exists = pg_cursor.fetchone()[0]
        log.append(f"检测表是否存在: {table_exists}")
        
        if table_exists:
            if conflict_strategy == 'error':
                raise Exception(f"表 {display_table_name} 已存在")
            elif conflict_strategy == 'replace':
                log.append(f"冲突策略为replace，删除已存在的表 {display_table_name}")
                pg_cursor.execute(f"DROP TABLE IF EXISTS {qualified_table_name}")
                pg_conn.commit()
                table_exists = False
            elif conflict_strategy == 'skip':
                log.append(f"冲突策略为skip，跳过已存在的表 {display_table_name}")
                task.status = 'completed'
                task.log = '\n'.join(log)
                task.completed_at = timezone.now()
                task.save()
                oracle_cursor.close()
                oracle_conn.close()
                pg_cursor.close()
                pg_conn.close()
                return
            elif conflict_strategy == 'truncate':
                log.append(f"冲突策略为truncate，清空表 {display_table_name}")
                pg_cursor.execute(f"TRUNCATE TABLE {qualified_table_name}")
                pg_conn.commit()
            elif conflict_strategy == 'append':
                log.append(f"冲突策略为append，将向现有表 {display_table_name} 追加数据")
        
        # 执行创建表
        try:
            if not table_exists:
                pg_cursor.execute(create_table_sql)
                pg_conn.commit()
                log.append(f"成功创建PostgreSQL表 {display_table_name}")

            # 从Oracle视图查询数据并插入到PostgreSQL表中
            if selected_fields:
                oracle_columns = ', '.join([col[0] for col in columns])
            else:
                oracle_columns = '*'
            oracle_query = f"SELECT {oracle_columns} FROM {task.source_schema}.{task.source_object}"
            log.append(f"查询视图数据SQL: {oracle_query}")
            
            oracle_cursor.arraysize = 5000
            oracle_cursor.execute(oracle_query)
            rows = oracle_cursor.fetchall()
            
            # 如果有数据，批量插入到PostgreSQL表中
            if rows:
                column_names = [apply_identifier_case(col[0], identifier_case) for col in oracle_cursor.description]
                placeholders = ", ".join(["%s"] * len(column_names))
                quoted_columns = [quote_identifier(col) for col in column_names]
                insert_sql = f"INSERT INTO {qualified_table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders})"
                widened_columns = set()
                
                while True:
                    try:
                        pg_cursor.executemany(insert_sql, rows)
                        pg_conn.commit()
                        break
                    
                    except psycopg2.errors.StringDataRightTruncation as trunc_err:
                        pg_conn.rollback()
                        column_name = getattr(getattr(trunc_err, 'diag', None), 'column_name', None)
                        if not column_name or column_name in widened_columns:
                            raise
                        widened_columns.add(column_name)
                        log.append(f"检测到列 {column_name} 字符串截断，自动扩展为TEXT")
                        alter_sql = f"ALTER TABLE {qualified_table_name} ALTER COLUMN {quote_identifier(column_name)} TYPE TEXT"
                        try:
                            pg_cursor.execute(alter_sql)
                            pg_conn.commit()
                        except psycopg2.errors.ObjectNotInPrerequisiteState as state_err:
                            log.append(f"尝试将列 {column_name} 调整为TEXT时出错: {str(state_err)}")
                        
                        log.append(f"已将列 {column_name} 调整为TEXT，重试数据写入")
                log.append(f"成功从视图导入 {len(rows)} 行数据到表 {display_table_name}")
            else:
                log.append(f"视图 {task.source_schema}.{task.source_object} 中没有找到数据")
         
        except psycopg2.Error as table_err:
            log.append(f"创建表或导入数据时出错: {str(table_err)}")
            # 记录 PostgreSQL 错误代码
            log.append(f"PostgreSQL 错误代码: {table_err.pgcode}")
            log.append(f"PostgreSQL 错误信息: {table_err.pgerror}")
            # 报错插入语句
            



        except Exception as table_err:
            log.append(f"创建表或导入数据时出错: {str(table_err)}")
            # 记录 PostgreSQL 错误代码
            log.append(f"PostgreSQL 错误代码: {table_err.pgcode}")
            log.append(f"PostgreSQL 错误信息: {table_err.pgerror}")
            if hasattr(table_err, 'target_column_name'):
                log.append(f"目标列名: {table_err.target_column_name}")
            # 打印出异常的完整信息
            log.append(f"异常详细信息: {table_err}")

            raise
        
        # 关闭连接
        oracle_cursor.close()
        oracle_conn.close()
        pg_cursor.close()
        pg_conn.close()
        
        # 更新任务状态
        task.status = 'completed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
        
    except Exception as e:
        error_msg = str(e)
        trace = traceback.format_exc()
        log.append(f"处理视图 {task.source_object} 时发生错误: {error_msg}")
        log.append(f"详细错误: {trace}")
        
        # 尝试关闭连接
        try:
            if 'oracle_cursor' in locals() and oracle_cursor:
                oracle_cursor.close()
            if 'oracle_conn' in locals() and oracle_conn:
                oracle_conn.close()
            if 'pg_cursor' in locals() and pg_cursor:
                pg_cursor.close()
            if 'pg_conn' in locals() and pg_conn:
                pg_conn.close()
        except Exception as close_err:
            log.append(f"关闭数据库连接时出错: {str(close_err)}")
        
        # 更新任务状态
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
    
    log = []
    
    # 记录数据库信息
    if postgres_database:
        log.append(f"目标PostgreSQL数据库: {postgres_database}")
    
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
        
        # 获取存储过程或函数定义
        query = """
        SELECT TEXT FROM ALL_SOURCE 
        WHERE OWNER = :schema AND NAME = :routine_name
        ORDER BY LINE
        """
        oracle_cursor.execute(query, schema=task.source_schema, routine_name=task.source_object)
        results = oracle_cursor.fetchall()
        
        if not results:
            raise Exception(f"找不到例程 {task.source_schema}.{task.source_object}")
        
        routine_text = '\n'.join([row[0] for row in results])
        log.append(f"获取到例程定义: {routine_text}")
        
        # 转换为PostgreSQL函数语法
        pg_routine_text = convert_oracle_to_pg_routine(routine_text)
        log.append(f"转换后的PostgreSQL函数定义: {pg_routine_text}")
        
        # 创建PostgreSQL函数
        pg_cursor.execute(pg_routine_text)
        pg_conn.commit()
        
        log.append(f"成功创建PostgreSQL函数 {task.target_schema}.{task.source_object}")
        
        # 关闭连接
        oracle_cursor.close()
        oracle_conn.close()
        pg_cursor.close()
        pg_conn.close()
        
        # 更新任务状态
        task.status = 'completed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
        
    except Exception as e:
        error_msg = str(e)
        trace = traceback.format_exc()
        log.append(f"错误: {error_msg}")
        log.append(f"详细错误: {trace}")
        
        # 更新任务状态
        task.status = 'failed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

def migrate_table(task_id, postgres_database=None):
    """迁移表结构和数据"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    
    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    
    log = []
    
    # 记录数据库信息
    if postgres_database:
        log.append(f"目标PostgreSQL数据库: {postgres_database}")
    
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
        
        # 获取表结构信息
        column_query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            DATA_LENGTH,
            DATA_PRECISION,
            DATA_SCALE,
            NULLABLE,
            COLUMN_ID
        FROM ALL_TAB_COLUMNS 
        WHERE OWNER = :schema 
          AND TABLE_NAME = :table_name
        ORDER BY COLUMN_ID
        """
        oracle_cursor.execute(column_query, schema=task.source_schema, table_name=task.source_object)
        columns = oracle_cursor.fetchall()
        
        if not columns:
            raise Exception(f"找不到表 {task.source_schema}.{task.source_object}")
        
        # 获取表主键信息
        pk_query = """
        SELECT cols.column_name
        FROM all_constraints cons, all_cons_columns cols
        WHERE cons.constraint_type = 'P'
          AND cons.constraint_name = cols.constraint_name
          AND cons.owner = cols.owner
          AND cols.owner = :schema
          AND cols.table_name = :table_name
        ORDER BY cols.position
        """
        oracle_cursor.execute(pk_query, schema=task.source_schema, table_name=task.source_object)
        primary_keys = [row[0] for row in oracle_cursor.fetchall()]
        
        # 构建创建表的SQL语句
        create_table_sql = f"CREATE TABLE {task.target_schema}.{task.source_object} (\n"
        
        # 映射Oracle数据类型到PostgreSQL数据类型
        column_definitions = []
        for column in columns:
            column_name = column[0]
            data_type = column[1]
            data_length = column[2]
            data_precision = column[3]
            data_scale = column[4]
            nullable = column[5]
            
            # 根据Oracle数据类型转换为PostgreSQL数据类型
            pg_type = convert_oracle_to_pg_type(data_type, data_length, data_precision, data_scale)
            
            # 处理VARCHAR长度为0或过小的问题
            if pg_type.startswith('VARCHAR('):
                # 提取括号中的长度
                match = re.search(r'VARCHAR\((\d+)\)', pg_type)
                if match:
                    length = int(match.group(1))
                    # 如果长度为0或过小，使用默认值
                    if length < 1:
                        pg_type = 'VARCHAR(255)'  # 设置默认长度为255
                        log.append(f"警告: 列 {column_name} 的VARCHAR长度为0，已自动调整为VARCHAR(255)")
            
            # 添加非空约束
            not_null = "NOT NULL" if nullable == 'N' else ""
            
            column_definitions.append(f"    {column_name} {pg_type} {not_null}")
        
        create_table_sql += ",\n".join(column_definitions)
        create_table_sql += "\n)"
        
        log.append(f"创建表SQL: \n{create_table_sql}")
        
        # 执行创建表
        try:
            pg_cursor.execute(create_table_sql)
            pg_conn.commit()
            log.append(f"成功创建PostgreSQL表 {task.target_schema}.{task.source_object}")
            
            # 从Oracle视图查询数据并插入到PostgreSQL表中
            oracle_query = f"SELECT * FROM {task.source_schema}.{task.source_object}"
            log.append(f"查询视图数据SQL: {oracle_query}")
            
            oracle_cursor.execute(oracle_query)
            rows = oracle_cursor.fetchall()
            
            # 如果有数据，批量插入到PostgreSQL表中
            if rows:
                # 获取列名（小写）
                column_names = [col[0].lower() for col in oracle_cursor.description]
                
                # 创建INSERT语句
                placeholders = ", ".join(["%s"] * len(column_names))
                quoted_columns = [f'"{col}"' for col in column_names]
                insert_sql = f"INSERT INTO public.{task.source_object.lower()} ({', '.join(quoted_columns)}) VALUES ({placeholders})"
                
                # 批量插入数据
                pg_cursor.executemany(insert_sql, rows)
                pg_conn.commit()
                log.append(f"成功从视图导入 {len(rows)} 行数据到表 {task.target_schema}.{task.source_object}")
            else:
                log.append(f"视图 {task.source_schema}.{task.source_object} 中没有找到数据")
        except Exception as table_err:
            log.append(f"创建表或导入数据时出错: {str(table_err)}")
            raise
        
        # 关闭连接
        oracle_cursor.close()
        oracle_conn.close()
        pg_cursor.close()
        pg_conn.close()
        
        # 更新任务状态
        task.status = 'completed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
        
    except Exception as e:
        error_msg = str(e)
        trace = traceback.format_exc()
        log.append(f"处理表 {task.source_object} 时发生错误: {error_msg}")
        log.append(f"详细错误: {trace}")
        
        # 尝试关闭连接
        try:
            if 'oracle_cursor' in locals() and oracle_cursor:
                oracle_cursor.close()
            if 'oracle_conn' in locals() and oracle_conn:
                oracle_conn.close()
            if 'pg_cursor' in locals() and pg_cursor:
                pg_cursor.close()
            if 'pg_conn' in locals() and pg_conn:
                pg_conn.close()
        except Exception as close_err:
            log.append(f"关闭数据库连接时出错: {str(close_err)}")
        
        # 更新任务状态
        task.status = 'failed'
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
        'DATE': 'DATE',
        'TIMESTAMP': 'TIMESTAMP',
        'CLOB': 'TEXT',
        'BLOB': 'BYTEA',
        'NVARCHAR2': 'VARCHAR',
        'NCHAR': 'CHAR',
        'FLOAT': 'REAL',
        'BINARY_FLOAT': 'REAL',
        'BINARY_DOUBLE': 'DOUBLE PRECISION',
        'RAW': 'BYTEA',
        'LONG RAW': 'BYTEA',
        'LONG': 'TEXT',
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
    elif oracle_type in type_map:
        # 使用映射表中的对应类型
        return type_map[oracle_type]
    else:
        # 对于未知类型，记录警告并返回TEXT
        logger.warning(f"未知的Oracle数据类型: {oracle_type}，将使用TEXT代替")
        return "TEXT"

def apply_identifier_case(name, case_option):
    """根据任务配置调整标识符大小写"""
    if not name:
        return name
    if case_option == 'lower':
        return name.lower()
    if case_option == 'upper':
        return name.upper()
    return name

def quote_identifier(name):
    """对标识符进行双引号转义"""
    if name is None:
        return '""'
    safe = str(name).replace('"', '""')
    return f'"{safe}"'

def build_qualified_table_name(schema, table):
    """返回带双引号的schema.table格式"""
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"

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
    """将Oracle物化视图定义转换为PostgreSQL物化视图定义"""
    # 示例简单转换，实际情况可能需要更复杂的解析和转换
    pg_mview_text = oracle_mview_text
    
    # 替换Oracle特定的SQL语法
    pg_mview_text = pg_mview_text.replace('SYSDATE', 'CURRENT_DATE')
    pg_mview_text = pg_mview_text.replace('NVL(', 'COALESCE(')
    
    return pg_mview_text

def convert_oracle_to_pg_routine(oracle_routine_text):
    """将Oracle存储过程/函数定义转换为PostgreSQL函数定义"""
    # 示例简单转换，实际情况可能需要更复杂的解析和转换
    pg_routine_text = oracle_routine_text
    
    # 替换Oracle特定的SQL语法
    pg_routine_text = pg_routine_text.replace('SYSDATE', 'CURRENT_DATE')
    pg_routine_text = pg_routine_text.replace('NVL(', 'COALESCE(')
    
    return pg_routine_text

def migrate_all_tables(task_id, postgres_database=None):
    """迁移指定schema的所有表"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    
    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    
    log = []
    
    # 记录数据库信息
    if postgres_database:
        log.append(f"目标PostgreSQL数据库: {postgres_database}")
    
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
        tables = oracle_cursor.fetchall()
        
        if not tables:
            log.append(f"源schema '{task.source_schema}'中没有找到表")
            task.status = 'completed'
            task.log = '\n'.join(log)
            task.completed_at = timezone.now()
            task.save()
            return
        
        log.append(f"在源schema '{task.source_schema}'中找到 {len(tables)} 个表")
        
        # 创建批处理任务
        task.is_batch = True
        task.save()
        
        # 为每个表创建子任务
        for table_row in tables:
            table_name = table_row[0]
            log.append(f"为表 {table_name} 创建子任务")
            
            # 创建子任务
            subtask = MigrationTask(
                name=f"{task.name} - {table_name}",
                task_type='table',
                source_schema=task.source_schema,
                target_schema=task.target_schema,
                source_object=table_name,
                oracle_connection=task.oracle_connection,
                postgres_connection=task.postgres_connection,
                conflict_strategy=task.conflict_strategy,
                parent_task=task,
                status='pending'
            )
            subtask.save()
            
            # 提交子任务到执行器
            executor = get_task_executor()
            executor.submit(migrate_table, subtask.id, postgres_database)
        
        log.append(f"已为所有表创建子任务并提交执行")
        
        # 关闭连接
        oracle_cursor.close()
        oracle_conn.close()
        pg_cursor.close()
        pg_conn.close()
        
        # 更新任务状态
        task.status = 'running'  # 保持运行状态，直到所有子任务完成
        task.log = '\n'.join(log)
        task.save()
        
    except Exception as e:
        error_msg = str(e)
        trace = traceback.format_exc()
        log.append(f"错误: {error_msg}")
        log.append(f"详细错误: {trace}")
        
        # 更新任务状态
        task.status = 'failed'
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()

def oracle_database_management(request):
    """Oracle数据库管理视图"""
    # 获取所有Oracle连接
    oracle_connections = OracleConnection.objects.all()
    
    context = {
        'oracle_connections': oracle_connections,
    }
    return render(request, 'migration_app/oracle/database_management.html', context)

@csrf_exempt
def test_oracle_connection(request):
    """测试Oracle数据库连接"""
    if request.method == 'POST':
        try:
            if request.content_type and 'application/json' in request.content_type:
                try:
                    data = json.loads(request.body)
                    connection_id = data.get('connection_id')
                except json.JSONDecodeError:
                    return JsonResponse({'status': 'error', 'message': '无效的JSON数据'})
            else:
                connection_id = request.POST.get('connection_id')
            
            if not connection_id:
                return JsonResponse({'status': 'error', 'message': '未提供连接ID'})
            
            conn_obj = get_object_or_404(OracleConnection, pk=connection_id)
            dsn = cx_Oracle.makedsn(conn_obj.host, conn_obj.port, service_name=conn_obj.service_name)
            connection = cx_Oracle.connect(
                user=conn_obj.username,
                password=conn_obj.password,
                dsn=dsn,
                connect_timeout=5
            )
            connection.close()
            return JsonResponse({'status': 'success'})
        except cx_Oracle.DatabaseError as e:
            error_obj, = e.args
            if error_obj.code == 12170 or 'timeout' in str(e).lower():
                return JsonResponse({'status': 'error', 'message': '无法连接到数据库，连接超时'})
            return JsonResponse({'status': 'error', 'message': str(e)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

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
            
            return JsonResponse({'status': 'success', 'message': '连接保存成功'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

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
            
            return JsonResponse({'status': 'success', 'message': '连接删除成功'})
        except OracleConnection.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '连接不存在'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

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
            return JsonResponse({'status': 'success', 'message': '连接更新成功'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

# PolarDB-PG数据库连接管理

def pg_database_management(request):
    return render(request, 'migration_app/postgres/database_management.html')


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


def add_pg_connection(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            host = request.POST.get('host')
            port = request.POST.get('port')
            database = request.POST.get('database')
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            # 创建新连接
            connection = PostgresConnection.objects.create(
                name=name,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                status='active'
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def test_pg_connection(request):
    if request.method == 'POST':
        try:
            # 支持JSON和表单数据
            if request.content_type and 'application/json' in request.content_type:
                try:
                    data = json.loads(request.body)
                    connection_id = data.get('connection_id')
                except json.JSONDecodeError:
                    return JsonResponse({'status': 'error', 'message': '无效的JSON数据'})
            else:
                connection_id = request.POST.get('connection_id')
            
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
                # 测试连接，设置5秒超时
                conn = psycopg2.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database,
                    user=connection.username,
                    password=connection.password,
                    connect_timeout=5
                )
                conn.close()
                
                # 更新连接状态为正常
                connection.status = 'active'
                connection.save()
                
                return JsonResponse({'status': 'success'})
            except psycopg2.OperationalError as e:
                # 更新连接状态为异常
                connection.status = 'inactive'
                connection.save()
                error_msg = str(e).lower()
                if 'timeout' in error_msg or 'could not connect' in error_msg or 'connection timed out' in error_msg:
                    return JsonResponse({'status': 'error', 'message': '无法连接到数据库，连接超时'})
                return JsonResponse({'status': 'error', 'message': f'连接测试失败: {str(e)}'})
            except Exception as e:
                # 更新连接状态为异常
                connection.status = 'inactive'
                connection.save()
                return JsonResponse({'status': 'error', 'message': f'连接测试失败: {str(e)}'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'测试连接时发生错误: {str(e)}'})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

def delete_pg_connection(request):
    if request.method == 'POST':
        try:
            connection_id = request.POST.get('connection_id')
            connection = PostgresConnection.objects.get(id=connection_id, user=request.user)
            connection.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

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
            
            # 如果提供了新密码，则更新密码
            if password:
                connection.password = password
            
            connection.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})
