# Oracle到PolarDB-PG迁移平台 - Vue 3 + Django REST Framework

这是一个将Oracle数据库迁移到PolarDB-PG的Web平台，使用Vue 3作为前端，Django REST Framework作为后端。

## 项目结构

```
oracle2polardb_pg/
├── frontend/                 # Vue 3前端项目
│   ├── src/
│   │   ├── api/             # API调用封装
│   │   ├── router/          # Vue Router路由配置
│   │   ├── views/           # Vue页面组件
│   │   ├── App.vue          # 根组件
│   │   └── main.ts          # 入口文件
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── migration_app/           # Django应用
│   ├── api.py              # REST API视图
│   ├── serializers.py      # DRF序列化器
│   ├── models.py          # 数据模型
│   ├── views.py           # 原有视图
│   └── urls.py            # URL配置
└── oracle2polardb_pg/     # Django项目配置
    ├── settings.py         # Django设置
    └── urls.py            # 主URL配置
```

## 后端设置 (Django + REST Framework)

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

依赖包括：
- django
- djangorestframework
- django-cors-headers
- cx-Oracle
- psycopg2-binary

### 2. 配置数据库

默认使用SQLite，如需使用其他数据库，请修改 `oracle2polardb_pg/settings.py` 中的 `DATABASES` 配置。

### 3. 运行数据库迁移

```bash
python manage.py migrate
```

### 4. 创建超级用户（可选）

```bash
python manage.py createsuperuser
```

### 5. 启动Django开发服务器

```bash
python manage.py runserver
```

Django服务器将运行在 `http://localhost:8000`

## 前端设置 (Vue 3)

### 1. 进入前端目录

```bash
cd frontend
```

### 2. 安装依赖

```bash
npm install
```

如果遇到npm缓存权限问题，可以尝试：
```bash
npm cache clean --force
npm install
```

### 3. 启动Vue开发服务器

```bash
npm run dev
```

Vue开发服务器将运行在 `http://localhost:5173`

### 4. 构建生产版本

```bash
npm run build
```

构建后的文件将输出到 `frontend/dist/` 目录

## API端点

### Oracle连接管理
- `GET /api/oracle-connections/` - 获取所有Oracle连接
- `POST /api/oracle-connections/` - 创建Oracle连接
- `GET /api/oracle-connections/{id}/` - 获取单个Oracle连接
- `PUT /api/oracle-connections/{id}/` - 更新Oracle连接
- `DELETE /api/oracle-connections/{id}/` - 删除Oracle连接

### PostgreSQL连接管理
- `GET /api/postgres-connections/` - 获取所有PostgreSQL连接
- `POST /api/postgres-connections/` - 创建PostgreSQL连接
- `GET /api/postgres-connections/{id}/` - 获取单个PostgreSQL连接
- `PUT /api/postgres-connections/{id}/` - 更新PostgreSQL连接
- `DELETE /api/postgres-connections/{id}/` - 删除PostgreSQL连接
- `POST /api/postgres-connections/{id}/test/` - 测试PostgreSQL连接

### 迁移任务管理
- `GET /api/tasks/` - 获取所有任务
- `POST /api/tasks/` - 创建任务
- `GET /api/tasks/{id}/` - 获取单个任务
- `PUT /api/tasks/{id}/` - 更新任务
- `DELETE /api/tasks/{id}/` - 删除任务
- `POST /api/tasks/{id}/start/` - 开始任务
- `POST /api/tasks/{id}/cancel/` - 取消任务
- `GET /api/tasks/{id}/status/` - 获取任务状态
- `GET /api/tasks/{id}/info/` - 获取任务详细信息
- `POST /api/tasks/{id}/switch_database/` - 切换目标数据库

### 数据库查询
- `GET /api/schemas/` - 获取schemas
- `GET /api/database-objects/` - 获取数据库对象
- `GET /api/postgres-databases/` - 获取PostgreSQL数据库列表
- `GET /api/filesystem/directories/` - 浏览文件系统目录
- `GET /api/oracle/schemas/` - 获取Oracle schemas
- `GET /api/oracle/tables/` - 获取Oracle表
- `GET /api/oracle/users/` - 获取Oracle用户
- `GET /api/polardb/schemas/` - 获取PolarDB schemas
- `GET /api/polardb/tables/` - 获取PolarDB表
- `GET /api/polardb/users/` - 获取PolarDB用户

### 系统配置
- `GET /api/config/migration/` - 获取迁移配置
- `GET /api/config/system/` - 获取系统配置
- `GET /api/logs/` - 获取日志
- `GET /api/help/` - 获取帮助文档

## 开发模式

在开发模式下，可以同时运行Django和Vue开发服务器：

1. 终端1：启动Django服务器
```bash
python manage.py runserver
```

2. 终端2：启动Vue开发服务器
```bash
cd frontend
npm run dev
```

访问 `http://localhost:5173` 使用Vue前端，API请求会通过Vite代理转发到Django后端。

## 生产部署

### 1. 构建Vue前端

```bash
cd frontend
npm run build
```

### 2. 收集Django静态文件

```bash
python manage.py collectstatic
```

### 3. 使用生产级Web服务器

使用Gunicorn或uWSGI运行Django：

```bash
pip install gunicorn
gunicorn oracle2polardb_pg.wsgi:application
```

### 4. 配置Nginx（可选）

配置Nginx作为反向代理，同时提供静态文件服务。

## 功能特性

- **数据库连接管理**：管理Oracle和PostgreSQL数据库连接
- **迁移任务管理**：创建、监控和管理数据库迁移任务
- **多种迁移类型**：支持表、视图、物化视图、例程等多种对象迁移
- **实时状态监控**：实时查看任务执行状态和进度
- **冲突处理策略**：提供多种冲突处理策略
- **字段过滤**：支持选择特定字段进行迁移
- **批量迁移**：支持批量迁移多个对象

## 技术栈

### 后端
- Django 5.1
- Django REST Framework
- cx_Oracle (Oracle数据库驱动)
- psycopg2 (PostgreSQL数据库驱动)

### 前端
- Vue 3
- TypeScript
- Vue Router
- Pinia (状态管理)
- Axios (HTTP客户端)
- Bootstrap 5 (UI框架)
- Vite (构建工具)

## 注意事项

1. 确保Oracle客户端库已正确安装和配置
2. 确保PostgreSQL数据库可访问
3. 在生产环境中，请修改 `SECRET_KEY` 并设置 `DEBUG = False`
4. 配置适当的CORS设置以允许前端访问API
5. 使用环境变量管理敏感信息（如数据库密码）

## 故障排除

### npm缓存权限问题
```bash
npm cache clean --force
npm install
```

### Oracle连接问题
确保Oracle Instant Client已正确安装，并在 `settings.py` 中配置正确的库路径。

### PostgreSQL连接问题
确保PostgreSQL服务正在运行，并且连接参数正确。

## 许可证

请查看项目根目录的LICENSE文件。