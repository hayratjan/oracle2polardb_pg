# 后端镜像
FROM python:3.12-slim

WORKDIR /app

# v2.4: 明确生产环境标识(DJANGO_ENV=prod 覆盖默认 dev)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENV=prod \
    DJANGO_DEBUG=false

# v2.4.4: 移除 gcc/libpq-dev——requirements 使用 psycopg2-binary(预编译 wheel)，
# 无需源码编译；oracledb 为纯 Python(thin 模式)，无需 Oracle Instant Client。
# 镜像体积从 ~450MB 减至 ~250MB。
# 如需换源码版 psycopg2(性能略优)，恢复安装 libpq-dev gcc 并在 requirements 改为 psycopg2。

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# v2.4: collectstatic 构建期用 dev 模式
# 原因:DJANGO_ENV=prod 下 settings.py 强制要求 SECRET_KEY/ALLOWED_HOSTS/MIGRATION_FERNET_KEY,
# 构建期无这些环境变量会导致 collectstatic raise RuntimeError,docker build 失败。
# dev 模式不触发这些检查,collectstatic 只需静态文件目录即可成功。
# RUN 的环境变量仅在该层生效,不影响最终镜像 ENV(DJANGO_ENV=prod)
RUN DJANGO_ENV=dev python manage.py collectstatic --noinput

EXPOSE 8000

# v2.4: 增加非 root 用户运行(安全加固)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# v2.4: 增加容器健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).read()" || exit 1

CMD ["gunicorn", "oracle2polardb_pg.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
