"""
Oracle SQL 到 PolarDB/PostgreSQL 的语法转换（视图、物化视图、例程等）。
"""
from __future__ import annotations

import re
from typing import List, Tuple


# 不可自动转换的 Oracle 语法模式（用于生成人工审查清单）
_MANUAL_REVIEW_PATTERNS = [
    (r'\(\+\)', 'Oracle 外连接 (+) 语法'),
    (r'\bCONNECT\s+BY\b', '层次查询 CONNECT BY'),
    (r'\bSTART\s+WITH\b', '层次查询 START WITH'),
    (r'\bMINUS\b', '集合运算 MINUS'),
    (r'\bROWNUM\b', 'ROWNUM 伪列'),
    (r'\bSYS\.DBMS_', 'Oracle DBMS 包调用'),
    (r':NEW\b|:OLD\b', '触发器 :NEW/:OLD 引用'),
]


def _replace_nvl(text: str) -> str:
    """NVL(expr1, expr2) → COALESCE(expr1, expr2)（简单替换，嵌套需人工复核）。"""
    return re.sub(r'\bNVL\s*\(', 'COALESCE(', text, flags=re.IGNORECASE)


def _replace_sysdate(text: str) -> str:
    """SYSDATE → CURRENT_TIMESTAMP（保留日期语义含时分秒）。"""
    return re.sub(r'\bSYSDATE\b', 'CURRENT_TIMESTAMP', text, flags=re.IGNORECASE)


def _replace_dual(text: str) -> str:
    """FROM DUAL → 移除（PG 中 SELECT 无 FROM 亦可）。"""
    text = re.sub(r'\bFROM\s+DUAL\b', '', text, flags=re.IGNORECASE)
    return text


def _replace_decode_simple(text: str) -> str:
    """
    将简单 DECODE(a,b,c,d) 转为 CASE WHEN a=b THEN c ELSE d END。
    复杂多分支 DECODE 仅做标记，不强行转换。
    """
    pattern = re.compile(
        r'\bDECODE\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)',
        re.IGNORECASE,
    )

    def _repl(m: re.Match) -> str:
        expr, val1, result1, else_val = m.group(1), m.group(2), m.group(3), m.group(4)
        return f'CASE WHEN {expr.strip()} = {val1.strip()} THEN {result1.strip()} ELSE {else_val.strip()} END'

    return pattern.sub(_repl, text)


def detect_manual_review_items(sql_text: str) -> List[str]:
    """检测 SQL 中需人工审查的 Oracle 专有语法。"""
    items: List[str] = []
    for pattern, desc in _MANUAL_REVIEW_PATTERNS:
        if re.search(pattern, sql_text, re.IGNORECASE):
            items.append(desc)
    return items


def convert_oracle_to_pg_sql(
    oracle_sql: str,
    *,
    strip_trailing_semicolon: bool = True,
) -> Tuple[str, List[str]]:
    """
    将 Oracle SQL 转为 PolarDB-PG 可尝试执行的 SQL。
    返回 (转换后 SQL, 需人工审查项列表)。
    """
    if not oracle_sql or not str(oracle_sql).strip():
        return '', ['空 SQL 定义']

    text = str(oracle_sql).strip()
    # 去掉 Oracle 视图/物化视图包装中的 CREATE ... AS 前缀，保留查询体
    text = re.sub(
        r'^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:FORCE\s+)?(?:MATERIALIZED\s+)?VIEW\s+\S+\s+AS\s+',
        '',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if strip_trailing_semicolon:
        text = text.rstrip().rstrip(';').strip()

    text = _replace_sysdate(text)
    text = _replace_nvl(text)
    text = _replace_dual(text)
    text = _replace_decode_simple(text)

    manual_items = detect_manual_review_items(text)
    return text, manual_items


def convert_oracle_to_pg_view(oracle_view_text: str) -> Tuple[str, List[str]]:
    """将 Oracle 视图定义转为 PostgreSQL CREATE VIEW 可用的查询体。"""
    return convert_oracle_to_pg_sql(oracle_view_text)


def convert_oracle_to_pg_mview(oracle_mview_text: str) -> Tuple[str, List[str]]:
    """将 Oracle 物化视图定义转为 PostgreSQL 物化视图查询体。"""
    return convert_oracle_to_pg_sql(oracle_mview_text)


def convert_oracle_to_pg_routine(oracle_routine_text: str) -> Tuple[str, List[str]]:
    """将 Oracle 例程源码做基础语法替换（完整 PL/SQL 转换需人工）。"""
    text = str(oracle_routine_text or '')
    text = _replace_sysdate(text)
    text = _replace_nvl(text)
    manual_items = detect_manual_review_items(text)
    if ':=' in text:
        manual_items.append('PL/SQL 赋值运算符 := 需改为 PL/pgSQL')
    return text, manual_items
