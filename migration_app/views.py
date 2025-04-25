from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from .models import OracleConnection, PostgresConnection, MigrationTask
import cx_Oracle
import psycopg2
import logging
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
import os
from django.conf import settings
import io

# 配置日志
logger = logging.getLogger(__name__)

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

def get_postgres_connection(connection_id):
    """创建PostgreSQL连接"""
    conn_obj = get_object_or_404(PostgresConnection, pk=connection_id)
    connection = psycopg2.connect(
        host=conn_obj.host,
        port=conn_obj.port,
        database=conn_obj.database,
        user=conn_obj.username,
        password=conn_obj.password
    )
    return connection

def migrate_materialized_view(task_id):
    """迁移物化视图"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    
    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    
    log = []
    
    try:
        # 连接Oracle数据库
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        
        # 连接PostgreSQL数据库
        pg_conn = get_postgres_connection(task.postgres_connection.id)
        pg_cursor = pg_conn.cursor()
        
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

def migrate_view(task_id):
    """迁移视图"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    
    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    
    log = []
    
    try:
        # 连接Oracle数据库
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        
        # 连接PostgreSQL数据库
        pg_conn = get_postgres_connection(task.postgres_connection.id)
        pg_cursor = pg_conn.cursor()
        
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
        
        # 转换为PostgreSQL视图语法
        pg_view_text = convert_oracle_to_pg_view(view_text)
        log.append(f"转换后的PostgreSQL视图定义: {pg_view_text}")
        
        # 创建PostgreSQL视图
        create_view_sql = f"""
        CREATE OR REPLACE VIEW {task.target_schema}.{task.source_object} AS
        {pg_view_text}
        """
        
        pg_cursor.execute(create_view_sql)
        pg_conn.commit()
        
        log.append(f"成功创建PostgreSQL视图 {task.target_schema}.{task.source_object}")
        
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

def migrate_routine(task_id):
    """迁移例程（存储过程、函数）"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    
    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    
    log = []
    
    try:
        # 连接Oracle数据库
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        
        # 连接PostgreSQL数据库
        pg_conn = get_postgres_connection(task.postgres_connection.id)
        pg_cursor = pg_conn.cursor()
        
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

def migrate_table(task_id):
    """迁移表"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    
    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.progress = 0
    task.save()
    
    log = []
    
    try:
        # 连接Oracle数据库
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        
        # 连接PostgreSQL数据库
        pg_conn = get_postgres_connection(task.postgres_connection.id)
        pg_cursor = pg_conn.cursor()
        
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
            
            # 添加非空约束
            not_null = "NOT NULL" if nullable == 'N' else ""
            
            column_definitions.append(f"    {column_name} {pg_type} {not_null}")
        
        # 添加主键约束
        if primary_keys:
            primary_key_clause = f",\n    PRIMARY KEY ({', '.join(primary_keys)})"
        else:
            primary_key_clause = ""
        
        create_table_sql += ",\n".join(column_definitions)
        create_table_sql += primary_key_clause
        create_table_sql += "\n)"
        
        log.append(f"创建表SQL: \n{create_table_sql}")
        
        # 创建表
        pg_cursor.execute(create_table_sql)
        pg_conn.commit()
        
        # 更新进度
        task.progress = 20
        task.log = '\n'.join(log)
        task.save()
        
        # 检查是否请求取消
        task.refresh_from_db()
        if task.cancel_requested:
            raise Exception("任务被用户取消")
        
        # 获取数据总量
        count_query = f"SELECT COUNT(*) FROM {task.source_schema}.{task.source_object}"
        oracle_cursor.execute(count_query)
        total_count = oracle_cursor.fetchone()[0]
        log.append(f"总共有 {total_count} 条数据需要迁移")
        
        # 获取表数据
        data_query = f"SELECT * FROM {task.source_schema}.{task.source_object}"
        oracle_cursor.execute(data_query)
        
        # 准备插入语句
        column_names = [col[0] for col in columns]
        placeholders = ", ".join(["%s"] * len(column_names))
        insert_sql = f"INSERT INTO {task.target_schema}.{task.source_object} ({', '.join(column_names)}) VALUES ({placeholders})"
        
        # 批量插入数据
        batch_size = 1000
        row_count = 0
        batch_data = []
        
        for row in oracle_cursor:
            # 检查是否请求取消
            if row_count % 5000 == 0:  # 每5000行检查一次
                task.refresh_from_db()
                if task.cancel_requested:
                    raise Exception("任务被用户取消")
            
            # 将None转换为对应的null值，LOB类型转换为字符串或二进制数据
            processed_row = []
            for i, val in enumerate(row):
                # 处理LOB类型
                if val is None:
                    processed_row.append(None)
                elif isinstance(val, cx_Oracle.LOB):
                    # 记录LOB类型处理
                    column_name = column_names[i] if i < len(column_names) else f"列{i}"
                    logger.debug(f"处理LOB类型 {type(val).__name__} 数据，列: {column_name}")
                    
                    try:
                        # 根据LOB类型处理
                        if isinstance(val, cx_Oracle.CLOB) or isinstance(val, cx_Oracle.NCLOB):
                            # 文本LOB转为字符串
                            if val.size() > 10 * 1024 * 1024:  # 大于10MB的LOB
                                logger.info(f"发现大型CLOB，大小: {val.size()/(1024*1024):.2f}MB，使用分块读取")
                                # 分块读取大型LOB
                                chunk_size = 1024 * 1024  # 1MB块
                                offset = 1  # Oracle LOB是1-based
                                buffer = []
                                while offset <= val.size():
                                    chunk = val.read(offset, min(chunk_size, val.size() - offset + 1))
                                    buffer.append(chunk)
                                    offset += len(chunk)
                                processed_val = ''.join(buffer)
                            else:
                                processed_val = val.read()
                            logger.debug(f"已将CLOB/NCLOB转换为字符串，长度: {len(processed_val) if processed_val else 0}")
                        else:  # BLOB
                            # 二进制LOB转为二进制数据
                            if val.size() > 10 * 1024 * 1024:  # 大于10MB的LOB
                                logger.info(f"发现大型BLOB，大小: {val.size()/(1024*1024):.2f}MB，使用分块读取")
                                # 分块读取大型LOB
                                chunk_size = 1024 * 1024  # 1MB块
                                offset = 1  # Oracle LOB是1-based
                                buffer = io.BytesIO()
                                while offset <= val.size():
                                    chunk = val.read(offset, min(chunk_size, val.size() - offset + 1))
                                    buffer.write(chunk)
                                    offset += len(chunk)
                                buffer.seek(0)
                                processed_val = buffer.read()
                            else:
                                processed_val = val.read()
                            logger.debug(f"已将BLOB转换为二进制数据，长度: {len(processed_val) if processed_val else 0}")
                        
                        processed_row.append(processed_val)
                    except Exception as lob_err:
                        error_detail = str(lob_err)
                        logger.error(f"处理LOB数据失败: {error_detail}", exc_info=True)
                        log.append(f"处理列 {column_name} 的LOB数据失败: {error_detail}")
                        # 如果读取失败，用空值代替
                        processed_row.append(None)
                else:
                    processed_row.append(val)
            
            batch_data.append(processed_row)
            row_count += 1
            
            # 达到批处理大小时执行批量插入
            if len(batch_data) >= batch_size:
                try:
                    pg_cursor.executemany(insert_sql, batch_data)
                    pg_conn.commit()
                    progress_percent = min(80, 20 + (row_count / total_count * 60)) if total_count > 0 else 50
                    task.progress = progress_percent
                    log.append(f"已迁移 {row_count} 条数据，进度: {row_count}/{total_count}")
                except Exception as batch_error:
                    error_msg = str(batch_error)
                    logger.error(f"批量插入数据失败: {error_msg}", exc_info=True)
                    log.append(f"批量插入数据失败: {error_msg}")
                    # 尝试单行插入，跳过有问题的行
                    log.append("尝试单行插入模式，跳过有问题的行...")
                    success_count = 0
                    for i, single_row in enumerate(batch_data):
                        try:
                            pg_cursor.execute(insert_sql, single_row)
                            success_count += 1
                        except Exception as row_error:
                            log.append(f"跳过第 {row_count - len(batch_data) + i + 1} 行: {str(row_error)}")
                    
                    pg_conn.commit()
                    log.append(f"单行模式成功插入 {success_count}/{len(batch_data)} 行")
                
                task.log = '\n'.join(log)
                task.save()
                batch_data = []
        
        # 处理剩余数据
        if batch_data:
            try:
                pg_cursor.executemany(insert_sql, batch_data)
                pg_conn.commit()
                log.append(f"已迁移 {row_count} 条数据，进度: {row_count}/{total_count}")
            except Exception as batch_error:
                error_msg = str(batch_error)
                logger.error(f"批量插入剩余数据失败: {error_msg}", exc_info=True)
                log.append(f"批量插入剩余数据失败: {error_msg}")
                # 尝试单行插入，跳过有问题的行
                log.append("尝试单行插入模式，跳过有问题的行...")
                success_count = 0
                for i, single_row in enumerate(batch_data):
                    try:
                        pg_cursor.execute(insert_sql, single_row)
                        success_count += 1
                    except Exception as row_error:
                        log.append(f"跳过第 {row_count - len(batch_data) + i + 1} 行: {str(row_error)}")
                
                pg_conn.commit()
                log.append(f"单行模式成功插入 {success_count}/{len(batch_data)} 行")
        
        # 更新进度
        task.progress = 90
        task.log = '\n'.join(log)
        task.save()
        
        # 检查是否请求取消
        task.refresh_from_db()
        if task.cancel_requested:
            raise Exception("任务被用户取消")
        
        # 创建索引
        index_query = """
        SELECT 
            i.INDEX_NAME,
            i.UNIQUENESS,
            c.COLUMN_NAME
        FROM ALL_INDEXES i
        JOIN ALL_IND_COLUMNS c ON i.INDEX_NAME = c.INDEX_NAME AND i.OWNER = c.INDEX_OWNER
        WHERE i.TABLE_OWNER = :schema
          AND i.TABLE_NAME = :table_name
          AND i.INDEX_TYPE = 'NORMAL'
          AND i.UNIQUENESS = 'UNIQUE'
        ORDER BY i.INDEX_NAME, c.COLUMN_POSITION
        """
        oracle_cursor.execute(index_query, schema=task.source_schema, table_name=task.source_object)
        indexes = oracle_cursor.fetchall()
        
        # 按索引名称分组
        index_map = {}
        for idx in indexes:
            index_name = idx[0]
            uniqueness = idx[1]
            column_name = idx[2]
            
            if index_name not in index_map:
                index_map[index_name] = {
                    'uniqueness': uniqueness,
                    'columns': []
                }
            
            index_map[index_name]['columns'].append(column_name)
        
        # 创建索引
        for index_name, index_info in index_map.items():
            unique = "UNIQUE" if index_info['uniqueness'] == 'UNIQUE' else ""
            columns = ", ".join(index_info['columns'])
            create_index_sql = f"CREATE {unique} INDEX {index_name} ON {task.target_schema}.{task.source_object} ({columns})"
            
            try:
                pg_cursor.execute(create_index_sql)
                pg_conn.commit()
                log.append(f"创建索引: {create_index_sql}")
            except Exception as e:
                log.append(f"创建索引失败: {str(e)}")
        
        log.append(f"成功创建并填充表 {task.target_schema}.{task.source_object}")
        
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
        log.append(f"错误: {error_msg}")
        log.append(f"详细错误: {trace}")
        
        # 判断是否是用户取消
        if "任务被用户取消" in error_msg:
            task.status = 'canceled'
        else:
            task.status = 'failed'
        
        task.log = '\n'.join(log)
        task.completed_at = timezone.now()
        task.save()
        
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
        except:
            pass

def migrate_all_tables(task_id):
    """迁移所有表"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    
    # 更新任务状态
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    
    log = []
    
    try:
        # 连接Oracle数据库
        oracle_conn = get_oracle_connection(task.oracle_connection.id)
        oracle_cursor = oracle_conn.cursor()
        
        # 获取源Schema中所有表
        query = """
        SELECT TABLE_NAME 
        FROM ALL_TABLES 
        WHERE OWNER = :schema 
        ORDER BY TABLE_NAME
        """
        oracle_cursor.execute(query, schema=task.source_schema)
        tables = oracle_cursor.fetchall()
        
        if not tables:
            raise Exception(f"在Schema {task.source_schema}中未找到任何表")
        
        log.append(f"在Schema {task.source_schema}中找到 {len(tables)} 个表")
        
        # 为每个表创建子任务
        successful_tables = 0
        failed_tables = 0
        
        for table in tables:
            table_name = table[0]
            sub_task = MigrationTask.objects.create(
                name=f"{task.name} - {table_name}",
                task_type='table',
                oracle_connection=task.oracle_connection,
                postgres_connection=task.postgres_connection,
                source_schema=task.source_schema,
                target_schema=task.target_schema,
                source_object=table_name,
                parent_task=task,
                is_batch=False
            )
            
            log.append(f"创建子任务 #{sub_task.id} 用于迁移表 {table_name}")
            
            try:
                # 同步执行迁移，而不是异步
                migrate_table(sub_task.id)
                
                # 检查子任务状态
                sub_task.refresh_from_db()
                if sub_task.status == 'completed':
                    successful_tables += 1
                    log.append(f"表 {table_name} 迁移成功")
                else:
                    failed_tables += 1
                    log.append(f"表 {table_name} 迁移失败：{sub_task.log}")
            except Exception as e:
                failed_tables += 1
                error_msg = str(e)
                log.append(f"表 {table_name} 迁移出错: {error_msg}")
                
                # 更新子任务状态
                sub_task.status = 'failed'
                sub_task.log = error_msg
                sub_task.completed_at = timezone.now()
                sub_task.save()
        
        # 关闭连接
        oracle_cursor.close()
        oracle_conn.close()
        
        # 更新主任务状态
        if failed_tables == 0:
            task.status = 'completed'
            log.append(f"所有 {len(tables)} 个表迁移成功")
        elif successful_tables == 0:
            task.status = 'failed'
            log.append(f"所有 {len(tables)} 个表迁移失败")
        else:
            task.status = 'partial'
            log.append(f"部分表迁移成功: {successful_tables} 成功, {failed_tables} 失败")
        
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

# 转换函数
def convert_oracle_to_pg_mview(oracle_mview_text):
    """将Oracle物化视图语法转换为PostgreSQL物化视图语法"""
    # 这里实现语法转换逻辑
    # 简单示例，实际中可能需要更复杂的处理
    pg_mview_text = oracle_mview_text
    
    # 替换常见的Oracle特有语法
    pg_mview_text = pg_mview_text.replace('NVL(', 'COALESCE(')
    pg_mview_text = pg_mview_text.replace('TO_CHAR(', 'CAST(')
    pg_mview_text = pg_mview_text.replace('TO_DATE(', 'TO_TIMESTAMP(')
    
    return pg_mview_text

def convert_oracle_to_pg_view(oracle_view_text):
    """将Oracle视图语法转换为PostgreSQL视图语法"""
    # 这里实现语法转换逻辑
    # 简单示例，实际中可能需要更复杂的处理
    pg_view_text = oracle_view_text
    
    # 替换常见的Oracle特有语法
    pg_view_text = pg_view_text.replace('NVL(', 'COALESCE(')
    pg_view_text = pg_view_text.replace('TO_CHAR(', 'CAST(')
    pg_view_text = pg_view_text.replace('TO_DATE(', 'TO_TIMESTAMP(')
    
    return pg_view_text

def convert_oracle_to_pg_routine(oracle_routine_text):
    """将Oracle存储过程/函数语法转换为PostgreSQL函数语法"""
    # 这里实现语法转换逻辑
    # 简单示例，实际中需要更复杂的处理
    
    # 检测是函数还是过程
    is_function = 'FUNCTION' in oracle_routine_text.upper()
    
    if is_function:
        # 处理函数
        # 提取函数名、参数和返回类型
        pg_routine_text = oracle_routine_text
        
        # 替换BEGIN/END语法为PostgreSQL的$$ ... $$语法
        pg_routine_text = pg_routine_text.replace('BEGIN', '$$')
        pg_routine_text = pg_routine_text.replace('END;', '$$')
        
        # 替换常见的Oracle特有语法
        pg_routine_text = pg_routine_text.replace('NVL(', 'COALESCE(')
        pg_routine_text = pg_routine_text.replace(':=', '=')
    else:
        # 处理存储过程
        # 在PostgreSQL中，存储过程也是以函数形式实现的
        pg_routine_text = oracle_routine_text
        
        # 替换常见的Oracle特有语法
        pg_routine_text = pg_routine_text.replace('PROCEDURE', 'FUNCTION')
        pg_routine_text = pg_routine_text.replace('BEGIN', '$$')
        pg_routine_text = pg_routine_text.replace('END;', '$$')
        pg_routine_text = pg_routine_text.replace('NVL(', 'COALESCE(')
        pg_routine_text = pg_routine_text.replace(':=', '=')
        
        # 添加返回类型
        if 'RETURNS' not in pg_routine_text:
            pg_routine_text = pg_routine_text.replace(')', ') RETURNS VOID')
    
    return pg_routine_text

def convert_oracle_to_pg_type(oracle_type, data_length=None, data_precision=None, data_scale=None):
    """将Oracle数据类型转换为PostgreSQL数据类型"""
    oracle_type = oracle_type.upper()
    
    # 数值类型转换
    if oracle_type == 'NUMBER':
        if data_precision is None:
            return 'NUMERIC'
        elif data_scale == 0:
            if data_precision <= 4:
                return 'SMALLINT'
            elif data_precision <= 9:
                return 'INTEGER'
            elif data_precision <= 18:
                return 'BIGINT'
            else:
                return 'NUMERIC'
        else:
            return f'NUMERIC({data_precision}, {data_scale})'
    
    # 字符类型转换
    elif oracle_type in ('VARCHAR', 'VARCHAR2', 'NVARCHAR2'):
        return f'VARCHAR({data_length})'
    elif oracle_type == 'CHAR':
        return f'CHAR({data_length})'
    elif oracle_type == 'CLOB':
        return 'TEXT'
    elif oracle_type == 'NCLOB':
        return 'TEXT'
    
    # 日期和时间类型
    elif oracle_type == 'DATE':
        return 'TIMESTAMP'
    elif oracle_type == 'TIMESTAMP':
        return 'TIMESTAMP'
    
    # LOB类型
    elif oracle_type == 'BLOB':
        return 'BYTEA'
    elif oracle_type == 'RAW':
        return 'BYTEA'
    
    # 默认使用TEXT
    else:
        return 'TEXT'

@csrf_exempt
def create_task(request):
    """创建新的迁移任务"""
    if request.method == 'GET':
        # 获取数据库连接列表
        oracle_connections = OracleConnection.objects.all()
        postgres_connections = PostgresConnection.objects.all()
        return render(request, 'migration_app/create_task.html', {
            'oracle_connections': oracle_connections,
            'postgres_connections': postgres_connections,
        })
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            task = MigrationTask.objects.create(
                name=data.get('name'),
                task_type=data.get('task_type'),
                oracle_connection_id=data.get('oracle_connection'),
                postgres_connection_id=data.get('postgres_connection'),
                source_schema=data.get('source_schema'),
                target_schema=data.get('target_schema'),
                source_object=data.get('source_object'),
                is_batch=data.get('task_type') == 'all_tables'
            )
            
            # 启动异步任务
            executor = ThreadPoolExecutor(max_workers=1)
            
            if task.task_type == 'table':
                executor.submit(migrate_table, task.id)
            elif task.task_type == 'materialized_view':
                executor.submit(migrate_materialized_view, task.id)
            elif task.task_type == 'view':
                executor.submit(migrate_view, task.id)
            elif task.task_type == 'routine':
                executor.submit(migrate_routine, task.id)
            elif task.task_type == 'all_tables':
                executor.submit(migrate_all_tables, task.id)
            
            return JsonResponse({'status': 'success', 'task_id': task.id})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def task_detail(request, task_id):
    """任务详情页面"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    subtasks = None
    
    if task.is_batch:
        subtasks = task.subtasks.all().order_by('-created_at')
    
    return render(request, 'migration_app/task_detail.html', {
        'task': task,
        'subtasks': subtasks
    })

@csrf_exempt
def task_status(request, task_id):
    """获取任务状态"""
    task = get_object_or_404(MigrationTask, pk=task_id)
    return JsonResponse({
        'status': task.status,
        'progress': task.progress,
        'log': task.log,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    })

@csrf_exempt
def get_schemas(request):
    """获取Schema列表"""
    if request.method == 'POST':
        try:
            # 添加日志
            logger.info(f"收到获取Schema请求 - 请求方法: {request.method}")
            logger.info(f"请求内容类型: {request.content_type}")
            logger.info(f"请求体: {request.body}")
            
            # 处理不同格式的请求数据
            if request.content_type and 'application/json' in request.content_type:
                # JSON格式请求
                data = json.loads(request.body)
            else:
                # 表单提交
                data = request.POST
            
            connection_id = data.get('connection_id')
            db_type = data.get('type')  # 'oracle' 或 'postgres'
            search_term = data.get('search_term', '')  # 可选的搜索条件
            limit = int(data.get('limit', 100))  # 默认限制100条
            
            logger.info(f"解析请求参数: connection_id={connection_id}, db_type={db_type}, search_term={search_term}, limit={limit}")
            
            if not connection_id or not db_type:
                logger.error("缺少必要参数")
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少必要参数'
                }, status=400)
            
            # 限制最大查询数量
            if limit > 500:
                limit = 500
            
            # 根据数据库类型获取实际Schema列表
            schemas = []
            total_count = 0
            try:
                if db_type == 'oracle':
                    # 获取Oracle的Schema列表
                    connection = get_oracle_connection(connection_id)
                    cursor = connection.cursor()
                    
                    # 先获取总数
                    if search_term:
                        count_sql = "SELECT COUNT(*) FROM all_users WHERE username LIKE :search_term"
                        cursor.execute(count_sql, search_term=f"%{search_term.upper()}%")
                    else:
                        count_sql = "SELECT COUNT(*) FROM all_users"
                        cursor.execute(count_sql)
                    total_count = cursor.fetchone()[0]
                    
                    # 执行查询，添加搜索和限制条件
                    if search_term:
                        query = """
                            SELECT username FROM all_users 
                            WHERE username LIKE :search_term
                            ORDER BY username
                        """
                        cursor.execute(query, search_term=f"%{search_term.upper()}%")
                    else:
                        query = "SELECT username FROM all_users ORDER BY username"
                        cursor.execute(query)
                    
                    # 只获取指定数量的记录
                    schemas = [row[0] for row in cursor.fetchmany(limit)]
                    
                    cursor.close()
                    connection.close()
                    logger.info(f"获取到Oracle Schema: {len(schemas)}条 (总共{total_count}条)")
                    
                elif db_type == 'postgres':
                    # 获取PostgreSQL的Schema列表
                    connection = get_postgres_connection(connection_id)
                    cursor = connection.cursor()
                    
                    # 先获取总数
                    if search_term:
                        count_sql = """
                            SELECT COUNT(*) FROM information_schema.schemata 
                            WHERE schema_name NOT LIKE 'pg_%' 
                            AND schema_name != 'information_schema'
                            AND schema_name LIKE %s
                        """
                        cursor.execute(count_sql, (f"%{search_term}%",))
                    else:
                        count_sql = """
                            SELECT COUNT(*) FROM information_schema.schemata 
                            WHERE schema_name NOT LIKE 'pg_%' 
                            AND schema_name != 'information_schema'
                        """
                        cursor.execute(count_sql)
                    total_count = cursor.fetchone()[0]
                    
                    # 执行查询，添加搜索和限制条件
                    if search_term:
                        query = """
                            SELECT schema_name FROM information_schema.schemata 
                            WHERE schema_name NOT LIKE 'pg_%%' 
                            AND schema_name != 'information_schema'
                            AND schema_name LIKE %s
                            ORDER BY schema_name
                            LIMIT %s
                        """
                        cursor.execute(query, (f"%{search_term}%", limit))
                    else:
                        query = """
                            SELECT schema_name FROM information_schema.schemata 
                            WHERE schema_name NOT LIKE 'pg_%%' 
                            AND schema_name != 'information_schema'
                            ORDER BY schema_name
                            LIMIT %s
                        """
                        cursor.execute(query, [limit])
                    
                    schemas = [row[0] for row in cursor.fetchall()]
                    
                    cursor.close()
                    connection.close()
                    logger.info(f"获取到PostgreSQL Schema: {len(schemas)}条 (总共{total_count}条)")
                    
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'不支持的数据库类型: {db_type}'
                    }, status=400)
            except Exception as db_error:
                logger.error(f"数据库查询错误: {str(db_error)}", exc_info=True)
                return JsonResponse({
                    'status': 'error',
                    'message': f'数据库查询错误: {str(db_error)}'
                }, status=500)
            
            # 构造响应
            response_data = {
                'status': 'success',
                'schemas': schemas,
                'total': total_count,
                'count': len(schemas),
                'has_more': len(schemas) < total_count
            }
            logger.info(f"返回响应: schema数量 {len(schemas)}")
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"获取Schema列表出错: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@csrf_exempt
def get_database_objects(request):
    """获取数据库对象列表"""
    if request.method == 'POST':
        try:
            # 添加日志
            logger.info(f"收到获取数据库对象请求 - 请求方法: {request.method}")
            logger.info(f"请求内容类型: {request.content_type}")
            logger.info(f"请求体: {request.body}")
            
            # 处理不同格式的请求数据
            if request.content_type and 'application/json' in request.content_type:
                # JSON格式请求
                data = json.loads(request.body)
            else:
                # 表单提交
                data = request.POST
            
            connection_id = data.get('connection_id')
            schema = data.get('schema')
            object_type = data.get('object_type')
            search_term = data.get('search_term', '')  # 可选的搜索条件
            limit = int(data.get('limit', 100))  # 默认限制100条
            
            logger.info(f"解析请求参数: connection_id={connection_id}, schema={schema}, object_type={object_type}, search_term={search_term}, limit={limit}")
            
            if not connection_id or not schema or not object_type:
                logger.error("缺少必要参数")
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少必要参数'
                }, status=400)
            
            # 限制最大查询数量
            if limit > 500:
                limit = 500
            
            # 查询实际的数据库对象
            objects = []
            total_count = 0
            try:
                # 获取Oracle连接
                connection = get_oracle_connection(connection_id)
                cursor = connection.cursor()
                
                # 根据对象类型构建查询SQL并添加搜索条件
                if object_type == 'table':
                    # 先获取总数
                    if search_term:
                        count_query = """
                            SELECT COUNT(*) 
                            FROM all_tables 
                            WHERE owner = :schema 
                            AND table_name LIKE :search_term
                        """
                        cursor.execute(count_query, schema=schema, search_term=f"%{search_term.upper()}%")
                    else:
                        count_query = """
                            SELECT COUNT(*) 
                            FROM all_tables 
                            WHERE owner = :schema
                        """
                        cursor.execute(count_query, schema=schema)
                    total_count = cursor.fetchone()[0]
                    
                    # 获取数据列表
                    if search_term:
                        query = """
                            SELECT table_name 
                            FROM all_tables 
                            WHERE owner = :schema 
                            AND table_name LIKE :search_term
                            ORDER BY table_name
                        """
                        cursor.execute(query, schema=schema, search_term=f"%{search_term.upper()}%")
                    else:
                        query = """
                            SELECT table_name 
                            FROM all_tables 
                            WHERE owner = :schema 
                            ORDER BY table_name
                        """
                        cursor.execute(query, schema=schema)
                    
                elif object_type == 'view':
                    # 先获取总数
                    if search_term:
                        count_query = """
                            SELECT COUNT(*) 
                            FROM all_views 
                            WHERE owner = :schema 
                            AND view_name LIKE :search_term
                        """
                        cursor.execute(count_query, schema=schema, search_term=f"%{search_term.upper()}%")
                    else:
                        count_query = """
                            SELECT COUNT(*) 
                            FROM all_views 
                            WHERE owner = :schema
                        """
                        cursor.execute(count_query, schema=schema)
                    total_count = cursor.fetchone()[0]
                    
                    # 获取数据列表
                    if search_term:
                        query = """
                            SELECT view_name 
                            FROM all_views 
                            WHERE owner = :schema 
                            AND view_name LIKE :search_term
                            ORDER BY view_name
                        """
                        cursor.execute(query, schema=schema, search_term=f"%{search_term.upper()}%")
                    else:
                        query = """
                            SELECT view_name 
                            FROM all_views 
                            WHERE owner = :schema 
                            ORDER BY view_name
                        """
                        cursor.execute(query, schema=schema)
                    
                elif object_type == 'materialized_view':
                    # 先获取总数
                    if search_term:
                        count_query = """
                            SELECT COUNT(*) 
                            FROM all_mviews 
                            WHERE owner = :schema 
                            AND mview_name LIKE :search_term
                        """
                        cursor.execute(count_query, schema=schema, search_term=f"%{search_term.upper()}%")
                    else:
                        count_query = """
                            SELECT COUNT(*) 
                            FROM all_mviews 
                            WHERE owner = :schema
                        """
                        cursor.execute(count_query, schema=schema)
                    total_count = cursor.fetchone()[0]
                    
                    # 获取数据列表
                    if search_term:
                        query = """
                            SELECT mview_name 
                            FROM all_mviews 
                            WHERE owner = :schema 
                            AND mview_name LIKE :search_term
                            ORDER BY mview_name
                        """
                        cursor.execute(query, schema=schema, search_term=f"%{search_term.upper()}%")
                    else:
                        query = """
                            SELECT mview_name 
                            FROM all_mviews 
                            WHERE owner = :schema 
                            ORDER BY mview_name
                        """
                        cursor.execute(query, schema=schema)
                    
                elif object_type == 'routine':
                    # 先获取总数
                    if search_term:
                        count_query = """
                            SELECT COUNT(*) 
                            FROM all_objects 
                            WHERE owner = :schema 
                            AND object_type IN ('FUNCTION', 'PROCEDURE')
                            AND object_name LIKE :search_term
                        """
                        cursor.execute(count_query, schema=schema, search_term=f"%{search_term.upper()}%")
                    else:
                        count_query = """
                            SELECT COUNT(*) 
                            FROM all_objects 
                            WHERE owner = :schema 
                            AND object_type IN ('FUNCTION', 'PROCEDURE')
                        """
                        cursor.execute(count_query, schema=schema)
                    total_count = cursor.fetchone()[0]
                    
                    # 获取数据列表
                    if search_term:
                        query = """
                            SELECT object_name 
                            FROM all_objects 
                            WHERE owner = :schema 
                            AND object_type IN ('FUNCTION', 'PROCEDURE')
                            AND object_name LIKE :search_term
                            ORDER BY object_name
                        """
                        cursor.execute(query, schema=schema, search_term=f"%{search_term.upper()}%")
                    else:
                        query = """
                            SELECT object_name 
                            FROM all_objects 
                            WHERE owner = :schema 
                            AND object_type IN ('FUNCTION', 'PROCEDURE')
                            ORDER BY object_name
                        """
                        cursor.execute(query, schema=schema)
                    
                else:
                    cursor.close()
                    connection.close()
                    logger.error(f"不支持的对象类型: {object_type}")
                    return JsonResponse({
                        'status': 'error',
                        'message': f'不支持的对象类型: {object_type}'
                    }, status=400)
                
                # 执行查询，只获取指定数量的记录
                objects = [row[0] for row in cursor.fetchmany(limit)]
                
                cursor.close()
                connection.close()
                
                logger.info(f"从数据库获取到 {len(objects)} 个对象 (总共 {total_count} 个)")
                
            except Exception as db_error:
                logger.error(f"数据库查询错误: {str(db_error)}", exc_info=True)
                return JsonResponse({
                    'status': 'error',
                    'message': f'数据库查询错误: {str(db_error)}'
                }, status=500)
            
            response_data = {
                'status': 'success',
                'objects': objects,
                'total': total_count,
                'count': len(objects),
                'has_more': len(objects) < total_count
            }
            logger.info(f"返回响应: 对象数量 {len(objects)}")
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"获取数据库对象列表出错: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@csrf_exempt
def start_task(request, task_id):
    """启动迁移任务"""
    # 添加详细的请求调试日志
    logger.info(f"收到启动任务请求: 任务ID={task_id}")
    logger.info(f"请求方法: {request.method}")
    logger.info(f"请求头: {dict(request.headers)}")
    logger.info(f"请求体: {request.body.decode('utf-8') if request.body else '空'}")
    logger.info(f"Content-Type: {request.content_type}")
    
    if request.method == 'POST':
        try:
            logger.info(f"开始处理启动任务: 任务ID={task_id}")
            task = get_object_or_404(MigrationTask, pk=task_id)
            logger.info(f"任务信息: {task.name}, 当前状态: {task.status}")
            
            # 只有待执行和失败的任务可以重新启动
            if task.status not in ['pending', 'failed', 'canceled']:
                logger.warning(f"任务状态不允许启动: {task.status}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'任务当前状态为{task.get_status_display()}，无法启动'
                }, status=400)
            
            # 重置任务状态
            task.status = 'pending'
            task.cancel_requested = False
            task.progress = 0
            task.log = ''
            task.started_at = None
            task.completed_at = None
            task.save()
            logger.info(f"任务状态已重置为待执行: 任务ID={task_id}")
            
            # 启动异步任务
            executor = ThreadPoolExecutor(max_workers=1)
            
            if task.task_type == 'table':
                logger.info(f"提交表迁移任务: {task.source_schema}.{task.source_object}")
                executor.submit(migrate_table, task.id)
            elif task.task_type == 'materialized_view':
                logger.info(f"提交物化视图迁移任务: {task.source_schema}.{task.source_object}")
                executor.submit(migrate_materialized_view, task.id)
            elif task.task_type == 'view':
                logger.info(f"提交视图迁移任务: {task.source_schema}.{task.source_object}")
                executor.submit(migrate_view, task.id)
            elif task.task_type == 'routine':
                logger.info(f"提交存储过程/函数迁移任务: {task.source_schema}.{task.source_object}")
                executor.submit(migrate_routine, task.id)
            elif task.task_type == 'all_tables':
                logger.info(f"提交全部表迁移任务: {task.source_schema}.*")
                executor.submit(migrate_all_tables, task.id)
            else:
                logger.error(f"未知的任务类型: {task.task_type}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'未知的任务类型: {task.task_type}'
                }, status=400)
            
            logger.info(f"任务已成功提交执行: 任务ID={task_id}")
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"启动任务时发生错误: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    logger.warning(f"非法的请求方法: {request.method}")
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
    logger.info(f"请求体: {request.body.decode('utf-8') if request.body else '空'}")
    logger.info(f"Content-Type: {request.content_type}")
    
    if request.method == 'POST':
        try:
            logger.info(f"开始处理取消任务: 任务ID={task_id}")
            task = get_object_or_404(MigrationTask, pk=task_id)
            logger.info(f"任务信息: {task.name}, 当前状态: {task.status}")
            
            # 只有运行中的任务可以取消
            if task.status != 'running':
                logger.warning(f"任务状态不允许取消: {task.status}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'任务当前状态为{task.get_status_display()}，无法取消'
                }, status=400)
            
            # 设置取消标志
            task.cancel_requested = True
            task.save()
            logger.info(f"任务取消标志已设置: 任务ID={task_id}")
            
            # 如果是批量任务，也将所有运行中的子任务标记为取消
            if task.is_batch:
                logger.info(f"批量任务: 标记所有运行中的子任务为取消")
                running_subtasks = task.subtasks.filter(status='running')
                for subtask in running_subtasks:
                    subtask.cancel_requested = True
                    subtask.save()
                    logger.info(f"子任务取消标志已设置: 子任务ID={subtask.id}")
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"取消任务时发生错误: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    logger.warning(f"非法的请求方法: {request.method}")
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

# 读取README.md并返回内容
def get_readme_content():
    try:
        readme_path = settings.SIMPLEUI_HOME_INFO_PATH
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
        return "README.md 文件不存在"
    except Exception as e:
        return f"读取README.md失败: {str(e)}"
