"""
连接凭据加解密：设置环境变量 MIGRATION_FERNET_KEY 为 Fernet 密钥（url-safe base64 44 字符）
或任意字符串时将从该字符串派生密钥。未设置密钥时密码以明文存储（兼容旧数据）。
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet_from_settings():
    """根据配置返回 Fernet 实例；无有效密钥时返回 None。"""
    key = (getattr(settings, 'MIGRATION_FERNET_KEY', None) or '').strip()
    if not key:
        return None
    raw = key.encode('utf-8')
    if len(raw) == 44 and raw.endswith(b'='):
        try:
            return Fernet(raw)
        except Exception:
            pass
    derived = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(derived)


def maybe_encrypt_password(plain: str) -> str:
    """若已配置密钥且明文非密文前缀，则加密为 enc:... 形式。"""
    if not plain:
        return plain
    if plain.startswith('enc:'):
        return plain
    f = _fernet_from_settings()
    if not f:
        return plain
    token = f.encrypt(plain.encode('utf-8'))
    return 'enc:' + token.decode('ascii')


def maybe_decrypt_password(stored: str) -> str:
    """解密 enc: 前缀的密码；否则原样返回（兼容明文）。"""
    if not stored:
        return ''
    if not stored.startswith('enc:'):
        return stored
    f = _fernet_from_settings()
    if not f:
        # 配置了密文但无密钥，无法解密
        return ''
    try:
        return f.decrypt(stored[4:].encode('ascii')).decode('utf-8')
    except InvalidToken:
        return ''

