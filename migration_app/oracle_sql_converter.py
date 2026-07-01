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


def _replace_to_date(text: str) -> str:
    """TO_DATE('2024-01-01','YYYY-MM-DD') → '2024-01-01'::timestamp。

    仅处理双参数字面量格式，复杂表达式仅标记不转。
    """
    pattern = re.compile(
        r"TO_DATE\s*\(\s*('[^']*')\s*,\s*'[^']*'\s*\)",
        re.IGNORECASE,
    )
    return pattern.sub(r'\1::timestamp', text)


def _replace_to_char(text: str) -> str:
    """TO_CHAR(expr) → expr::text（简单替换，格式化参数丢失需人工复核）。"""
    # 仅替换单参数 TO_CHAR(x) → x::text
    return re.sub(r'\bTO_CHAR\s*\(', 'CAST(', text, flags=re.IGNORECASE)


def _replace_to_number(text: str) -> str:
    """TO_NUMBER(expr) → expr::numeric。"""
    return re.sub(r'\bTO_NUMBER\s*\(', 'CAST(', text, flags=re.IGNORECASE)


def _replace_rownum(text: str) -> str:
    """ROWNUM → ROW_NUMBER() OVER() 占位（仅简单场景，复杂需人工）。"""
    # 仅在 SELECT 列表中替换 ROWNUM 为 ROW_NUMBER() OVER()
    return re.sub(r'\bROWNUM\b', 'ROW_NUMBER() OVER()', text, flags=re.IGNORECASE)


def _replace_execute_immediate(text: str) -> str:
    """EXECUTE IMMEDIATE 'sql' → EXECUTE 'sql'（PG plpgsql 语法）。"""
    return re.sub(r'\bEXECUTE\s+IMMEDIATE\b', 'EXECUTE', text, flags=re.IGNORECASE)


def _replace_dbms_output(text: str) -> str:
    """DBMS_OUTPUT.PUT_LINE(x) → RAISE NOTICE '%', x。"""
    text = re.sub(
        r'\bDBMS_OUTPUT\.PUT_LINE\s*\(',
        'RAISE NOTICE \'%\', ',
        text,
        flags=re.IGNORECASE,
    )
    return text


def convert_oracle_to_pg_routine(oracle_routine_text: str) -> Tuple[str, List[str]]:
    """将 Oracle 例程源码做基础语法替换（完整 PL/SQL 转换需人工）。

    v2.3 增强：新增 DECODE/FROM DUAL/TO_DATE/TO_CHAR/TO_NUMBER/ROWNUM/
    EXECUTE IMMEDIATE/DBMS_OUTPUT 等高频语法替换，并检测 Oracle
    PROCEDURE 语法（与 PG 不兼容），返回 manual_items 提示人工处理。
    """
    text = str(oracle_routine_text or '')
    original_text = text  # 保留原文用于检测 Oracle 专有语法
    text = _replace_sysdate(text)
    text = _replace_nvl(text)
    text = _replace_dual(text)
    text = _replace_decode_simple(text)
    text = _replace_to_date(text)
    text = _replace_to_char(text)
    text = _replace_to_number(text)
    text = _replace_rownum(text)
    text = _replace_execute_immediate(text)
    text = _replace_dbms_output(text)

    manual_items = detect_manual_review_items(original_text)

    # 检测 Oracle PROCEDURE/FUNCTION 头部语法（与 PG 不兼容）
    # Oracle: CREATE OR REPLACE PROCEDURE name IS/AS ... BEGIN ... END;
    # PG:    CREATE OR REPLACE FUNCTION name() RETURNS ... LANGUAGE plpgsql AS $$ ... $$
    if re.search(r'\bCREATE\s+(OR\s+REPLACE\s+)?PROCEDURE\b', original_text, re.IGNORECASE):
        manual_items.append('Oracle CREATE PROCEDURE 语法需改写为 PG CREATE FUNCTION（含 RETURNS 与 LANGUAGE plpgsql）')
    if re.search(r'\bCREATE\s+(OR\s+REPLACE\s+)?FUNCTION\b', original_text, re.IGNORECASE):
        manual_items.append('Oracle CREATE FUNCTION 头部签名需补全 RETURNS 与 LANGUAGE plpgsql AS $$ ... $$ 包装')
    # %TYPE / %ROWTYPE 需人工映射
    if re.search(r'%TYPE\b|%ROWTYPE\b', original_text, re.IGNORECASE):
        manual_items.append('PL/SQL %TYPE/%ROWTYPE 需手动映射为 PG 列类型或 composite type')
    # EXCEPTION WHEN OTHERS 需人工复核（PG 语法兼容但语义略不同）
    if re.search(r'\bEXCEPTION\s+WHEN\s+OTHERS\b', original_text, re.IGNORECASE):
        manual_items.append('EXCEPTION WHEN OTHERS 需复核 PG 异常处理语义')
    # := 在 plpgsql 中本就支持，不算需人工（修正之前的误报）

    return text, manual_items


def is_routine_safe_to_execute(pg_routine_text: str, manual_items: List[str]) -> bool:
    """判断转换后的例程是否可直接在 PG 执行。

    存在 Oracle 专有语法头部（PROCEDURE / %TYPE / %ROWTYPE）时返回 False，
    避免直接 execute 导致语法错误与任务失败。
    """
    # 检测 PG 不兼容的 Oracle 头部语法
    text = str(pg_routine_text or '')
    if re.search(r'\bCREATE\s+(OR\s+REPLACE\s+)?PROCEDURE\b', text, re.IGNORECASE):
        return False
    if re.search(r'%TYPE\b|%ROWTYPE\b', text, re.IGNORECASE):
        return False
    # 缺少 LANGUAGE plpgsql 包装的裸 BEGIN ... END
    if re.search(r'\bBEGIN\b', text, re.IGNORECASE) and not re.search(r'\bLANGUAGE\s+plpgsql\b', text, re.IGNORECASE):
        return False
    return True
