# Docker 部署指南

> v2.5 · Docker 镜像构建与 docker-compose 一键部署。
> **v2.5 起前后端合并为单镜像**：Vue 构建产物打进镜像，由 Django + WhiteNoise 同源直出，不再有独立 nginx 前端容器，生产无需 CORS 配置。
> 镜像基于 `python:3.12-slim`，gunicorn 生产启动，非 root 运行，内置健康检查。
> 两个构建目标（target）：`thin`（默认，oracledb thin 模式，**连不上 Oracle 11g**）与 `thick`（内含 Instant Client 19.32，面向 11.2.0.4 这类老源库）。

## 目录

- [一、部署形态总览](#一部署形态总览)
- [二、镜像获取与构建](#二镜像获取与构建)
- [三、docker-compose 一键部署](#三docker-compose-一键部署)
- [四、镜像变体与可选服务组](#四镜像变体与可选服务组)
- [五、Dockerfile 关键设计](#五dockerfile-关键设计)
- [六、CI 自动构建与推送](#六ci-自动构建与推送)
- [七、生产部署架构建议](#七生产部署架构建议)
- [八、常见问题](#八常见问题)

---

## 一、部署形态总览

```
            用户 ──HTTP/HTTPS──▶ ┌───────────────────────┐
                                 │ web            :8000  │ ← 唯一对外入口
                                 │  Vue SPA + REST API   │   (WhiteNoise 直出前端)
                                 │  gunicorn + Django    │
                                 └────┬─────────────┬────┘
                        ┌─────────────▼──┐   ┌──────▼────────────┐
                        │ redis   (内部) │   │ celery-worker/beat│
                        └────────────────┘   └───────────────────┘
  可选: --profile meta-db 起 PostgreSQL 元数据库(db:5432, 仅 compose 内网)
  外部: Oracle 源库 / PolarDB 目标库 永远在容器外
```

| 形态 | 命令 | 适用 |
|------|------|------|
| 最小栈 | `docker compose up -d` | 快速试用；元数据库用 SQLite |
| + 元数据库 | `docker compose --profile meta-db up -d` | 需要独立 PostgreSQL 存任务元数据 |
| 源库是 Oracle 11g | `APP_TARGET=thick docker compose up -d --build` | 内含 Instant Client；thin 连 11g 报 DPY-3010 |

> 浏览器直接访问 `http://<主机>:8000/` 就是完整应用，前后端同源，不再有 8080 前端容器。
> **纯 HTTP 直连时 `.env` 必须设 `SECURE_SSL_REDIRECT=false`**：`DJANGO_ENV=prod` 下该项默认为 `true`（假定前面有反代终结 TLS），否则首页会被 301 到 `https://`，而没有监听 443 的容器会把浏览器送到死路。

## 二、镜像获取与构建

### 2.1 从镜像仓库拉取（CI 自动构建）

```bash
# GHCR
docker pull ghcr.io/<github用户名>/oracle2polardb_pg:latest          # master 最新(thin)
docker pull ghcr.io/<github用户名>/oracle2polardb_pg:latest-thick    # master 最新(thick)
docker pull ghcr.io/<github用户名>/oracle2polardb_pg:v2.5.0          # 版本标签

# 阿里云 ACR(个人版)——CI 配好 ACR Secrets 后才会同步推到这里
docker pull registry.cn-hangzhou.aliyuncs.com/hayrat/oracle2polardb_pg:latest
docker pull registry.cn-hangzhou.aliyuncs.com/hayrat/oracle2polardb_pg:latest-thick
```

> GHCR 首次使用需在仓库 → Packages 设置可见性 public（或 PAT 登录拉私有镜像）；
> ACR 侧必须先在控制台建好命名空间 `hayrat` 与仓库 `oracle2polardb_pg`，否则推送报 `NAME_UNKNOWN`。

### 2.2 本地构建

```bash
git clone <仓库地址> && cd oracle2polardb_pg
docker build --target thin  -t oracle2polardb_pg:thin  .    # 默认变体
docker build --target thick -t oracle2polardb_pg:thick .    # 需要连 11g 源库时
```

> 不写 `--target` 时 `docker build .` 构建文件里最后一个阶段，即 `thin`。

**体积说明**：后端依赖 `psycopg2-binary`（预编译 wheel），不装 `gcc`/`libpq-dev`；node 只作为多阶段构建的中间层，产物 `dist/` 复制进运行镜像，node 本身不进镜像。`thick` 比 `thin` 大约 +90MB（Instant Client basic RPM 62.8MB 解包出的 .so）。

## 三、docker-compose 一键部署

### 3.1 准备环境变量

```bash
cp .env.example .env && vim .env
```

**生产环境必填项**：

| 变量 | 说明 | 生成方式/示例 |
|------|------|------|
| `DJANGO_SECRET_KEY` | Django 密钥 | `python -c "import secrets;print(secrets.token_urlsafe(50))"` |
| `ALLOWED_HOSTS` | 允许的域名（逗号分隔） | `mg.example.com`（探针已豁免 Host 校验，不必再写 `localhost`） |
| `CORS_ALLOWED_ORIGINS` | 前端域名（逗号分隔） | 合并镜像后同源访问，可留空（仅前后端分离开发时需要） |
| `MIGRATION_FERNET_KEY` | 连接密码加密密钥 | `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"` |
| `REDIS_PASSWORD` | Redis 密码 | 随机串 |
| `DATABASE_URL` | 元数据库 PG 连接 | 启用 meta-db profile 时：`postgres://migration:<META_DB_PASSWORD>@db:5432/migration_meta` |

启用 meta-db profile 时还需：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `META_DB_USER` | `migration` | 元数据库用户 |
| `META_DB_PASSWORD` | `changeme_metadb` | 元数据库密码（务必修改） |

镜像变体（v2.5）：`APP_TARGET`（默认 `thin`）决定 compose 里 `web`/`celery-worker`/`celery-beat` 共用哪个 Dockerfile target，改一处全生效：

```bash
APP_TARGET=thick docker compose up -d --build
```

### 3.2 启动

```bash
# 最小栈
docker compose up -d

# 生产推荐（独立元数据库）
docker compose --profile meta-db up -d

# 源库是 Oracle 11g
APP_TARGET=thick docker compose up -d --build
```

| 服务 | 说明 | 端口 |
|------|------|------|
| `web` | gunicorn 应用，同时提供 Vue SPA 与 REST API（启动时自动 migrate） | 宿主机 8000 |
| `redis` | 缓存与 Celery broker（带密码，仅 compose 内网） | 仅内部 |
| `celery-worker` | 异步任务（增量同步、整库迁移），带存活检查 | — |
| `celery-beat` | 定时调度（每 5 分钟扫描定时增量） | — |
| `db`（可选） | PostgreSQL 16 元数据库，数据持久化在 `meta_db_data` 卷 | 仅内部 |

### 3.3 健康检查与日志

```bash
docker compose ps                       # 服务状态（healthy/unhealthy）
docker compose logs -f web              # 后端日志
curl http://localhost:8000/healthz      # 存活探测
curl http://localhost:8000/readyz       # 就绪探测（含元数据库连通性）
curl -s http://localhost:8000/ | head -3        # SPA 首页（应为 Vue 的 index.html）
```

### 3.4 初始化管理员

```bash
docker compose exec web python manage.py init_admin --username admin --password <密码>
```

### 3.5 升级

```bash
git pull
docker compose build          # 需要换变体时带上 APP_TARGET=thick
docker compose up -d          # 已启用 profile 的照原样加 --profile 参数
```

## 四、镜像变体与可选服务组

### 4.1 thin / thick（决定能不能连老 Oracle）

| target | Oracle 驱动 | 可连源库版本 | 镜像内容 |
|--------|-------------|--------------|----------|
| `thin`（默认） | python-oracledb thin，纯 Python | **12.1 及以上** | 无 Oracle 客户端 |
| `thick` | python-oracledb thick | 11.2 起（含 11.2.0.4） | `/opt/oracle/instantclient_19_32`，已设 `ORACLE_CLIENT_LIB` |

- 切换方式：`docker build --target thick`，或 compose 里 `APP_TARGET=thick`；也可以在运行时用 `ORACLE_CLIENT_LIB` 指向自备的 Instant Client 目录（settings 里该变量非空才切 thick）。
- **thick 变体仅 x86_64**（Oracle 只为 x86_64 发布 19c 客户端 RPM）。arm 机器上运行需要 `--platform linux/amd64` 转译。
- thick 模式有一处实测差异：它**忽略** `connect(tcp_connect_timeout=…)`，超时只认 DSN 里的 `(CONNECT_TIMEOUT=n)(RETRY_COUNT=0)`；平台构造 DSN 时已按此处理。

### 4.2 meta-db

- 提供 PostgreSQL 16 作为元数据库（任务/连接/审计记录）；
- 数据持久化在命名卷 `meta_db_data`，`docker compose down` 不丢失（`down -v` 才删除）；
- `.env` 中 `DATABASE_URL` 指向 `db:5432`（compose 服务名）；
- 已有外部 PG 时不用此 profile，直接把 `DATABASE_URL` 指向外部实例。

## 五、Dockerfile 关键设计

### 5.1 多阶段与两个 target

```
web-builder (node:22-alpine, pnpm 11.17)  ──▶  dist/
                                                        │
base (python:3.12-slim: pip 依赖 + 项目 + dist + collectstatic)
   ├──▶ thick (Instant Client 19.32 + ENV ORACLE_CLIENT_LIB)
   └──▶ thin  (默认；写在文件最后，使不带 target 的 build 得到 thin)
```

### 5.2 构建期 collectstatic 模式切换

`DJANGO_ENV=prod` 下 settings 强制要求 `SECRET_KEY`/`ALLOWED_HOSTS`/`MIGRATION_FERNET_KEY`，构建期没有这些变量。因此构建期用 dev 模式跑 collectstatic（不触发检查），该环境变量仅在该层生效：

```dockerfile
RUN DJANGO_ENV=dev python manage.py collectstatic --noinput
```

compose 的 `web` 启动命令里**不再**跑 collectstatic：镜像内已收集完并生成 WhiteNoise 的 hash 清单，运行时重做是 1900 个文件的重处理（实测约 10s），还与 gunicorn 读清单抢时间。

### 5.3 静态资源：WhiteNoise

Django 的 `static()` 在 `DEBUG=False` 时恒返回空列表（`django/conf/urls/static.py:23`），所以旧生产分支那两行是死代码，`/static/`、`/assets/` 一律 404。现在由 WhiteNoise 承担：

- `whitenoise.middleware.WhiteNoiseMiddleware` 排在 `SecurityMiddleware` 之后、`CommonMiddleware` 之前（否则响应已被 GZip 接管，命中不到文件索引）；
- `WHITENOISE_ROOT = frontend/dist` → Vue 的 `/assets/*.js`、`index.html` 按原路径直出；
- `STORAGES['staticfiles'] = whitenoise.storage.CompressedManifestStaticFilesStorage` → hash 清单 + gzip/brotli 预压缩，容器内可长缓存；
- manifest 存储会校验每个 `url()` 都落在 `STATIC_ROOT` 内，于是 **collectstatic 顺带成了静态资源引用完整性检查**（正是它暴露了 `content.css` 里指向不存在文件的 `@font-face`）。

### 5.4 SPA 深层链接回退

`oracle2polardb_pg/urls.py` 的 `spa_fallback`：生产分支把非真实前缀的 GET/HEAD 一律回退到 `index.html`，支持前端路由直刷；但 `api/admin/static/media/healthz/readyz` 前缀下的未知路径仍返回 404（否则打错的 `/api/xxx` 会被伪装成首页，前端只能看到"200 但 JSON 解析失败"），非 GET/HEAD 返回 405。

### 5.5 安全加固

- 非 root 用户 `appuser`(UID 1000) 运行 gunicorn；
- 内置 `HEALTHCHECK` 探测 `/healthz`；
- `.dockerignore` 排除 `.env`/`.git`/`db.sqlite3`/`.mimosa`/`node_modules`/`docs` 等敏感与冗余内容；
- `thick` 变体在构建期就调用一次 `oracledb.init_oracle_client()` 加载客户端库，缺 `.so` 当场构建失败（DPI-1047），不会把问题留到运行时。

## 六、CI 自动构建与推送

**文件**：[.github/workflows/docker-build.yml](../.github/workflows/docker-build.yml)

- **矩阵**：`thin` 与 `thick` 各构建一次，`thick` 的标签统一加 `-thick` 后缀（于是 `latest` 与 `latest-thick` 并存）；`fail-fast: false`，一个变体失败不影响另一个；
- **触发**：push `master`、push `v*` 标签、手动 workflow_dispatch；
- **标签策略**：master → `latest`(+`-thick`) 与 `master-<sha>`；`v2.5.0` → `v2.5.0` + `2.5`；
- **推送目标与顺序**：先 GHCR 构建并按标签推送 → 用刚推上去的 digest 起真容器做端点冒烟 → 冒烟全绿打 `smoke-<变体>` 标记 → 最后才镜像一份到阿里云 ACR。ACR 这步允许失败（`continue-on-error`），因为凭证填错不该把"镜像到底能不能跑"的证据一起抹掉；
- **无日志权限时怎么判断卡在哪**：失败步骤名会以标签形式落到 GHCR，匿名可查——
  `curl -s -H "Authorization: Bearer $(curl -s 'https://ghcr.io/token?scope=repository:<owner>/<repo>:pull' | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')" https://ghcr.io/<owner>/<repo>/tags/list`。
  出现 `smoke-thin` 表示 thin 镜像真的起来并答对了所有端点；出现 `ci-<sha前8位>-<变体>-<步骤>` 表示该步骤失败（如 `acr-mirror` 就是阿里云凭证问题）；一个标签都没新增则是 GHCR 登录之前的失败；
- **缓存**：`type=gha` 且按 target 分 scope（否则两个变体互相顶掉缓存层）。

**一次性配置**：

1. GitHub 仓库 Settings → Actions → General → Workflow permissions → **Read and write permissions**（GHCR 需要）；
2. 阿里云容器镜像服务控制台：创建命名空间 `hayrat` + 仓库 `oracle2polardb_pg`，并在**访问凭证**里设置**固定密码**（这张固定密码只用于 Docker 登录，和阿里云登录密码是两回事，改它不影响登录控制台）；
3. GitHub 仓库 Settings → Secrets and variables → Actions → 新增仓库 Secrets：

| Secret | 值 |
|--------|----|
| `ALIYUN_REGISTRY_USER` | ACR 的**登录名**（控制台访问凭证页显示的那串，形如 `hayratjan245938`；填命名空间名 `hayrat` 会 401） |
| `ALIYUN_REGISTRY_PASSWORD` | 上面设置的访问凭证固定密码 |

> 口令只进 Secrets，不写进代码、workflow 明文、命令行或日志。注意"能编辑 workflow 的人 ≈ 能读到 Secrets"；若仓库有外部贡献者，改用 Environment + 必需审批人来推送 ACR。

## 七、生产部署架构建议

```
                 ┌──────────────┐
  用户 ── HTTPS ─│  Nginx / 云LB │ ← TLS、域名、访问控制
                 └──────┬───────┘
                        │ HTTP(内网)
                 ┌──────▼───────┐
                 │  web  :8000  │ gunicorn(唯一应用入口, SPA + API 同源)
                 └──┬────────┬──┘
          ┌─────────▼──┐  ┌──▼───────────┐
          │ redis      │  │ worker / beat │
          └────────────┘  └──┬───────────┘
                            │
              ┌─────────────▼──────────────┐
              │ db(元数据库 PG,可外置)       │
              │ Oracle 源库 / PolarDB 目标库  │ ← 永远在容器外
              └────────────────────────────┘
```

**安全清单**：

- [ ] `web` 不直接对公网暴露，前置 Nginx/云 LB 终结 TLS；
- [ ] Redis 保持 `expose`（不映射宿主机端口）；
- [ ] `META_DB_PASSWORD`/`REDIS_PASSWORD` 全部改掉默认值；
- [ ] `ALLOWED_HOSTS` 只列实际域名；经代理转发时确认 `USE_X_FORWARDED_PROTO`/`SECURE_PROXY_SSL_HEADER` 与实际拓扑一致（gunicorn 直接对外时不要信任 `X-Forwarded-Proto`）；
- [ ] 设置 `MIGRATION_FERNET_KEY`，否则 Oracle 连接口令在元数据库里是明文。

## 八、常见问题

### Q1: docker build 报 `RuntimeError: 生产环境必须通过 DJANGO_SECRET_KEY...`

构建期 collectstatic 已用 dev 模式规避。若仍报错，确认 Dockerfile 中 collectstatic 一行为 `RUN DJANGO_ENV=dev python manage.py collectstatic --noinput`。

### Q2: collectstatic 报 `SuspiciousFileOperation` / 引用的文件不存在

WhiteNoise 的 manifest 存储会校验 CSS 里每个 `url()` 都能解析到 `STATIC_ROOT` 内的真实文件。报错路径就是那条死引用——删掉引用（不要换成非 manifest 存储来回避检查）。

### Q3: pip install 失败 / 装到的 Django 和开发机不一致

`requirements.txt` 的版本区间才是镜像里的事实（当前 `django>=4.2,<5.0`）。若开发机用的是更高版本，把 requirements 一起升级，别只改本机环境。

### Q4: GHCR 推送报 `denied: permission_denied`

仓库 Settings → Actions → General → Workflow permissions → 勾选 **Read and write permissions**。

### Q5: 阿里云推送报 `NAME_UNKNOWN` / `denied: requested access to the resource is hidden`

命名空间或仓库没在 ACR 控制台创建；或登录用的是阿里云账号密码而不是"访问凭证固定密码"；或用户名填成了命名空间名（应为 ACR 登录名）；或命名空间为私有且该凭证没有推送权限。

这一步现在排在 GHCR 冒烟之后且允许失败：它红了不影响 `master-<sha>`、`latest`、`smoke-<变体>` 已经推好，修凭证后重跑一次即可。

### Q6: compose up 后 web 启动即崩溃（RuntimeError）

应用服务均有 `env_file: .env`，检查 `.env` 是否填写：`DJANGO_SECRET_KEY`、`ALLOWED_HOSTS`、`MIGRATION_FERNET_KEY`、`REDIS_PASSWORD`。

### Q7: 健康检查失败

```bash
docker compose logs web | tail -50
docker inspect --format '{{json .State.Health}}' <容器> | python -m json.tool
docker compose exec web python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/healthz',timeout=5).status)"
```
常见原因：生产必填变量缺失，或 `DATABASE_URL` 指向的元数据库不可达。

另一个曾出现过的原因是 `ALLOWED_HOSTS`：探针从容器内用 `localhost` 发起，而 Django 会校验 Host 头，
只配真实域名时探针会拿到 400，应用其实healthy。现由
`oracle2polardb_pg/probe_host.py` 对 `/healthz`、`/readyz` 两个固定 JSON 端点改写 Host，
其余路径仍严格校验，因此 `ALLOWED_HOSTS` 不必再加 `localhost`。
若用的是不含本次修复的旧镜像，临时绕法是把 `localhost` 加进 `ALLOWED_HOSTS`。

### Q8: 打开页面 404 / 刷新子路由白屏 / JS 拿不到

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/   # 应为 200
docker compose exec web ls frontend/dist                          # 应有 index.html 与 assets/
```
`/` 与深层路由由 `spa_fallback` 回退到 `index.html`，`/assets/*` 由 WhiteNoise 直出。若 `frontend/dist` 为空，说明镜像不是用 v2.5 的 Dockerfile 构建的（前端阶段没跑，或 `--target` 写成了中间阶段）。

### Q9: 浏览器里前端请求打到 localhost:8000 而不是当前主机

同源部署要求构建时 `VITE_API_BASE_URL` 为空串。`frontend/src/api/client.ts` 现在区分"未定义"（开发，回落 `http://localhost:8000`）与"空串"（同源，走相对路径）；如果你在别处手工设过 `VITE_API_BASE_URL=http://...`，就以那个值为准。

### Q10: thick 变体构建报 `DPI-1047` / 缺 `libaio.so.1`

Instant Client 需要 `libaio`。Debian 新版把包名改成 `libaio1t64`（提供 `libaio.so.1t64`），Dockerfile 里已做"装不到 `libaio1` 就装 `libaio1t64` 并补软链"的处理；另外 thick 阶段用的是 x86_64 RPM，arm 机器构建需 `--platform linux/amd64`。

### Q11: 容器内能连 Oracle 吗？要装 Instant Client 吗？

看源库版本：

- **Oracle 12.1+**：`thin` 即可，纯 Python 直连，只要容器网络能到源库 1521（可 `docker compose exec web python -c "import socket;socket.create_connection(('10.x.x.x',1521),5);print('OK')"` 验证连通性）；
- **Oracle 11.2（本项目实测的 11.2.0.4）**：thin 连不上（`DPY-3010`），必须用 `APP_TARGET=thick`（或 `ORACLE_CLIENT_LIB` 指向自备客户端目录）。

### Q12: celery-worker 连不上 Redis

`.env` 的 `REDIS_PASSWORD` 与 compose 中 `${REDIS_PASSWORD:-changeme_redis}` 一致；broker 地址是 `redis:6379`（compose 服务名），不是 `localhost`。

### Q13: 如何备份数据

```bash
# 元数据库（启用 meta-db 时）
docker compose exec db pg_dump -U migration migration_meta > backup_$(date +%F).sql
# SQLite（未启用 meta-db）: 备份宿主机挂载或 exec 导出 db.sqlite3
docker compose exec web python -c "import shutil;shutil.copy('db.sqlite3','/tmp/backup.sqlite3')" && docker compose cp web:/tmp/backup.sqlite3 ./backup.sqlite3
```
