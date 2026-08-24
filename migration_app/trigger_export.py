"""
Oracle 触发器导出与 PL/pgSQL 改写模板生成。

日志采用统一前缀格式 `[LEVEL] message`，便于前端解析着色：
  [STEP] 阶段步骤    [INFO] 一般信息    [OK] 成功    [WARN] 警告
  [ERROR] 错误      [META] 元数据      [SQL] 源码/模板
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .task_logging import (
    build_log_line,
)


def _parse_trigger_type(trigger_type):
    """解析 Oracle 触发类型,返回 (timing, level)。
    timing: BEFORE / AFTER / INSTEAD OF
    level: ROW / STATEMENT
    """
    tt = (trigger_type or '').upper()
    if 'INSTEAD OF' in tt:
        timing = 'INSTEAD OF'
    elif 'BEFORE' in tt:
        timing = 'BEFORE'
    else:
        timing = 'AFTER'
    level = 'STATEMENT' if 'STATEMENT' in tt else 'ROW'
    return timing, level


def _parse_trigger_event(triggering_event):
    """解析触发事件,返回 (events_list, update_of_cols)。
    例: 'INSERT OR UPDATE OF col1, col2 OR DELETE' → (['INSERT', 'UPDATE', 'DELETE'], 'col1, col2')
    """
    ev = (triggering_event or '').upper().strip()
    update_of_cols = ''
    # 提取 UPDATE OF 列列表
    m = re.search(r'UPDATE\s+OF\s+([^()]+?)(?:\s+OR\s+|$)', ev)
    if m:
        update_of_cols = m.group(1).strip()
    events = []
    for e in ['INSERT', 'UPDATE', 'DELETE', 'TRUNCATE']:
        if e in ev:
            events.append(e)
    if not events:
        events = ['INSERT']
    return events, update_of_cols


def _convert_when_clause(when_clause):
    """转换 Oracle WHEN 子句到 PL/pgSQL。
    :NEW.col → NEW.col, :OLD.col → OLD.col
    """
    result = when_clause
    result = re.sub(r':NEW\.', 'NEW.', result, flags=re.IGNORECASE)
    result = re.sub(r':OLD\.', 'OLD.', result, flags=re.IGNORECASE)
    return result


def _extract_when_from_source(source_body):
    """从触发器源码中提取 WHEN 子句内容。"""
    if not source_body:
        return None
    m = re.search(r'WHEN\s*\(([^)]+)\)', source_body, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def _extract_referencing_cols(source_body):
    """从源码中提取 :NEW 和 :OLD 引用的列名。
    返回 (new_cols, old_cols) 去重列表。
    """
    if not source_body:
        return [], []
    new_cols = set(re.findall(r':NEW\.(\w+)', source_body, re.IGNORECASE))
    old_cols = set(re.findall(r':OLD\.(\w+)', source_body, re.IGNORECASE))
    return sorted(new_cols), sorted(old_cols)


def build_plpgsql_trigger_template(
    *,
    trigger_name: str,
    table_name: str,
    trigger_type: str,
    triggering_event: str,
    schema: str = 'public',
    status: str = 'ENABLED',
    when_clause=None,
    source_body=None,
    base_object_type: str = 'TABLE',
):
    """根据 Oracle 触发器元数据生成 PL/pgSQL 改写骨架。"""
    func_name = f"trg_{trigger_name.lower()}_fn"
    timing, level = _parse_trigger_type(trigger_type)
    events, update_of_cols = _parse_trigger_event(triggering_event)
    event_sql = ' OR '.join(events)

    event_clause_parts = []
    for ev in events:
        if ev == 'UPDATE' and update_of_cols:
            event_clause_parts.append(f'UPDATE OF {update_of_cols}')
        else:
            event_clause_parts.append(ev)
    event_clause = ' OR '.join(event_clause_parts)

    pg_when = ''
    if when_clause:
        pg_when = _convert_when_clause(when_clause)
    elif source_body:
        extracted = _extract_when_from_source(source_body)
        if extracted:
            pg_when = _convert_when_clause(extracted)

    new_cols, old_cols = [], []
    if source_body:
        new_cols, old_cols = _extract_referencing_cols(source_body)

    is_disabled = status and status.upper() == 'DISABLED'

    # v2.4.4: 兼容性预检
    # PG 的 INSTEAD OF 触发器仅允许建在视图上
    instead_of_on_table = (
        timing == 'INSTEAD OF' and str(base_object_type or 'TABLE').upper() != 'VIEW'
    )
    # Oracle 11g+ 组合触发器（单对象聚合多种时机/级别）PG 无对应，需拆分为多个触发器
    is_compound = bool(
        source_body and re.search(r'\bCOMPOUND\s+TRIGGER\b', source_body, re.IGNORECASE)
    )

    body_lines = [
        'BEGIN',
        '    -- TODO: 在此粘贴从 Oracle 改写的业务逻辑',
    ]
    if new_cols:
        body_lines.append(f'    -- :NEW 引用的列: {", ".join(new_cols)}')
    if old_cols:
        body_lines.append(f'    -- :OLD 引用的列: {", ".join(old_cols)}')

    if level == 'ROW':
        body_lines.extend([
            '    -- 行级触发器:NEW/OLD 可用,必须 RETURN',
            '    IF TG_OP = \'INSERT\' THEN',
            '        -- NEW.col := 值;',
            '        RETURN NEW;',
            '    ELSIF TG_OP = \'UPDATE\' THEN',
            '        -- NEW.col := 值;',
            '        RETURN NEW;',
            '    ELSIF TG_OP = \'DELETE\' THEN',
            '        RETURN OLD;',
            '    END IF;',
            '    RETURN NULL;',
        ])
    else:
        body_lines.extend([
            '    -- 语句级触发器:NEW/OLD 不可用,无需 RETURN',
            '    IF TG_OP = \'INSERT\' THEN',
            '        NULL;',
            '    ELSIF TG_OP = \'UPDATE\' THEN',
            '        NULL;',
            '    ELSIF TG_OP = \'DELETE\' THEN',
            '        NULL;',
            '    END IF;',
        ])
    body_lines.append('END;')

    func_body = '\n'.join(body_lines)
    when_clause_sql = f'\n    WHEN ({pg_when})' if pg_when else ''
    # PG 语句级触发器禁止引用 NEW/OLD —— 引用时必须改行级或去掉 WHEN
    stmt_when_invalid = (
        level == 'STATEMENT'
        and pg_when
        and re.search(r'\b(NEW|OLD)\.', pg_when, re.IGNORECASE)
    )
    if stmt_when_invalid:
        when_clause_sql = ''

    ddl_lines = [
        f'-- ===== PolarDB-PG 触发器改写模板(需人工完成) =====',
        f'-- 源触发器: {schema}.{trigger_name}',
        f'-- 绑定表/视图: {table_name}',
        f'-- 触发时机: {timing} | 级别: {level} | 事件: {event_sql}',
    ]
    if update_of_cols:
        ddl_lines.append(f'-- UPDATE OF 列: {update_of_cols}')
    if pg_when:
        ddl_lines.append(f'-- WHEN 条件: {pg_when}')
    if is_disabled:
        ddl_lines.append(f'-- 源状态: DISABLED(已禁用,目标库也将禁用)')
    if instead_of_on_table:
        ddl_lines.append(
            f'-- 注意: INSTEAD OF 触发器在 PG 中仅支持建在视图上,'
            f'而本触发器基对象为 {base_object_type}(表);'
            f'请改写为 BEFORE/AFTER 行级触发器,或将基对象改为视图')
    if is_compound:
        ddl_lines.append(
            f'-- 注意: 检测到 Oracle 组合触发器(COMPOUND TRIGGER);'
            f'PG 无对应结构,需按 BEFORE/AFTER 各拆分为独立触发器+函数')
    if stmt_when_invalid:
        ddl_lines.append(
            f'-- 注意: 源 WHEN 条件引用了 NEW/OLD,但 PG 语句级触发器不允许引用它们;'
            f'已从 DDL 中移除 WHEN,请改为行级触发器或将条件移入函数体')
    if pg_when and stmt_when_invalid:
        ddl_lines.append(f'-- 原 WHEN 条件(需人工改写): {pg_when}')
    ddl_lines.extend([
        f'-- 建议步骤:',
        f'--   1. 将下方函数体替换为从 Oracle 源码改写的 PL/pgSQL 逻辑',
        f'--   2. Oracle 的 :NEW.col / :OLD.col → PG 的 NEW.col / OLD.col',
        f'--   3. 行级触发器请在函数末尾 RETURN NEW 或 RETURN OLD',
        f'--   4. 在目标库执行本脚本',
        '',
        f'CREATE OR REPLACE FUNCTION {schema}.{func_name}()',
        f'RETURNS TRIGGER',
        f'LANGUAGE plpgsql',
        f'AS $$',
        func_body,
        f'$$;',
        '',
        f'DROP TRIGGER IF EXISTS {trigger_name.lower()} ON {schema}.{table_name.lower()};',
        f'CREATE TRIGGER {trigger_name.lower()}',
        f'    {timing} {event_clause}',
        f'    ON {schema}.{table_name.lower()}',
        f'    FOR EACH {level}{when_clause_sql}',
        f'    EXECUTE FUNCTION {schema}.{func_name}();',
    ])

    if is_disabled:
        ddl_lines.extend([
            '',
            f'-- 源触发器为 DISABLED 状态,目标库也禁用:',
            f'ALTER TABLE {schema}.{table_name.lower()} DISABLE TRIGGER {trigger_name.lower()};',
        ])

    return '\n'.join(ddl_lines)


def export_one_trigger(
    oracle_cursor,
    source_schema: str,
    trigger_name: str,
    *,
    max_body_chars: int = 8000,
) -> Tuple[Optional[dict], str, str]:
    """
    导出单个触发器元数据与源码。
    返回 (元数据字典, 源码正文, 日志文本)。
    日志文本为多行字符串，每行以 [LEVEL] 前缀开头，便于前端着色。
    """
    oracle_cursor.execute(
        """
        SELECT TRIGGER_NAME, TRIGGER_TYPE, TRIGGERING_EVENT, TABLE_NAME, STATUS, DESCRIPTION
        FROM ALL_TRIGGERS
        WHERE OWNER = :o AND TRIGGER_NAME = :n
        """,
        {'o': source_schema.upper(), 'n': trigger_name.upper()},
    )
    meta_row = oracle_cursor.fetchone()
    if not meta_row:
        return None, '', build_log_line('ERROR', f'找不到触发器 {source_schema}.{trigger_name}')

    meta = {
        'name': meta_row[0],
        'type': meta_row[1],
        'event': meta_row[2],
        'table': meta_row[3],
        'status': meta_row[4],
        'description': meta_row[5],
    }
    # v2.4.4: 基对象类型（TABLE/VIEW）供模板做 INSTEAD OF 校验
    try:
        from .full_database import fetch_trigger_base_object_type
        meta['base_object_type'] = fetch_trigger_base_object_type(
            oracle_cursor, source_schema, trigger_name)
    except Exception:
        meta['base_object_type'] = 'TABLE'

    oracle_cursor.execute(
        """
        SELECT TEXT FROM ALL_SOURCE
        WHERE OWNER = :o AND NAME = :n AND TYPE = 'TRIGGER'
        ORDER BY LINE
        """,
        {'o': source_schema.upper(), 'n': trigger_name.upper()},
    )
    body = '\n'.join(r[0] for r in oracle_cursor.fetchall() if r[0])
    body_lines = body.count('\n') + 1 if body else 0
    if len(body) > max_body_chars:
        body_display = body[:max_body_chars] + '\n...(截断，完整源码请从 Oracle 导出)'
    else:
        body_display = body

    template = build_plpgsql_trigger_template(
        trigger_name=meta['name'],
        table_name=meta['table'],
        trigger_type=meta['type'],
        triggering_event=meta['event'],
        schema=source_schema.lower(),
        status=meta['status'],
        source_body=body,
        base_object_type=meta.get('base_object_type') or 'TABLE',
    )

    # 构建结构化多行日志（每行带 [LEVEL] 前缀）
    log_parts: List[str] = [
        build_log_line('STEP', f'触发器导出: {source_schema}.{trigger_name}'),
        build_log_line('META', f'名称: {meta["name"]}'),
        build_log_line('META', f'类型: {meta["type"]} | 事件: {meta["event"]} | 表: {meta["table"]} | 状态: {meta["status"]}'),
        build_log_line('INFO', f'源码行数: {body_lines} 字符: {len(body)}'),
    ]
    if meta.get('description'):
        log_parts.append(build_log_line('META', f'描述: {meta["description"]}'))
    # Oracle 源码：以多行形式附加，每行缩进 4 空格以保留格式
    log_parts.append(build_log_line('SQL', 'Oracle 源码:'))
    for line in body_display.splitlines() or ['(空)']:
        log_parts.append(f'    {line}')
    # 改写模板：同上
    log_parts.append(build_log_line('SQL', 'PL/pgSQL 改写模板:'))
    for line in template.splitlines():
        log_parts.append(f'    {line}')
    log_parts.append(build_log_line('OK', f'触发器 {trigger_name} 导出完成'))

    log_text = '\n'.join(log_parts)
    return meta, body, log_text


def parse_trigger_names(task) -> List[str]:
    """从任务解析待导出的触发器名列表。"""
    names: List[str] = []
    if task.source_objects and str(task.source_objects).strip():
        names = [n.strip() for n in task.source_objects.split(',') if n.strip()]
    elif task.source_object and str(task.source_object).strip():
        names = [task.source_object.strip()]
    return names
