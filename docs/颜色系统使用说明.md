# 全局颜色系统使用说明

## 概述

本系统提供了一套完整的企业级颜色主题系统，支持多种主题切换，色彩设计遵循简洁、专业的视觉风格，适合企业级应用。

## 颜色系统架构

### 1. 主题色彩体系

系统包含以下核心色彩定义：

#### 主要颜色变量
- `--primary`: 主要颜色（按钮、链接等）
- `--primary-hover`: 主要颜色悬停状态
- `--secondary`: 次要颜色
- `--accent`: 强调色

#### 背景与表面颜色
- `--background`: 页面背景色
- `--surface`: 卡片、面板等表面颜色
- `--input-background`: 输入框背景色

#### 字体颜色
- `--text`: 主要文本颜色
- `--text-muted`: 次要文本颜色

#### 边框与分割线
- `--border`: 边框颜色
- `--divider`: 分割线颜色
- `--input-border`: 输入框边框颜色
- `--card-border`: 卡片边框颜色

#### 状态颜色
- `--success`: 成功状态（绿色）
- `--danger`: 危险状态（红色）
- `--warning`: 警告状态（橙色）
- `--info`: 信息状态（蓝色）

#### 渐变色
- `--gradient`: 主渐变色
- `--gradient-secondary`: 次渐变色

#### 阴影与遮罩
- `--shadow`: 阴影颜色
- `--shadow-light`: 轻阴影颜色
- `--overlay`: 遮罩层颜色

#### 表格颜色
- `--table-header`: 表头颜色
- `--table-row-hover`: 表格行悬停颜色

#### 链接颜色
- `--link`: 链接颜色
- `--link-hover`: 链接悬停颜色

### 2. 可用主题

系统提供7种企业级主题：

| 主题名称 | 显示名称 | 主色调 | 适用场景 |
|---------|---------|-------|---------|
| default | 默认蓝 | #667eea | 通用场景 |
| ocean | 海洋蓝 | #0ea5e9 | 科技、互联网 |
| forest | 森林绿 | #10b981 | 环保、健康 |
| sunset | 日落橙 | #f97316 | 活力、创意 |
| purple | 皇家紫 | #8b5cf6 | 高端、专业 |
| rose | 玫瑰红 | #e11d48 | 时尚、电商 |
| dark | 暗夜黑 | #6366f1 | 深色模式 |

## 使用方法

### 1. 在CSS中使用颜色变量

```css
/* 直接使用CSS变量 */
.my-component {
  background-color: var(--primary);
  color: var(--text);
  border: 1px solid var(--border);
}

/* 使用渐变 */
.gradient-button {
  background: var(--gradient);
}

/* 使用阴影 */
.card {
  box-shadow: 0 4px 12px var(--shadow);
}
```

### 2. 在Vue组件中使用

```vue
<template>
  <div class="my-component">
    <button class="btn btn-primary">主要按钮</button>
    <div class="card">
      <h3>卡片标题</h3>
      <p>卡片内容</p>
    </div>
  </div>
</template>

<style scoped>
.my-component {
  background: var(--background);
  color: var(--text);
}

.card {
  background: var(--surface);
  border: 1px solid var(--card-border);
  box-shadow: 0 4px 12px var(--shadow);
}
</style>
```

### 3. 在TypeScript中使用主题配置

```typescript
import { themes, getTheme, type Theme } from '@/config/themes'

// 获取当前主题
const currentTheme = getTheme('default')

// 使用主题颜色
const primaryColor = currentTheme.primary
const backgroundColor = currentTheme.background

// 遍历所有主题
Object.values(themes).forEach((theme: Theme) => {
  console.log(theme.name, theme.primary)
})
```

### 4. 主题切换

系统已集成 `ThemeSwitcher` 组件，可以在导航栏中直接切换主题。

#### 手动切换主题

```typescript
// 在组件中切换主题
const changeTheme = (themeName: string) => {
  localStorage.setItem('theme', themeName)
  document.documentElement.setAttribute('data-theme', themeName)
}

// 切换到海洋蓝主题
changeTheme('ocean')
```

## 继承与自定义

### 1. 继承现有主题

```typescript
// 在 themes.ts 中添加新主题
export const themes: Record<string, Theme> = {
  // 现有主题...
  
  // 自定义主题
  custom: {
    name: 'custom',
    displayName: '自定义主题',
    primary: '#your-primary-color',
    primaryHover: '#your-hover-color',
    // ... 其他颜色定义
  }
}
```

### 2. 覆盖特定颜色

```css
/* 在全局样式或组件样式中覆盖特定颜色 */
:root {
  --primary: #custom-color;
}

/* 或者为特定主题覆盖 */
[data-theme="default"] {
  --primary: #custom-blue;
}
```

### 3. 创建主题变体

```css
/* 基于现有主题创建变体 */
[data-theme="default-variant"] {
  --primary: #667eea;
  --background: #ffffff;
  /* 继承其他默认主题的颜色 */
}

/* 使用CSS变量继承 */
[data-theme="default-variant"] {
  --success: var(--success);
  --danger: var(--danger);
}
```

## Bootstrap 集成

### 1. 安装Bootstrap

```bash
pnpm add bootstrap
```

### 2. 引入Bootstrap

在 `main.ts` 中已引入：

```typescript
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'
```

### 3. 使用Bootstrap组件

```vue
<template>
  <div class="container">
    <!-- 使用Bootstrap网格系统 -->
    <div class="row">
      <div class="col-md-6">
        <div class="card">
          <div class="card-header">
            卡片标题
          </div>
          <div class="card-body">
            <p>卡片内容</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 使用Bootstrap按钮 -->
    <button class="btn btn-primary">主要按钮</button>
    <button class="btn btn-outline-secondary">次要按钮</button>
    
    <!-- 使用Bootstrap表单 -->
    <form>
      <div class="mb-3">
        <label class="form-label">用户名</label>
        <input type="text" class="form-control" placeholder="请输入用户名">
      </div>
    </form>
  </div>
</template>
```

### 4. Bootstrap与主题系统集成

Bootstrap组件会自动使用主题颜色变量：

```css
/* Bootstrap组件使用主题颜色 */
.btn-primary {
  background: var(--gradient);
  border: none;
}

.form-control {
  background: var(--input-background);
  border-color: var(--input-border);
  color: var(--text);
}

.card {
  background: var(--surface);
  border-color: var(--card-border);
}
```

## Bootstrap Icons 使用

### 1. 安装Bootstrap Icons

```bash
pnpm add bootstrap-icons
```

### 2. 引入Bootstrap Icons

在 `main.ts` 中已引入：

```typescript
import 'bootstrap-icons/font/bootstrap-icons.css'
```

### 3. 使用图标

#### 在HTML中使用

```html
<i class="bi bi-house-door"></i>
<i class="bi bi-person"></i>
<i class="bi bi-gear"></i>
```

#### 在Vue组件中使用

```vue
<template>
  <div>
    <button class="btn btn-primary">
      <i class="bi bi-plus-circle me-2"></i>
      新建任务
    </button>
    
    <nav class="nav">
      <a class="nav-link" href="#">
        <i class="bi bi-house-door me-1"></i>
        首页
      </a>
    </nav>
  </div>
</template>
```

#### 常用图标示例

| 图标类名 | 说明 |
|---------|------|
| bi-house-door | 首页 |
| bi-list-task | 任务列表 |
| bi-plus-circle | 添加 |
| bi-database-gear | 数据库配置 |
| bi-server | 服务器 |
| bi-gear | 设置 |
| bi-person | 用户 |
| bi-box-arrow-right | 登出 |
| bi-check-circle | 成功 |
| bi-exclamation-triangle | 警告 |
| bi-info-circle | 信息 |
| bi-x-circle | 错误 |

更多图标请参考：[Bootstrap Icons 官方文档](https://icons.getbootstrap.com/)

## pnpm 使用指南

### 1. 安装pnpm

```bash
npm install -g pnpm
```

### 2. 安装项目依赖

```bash
cd frontend
pnpm install
```

### 3. 常用命令

```bash
# 启动开发服务器
pnpm dev

# 构建生产版本
pnpm build

# 预览生产构建
pnpm preview

# 添加依赖
pnpm add package-name

# 添加开发依赖
pnpm add -D package-name

# 移除依赖
pnpm remove package-name

# 更新依赖
pnpm update

# 清理缓存
pnpm store prune
```

### 4. pnpm配置

在项目根目录的 `.npmrc` 文件中配置：

```ini
# 使用淘宝镜像
registry=https://registry.npmmirror.com

# 严格对等依赖
strict-peer-dependencies=false

# 自动安装对等依赖
auto-install-peers=true
```

### 5. 工作空间（Workspace）使用

如果项目使用monorepo结构：

```json
{
  "name": "oracle2polardb-pg",
  "private": true,
  "workspaces": [
    "frontend",
    "packages/*"
  ]
}
```

## Python uv 环境使用

### 1. 安装uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 创建虚拟环境

```bash
# 在项目根目录
uv venv

# 或指定Python版本
uv venv --python 3.11
```

### 3. 激活虚拟环境

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 4. 安装依赖

```bash
# 从requirements.txt安装
uv pip install -r requirements.txt

# 从pyproject.toml安装
uv pip install -e .

# 安装单个包
uv pip install package-name
```

### 5. 运行Django项目

```bash
# 数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver

# 指定端口
python manage.py runserver 8000
```

### 6. Django管理命令

```bash
# 创建应用
python manage.py startapp app_name

# 收集静态文件
python manage.py collectstatic

# Django Shell
python manage.py shell

# 检查项目
python manage.py check

# 创建迁移文件
python manage.py makemigrations

# 应用迁移
python manage.py migrate

# 查看迁移状态
python manage.py showmigrations
```

### 7. uv常用命令

```bash
# 列出已安装的包
uv pip list

# 冻结依赖
uv pip freeze > requirements.txt

# 升级包
uv pip install --upgrade package-name

# 卸载包
uv pip uninstall package-name

# 查看包信息
uv pip show package-name

# 清理缓存
uv cache clean
```

## 项目启动完整流程

### 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
pnpm install

# 3. 启动开发服务器
pnpm dev
```

### 后端启动

```bash
# 1. 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate  # Windows

# 2. 安装依赖
uv pip install -r requirements.txt

# 3. 数据库迁移
python manage.py migrate

# 4. 启动开发服务器
python manage.py runserver
```

### 同时启动前后端

使用两个终端窗口：

**终端1 - 后端：**
```bash
source .venv/bin/activate
python manage.py runserver
```

**终端2 - 前端：**
```bash
cd frontend
pnpm dev
```

## 最佳实践

### 1. 颜色使用建议

- **主要操作**：使用 `--primary` 和 `--gradient`
- **次要操作**：使用 `--secondary` 和 `--gradient-secondary`
- **成功状态**：使用 `--success`
- **危险操作**：使用 `--danger`
- **警告提示**：使用 `--warning`
- **信息展示**：使用 `--info`

### 2. 主题切换建议

- 为用户提供主题选择器（如 `ThemeSwitcher` 组件）
- 保存用户主题偏好到 `localStorage`
- 根据系统主题自动切换（深色/浅色模式）

### 3. 性能优化

- 使用CSS变量而非JavaScript动态修改样式
- 避免频繁切换主题
- 使用CSS过渡效果实现平滑切换

### 4. 可访问性

- 确保颜色对比度符合WCAG标准
- 为色盲用户提供足够的视觉区分
- 不要仅依赖颜色传达信息

## 故障排除

### 1. 主题不生效

- 检查是否正确引入 `global.css`
- 确认 `data-theme` 属性是否设置
- 清除浏览器缓存

### 2. Bootstrap样式冲突

- 检查样式引入顺序
- 使用 `!important` 覆盖（谨慎使用）
- 使用更具体的选择器

### 3. 图标不显示

- 确认已安装 `bootstrap-icons`
- 检查CSS文件是否正确引入
- 验证图标类名是否正确

### 4. pnpm安装失败

- 清理pnpm缓存：`pnpm store prune`
- 检查网络连接
- 尝试切换npm镜像源

### 5. uv环境问题

- 重新创建虚拟环境：`uv venv --force`
- 检查Python版本兼容性
- 清理uv缓存：`uv cache clean`

## 参考资源

- [Bootstrap 5 文档](https://getbootstrap.com/docs/5.3/)
- [Bootstrap Icons](https://icons.getbootstrap.com/)
- [pnpm 文档](https://pnpm.io/)
- [uv 文档](https://github.com/astral-sh/uv)
- [Vue 3 文档](https://vuejs.org/)
- [TypeScript 文档](https://www.typescriptlang.org/)

## 更新日志

### v1.0.0 (2025-01-26)
- 初始版本发布
- 支持7种企业级主题
- 完整的颜色变量系统
- Bootstrap 5 集成
- Bootstrap Icons 支持
- 主题切换功能
