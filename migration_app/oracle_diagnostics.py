"""Oracle 连接失败诊断：把 DPY/ORA/DPI 原始错误翻译为可自助定位的中文结论。

此前 test_oracle_connection 直接把 str(e) 回给前端，源库为 Oracle 11g 时用户看到的
是 DPY-6005/DPY-3010 整段英文 + CONNECTION_ID + Help 链接，无法据此行动。本模块
统一输出三件套：message（结论）、hint（下一步动作）、detail（脱敏后的原始错误）。
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

# 原始错误中无诊断价值的噪声
_NOISE_PATTERNS = (
    re.compile(r'\s*Help:\s*https?://\S+', re.I),
    re.compile(r'\(CONNECTION_ID=[^)]*\)'),
)

# (匹配模式, 结论, 下一步)。顺序敏感：先具体错误码，后通用连接失败。
_RULES = (
    (
        re.compile(r'DPY-3010', re.I),
        '目标数据库版本过低：python-oracledb 的 thin（免客户端）模式仅支持 Oracle 12.1 及以上',
        '需改用 thick 模式：安装与 Python 同架构的 Oracle Instant Client，'
        '设置 ORACLE_CLIENT_LIB 指向其目录（如 ~/instantclient_23_3）后重启服务。',
    ),
    (
        re.compile(r'DPI-1047', re.I),
        'Oracle Instant Client 未加载或架构不匹配（例如 Apple Silicon 上装了 x86_64 版客户端库）',
        '确认 ORACLE_CLIENT_LIB 指向与 Python 同架构的 Instant Client 目录（arm64 机器需 arm64 版），'
        '或将其留空以退回 thin 模式（thin 模式仅支持 Oracle 12.1+）。',
    ),
    (
        re.compile(r'ORA-01017', re.I),
        '用户名或密码错误',
        '请核对账号口令；Oracle 11g 及以前口令大小写敏感，并注意不要把 SID 当成服务名填写。',
    ),
    (
        re.compile(r'ORA-28000', re.I),
        '账号已被锁定',
        '请联系 DBA 解锁账号（ALTER USER ... ACCOUNT UNLOCK），通常是连续错误口令触发。',
    ),
    (
        re.compile(r'ORA-01031', re.I),
        '权限不足（insufficient privileges）',
        '该账号缺少连接或查询所需权限，请由 DBA 授予 CREATE SESSION 及迁移所需视图权限。',
    ),
    (
        re.compile(r'ORA-12541', re.I),
        '目标端口上没有监听在运行（no listener）',
        '请确认监听服务已启动、端口填写正确（默认 1521），以及主机防火墙放行。',
    ),
    (
        re.compile(r'ORA-12514', re.I),
        '监听存在，但不认识所填写的服务名',
        '请核对服务名（Service Name）与 SID 的区别，可在源库执行 '
        "SELECT value FROM v$parameter WHERE name='service_names' 确认。",
    ),
    (
        re.compile(r'ORA-12154', re.I),
        '服务名/连接串解析失败（TNS 配置问题）',
        '请直接填写服务名而非 TNS 别名；本工具通过 host:port/service_name 建立连接。',
    ),
    (
        re.compile(r'ORA-12170|timeout', re.I),
        '连接超时，网络不可达或被防火墙拦截',
        '请确认源库主机与端口从本机可达（如 telnet/nc 测试），必要时放宽安全组或调大超时。',
    ),
    (
        re.compile(r'DPY-6005', re.I),
        '无法建立到 Oracle 数据库的网络连接',
        '请逐项核对主机、端口、服务名，并确认监听已启动、防火墙/安全组放行。',
    ),
)

_MAX_DETAIL_LEN = 400


def _clean_detail(text: str) -> str:
    cleaned = text.strip()
    for pattern in _NOISE_PATTERNS:
        cleaned = pattern.sub('', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    if len(cleaned) > _MAX_DETAIL_LEN:
        cleaned = cleaned[: _MAX_DETAIL_LEN - 3] + '...'
    return cleaned


def _raw_text(exc: BaseException) -> str:
    """提取可读原文，兼容 oracledb ErrorInfo、普通字符串参数与任意异常。"""
    chunks = []
    for arg in getattr(exc, 'args', ()):
        if isinstance(arg, BaseException):
            chunks.append(str(arg))
        elif isinstance(arg, str):
            chunks.append(arg)
        else:
            message = getattr(arg, 'message', None)
            code = getattr(arg, 'code', None)
            if message:
                chunks.append(str(message))
            elif code is not None:
                chunks.append(f'错误码 {code}')
    text = '\n'.join(chunks).strip()
    return text or str(exc).strip() or exc.__class__.__name__


def diagnose_oracle_connect_error(
    exc: BaseException,
    *,
    target: Optional[str] = None,
) -> Dict[str, Any]:
    """返回 {'message', 'hint', 'detail'}；message 为中文结论，detail 已脱敏。"""
    raw = _raw_text(exc)
    for pattern, message, hint in _RULES:
        if pattern.search(raw):
            if target and target not in message:
                message = f'{message}（目标 {target}）'
            return {'message': message, 'hint': hint, 'detail': _clean_detail(raw)}
    if target:
        message = f'连接失败（目标 {target}）'
    else:
        message = '连接失败'
    return {
        'message': message,
        'hint': '请核对连接参数与源库状态；如需进一步定位，可展开原始数据库错误。',
        'detail': _clean_detail(raw),
    }
