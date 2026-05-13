# 未安装 celery 时仍可启动 Django（本地开发可不跑 Worker）
try:
    from .celery import app as celery_app
except ImportError:  # pragma: no cover - 可选依赖
    celery_app = None

__all__ = ('celery_app',)
