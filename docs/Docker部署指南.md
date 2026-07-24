# Docker 部署指南

> v2.4 提供 Docker 镜像构建与 docker-compose 一键部署,支持 GHCR 自动构建。
> 镜像基于 `python:3.12-slim`,gunicorn 生产启动,非 root 用户运行,内置健康检查。
> v2.4.2: Oracle 驱动从 `cx_Oracle` 迁移至官方继任者 `oracledb`(修复 Python 3.12 下 Docker 构建失败)。

## 一、镜像获取

### 1.1 从 GHCR 拉取(推荐,CI 自动构建)

每次推送到 `master` 分支或打 `v*` 标签,GitHub Actions 自动构建并推送镜像到 GitHub Container Registry。

```bash
# 拉取最新版(master 分支)
docker pull ghcr.io/<github用户名>/oracle2polardb_pg:latest

# 拉取指定 git sha(可追溯)
docker pull ghcr.io/<github用户名>/oracle2polardb_pg:master-<sha短码>

# 拉取版本标签
docker pull ghcr.io/<github用户名>/oracle2polardb_pg:v2.4.0
```

> 镜像地址中的 `<github用户名>/oracle2polardb_pg` 会自动转小写。
> 首次使用需在 GitHub 仓库 → Packages 将镜像可见性设为 public(或用 PAT 登录拉取私有镜像)。

### 1.2 本地构建

```bash
git clone <仓库地址>
cd oracle2polardb_pg
docker build -t oracle2polardb_pg:local .
```

## 二、docker-compose 一键部署

### 2.1 准备环境变量

复制 `.env.example` 为 `.env`,按实际填写:

```bash
cp .env.example .env
vim .env
```

**生产环境必填项**:

| 变量 | 说明 | 示例 |
|------|------|------|
| `DJANGO_SECRET_KEY` | Django 密钥(随机长字符串) | `python -c "import secrets;print(secrets.token_urlsafe(50))"` |
| `ALLOWED_HOSTS` | 允许的域名(逗号分隔) | `mg.example.com,localhost` |
| `CORS_ALLOWED_ORIGINS` | 前端域名(逗号分隔) | `https://mg.example.com` |
| `MIGRATION_FERNET_KEY` | 连接密码加密密钥 | `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"` |
| `DATABASE_URL` | 元数据库 PG 连接 | `postgres://user:pass@db:5432/migration_meta` |
| `CELERY_BROKER_URL` | Redis 连接(需带密码) | `redis://:redispass@redis:6379/0` |
| `REDIS_PASSWORD` | Redis 密码 | `changeme_redis` |

### 2.2 启动服务

```bash
docker compose up -d
```

启动的服务:
- **web**:gunicorn 应用(8000 端口),依赖 Redis 健康检查
- **redis**:缓存与 Celery broker(仅内网,带密码)
- **celery-worker**:异步任务执行(增量同步、整库迁移)
- **celery-beat**:定时任务调度(每 5 分钟扫描定时增量)

### 2.3 健康检查与日志

```bash
# 查看服务状态
docker compose ps

# 查看 web 日志
docker compose logs -f web

# 健康检查(内置 healthcheck)
curl http://localhost:8000/healthz
```

### 2.4 初始化管理员

首次部署需创建管理员账号:

```bash
docker compose exec web python manage.py init_admin
```

## 三、Dockerfile 关键设计

### 3.1 构建期 collectstatic 模式切换

**问题**:Dockerfile 设 `DJANGO_ENV=prod`,但生产模式 settings.py 强制要求 `SECRET_KEY`/`ALLOWED_HOSTS`/`MIGRATION_FERNET_KEY`,构建期无这些变量导致 `collectstatic` 报错。

**修复**:构建期用 `DJANGO_ENV=dev` 跑 collectstatic(不触发生产强制检查),`RUN` 环境变量仅在该层生效,不影响最终镜像 `ENV DJANGO_ENV=prod`:

```dockerfile
RUN DJANGO_ENV=dev python manage.py collectstatic --noinput
```

### 3.2 非 root 用户与 healthcheck

- 构建完成后创建 `appuser`(UID 1000),`chown /app`,以 `appuser` 运行 gunicorn
- 内置 `HEALTHCHECK`,30 秒间隔探测 `/healthz`

### 3.3 Oracle 驱动:oracledb(替代 cx_Oracle)

**背景**:`cx_Oracle 8.3.0` 是 Oracle 官方驱动的最终版本,已停止维护,且无 Python 3.12 wheel。在 `python:3.12-slim` 基础镜像上 `pip install cx-Oracle` 会回退到源码编译,因缺少 Oracle Client SDK 而失败。

**修复**(v2.4.2):`requirements.txt` 改用官方继任者 `oracledb>=2.0,<3.0`,该包提供 cp312 预编译 wheel,安装无需编译,且 API 与 `cx_Oracle` 高度兼容。

**Thin / Thick 模式**:
- **Thin 模式**(默认):纯 Python 实现,无需安装 Oracle Instant Client,开箱即用。适合大多数场景。
- **Thick 模式**:需设置 `ORACLE_CLIENT_LIB` 环境变量指向 Instant Client 路径,`settings.py` 自动调用 `oracledb.init_oracle_client()` 切换。连接 Oracle 11g 等旧版本时可能需要此模式。

Docker 部署时,如需 Thick 模式,在 `docker-compose.yml` 的 `environment` 中添加:
```yaml
ORACLE_CLIENT_LIB: /opt/oracle/instantclient_23_3
```
并在 Dockerfile 中安装 Instant Client(或挂载宿主机目录)。默认 Thin 模式无需额外配置。

## 四、CI 自动构建(GitHub Actions)

### 4.1 docker-build.yml

**文件**: [.github/workflows/docker-build.yml](../.github/workflows/docker-build.yml)

**触发条件**:
- 推送到 `master` 分支
- 推送 `v*` 标签(如 `v2.4.0`)
- 手动触发(workflow_dispatch)

**镜像标签策略**:
| 触发场景 | 标签 |
|----------|------|
| master 推送 | `latest`、`master-<sha>` |
| v2.4.0 标签 | `v2.4.0`、`2.4` |
| 分支推送 | `<分支名>` |

**缓存**:使用 GitHub Actions cache(`type=gha`),加速重复构建。

### 4.2 首次使用前置步骤

1. 仓库 → Settings → Actions → General → Workflow permissions 设为 **Read and write permissions**
2. 推送代码触发首次构建后,仓库右侧 Packages 出现镜像
3. 镜像默认 private,若需公开:Packages → 点击镜像 → Package settings → Change visibility → Public

## 五、生产部署架构建议

```
                    ┌──────────────┐
   用户 ──── HTTPS ─│  Nginx/Cdn   │
                    └──────┬───────┘
                           │ HTTP(内网)
                    ┌──────▼───────┐
                    │  gunicorn    │  ← docker compose web
                    │  (web:8000)  │
                    └──┬────────┬──┘
                       │        │
              ┌────────▼──┐  ┌──▼──────────┐
              │  Redis    │  │ Celery      │
              │ (broker)  │  │ worker/beat │
              └───────────┘  └──────┬──────┘
                                    │
                    ┌───────────────▼──────────────┐
                    │  PostgreSQL(元数据库)         │
                    │  + PolarDB PG(迁移目标)       │
                    └──────────────────────────────┘
```

**安全建议**:
- gunicorn 不直接对外暴露,前置 Nginx 处理 TLS
- 若 gunicorn 直接对外,设 `USE_X_FORWARDED_PROTO=false`(防 `X-Forwarded-Proto` 伪造)
- Redis 设 `expose`(仅 compose 网络内),不 `ports` 映射到宿主机
- 元数据库 PG 与迁移目标 PolarDB PG 应分离部署

## 六、数据库对比与立即增量同步(配套功能)

v2.4 新增「对比预览」与「立即增量同步」功能,用于近实时数据同步:

1. **创建 pk_mirror 任务**:任务类型选 `table`,增量模式选 `pk_mirror`(主键对齐)
2. **对比预览**:任务详情页点「对比预览」,只读查看源/目标差异(待插入/待删除/共存行数)
3. **立即同步**:点「立即增量同步」,同步执行主键对齐(补插缺失行、删除多余行、检测更新行)

详见 [数据库对比与增量同步使用说明](数据库对比与增量同步使用说明.md)。

## 七、常见问题

### Q1: docker build 报 `RuntimeError: 生产环境必须通过 DJANGO_SECRET_KEY...`

**原因**:旧版 Dockerfile 在 `DJANGO_ENV=prod` 下跑 collectstatic,触发生产强制检查。

**解决**:已修复(构建期用 `DJANGO_ENV=dev`)。若仍报错,确认 Dockerfile 第 27 行为 `RUN DJANGO_ENV=dev python manage.py collectstatic --noinput`。

### Q2: GitHub Actions docker build 报 `pip install did not complete successfully: exit code: 1`

**原因**:`requirements.txt` 中 `django>=6.0,<6.1` 在 PyPI 不存在(最新 LTS 为 4.2.x),pip 找不到匹配版本。

**解决**:已修复(v2.4.1),`requirements.txt` 改为 `django>=4.2,<5.0`,与本地开发环境一致。

### Q2.1: GitHub Actions docker build 报 `error: Getting requirements to build wheel did not run successfully` (cx_Oracle 编译失败)

**原因**:`cx-Oracle 8.3.0` 是最终版本(Oracle 官方已停止维护,继任者为 `oracledb`),**没有 Python 3.12 的预编译 wheel**。Dockerfile 基础镜像为 `python:3.12-slim`,pip 回退到从源码编译 `cx_Oracle`,但构建环境缺少 Oracle Client SDK 头文件,编译失败。

**解决**:已修复(v2.4.2),将 `cx-Oracle>=8.3,<9.0` 替换为官方继任者 `oracledb>=2.0,<3.0`。`oracledb` 由 Oracle 官方维护,提供 Python 3.12 wheel(纯安装无需编译),API 与 `cx_Oracle` 高度兼容。代码层面的主要变更:

| cx_Oracle (旧) | oracledb (新) | 说明 |
|:-----|:-----|:-----|
| `import cx_Oracle` | `import oracledb` | 模块名变更 |
| `cx_Oracle.makedsn()` | `oracledb.makedsn()` | API 不变 |
| `cx_Oracle.connect()` | `oracledb.connect()` | API 不变 |
| `cx_Oracle.DatabaseError` | `oracledb.DatabaseError` | 异常类不变 |
| `cx_Oracle.init_oracle_client()` | `oracledb.init_oracle_client()` | Thick 模式初始化 |
| `cx_Oracle.SessionPool()` | `oracledb.create_pool()` | 工厂函数名变更 |
| `cx_Oracle.SPOOL_ATTRVAL_WAIT` | `oracledb.SPOOL_ATTRVAL_WAIT` | 常量保留(向后兼容) |
| `threaded=True` 参数 | 移除(oracledb 池默认线程安全) | 不再需要 |

> **注意**:`oracledb` 默认以 **Thin 模式** 运行(纯 Python,无需 Oracle Instant Client)。如需 Thick 模式功能(如连接旧版 Oracle 11g),设置 `ORACLE_CLIENT_LIB` 环境变量指向 Instant Client 路径,`settings.py` 会自动调用 `oracledb.init_oracle_client()` 切换。

### Q3: GitHub Actions docker build 报 `denied: permission_denided`

**原因**:Workflow 无写入 Packages 权限。

**解决**:仓库 Settings → Actions → General → Workflow permissions → 勾选 **Read and write permissions**。

### Q4: docker compose up 后 web 容器启动即崩溃(RuntimeError)

**原因**:`docker-compose.yml` 中 web/worker/beat 服务仅设了 `DJANGO_ENV=prod` 但未注入 `DJANGO_SECRET_KEY`/`ALLOWED_HOSTS`/`MIGRATION_FERNET_KEY`,生产模式强制检查导致崩溃。

**解决**:已修复(v2.4.1),三个服务均添加 `env_file: .env`,从 `.env` 文件注入所有生产必填变量。确保 `.env` 中已填写:
- `DJANGO_SECRET_KEY`(随机长字符串)
- `ALLOWED_HOSTS`(逗号分隔域名)
- `MIGRATION_FERNET_KEY`(Fernet 密钥)
- `REDIS_PASSWORD`(Redis 密码)

### Q5: 容器启动后健康检查失败

**排查**:
```bash
docker compose logs web | tail -50
docker compose exec web python -c "import django; django.setup()"
```
常见原因:`DJANGO_SECRET_KEY`/`ALLOWED_HOSTS`/`MIGRATION_FERNET_KEY` 未设(生产模式强制检查)。

### Q6: celery-worker 连不上 Redis

**确认**:`.env` 中 `REDIS_PASSWORD` 与 docker-compose.yml 中 `${REDIS_PASSWORD:-changeme_redis}` 一致,且 `CELERY_BROKER_URL` 地址为 `redis:6379`(compose 服务名)。
