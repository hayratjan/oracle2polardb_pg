# 前后端路由配置说明

## 路由架构

本项目采用前后端分离架构，前端使用Vue Router，后端使用Django REST Framework。

### 开发环境

- **前端**: Vue开发服务器运行在 `http://localhost:5173`
- **后端**: Django服务器运行在 `http://localhost:8000`
- **API**: 所有API请求通过Vite代理转发到Django后端

### 生产环境

- **前端**: Vue构建后的静态文件由Django提供
- **后端**: Django服务器同时提供API和静态文件服务

## 后端路由 (Django)

### 主路由配置 (`oracle2polardb_pg/urls.py`)

```
http://localhost:8000/
├── admin/                    # Django管理后台
├── api/                     # REST API路由
│   ├── oracle-connections/    # Oracle连接管理
│   ├── postgres-connections/  # PostgreSQL连接管理
│   ├── tasks/                # 迁移任务管理
│   ├── schemas/              # Schema查询
│   ├── database-objects/     # 数据库对象查询
│   ├── postgres-databases/   # PostgreSQL数据库列表
│   ├── filesystem/directories/ # 文件系统浏览
│   ├── database-info/        # 数据库信息
│   ├── oracle/              # Oracle相关API
│   │   ├── schemas/
│   │   ├── tables/
│   │   ├── users/
│   │   ├── test-connection/
│   │   ├── save-connection/
│   │   └── delete-connection/
│   ├── polardb/             # PolarDB相关API
│   │   ├── schemas/
│   │   ├── tables/
│   │   └── users/
│   ├── postgres/             # PostgreSQL连接API
│   │   ├── test-connection/
│   │   ├── save-connection/
│   │   ├── delete-connection/
│   │   └── edit-connection/
│   ├── config/              # 配置API
│   │   ├── migration/
│   │   └── system/
│   ├── logs/                # 日志API
│   └── help/               # 帮助文档
└── (开发环境重定向到Vue开发服务器)
```

### 应用路由配置 (`migration_app/urls.py`)

**重要说明**: 
- 主 `urls.py` 中已经配置了 `path('api/', include('migration_app.urls'))`
- 因此在 `migration_app/urls.py` 中不需要再加 `api/` 前缀
- router注册时使用相对路径，如 `r'oracle-connections'` 而不是 `r'api/oracle-connections'`

所有API路由统一使用 `/api/` 前缀，确保前后端分离清晰。

#### REST API ViewSets (自动生成的路由)

- `GET /api/oracle-connections/` - 获取Oracle连接列表
- `POST /api/oracle-connections/` - 创建Oracle连接
- `GET /api/oracle-connections/{id}/` - 获取单个Oracle连接
- `PUT /api/oracle-connections/{id}/` - 更新Oracle连接
- `DELETE /api/oracle-connections/{id}/` - 删除Oracle连接

- `GET /api/postgres-connections/` - 获取PostgreSQL连接列表
- `POST /api/postgres-connections/` - 创建PostgreSQL连接
- `GET /api/postgres-connections/{id}/` - 获取单个PostgreSQL连接
- `PUT /api/postgres-connections/{id}/` - 更新PostgreSQL连接
- `DELETE /api/postgres-connections/{id}/` - 删除PostgreSQL连接

- `GET /api/tasks/` - 获取任务列表
- `POST /api/tasks/` - 创建任务
- `GET /api/tasks/{id}/` - 获取单个任务
- `PUT /api/tasks/{id}/` - 更新任务
- `DELETE /api/tasks/{id}/` - 删除任务
- `POST /api/tasks/{id}/start/` - 开始任务
- `POST /api/tasks/{id}/cancel/` - 取消任务
- `GET /api/tasks/{id}/status/` - 获取任务状态
- `GET /api/tasks/{id}/info/` - 获取任务详情
- `POST /api/tasks/{id}/switch_database/` - 切换目标数据库

#### 自定义API端点

- `GET /api/schemas/` - 获取schemas
- `GET /api/database-objects/` - 获取数据库对象
- `GET /api/postgres-databases/` - 获取PostgreSQL数据库列表
- `GET /api/filesystem/directories/` - 浏览文件系统目录
- `GET /api/database-info/` - 获取数据库信息
- `GET /api/oracle/schemas/` - 获取Oracle schemas
- `GET /api/oracle/tables/` - 获取Oracle表
- `GET /api/oracle/users/` - 获取Oracle用户
- `POST /api/oracle/test-connection/` - 测试Oracle连接
- `POST /api/oracle/save-connection/` - 保存Oracle连接
- `POST /api/oracle/delete-connection/` - 删除Oracle连接
- `GET /api/polardb/schemas/` - 获取PolarDB schemas
- `GET /api/polardb/tables/` - 获取PolarDB表
- `GET /api/polardb/users/` - 获取PolarDB用户
- `POST /api/postgres/test-connection/` - 测试PostgreSQL连接
- `POST /api/postgres/save-connection/` - 保存PostgreSQL连接
- `POST /api/postgres/delete-connection/` - 删除PostgreSQL连接
- `POST /api/postgres/edit-connection/` - 编辑PostgreSQL连接
- `GET /api/config/migration/` - 获取迁移配置
- `GET /api/config/system/` - 获取系统配置
- `GET /api/logs/` - 获取日志
- `GET /api/help/` - 获取帮助文档
- `POST /api/create-task/` - 创建任务（带验证）

#### 旧的HTML视图路由（向后兼容）

旧的HTML模板路由保留在 `/app/` 路径下，用于向后兼容：

- `/app/` - 仪表板
- `/app/tasks/` - 任务列表
- `/app/task/create/` - 创建任务
- 等等...

## 前端路由 (Vue Router)

### 路由配置 (`frontend/src/router/index.ts`)

```
http://localhost:5173/
├── /                    # 首页 (HomeView)
├── /tasks               # 任务列表 (TaskListView)
├── /task/create         # 创建任务 (CreateTaskView)
├── /task/:id           # 任务详情 (TaskDetailView)
├── /oracle             # Oracle数据库管理 (OracleDatabaseView)
├── /postgres           # PostgreSQL数据库管理 (PostgresDatabaseView)
└── /config             # 系统配置 (ConfigView)
```

### 路由详情

| 路径 | 名称 | 组件 | 说明 |
|------|------|------|------|
| `/` | Home | HomeView | 首页，显示最近任务和连接统计 |
| `/tasks` | TaskList | TaskListView | 任务列表，显示所有迁移任务 |
| `/task/create` | CreateTask | CreateTaskView | 创建新任务 |
| `/task/:id` | TaskDetail | TaskDetailView | 任务详情，显示任务信息和日志 |
| `/oracle` | OracleDatabase | OracleDatabaseView | Oracle数据库连接管理 |
| `/postgres` | PostgresDatabase | PostgresDatabaseView | PostgreSQL数据库连接管理 |
| `/config` | Config | ConfigView | 系统配置和日志 |

## API调用配置

### API客户端配置 (`frontend/src/api/client.ts`)

```typescript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})
```

### 环境变量 (`.env`)

```bash
VITE_API_BASE_URL=http://localhost:8000
```

### Vite代理配置 (`vite.config.ts`)

```typescript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## 开发流程

### 1. 启动后端

```bash
python manage.py runserver
```

Django服务器运行在 `http://localhost:8000`

### 2. 启动前端

```bash
cd frontend
npm run dev
```

Vue开发服务器运行在 `http://localhost:5173`

### 3. 访问应用

- 前端应用: `http://localhost:5173`
- API文档: `http://localhost:8000/api/`
- Django管理: `http://localhost:8000/admin/`

### 4. API请求流程

1. 前端在 `http://localhost:5173` 发起API请求
2. Vite代理拦截 `/api/*` 请求
3. 代理转发到 `http://localhost:8000/api/*`
4. Django处理请求并返回JSON响应
5. 前端接收响应并更新UI

## 生产部署

### 1. 构建前端

```bash
cd frontend
npm run build
```

构建文件输出到 `frontend/dist/`

### 2. 收集静态文件

```bash
python manage.py collectstatic
```

### 3. 配置生产环境

在 `settings.py` 中设置：

```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']
```

### 4. 运行生产服务器

```bash
gunicorn oracle2polardb_pg.wsgi:application
```

### 5. 访问应用

- 前端应用: `http://yourdomain.com/`
- API: `http://yourdomain.com/api/`
- Django管理: `http://yourdomain.com/admin/`

## 路由设计原则

### 后端路由原则

1. **统一前缀**: 所有API使用 `/api/` 前缀
2. **RESTful设计**: 使用标准HTTP方法（GET, POST, PUT, DELETE）
3. **资源命名**: 使用复数形式（如 `tasks`, `connections`）
4. **嵌套路由**: 子资源使用路径参数（如 `/tasks/{id}/start/`）

### 前端路由原则

1. **语义化**: 路径清晰表达页面功能
2. **参数化**: 使用动态参数（如 `/task/:id`）
3. **懒加载**: 使用动态导入优化加载性能
4. **用户友好**: 路径简洁易记

## 常见问题

### Q: 开发环境如何避免CORS问题？

A: Vite代理会自动处理CORS，API请求通过代理转发到后端。

### Q: 生产环境如何部署？

A: 构建Vue前端后，Django会提供静态文件服务，无需单独部署前端服务器。

### Q: 如何添加新的API端点？

A: 
1. 在 `migration_app/api.py` 中添加新的APIView或ViewSet
2. 在 `migration_app/urls.py` 中注册路由
3. 在 `frontend/src/api/index.ts` 中添加对应的API调用函数

### Q: 如何添加新的前端页面？

A:
1. 在 `frontend/src/views/` 中创建新的Vue组件
2. 在 `frontend/src/router/index.ts` 中添加路由配置
3. 在导航菜单中添加链接

## 相关文件

- 后端主路由: `oracle2polardb_pg/urls.py`
- 应用路由: `migration_app/urls.py`
- 前端路由: `frontend/src/router/index.ts`
- API客户端: `frontend/src/api/client.ts`
- API封装: `frontend/src/api/index.ts`
- Vite配置: `frontend/vite.config.ts`
- Django设置: `oracle2polardb_pg/settings.py`