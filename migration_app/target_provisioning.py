"""
PolarDB-PG 目标环境 DDL：创建数据库、表空间、用户、Schema 及授权。
"""
from __future__ import annotations

import re
from typing import Any

import psycopg2
from django.shortcuts import get_object_or_404

from .models import PostgresConnection
from .pg_identifiers import quote_identifier
from .views import _pg_connect_kwargs

# 标识符白名单：字母数字下划线，首字符为字母或下划线
_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_identifier(name: str, label: str = '标识符') -> str:
    """校验并返回合法标识符，防止 SQL 注入。"""
    if not name or not str(name).strip():
        raise ValueError(f'{label}不能为空')
    n = str(name).strip()
    if not _IDENTIFIER_RE.match(n):
        raise ValueError(f'{label}「{n}」含非法字符，仅允许字母、数字、下划线且不能以数字开头')
    return n


def _connect_pg(connection_id: int, database: str | None = None):
    """建立 PostgreSQL 连接。"""
    conn_obj = get_object_or_404(PostgresConnection, pk=connection_id)
    db = database or conn_obj.database or 'postgres'
    return psycopg2.connect(**_pg_connect_kwargs(conn_obj, db)), conn_obj


def list_tablespaces(connection_id: int, database: str | None = None) -> list[str]:
    """列出表空间名称。"""
    conn, _ = _connect_pg(connection_id, database or 'postgres')
    try:
        cur = conn.cursor()
        cur.execute("SELECT spcname FROM pg_tablespace ORDER BY spcname")
        names = [row[0] for row in cur.fetchall()]
        cur.close()
        return names
    finally:
        conn.close()


def database_exists(connection_id: int, name: str) -> bool:
    """检查数据库是否已存在。"""
    db_name = _validate_identifier(name, '数据库名')
    conn, _ = _connect_pg(connection_id, 'postgres')
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", [db_name])
        exists = cur.fetchone() is not None
        cur.close()
        return exists
    finally:
        conn.close()


def role_exists(connection_id: int, username: str, database: str | None = None) -> bool:
    """检查角色/用户是否已存在。"""
    uname = _validate_identifier(username, '用户名')
    conn, _ = _connect_pg(connection_id, database or 'postgres')
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [uname])
        exists = cur.fetchone() is not None
        cur.close()
        return exists
    finally:
        conn.close()


def create_database(
    connection_id: int,
    name: str,
    owner: str | None = None,
    encoding: str = 'UTF8',
) -> dict[str, Any]:
    """在实例上创建数据库（连接 postgres 维护库）。"""
    db_name = _validate_identifier(name, '数据库名')
    if database_exists(connection_id, db_name):
        return {'status': 'skipped', 'message': f'数据库 {db_name} 已存在', 'name': db_name}

    conn, _ = _connect_pg(connection_id, 'postgres')
    try:
        conn.autocommit = True
        cur = conn.cursor()
        parts = [f'CREATE DATABASE {quote_identifier(db_name)}']
        enc = (encoding or 'UTF8').strip().upper()
        if enc:
            parts.append(f"ENCODING '{enc}'")
        if owner:
            owner_id = _validate_identifier(owner, '所有者')
            parts.append(f'OWNER {quote_identifier(owner_id)}')
        cur.execute(' '.join(parts))
        cur.close()
        return {'status': 'created', 'message': f'已创建数据库 {db_name}', 'name': db_name}
    finally:
        conn.close()


def create_tablespace(connection_id: int, name: str, location: str) -> dict[str, Any]:
    """创建表空间（需超级用户权限）。"""
    ts_name = _validate_identifier(name, '表空间名')
    loc = (location or '').strip()
    if not loc:
        raise ValueError('创建表空间必须提供 LOCATION 路径')

    conn, _ = _connect_pg(connection_id, 'postgres')
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            f"SELECT 1 FROM pg_tablespace WHERE spcname = %s",
            [ts_name],
        )
        if cur.fetchone():
            cur.close()
            return {'status': 'skipped', 'message': f'表空间 {ts_name} 已存在', 'name': ts_name}
        cur.execute(
            f"CREATE TABLESPACE {quote_identifier(ts_name)} LOCATION %s",
            [loc],
        )
        cur.close()
        return {'status': 'created', 'message': f'已创建表空间 {ts_name}', 'name': ts_name}
    finally:
        conn.close()


def create_role(
    connection_id: int,
    username: str,
    password: str,
    *,
    createdb: bool = False,
    database: str | None = None,
) -> dict[str, Any]:
    """创建可登录角色并授予连接目标库的权限。"""
    uname = _validate_identifier(username, '用户名')
    pwd = password or ''
    if not pwd:
        raise ValueError('创建用户必须提供密码')

    if role_exists(connection_id, uname, database):
        return {'status': 'skipped', 'message': f'用户 {uname} 已存在', 'username': uname}

    conn, _ = _connect_pg(connection_id, database or 'postgres')
    try:
        conn.autocommit = True
        cur = conn.cursor()
        opts = ['LOGIN']
        if createdb:
            opts.append('CREATEDB')
        cur.execute(
            f"CREATE ROLE {quote_identifier(uname)} WITH {' '.join(opts)} PASSWORD %s",
            [pwd],
        )
        cur.close()
        return {'status': 'created', 'message': f'已创建用户 {uname}', 'username': uname}
    finally:
        conn.close()


def grant_connect_on_database(connection_id: int, username: str, database: str) -> None:
    """授予用户对数据库的连接权限。"""
    uname = _validate_identifier(username, '用户名')
    db_name = _validate_identifier(database, '数据库名')
    conn, _ = _connect_pg(connection_id, 'postgres')
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            f'GRANT CONNECT ON DATABASE {quote_identifier(db_name)} TO {quote_identifier(uname)}'
        )
        cur.close()
    finally:
        conn.close()


def create_schema(
    connection_id: int,
    database: str,
    schema: str,
    owner: str | None = None,
) -> dict[str, Any]:
    """在指定数据库中创建 Schema。"""
    schema_name = _validate_identifier(schema, 'Schema名')
    db_name = _validate_identifier(database, '数据库名')

    conn, _ = _connect_pg(connection_id, db_name)
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            [schema_name],
        )
        if cur.fetchone():
            cur.close()
            return {'status': 'skipped', 'message': f'Schema {schema_name} 已存在', 'name': schema_name}
        sql = f'CREATE SCHEMA {quote_identifier(schema_name)}'
        if owner:
            owner_id = _validate_identifier(owner, '所有者')
            sql += f' AUTHORIZATION {quote_identifier(owner_id)}'
        cur.execute(sql)
        cur.close()
        return {'status': 'created', 'message': f'已创建 Schema {schema_name}', 'name': schema_name}
    finally:
        conn.close()


def grant_schema_privileges(
    connection_id: int,
    database: str,
    schema: str,
    username: str,
) -> dict[str, Any]:
    """授予用户对 Schema 的完整权限。"""
    schema_name = _validate_identifier(schema, 'Schema名')
    uname = _validate_identifier(username, '用户名')
    db_name = _validate_identifier(database, '数据库名')

    conn, _ = _connect_pg(connection_id, db_name)
    try:
        conn.autocommit = True
        cur = conn.cursor()
        q_schema = quote_identifier(schema_name)
        q_user = quote_identifier(uname)
        cur.execute(f'GRANT USAGE ON SCHEMA {q_schema} TO {q_user}')
        cur.execute(f'GRANT CREATE ON SCHEMA {q_schema} TO {q_user}')
        cur.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {q_schema} TO {q_user}')
        cur.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {q_schema} TO {q_user}')
        cur.execute(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA {q_schema} '
            f'GRANT ALL ON TABLES TO {q_user}'
        )
        cur.execute(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA {q_schema} '
            f'GRANT ALL ON SEQUENCES TO {q_user}'
        )
        cur.close()
        return {'status': 'granted', 'message': f'已授权 {uname} 对 Schema {schema_name} 的权限'}
    finally:
        conn.close()


def _run_step(step_name: str, fn) -> dict[str, Any]:
    """执行单步并捕获结果。"""
    try:
        result = fn()
        if isinstance(result, dict):
            return {'step': step_name, **result}
        return {'step': step_name, 'status': 'ok', 'message': str(result)}
    except Exception as e:
        return {'step': step_name, 'status': 'failed', 'message': str(e)}


def prepare_target_env(config: dict[str, Any]) -> dict[str, Any]:
    """
    按向导配置顺序准备目标环境：库 → 表空间 → 用户 → Schema → 授权。
    config 需含 connection_id，及各资源的 mode/name 等字段。
    """
    connection_id = config.get('connection_id')
    if not connection_id:
        raise ValueError('缺少 connection_id')

    steps: list[dict[str, Any]] = []
    resolved_db = None
    resolved_user = None
    resolved_schema = None

    # 1. 数据库
    db_cfg = config.get('database') or {}
    db_mode = (db_cfg.get('mode') or 'existing').lower()
    if db_mode == 'skip':
        resolved_db = db_cfg.get('name') or config.get('postgres_database')
    elif db_mode == 'create':
        db_name = db_cfg.get('name')
        if not db_name:
            raise ValueError('创建数据库需指定 name')
        owner = db_cfg.get('owner')
        encoding = db_cfg.get('encoding') or 'UTF8'
        steps.append(_run_step(
            'database',
            lambda: create_database(connection_id, db_name, owner=owner, encoding=encoding),
        ))
        resolved_db = db_name
    else:
        resolved_db = db_cfg.get('name')
        if not resolved_db:
            raise ValueError('选择已有数据库需指定 name')

    # 2. 表空间
    ts_cfg = config.get('tablespace') or {}
    ts_mode = (ts_cfg.get('mode') or 'skip').lower()
    if ts_mode == 'create':
        ts_name = ts_cfg.get('name')
        location = ts_cfg.get('location')
        if not ts_name:
            raise ValueError('创建表空间需指定 name')
        steps.append(_run_step(
            'tablespace',
            lambda: create_tablespace(connection_id, ts_name, location or ''),
        ))
    elif ts_mode == 'existing':
        steps.append({'step': 'tablespace', 'status': 'skipped', 'message': f"使用已有表空间 {ts_cfg.get('name', 'pg_default')}"})

    # 3. 用户
    user_cfg = config.get('user') or {}
    user_mode = (user_cfg.get('mode') or 'skip').lower()
    if user_mode == 'create':
        username = user_cfg.get('username')
        password = user_cfg.get('password')
        if not username:
            raise ValueError('创建用户需指定 username')
        steps.append(_run_step(
            'user',
            lambda: create_role(
                connection_id, username, password or '',
                createdb=bool(user_cfg.get('createdb')),
            ),
        ))
        resolved_user = username
        if resolved_db:
            steps.append(_run_step(
                'grant_connect',
                lambda: (grant_connect_on_database(connection_id, username, resolved_db),
                         {'status': 'granted', 'message': f'已授予 {username} 连接 {resolved_db} 的权限'})[1],
            ))
    elif user_mode == 'existing':
        resolved_user = user_cfg.get('username')

    # 4. Schema
    schema_cfg = config.get('schema') or {}
    schema_mode = (schema_cfg.get('mode') or 'existing').lower()
    if schema_mode == 'create':
        schema_name = schema_cfg.get('name')
        if not schema_name or not resolved_db:
            raise ValueError('创建 Schema 需指定 name 且已确定目标数据库')
        owner = schema_cfg.get('owner') or resolved_user
        steps.append(_run_step(
            'schema',
            lambda: create_schema(connection_id, resolved_db, schema_name, owner=owner),
        ))
        resolved_schema = schema_name
    else:
        resolved_schema = schema_cfg.get('name') or 'public'

    # 5. 授权
    if resolved_user and resolved_schema and resolved_db:
        steps.append(_run_step(
            'grant_schema',
            lambda: grant_schema_privileges(connection_id, resolved_db, resolved_schema, resolved_user),
        ))

    failed = [s for s in steps if s.get('status') == 'failed']
    return {
        'status': 'error' if failed else 'success',
        'steps': steps,
        'resolved': {
            'database': resolved_db,
            'schema': resolved_schema,
            'user': resolved_user,
        },
        'message': failed[0]['message'] if failed else '目标环境准备完成',
    }
