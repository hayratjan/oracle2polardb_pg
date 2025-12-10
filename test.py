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
        pg_cursor.execute(alter_sql)
        pg_conn.commit()
        log.append(f"已将列 {column_name} 调整为TEXT，重试数据写入")