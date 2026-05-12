"""
迁移日志脱敏：避免在日志中泄露密码等敏感片段。
"""
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

