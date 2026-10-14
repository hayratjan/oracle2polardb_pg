# Docker 部署指南

> v2.4.4 · Docker 镜像构建与 docker-compose 一键部署。
> 后端镜像基于 `python:3.12-slim`（~250MB，无编译链、无 Oracle 客户端），gunicorn 生产启动，非 root 运行，内置健康检查。
> v2.5 起驱动为 **python-oracledb（thin 模式，纯 Python）**——容器内**无需安装 Oracle Instant Client**。

## 目录

- [一、部署形态总览](#一部署形态总览)
- [二、镜像获取与构建](#二镜像获取与构建)
- [三、docker-compose 一键部署](#三docker-compose-一键部署)
- [四、可选服务组（profile）](#四可选服务组profile)
- [五、Dockerfile 关键设计](#五dockerfile-关键设计)
- [六、CI 自动构建](#六ci-自动构建)
- [七、生产部署架构建议](#七生产部署架构建议)
- [八、常见问题](#八常见问题)

---

## 一、部署形态总览

```
最小栈（默认）          全栈（--profile meta-db --profile frontend）

┌─────────────┐        用户 ──8080──▶ ┌──────────┐
│ web   :8000 │◀── API ───────────── │ frontend │ nginx
│ redis (内部) │                      │  (SPA+反代)│
│ worker/beat │                      └────┬─────┘
└─────────────┘                           │ /api/ 同源反代
外加可选:                            ┌────▼─────┐
│ db    :5432 │ PostgreSQL 元数据库   │ web:8000 │ gunicorn
             │（compose 内置或外置）  └──┬───────┘
                                         │
                                   redis + worker + beat
```

| 形态 | 命令 | 适用 |
|------|------|------|
| 最小栈 | `docker compose up -d` | 快速试用；元数据库用 SQLite、无前端容器 |
| + 前端 | `docker compose --profile frontend up -d` | 生产推荐：nginx 托管前端 + 同源反代，**无 CORS 配置** |
| + 元数据库 | `docker compose --profile meta-db up -d` | 需要独立 PostgreSQL 存任务元数据 |
| 全栈 | `docker compose --profile meta-db --profile frontend up -d` | 完整生产拓扑 |

> Oracle 源库与 PolarDB 目标库**始终在容器外**——平台是迁移工具，不托管业务数据库。

## 二、镜像获取与构建

### 2.1 从 GHCR 拉取（CI 自动构建）

```bash
docker pull ghcr.io/<github用户名>/oracle2polardb_pg:latest      # master 最新
docker pull ghcr.io/<github用户名>/oracle2polardb_pg:v2.4.4      # 版本标签
docker pull ghcr.io/<github用户名>/oracle2polardb_pg:master-<sha> # 可追溯
```

> 首次使用需在 GitHub 仓库 → Packages 设置可见性 public（或 PAT 登录拉私有镜像）。

### 2.2 本地构建

```bash
git clone <仓库地址> && cd oracle2polardb_pg
docker build -t oracle2polardb_pg:local .              # 后端
docker build -t oracle2polardb_frontend:local ./frontend   # 前端（可选）
```

**体积说明**：v2.4.4 起后端镜像不再安装 `gcc`/`libpq-dev`（依赖 `psycopg2-binary` 预编译 wheel）与 Oracle Instant Client（oracledb thin 模式），镜像从 ~450MB 降至 ~250MB。如需换源码版 `psycopg2`（性能略优），在 Dockerfile 恢复 `apt-get install libpq-dev gcc` 并把 requirements 改为 `psycopg2`。

## 三、docker-compose 一键部署

### 3.1 准备环境变量

```bash
cp .env.example .env && vim .env
```

**生产环境必填项**：

| 变量 | 说明 | 生成方式/示例 |
|------|------|------|
| `DJANGO_SECRET_KEY` | Django 密钥 | `python -c "import secrets;print(secrets.token_urlsafe(50))"` |
| `ALLOWED_HOSTS` | 允许的域名（逗号分隔） | `mg.example.com,localhost` |
| `CORS_ALLOWED_ORIGINS` | 前端域名（逗号分隔） | 用 frontend profile 时可留空（同源） |
| `MIGRATION_FERNET_KEY` | 连接密码加密密钥 | `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"` |
| `REDIS_PASSWORD` | Redis 密码 | 随机串 |
| `DATABASE_URL` | 元数据库 PG 连接 | 启用 meta-db profile 时：`postgres://migration:<META_DB_PASSWORD>@db:5432/migration_meta` |

启用 meta-db profile 时还需：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `META_DB_USER` | `migration` | 元数据库用户 |
| `META_DB_PASSWORD` | `changeme_metadb` | 元数据库密码（务必修改） |

启用 frontend profile 时可选 `FRONTEND_PORT`（默认 `8080`）。

### 3.2 启动

```bash
# 最小栈
docker compose up -d

# 生产推荐（前端 + 元数据库）
docker compose --profile meta-db --profile frontend up -d
```

| 服务 | 说明 | 端口 |
|------|------|------|
| `web` | gunicorn 应用（启动时自动 migrate + collectstatic） | 宿主机 8000 |
| `redis` | 缓存与 Celery broker（带密码，仅 compose 内网） | 仅内部 |
| `celery-worker` | 异步任务（增量同步、整库迁移），带存活检查 | — |
| `celery-beat` | 定时调度（每 5 分钟扫描定时增量） | — |
| `db`（可选） | PostgreSQL 16 元数据库，数据持久化在 `meta_db_data` 卷 | 仅内部 |
| `frontend`（可选） | nginx：SPA 托管 + `/api/`、`/ws/`、`/admin/` 同源反代 | 宿主机 8080 |

### 3.3 健康检查与日志

```bash
docker compose ps                       # 服务状态（healthy/unhealthy）
docker compose logs -f web              # 后端日志
curl http://localhost:8000/healthz      # 存活探测
curl http://localhost:8000/readyz       # 就绪探测（含元数据库连通性）
# 启用 frontend 后,入口统一为:
curl http://localhost:8080/healthz
```

### 3.4 初始化管理员

```bash
docker compose exec web python manage.py init_admin --username admin --password <密码>
```

### 3.5 升级

```bash
git pull
docker compose build
docker compose up -d        # 已启用 profile 的照原样加 --profile 参数
```

## 四、可选服务组（profile）

### 4.1 frontend（推荐生产启用）

- **构建**：`frontend/Dockerfile` 多阶段——node 22 构建产物复制进 nginx 1.27；
- **同源反代**：前端构建时 `VITE_API_BASE_URL` 留空 → 浏览器请求相对路径 → nginx `/api/` 反代到 `web:8000`。**全程同源，生产无需任何 CORS 配置**（开发环境的 CORS 仅为前后端分离 dev server 服务）；
- **SPA 回退**：`try_files ... /index.html` 支持前端路由直刷；
- 前端入口改为 `http://<主机>:8080`，可在 compose 中删掉 web 的 `ports: 8000`，让后端仅内网可达。

### 4.2 meta-db

- 提供 PostgreSQL 16 作为元数据库（任务/连接/审计记录）；
- 数据持久化在命名卷 `meta_db_data`，`docker compose down` 不丢失（`down -v` 才删除）；
- `.env` 中 `DATABASE_URL` 指向 `db:5432`（compose 服务名）；
- 已有外部 PG 时不用此 profile，直接把 `DATABASE_URL` 指向外部实例。

## 五、Dockerfile 关键设计

### 5.1 构建期 collectstatic 模式切换

`DJANGO_ENV=prod` 下 settings 强制要求 `SECRET_KEY`/`ALLOWED_HOSTS`/`MIGRATION_FERNET_KEY`，构建期没有这些变量。因此构建期用 dev 模式跑 collectstatic（不触发检查），该环境变量仅在该层生效：

```dockerfile
RUN DJANGO_ENV=dev python manage.py collectstatic --noinput
```

### 5.2 无编译链、无 Oracle 客户端

| 依赖 | 原因 |
|------|------|
| 不装 `gcc`/`libpq-dev` | `psycopg2-binary` 是预编译 wheel |
| 不装 Oracle Instant Client | `oracledb` thin 模式为纯 Python 直连 |

### 5.3 安全加固

- 非 root 用户 `appuser`(UID 1000) 运行 gunicorn；
- 内置 `HEALTHCHECK` 探测 `/healthz`；
- `.dockerignore` 排除 `.env`/`.git`/`db.sqlite3`/`.mimosa`/`node_modules` 等敏感与冗余内容。

## 六、CI 自动构建

**文件**：[.github/workflows/docker-build.yml](../.github/workflows/docker-build.yml)

- **触发**：push `master`、push `v*` 标签、手动 workflow_dispatch；
- **标签策略**：master → `latest` + `master-<sha>`；`v2.4.4` → `v2.4.4` + `2.4`；
- **缓存**：GitHub Actions cache（`type=gha`）；
- **首次使用**：Settings → Actions → General → Workflow permissions → **Read and write permissions**；Packages 默认 private，需要公开则手动改 visibility。

## 七、生产部署架构建议

```
                 ┌──────────────┐
  用户 ── HTTPS ─│  Nginx/Cdn    │ ←（frontend 容器可充当此层,或前置云 LB）
                 └──────┬───────┘
                        │ HTTP(内网)
                 ┌──────▼───────┐
                 │  frontend     │ nginx :8080
                 │  (SPA+反代)   │
                 └──────┬───────┘
                        │ /api/ 同源
                 ┌──────▼───────┐
                 │  web          │ gunicorn :8000(仅内网)
                 └──┬────────┬──┘
          ┌─────────▼──┐  ┌──▼───────────┐
          │ redis       │  │ worker / beat │
          └────────────┘  └──┬───────────┘
                            │
              ┌─────────────▼──────────────┐
              │ db(元数据库 PG,可外置)       │
              │ Oracle 源库 / PolarDB 目标库  │ ← 永远在容器外
              └────────────────────────────┘
```

**安全清单**：

- [ ] 启用 frontend 后，删除 web 的宿主机端口映射（仅 nginx 对外）；
- [ ] Redis 保持 `expose`（不映射宿主机端口）；
- [ ] `META_DB_PASSWORD`/`REDIS_PASSWORD` 全部改掉默认值；
- [ ] 前置云 LB 做 TLS，或自备 nginx 加证书；
- [ ] `ALLOWED_HOSTS` 只列实际域名；若 nginx 转发 Header，确认 `USE_X_FORWARDED_PROTO` 配置。

## 八、常见问题

### Q1: docker build 报 `RuntimeError: 生产环境必须通过 DJANGO_SECRET_KEY...`

构建期 collectstatic 已用 dev 模式规避。若仍报错，确认 Dockerfile 中 collectstatic 一行为 `RUN DJANGO_ENV=dev python manage.py collectstatic --noinput`。

### Q2: pip install 失败 / 找不到 django 6.0

v2.4.1 已锁定 `django>=4.2,<5.0`；v2.5 驱动改为 `oracledb`（替代废弃的 cx_Oracle）。确保使用最新 `requirements.txt`。

### Q3: GHCR 推送报 `denied: permission_denied`

仓库 Settings → Actions → General → Workflow permissions → 勾选 **Read and write permissions**。

### Q4: compose up 后 web 启动即崩溃（RuntimeError）

三个服务均有 `env_file: .env`，检查 `.env` 是否填写：`DJANGO_SECRET_KEY`、`ALLOWED_HOSTS`、`MIGRATION_FERNET_KEY`、`REDIS_PASSWORD`。

### Q5: 健康检查失败

```bash
docker compose logs web | tail -50
docker compose exec web python -c "import django; django.setup()"
```
常见原因：生产必填变量缺失，或 `DATABASE_URL` 指向的元数据库不可达。

### Q6: celery-worker 连不上 Redis

`.env` 的 `REDIS_PASSWORD` 与 compose 中 `${REDIS_PASSWORD:-changeme_redis}` 一致；broker 地址是 `redis:6379`（compose 服务名），不是 `localhost`。

### Q7: 前端容器访问 8080 白屏 / 请求 404

确认前端构建时 `VITE_API_BASE_URL` 为空（相对路径）；检查 `docker compose logs frontend` 中 nginx 反代目标 `web:8000` 可达（web 服务需处于 healthy）。

### Q8: 容器内能连 Oracle 吗？要装 Instant Client 吗？

不需要。oracledb thin 模式纯 Python 直连 Oracle 11g+；只要容器网络能路由到 Oracle 主机的 1521 端口即可（可 `docker compose exec web python -c "import socket;s=socket.create_connection(('10.x.x.x',1521),5);print('OK')")` 验证连通性）。

### Q9: 如何备份数据

```bash
# 元数据库（启用 meta-db 时）
docker compose exec db pg_dump -U migration migration_meta > backup_$(date +%F).sql
# SQLite（未启用 meta-db）: 备份宿主机挂载或 exec 导出 db.sqlite3
docker compose exec web python -c "import shutil;shutil.copy('db.sqlite3','/tmp/backup.sqlite3')" && docker compose cp web:/tmp/backup.sqlite3 ./backup.sqlite3
```
