# Oracle到PolarDB迁移工具

## 项目介绍

Oracle到PolarDB迁移工具是一个专业的数据库迁移解决方案，旨在帮助企业高效、安全地将Oracle数据库迁移到阿里云PolarDB PostgreSQL数据库。

## 核心功能

- **数据结构迁移**：自动转换表、视图、物化视图和存储过程
- **数据迁移**：高效同步数据，支持增量迁移
- **SQLite导出**：支持将Oracle 11g表和视图数据一键导出为本地SQLite文件
- **兼容性检查**：自动识别并解决Oracle与PostgreSQL之间的语法差异
- **迁移监控**：实时监控迁移进度和状态
- **错误诊断**：提供详细的错误报告和修复建议

## 使用流程

1. 配置Oracle源数据库连接
2. 配置PolarDB目标数据库连接
3. 选择需要迁移的对象
4. 创建迁移任务
5. 启动迁移并监控进度

## 技术特点

- 基于Django框架开发
- 支持多任务并行处理
- 使用SimpleUI美化管理界面
- 提供RESTful API接口
- 支持断点续传

## 系统要求

- Python 3.6+
- Oracle客户端库
- PostgreSQL客户端库
- Node.js 18+
- pnpm (推荐) 或 npm

## 前端开发

本项目使用Vue 3 + TypeScript + Vite构建前端界面。

### 安装依赖

**重要：请使用pnpm而不是npm来管理前端依赖**

```bash
cd frontend
pnpm install
```

### 开发模式

```bash
cd frontend
pnpm dev
```

### 构建生产版本

```bash
cd frontend
pnpm build
```

### 为什么使用pnpm？

pnpm比npm更快、更节省磁盘空间，并且能更好地处理依赖关系。本项目统一使用pnpm作为包管理工具。

---

# 后端开发

本项目使用Django 3.2 + Python 3.8构建后端服务。

### 安装依赖

```bash
uv pip install -r requirements.txt
```

### 数据库迁移

```bash
uv run manage.py migrate
```

### 运行开发服务器

```bash
uv run manage.py runserver
```

### 为什么使用Django？

Django是一个功能强大、快速开发的Web框架，非常适合构建RESTful API服务。本项目选择Django作为后端框架，以提供稳定、可靠的服务。

---

© 2025 Oracle到PolarDB迁移工具 | 版权所有 
