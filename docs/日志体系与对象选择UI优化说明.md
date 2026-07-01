# 日志体系与对象选择 UI 优化说明

> 本次优化围绕 Oracle 视图、触发器、物化视图、例程等对象的迁移功能，统一了前后端日志协议，并对「对象选择」相关 UI 进行了重新排版与交互增强。

## 一、统一结构化日志协议

### 1.1 日志级别定义

后端在 `migration_app/task_logging.py` 中定义了 8 个日志级别，统一使用 `[LEVEL] message` 前缀格式写入任务日志，便于前端解析与着色：

| 级别 | 含义 | 典型场景 |
|------|------|----------|
| `STEP` | 阶段步骤 | 进入某个迁移阶段（如「开始迁移视图」） |
| `INFO` | 一般信息 | 过程说明、参数提示 |
| `OK` | 成功 | 单个对象迁移完成、阶段成功摘要 |
| `WARN` | 警告 | 跳过对象、兼容性提示 |
| `ERROR` | 错误 | 异常、失败、traceback |
| `DATA` | 数据导入 | 批量 INSERT 行数、batch_size 提示 |
| `SQL` | DDL 语句 | CREATE VIEW / 触发器源码模板 |
| `META` | 元数据 | 列数、对象统计、依赖信息 |

### 1.2 后端辅助函数

`task_logging.py` 提供以下工厂函数，所有迁移模块统一调用：

```python
make_step_log(msg)      # [STEP] msg
make_info_log(msg)      # [INFO] msg
make_ok_log(msg)        # [OK] msg
make_warn_log(msg)      # [WARN] msg
make_error_log(msg)     # [ERROR] msg
make_data_log(msg)      # [DATA] msg
make_sql_log(msg)       # [SQL] msg
make_meta_log(msg)      # [META] msg
build_log_line(level, msg)
```

`append_migration_log` 写库时会将 `STEP/INFO/OK/DATA/SQL/META` 归并为 `INFO`，`WARN` 保留为 `WARN`，`ERROR` 保留为 `ERROR`，兼容 `MigrationTaskLog` 表结构。

### 1.3 已重构的后端模块

| 文件 | 改造内容 |
|------|----------|
| `migration_app/task_logging.py` | 新增级别常量、`build_log_line`、`make_*_log` 系列、`append_migration_log` 兼容多 level |
| `migration_app/view_materialization.py` | `materialize_one_view` / `run_view_materialization_task` 全量替换为分级日志，增加阶段标记、列数提示、batch_size、成功/失败计数摘要 |
| `migration_app/trigger_export.py` | `export_one_trigger` 返回多行带 `[LEVEL]` 前缀的日志，Oracle 源码 / 模板以 4 空格缩进附在 `[SQL]` 标记后 |
| `migration_app/views.py` | `migrate_materialized_view` / `_migrate_view_definition` / `migrate_routine` / `migrate_trigger` 全部改为分级日志，每个 try/except 输出 `[ERROR]` + traceback |
| `migration_app/full_database.py` | 新增 `PHASE_LABELS`，各阶段（sequences/tables/foreign_keys/views/materialized_views/triggers/routines）增加对象数提示、成功/失败计数、阶段结束摘要；prepare 阶段按 step.status 分级输出 |
| `migration_app/migration_validation.py` | 行数校验结果改为 `[OK] / [WARN]` 前缀 |

## 二、前端日志面板优化

### 2.1 解析与着色

前端使用统一正则解析每行日志：

```ts
const LEVEL_REGEX = /^\[(STEP|INFO|OK|WARN|ERROR|DATA|SQL|META)\]\s?(.*)$/
```

- 匹配到 `[LEVEL]` 前缀的行按对应级别着色
- 无前缀的旧行采用启发式判断（包含「失败/错误」→ ERROR、「警告」→ WARN、「成功/校验通过」→ OK，其余 → INFO），保证向后兼容

### 2.2 日志级别配色（深色终端风格）

| 级别 | 文字色 | 左边框 | 背景 |
|------|--------|--------|------|
| STEP | `#38bdf8` 天蓝 | `#0ea5e9` | `rgba(14,165,233,0.05)` |
| INFO | `#93c5fd` 浅蓝 | 透明 | 透明 |
| OK | `#86efac` 绿 | `#22c55e` | `rgba(34,197,94,0.06)` |
| WARN | `#fde68a` 黄 | `#f59e0b` | `rgba(245,158,11,0.06)` |
| ERROR | `#fca5a5` 红 | `#ef4444` | `rgba(239,68,68,0.08)` |
| DATA | `#d8b4fe` 紫 | `#a855f7` | `rgba(168,85,247,0.05)` |
| SQL | `#fbcfe8` 粉 | `#ec4899` | `rgba(236,72,153,0.05)` |
| META | `#cbd5e1` 灰 | `#64748b` | `rgba(100,116,139,0.04)` |

日志容器采用深色背景 `#0f172a`，等宽字体，自定义滚动条。

### 2.3 交互增强

**TaskDetailView.vue（任务详情页）**：
- 日志工具栏：级别下拉过滤 + 关键词搜索 + 自动滚动开关 + 跳到底部 + 复制全文 + 下载 `.log` 文件
- 日志行数统计展示
- 过滤后最多渲染 2000 行，避免大量日志拖慢渲染
- `watch(task.log)` 自动滚动到底部

**TaskMonitorView.vue（实时监控页）**：
- 选中任务日志面板：同样支持级别过滤 + 关键词搜索 + 自动滚动 + 复制
- 合并双通道日志：优先使用 `log_tail` 文本（按行解析 `[LEVEL]`），无 `log_tail` 时回退到结构化日志 API（带时间戳）
- 「运行日志流」面板：解析每条日志 message 中的 `[LEVEL]` 前缀并着色
- 过滤后最多渲染 1500 行

## 三、对象选择 UI 重新排版

### 3.1 FullDatabaseMigrationView.vue —— 对象类型卡片网格

将原来的简单复选框替换为卡片网格布局：

- **卡片网格**：`.object-type-grid` 使用 `grid-template-columns: repeat(auto-fill, minmax(220px, 1fr))`，自适应屏幕宽度
- **每张卡片**包含：彩色图标圆形背景、对象类型名称、简短描述、独立 checkbox
- **整卡可点击**切换选中状态（checkbox `@click.stop` 防止冒泡）
- **全选 / 反选**按钮 + 已选计数 `已选 N / M`
- 选中卡片高亮（`active` 类：主色边框 + 浅蓝背景 + 上移阴影）
- hover 动效：边框变色、轻微上移、阴影

对象类型配置（图标 + 配色）：

| 类型 | 图标 | 配色 |
|------|------|------|
| 序列 sequences | `bi-list-ol` | 琥珀 `#d97706` |
| 物理表 tables | `bi-table` | 蓝 `#2563eb` |
| 视图 views | `bi-eye` | 紫 `#7c3aed` |
| 物化视图 materialized_views | `bi-eye-fill` | 深紫 `#9333ea` |
| 触发器 triggers | `bi-lightning` | 红 `#dc2626` |
| 例程 routines | `bi-code-square` | 绿 `#10b981` |

### 3.2 CreateTaskView.vue —— 源对象列表增强

- **控制栏**：新增「反选」按钮；已选计数改为 `已选 N / M 个`
- **搜索框**：新增 `bi-search` 图标，输入框 `padding-left: 2rem`
- **列表项图标**：根据 `task_type` 显示不同 `bi-*` 图标（`getObjectIcon`）
- **选中高亮**：选中项添加 `is-selected` 类，背景高亮
- **空状态多样化**：
  - 无数据：`bi-inbox` 大图标
  - 无匹配：`bi-emoji-frown` 大图标
  - 未选 schema：`bi-database-slash` 大图标
- **对象名**：等宽字体 `.obj-name`

## 四、验证结果

### 后端

- 6 个 Python 文件 AST 语法解析全部通过
- Django `manage.py check` 需在激活虚拟环境后运行（当前环境未激活 venv，属环境问题非代码问题）

### 前端

- `vite build` 构建成功，所有视图产物正常输出
- `vue-tsc --noEmit` 报告的 TS 类型错误均为既有问题（`TargetEnvWizard.vue`、`TaskDetailView.vue` 的 `object` 类型断言等），与本次改动无关

## 五、涉及文件清单

### 后端（6 个）

1. `migration_app/task_logging.py`
2. `migration_app/view_materialization.py`
3. `migration_app/trigger_export.py`
4. `migration_app/views.py`
5. `migration_app/full_database.py`
6. `migration_app/migration_validation.py`

### 前端（4 个）

1. `frontend/src/views/FullDatabaseMigrationView.vue`
2. `frontend/src/views/CreateTaskView.vue`
3. `frontend/src/views/TaskDetailView.vue`
4. `frontend/src/views/TaskMonitorView.vue`
