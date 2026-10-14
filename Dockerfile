# syntax=docker/dockerfile:1
# Oracle → PolarDB 迁移平台：前后端合并镜像（单进程 Django 同时提供 API 与 Vue SPA）
#
# 两个产物目标(target)，构建期二选一：
#   thin  —— 默认。python-oracledb thin 模式，纯 Python，无 Oracle 客户端依赖。
#            ⚠️ thin 最低支持 Oracle 12.1，连不上 11g 源库(实测 DPY-3010/DPY-6005)。
#   thick —— 附带 Instant Client 19.32(x86_64)，可连 11.2.0.4 这类老源库；
#            仅 amd64，体积比 thin 大约 +90MB。
#
# CI 用法: docker build --target thin  /  --target thick
# docker compose 默认 target: thin

# ─── 阶段 1：Vue 前端构建 ───
FROM node:22-alpine AS web-builder
WORKDIR /build
# corepack 首次下载 pnpm 时不在无 TTY 的 CI 里等确认（否则会挂到 job 超时）
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

# VITE_API_BASE_URL 留空 → 前端请求走同源相对路径 /api/，由本镜像内的 Django 直接受理，
# 不需要 nginx 反代，也没有 CORS。注意 client.ts 现在区分"未定义"和"空串"，
# 空串=同源（旧写法 `|| 'http://localhost:8000'` 会把空串也吞成 localhost）。
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# 依赖清单单独成层，源码改动不触发重新安装
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
# 锁死 pnpm 版本：lockfileVersion 9.0 + pnpm-workspace.yaml 的 allowBuilds 字段是 pnpm 11 的格式，
# corepack 未指定 packageManager 时拉的"known good"版本会变，这里显式 prepare 避免漂移
RUN corepack enable && corepack prepare pnpm@11.17.0 --activate && pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build

# ─── 阶段 2：Python 依赖 + 项目 + 前端产物 + collectstatic ───
FROM python:3.12-slim AS base
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENV=prod \
    DJANGO_DEBUG=false

# requirements 用 psycopg2-binary(预编译 wheel)、oracledb 纯 Python，无需 gcc/libpq-dev
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# 前端构建产物不进 git，也不在 .dockerignore 的 COPY 上下文里，只能从阶段 1 取
COPY --from=web-builder /build/dist ./frontend/dist

# 构建期用 dev：DJANGO_ENV=prod 下 settings 强制校验 SECRET_KEY/ALLOWED_HOSTS/
# MIGRATION_FERNET_KEY，镜像里没有这些变量会让 collectstatic 直接 RuntimeError。
# RUN 层的环境变量不写回最终镜像(ENV 仍是 prod)。
# WhiteNoise 的 manifest 存储会校验每个 url() 都落在 STATIC_ROOT 内，
# 所以 collectstatic 顺带是一次静态资源引用完整性检查。
RUN DJANGO_ENV=dev python manage.py collectstatic --noinput

# 非 root 运行（安全加固）；两个 target 都需要，放在 base 里
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# ─── 阶段 3：thick（Instant Client 19.32，可连 11g）───
FROM base AS thick
ARG IC_VERSION=19.32.0.0.0
ARG IC_RPM=oracle-instantclient19.32-basic-${IC_VERSION}-1.el9.x86_64.rpm
# Debian slim 装不了 RPM，用 rpm2cpio|cpio 解包到 /opt/oracle/instantclient_19_32
# （Oracle 公共源的公开路径是 .../x86_64/getPackage/<rpm>，直接列目录里的文件名会 404）
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends rpm2cpio cpio curl libnsl2; \
    apt-get install -y --no-install-recommends libaio1 \
      || apt-get install -y --no-install-recommends libaio1t64; \
    curl -fL --retry 3 -o /tmp/ic.rpm \
      "https://yum.oracle.com/repo/OracleLinux/OL9/oracle/instantclient/x86_64/getPackage/${IC_RPM}"; \
    rpm2cpio /tmp/ic.rpm | (cd / && cpio -idm --quiet); \
    rm /tmp/ic.rpm; \
    aio=/usr/lib/x86_64-linux-gnu/libaio.so.1; \
    if [ ! -e "$aio" ] && [ -e "${aio}t64" ]; then ln -s "${aio}t64" "$aio"; fi; \
    apt-get purge -y rpm2cpio curl; \
    apt-get autoremove -y; \
    rm -rf /var/lib/apt/lists/*; \
    ls -l /opt/oracle/instantclient_19_32/libclntsh.so.19.1
# 构建期即加载一次客户端库：缺 .so 会在这里报 DPI-1047，而不是等到运行时
RUN python -c "import oracledb; oracledb.init_oracle_client(lib_dir='/opt/oracle/instantclient_19_32'); print('thick OK', oracledb.clientversion()[:3])"
ENV ORACLE_CLIENT_LIB=/opt/oracle/instantclient_19_32 \
    LD_LIBRARY_PATH=/opt/oracle/instantclient_19_32
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).read()" || exit 1
CMD ["gunicorn", "oracle2polardb_pg.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]

# ─── 阶段 4：thin（默认 target，写在最后使其成为默认阶段）───
FROM base AS thin
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).read()" || exit 1
CMD ["gunicorn", "oracle2polardb_pg.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
