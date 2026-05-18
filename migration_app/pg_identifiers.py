"""
PostgreSQL 标识符转义与 DDL 列定义（避免 ISNULL 等保留字/函数名导致建表语法错误）。
"""
from __future__ import annotations


def apply_identifier_case(name: str, case_option: str) -> str:
    """根据任务配置调整标识符大小写。"""
    if not name:
        return name
    if case_option == 'lower':
        return str(name).lower()
    if case_option == 'upper':
        return str(name).upper()
    return str(name)


def quote_identifier(name: str) -> str:
    """对标识符加双引号转义（PostgreSQL）。"""
    if name is None:
        return '""'
    safe = str(name).replace('"', '""')
    return f'"{safe}"'


def build_qualified_table_name(schema: str, table: str) -> str:
    """返回 "schema"."table" 形式。"""
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"


def build_pg_column_definition(
    oracle_column_name: str,
    pg_type: str,
    nullable: str,
    *,
    id_case: str = 'lower',
) -> str:
    """
    生成 CREATE TABLE 中的单列定义，列名始终带双引号。
    例如 Oracle 列 ISNULL → "isnull" SMALLINT
    """
    pg_col = apply_identifier_case(oracle_column_name, id_case)
    parts = [quote_identifier(pg_col), (pg_type or 'TEXT').strip()]
    if nullable == 'N':
        parts.append('NOT NULL')
    return '    ' + ' '.join(parts)
