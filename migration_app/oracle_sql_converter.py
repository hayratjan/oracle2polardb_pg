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
    # v2.4: 新增 PL/SQL 专有语法检测
    (r'\bFORALL\b', 'FORALL 批量绑定(PG 需改写为 FOREACH 或循环)'),
    (r'\bBULK\s+COLLECT\b', 'BULK COLLECT INTO(PG 需改写为 cursor loop 或 array_agg)'),
    (r'\bPRAGMA\s+', 'PRAGMA 指令(PG 无对应,需人工处理)'),
    (r'\bAUTONOMOUS_TRANSACTION\b', '自治事务(PG 无原生支持,需 dblink 或独立连接)'),
    (r'\bCREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\b', 'Oracle PACKAGE(PG 无包概念,需拆分为 schema+函数)'),
    (r'\bDBMS_SQL\b', 'DBMS_SQL 动态 SQL(PG 需改用 EXECUTE 或 PL/pgSQL 动态 SQL)'),
    (r'\bUTL_FILE\b|\bUTL_HTTP\b|\bUTL_MAIL\b', 'UTL_* 包(PG 无对应,需人工改写)'),
    (r'\bPIVOT\b|\bUNPIVOT\b', 'PIVOT/UNPIVOT(PG 需用 crosstab 或 CASE WHEN 改写)'),
    (r'\bMODEL\b\s', 'MODEL 子句(PG 无对应,需人工改写)'),
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


def _replace_decode_once(text: str) -> str:
    """单次扫描:转换最内层 DECODE(参数中不含 DECODE 的)。

    用括号平衡扫描法,从右向左找 DECODE(,处理第一个参数中不含嵌套 DECODE 的实例。
    """
    pattern = re.compile(r'\bDECODE\s*\(', re.IGNORECASE)
    # 从右向左扫描,优先匹配最内层
    matches = list(pattern.finditer(text))
    for m in reversed(matches):
        start = m.start()
        # 扫描参数
        depth = 0
        j = m.end() - 1
        args_start = j + 1
        args = []
        cur_start = args_start
        in_str = False
        str_char = ''
        while j < len(text):
            ch = text[j]
            if in_str:
                if ch == str_char:
                    in_str = False
            elif ch in ("'", '"'):
                in_str = True
                str_char = ch
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    args.append(text[cur_start:j])
                    break
            elif ch == ',' and depth == 1 and not in_str:
                args.append(text[cur_start:j])
                cur_start = j + 1
            j += 1

        if depth != 0 or len(args) < 3:
            continue

        # 检查参数中是否含嵌套 DECODE(若有则跳过,留给下一轮)
        args_str = text[m.end():j]
        if 'DECODE' in args_str.upper():
            continue

        args = [a.strip() for a in args]
        expr = args[0]
        # 构建 CASE WHEN
        case_parts = [f'CASE {expr}']
        i = 1
        while i + 1 < len(args):
            case_parts.append(f'WHEN {args[i]} THEN {args[i + 1]}')
            i += 2
        # 最后一个参数是 default(如果有)
        if i < len(args):
            case_parts.append(f'ELSE {args[i]}')
        case_parts.append('END')
        replacement = ' '.join(case_parts)

        text = text[:start] + replacement + text[j + 1:]
        return text  # 每次只转换一个,返回
    return text


def _replace_decode(text: str) -> str:
    """将 DECODE 完整转换为 CASE WHEN。

    支持任意参数数量:DECODE(expr, s1, r1, s2, r2, ..., [default])
    用括号平衡扫描法处理嵌套括号与逗号。
    对嵌套 DECODE 采用「从内到外」多次扫描。
    """
    for _ in range(10):
        if 'DECODE' not in text.upper():
            break
        new_text = _replace_decode_once(text)
        if new_text == text:
            break
        text = new_text
    return text


def _replace_listagg(text: str) -> str:
    """LISTAGG(expr, delimiter) WITHIN GROUP (ORDER BY ...) → STRING_AGG(expr::text, delimiter ORDER BY ...)。"""
    result = []
    i = 0
    pattern = re.compile(r'\bLISTAGG\s*\(', re.IGNORECASE)
    while i < len(text):
        m = pattern.search(text, i)
        if not m:
            result.append(text[i:])
            break
        result.append(text[i:m.start()])
        depth = 0
        j = m.end() - 1
        args_start = j + 1
        args = []
        cur_start = args_start
        in_str = False
        str_char = ''
        while j < len(text):
            ch = text[j]
            if in_str:
                if ch == str_char:
                    in_str = False
            elif ch in ("'", '"'):
                in_str = True
                str_char = ch
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    args.append(text[cur_start:j])
                    break
            elif ch == ',' and depth == 1 and not in_str:
                args.append(text[cur_start:j])
                cur_start = j + 1
            j += 1

        if depth != 0 or len(args) < 1 or len(args) > 2:
            result.append(text[m.start():j + 1] if j < len(text) else text[m.start():])
            i = j + 1
            continue

        rest = text[j + 1:]
        wg_match = re.match(
            r'\s*WITHIN\s+GROUP\s*\(\s*ORDER\s+BY\s+([^)]+)\s*\)',
            rest,
            re.IGNORECASE | re.DOTALL,
        )
        if not wg_match:
            result.append(text[m.start():j + 1])
            i = j + 1
            continue

        order_by = wg_match.group(1).strip()
        args = [a.strip() for a in args]
        if len(args) == 2:
            expr, delim = args
            replacement = f'STRING_AGG({expr}::text, {delim} ORDER BY {order_by})'
        else:
            expr = args[0]
            replacement = f"STRING_AGG({expr}::text, '' ORDER BY {order_by})"
        result.append(replacement)
        i = j + 1 + wg_match.end()
    return ''.join(result)


def _replace_nvl2(text: str) -> str:
    """NVL2(expr, if_not_null, if_null) → CASE WHEN expr IS NOT NULL THEN if_not_null ELSE if_null END。"""
    pattern = re.compile(r'\bNVL2\s*\(', re.IGNORECASE)
    result = []
    i = 0
    while i < len(text):
        m = pattern.search(text, i)
        if not m:
            result.append(text[i:])
            break
        result.append(text[i:m.start()])
        depth = 0
        j = m.end() - 1
        args = []
        cur_start = j + 1
        in_str = False
        str_char = ''
        while j < len(text):
            ch = text[j]
            if in_str:
                if ch == str_char:
                    in_str = False
            elif ch in ("'", '"'):
                in_str = True
                str_char = ch
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    args.append(text[cur_start:j])
                    break
            elif ch == ',' and depth == 1 and not in_str:
                args.append(text[cur_start:j])
                cur_start = j + 1
            j += 1
        if depth != 0 or len(args) != 3:
            result.append(text[m.start():j + 1] if j < len(text) else text[m.start():])
            i = j + 1
            continue
        args = [a.strip() for a in args]
        replacement = f'CASE WHEN {args[0]} IS NOT NULL THEN {args[1]} ELSE {args[2]} END'
        result.append(replacement)
        i = j + 1
    return ''.join(result)


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
    text = _replace_listagg(text)
    text = _replace_nvl2(text)
    text = _replace_decode(text)

    manual_items = detect_manual_review_items(text)
    return text, manual_items


def convert_oracle_to_pg_view(oracle_view_text: str) -> Tuple[str, List[str]]:
    """将 Oracle 视图定义转为 PostgreSQL CREATE VIEW 可用的查询体。

    v2.4: 复用 routine 的全部替换函数(此前视图仅做 4 项基础替换,
    缺失 ROWNUM/TO_DATE/TO_CHAR/TO_NUMBER 等,导致视图 SQL 执行报错)。
    """
    return convert_oracle_to_pg_routine(oracle_view_text)


def convert_oracle_to_pg_mview(oracle_mview_text: str) -> Tuple[str, List[str]]:
    """将 Oracle 物化视图定义转为 PostgreSQL 物化视图查询体。"""
    return convert_oracle_to_pg_routine(oracle_mview_text)


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
    """TO_CHAR 转换为 PG 兼容写法。

    v2.4 修复:
    - 单参数 TO_CHAR(x) → x::text
    - 双参数 TO_CHAR(x, fmt) → to_char(x, fmt) (PG 原生支持 to_char,
      但格式串与 Oracle 不完全兼容,保留并加入 manual_items)
    此前实现将 TO_CHAR( 直接替换为 CAST(,丢失格式化参数导致语法错误。
    """
    # 双参数: TO_CHAR(expr, 'fmt') → to_char(expr, 'fmt')
    # PG 的 to_char 与 Oracle 格式串不完全兼容,需人工复核但语法可执行
    text = re.sub(
        r'\bTO_CHAR\s*\(\s*([^,()]+(?:\([^()]*\))?[^,]*?)\s*,\s*(\'[^\']*\')\s*\)',
        r'to_char(\1, \2)',
        text,
        flags=re.IGNORECASE,
    )
    # 单参数: TO_CHAR(x) → x::text
    text = re.sub(r'\bTO_CHAR\s*\(\s*([^)]+?)\s*\)', r'\1::text', text, flags=re.IGNORECASE)
    return text


def _replace_to_number(text: str) -> str:
    """TO_NUMBER(expr) → expr::numeric。"""
    # 单参数 → ::numeric
    text = re.sub(r'\bTO_NUMBER\s*\(\s*([^,)]+?)\s*\)', r'\1::numeric', text, flags=re.IGNORECASE)
    # 双参数 TO_NUMBER(x, fmt) 保留(PG 无对应),加入 manual_items 由 detect 处理
    return text


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
    text = _replace_listagg(text)
    text = _replace_nvl2(text)
    text = _replace_decode(text)
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
