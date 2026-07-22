"""
迁移日志脱敏：避免在日志中泄露密码等敏感片段。
"""
import logging
import re

# 常见键名后的赋值片段
_RE_SECRET = re.compile(
    r'(?i)(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*(\S+)',
)


def redact_sensitive_text(text: str) -> str:
    """将疑似密码字段替换为掩码。"""
    if not text or not isinstance(text, str):
        return text
    return _RE_SECRET.sub(lambda m: f'{m.group(1)}=***', text)


class SanitizeFilter(logging.Filter):
    """logging.Filter 实现:对 record.msg 与 args 做脱敏。

    v2.4: 挂载到 LOGGING 的 handlers.filters,自动过滤业务 logger 输出。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if record.msg and isinstance(record.msg, str):
                record.msg = redact_sensitive_text(record.msg)
            if record.args:
                record.args = tuple(
                    redact_sensitive_text(a) if isinstance(a, str) else a
                    for a in (record.args if isinstance(record.args, tuple) else (record.args,))
                )
        except Exception:
            # 脱敏失败不能影响日志输出
            pass
        return True


