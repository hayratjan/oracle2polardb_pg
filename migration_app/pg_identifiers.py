"""
PostgreSQL 标识符转义与 DDL 列定义（避免 ISNULL 等保留字/函数名导致建表语法错误）。

v2.4: 统一收口 Oracle/PG 标识符安全函数,其他模块统一从此处导入,
避免重复实现导致行为不一致。
"""
from __future__ import annotations

import re


# Oracle 未加引号标识符正则:大写字母开头,仅含大写字母/数字/下划线
_ORACLE_IDENT_RE = re.compile(r'^[A-Z][A-Z0-9_]*$')


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


def safe_oracle_identifier(name: str) -> str:
    """校验 Oracle 未加引号标识符,返回大写形式。

    Oracle 标识符若不强制校验,则用户可控的 schema/table/column 直接拼入
    f-string SQL 会形成 SQL 注入风险。本函数仅放行 `[A-Z][A-Z0-9_]*` 模式,
    杜绝任何特殊字符穿透到 SQL。

    Raises:
        ValueError: 当 name 为空或包含非法字符时。
    """
    n = (name or '').strip().upper().replace('"', '')
    if not n or not _ORACLE_IDENT_RE.match(n):
        raise ValueError(f'非法 Oracle 标识符: {name}')
    return n


def safe_pg_schema_name(name: str) -> str:
    """校验 PostgreSQL schema 名(用于 search_path 等无法绑参的语句)。

    仅允许 [A-Za-z_][A-Za-z0-9_]* 模式,杜绝 search_path 注入。
    返回原值(不转大小写),调用方按需 quote_identifier 包装。
    """
    n = (name or '').strip()
    if not n or not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', n):
        raise ValueError(f'非法 PostgreSQL schema 名: {name}')
    return n


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
