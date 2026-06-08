"""
Oracle 触发器导出与 PL/pgSQL 改写模板生成。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple


def build_plpgsql_trigger_template(
    *,
    trigger_name: str,
    table_name: str,
    trigger_type: str,
    triggering_event: str,
    schema: str = 'public',
) -> str:
    """
    根据 Oracle 触发器元数据生成 PL/pgSQL 改写骨架（供人工填充业务逻辑）。
    """
    func_name = f"trg_{trigger_name.lower()}_fn"
    # Oracle TRIGGER_TYPE 如 BEFORE EACH ROW / AFTER STATEMENT
    timing = 'BEFORE'
    level = 'ROW'
    upper_type = (trigger_type or '').upper()
    if 'AFTER' in upper_type:
        timing = 'AFTER'
    if 'INSTEAD OF' in upper_type:
        timing = 'INSTEAD OF'
    if 'STATEMENT' in upper_type:
        level = 'STATEMENT'

    events = (triggering_event or 'INSERT OR UPDATE OR DELETE').upper()
    # 规范为 PG 事件列表
    event_parts = []
    for ev in ('INSERT', 'UPDATE', 'DELETE'):
        if ev in events:
            event_parts.append(ev)
    event_sql = ' OR '.join(event_parts) if event_parts else 'INSERT OR UPDATE OR DELETE'

    return f"""-- ===== PolarDB-PG 触发器改写模板（需人工完成） =====
-- 源触发器: {schema}.{trigger_name}
-- 绑定表: {table_name}
-- 建议步骤:
--   1. 将下方函数体替换为从 Oracle 源码改写的 PL/pgSQL 逻辑
--   2. 行级触发器请在函数末尾 RETURN NEW 或 RETURN OLD
--   3. 在目标库执行本脚本

CREATE OR REPLACE FUNCTION {schema}.{func_name}()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- TODO: 在此粘贴改写后的业务逻辑
    -- 行级示例: NEW.column_name := 值;
    IF TG_OP = 'INSERT' THEN
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS {trigger_name.lower()} ON {schema}.{table_name.lower()};
CREATE TRIGGER {trigger_name.lower()}
    {timing} {event_sql}
    ON {schema}.{table_name.lower()}
    FOR EACH {level}
    EXECUTE FUNCTION {schema}.{func_name}();
"""


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
        return None, '', f"找不到触发器 {source_schema}.{trigger_name}"

    meta = {
        'name': meta_row[0],
        'type': meta_row[1],
        'event': meta_row[2],
        'table': meta_row[3],
        'status': meta_row[4],
        'description': meta_row[5],
    }

    oracle_cursor.execute(
        """
        SELECT TEXT FROM ALL_SOURCE
        WHERE OWNER = :o AND NAME = :n AND TYPE = 'TRIGGER'
        ORDER BY LINE
        """,
        {'o': source_schema.upper(), 'n': trigger_name.upper()},
    )
    body = '\n'.join(r[0] for r in oracle_cursor.fetchall() if r[0])
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
    )

    log_text = (
        f"---- 触发器 {meta['name']} ----\n"
        f"元数据: type={meta['type']}, event={meta['event']}, table={meta['table']}, status={meta['status']}\n"
        f"---- Oracle 源码 ----\n{body_display}\n"
        f"---- PL/pgSQL 改写模板 ----\n{template}\n"
    )
    return meta, body, log_text


def parse_trigger_names(task) -> List[str]:
    """从任务解析待导出的触发器名列表。"""
    names: List[str] = []
    if task.source_objects and str(task.source_objects).strip():
        names = [n.strip() for n in task.source_objects.split(',') if n.strip()]
    elif task.source_object and str(task.source_object).strip():
        names = [task.source_object.strip()]
    return names
