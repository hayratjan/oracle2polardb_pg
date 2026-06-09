<!-- 文档版本：v2 · 企业级迁移平台 -->
<h1 align="center">Oracle 至 PolarDB PostgreSQL</h1>
<h3 align="center">企业级数据库迁移与同步平台</h3>

<p align="center">
  <img src="https://img.shields.io/badge/版本-v2.0-2563EB?style=for-the-badge" alt="Version" />
  <img src="https://img.shields.io/badge/状态-生产可用-22C55E?style=for-the-badge" alt="Status" />
  <img src="https://img.shields.io/badge/许可-专有-64748B?style=for-the-badge" alt="License" />
</p>

<p align="center">
  <strong>一站式上云 · 表级精迁 · 整库编排 · 目标环境自动就绪</strong>
</p>

<p align="center">
  <sub>将 Oracle 11g+ 的结构与数据，安全、可控地迁移至 PolarDB PostgreSQL · 支持增量同步与断点续传</sub>
</p>

<br/>

<p align="center">
  <a href="#-快速开始"><img src="https://img.shields.io/badge/快速开始-立即上手-2563EB?style=flat-square" alt="快速开始" /></a>
  &nbsp;
  <a href="#-亮点功能--v2"><img src="https://img.shields.io/badge/新功能-v2_亮点-7C3AED?style=flat-square" alt="v2 亮点" /></a>
  &nbsp;
  <a href="#-系统架构"><img src="https://img.shields.io/badge/架构-技术全景-0891B2?style=flat-square" alt="系统架构" /></a>
  &nbsp;
  <a href="docs/文档索引.md"><img src="https://img.shields.io/badge/文档-完整索引-64748B?style=flat-square" alt="文档索引" /></a>
</p>

<br/>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/Vue_3-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Oracle-11g%2B-F80000?style=flat-square&logo=oracle&logoColor=white" alt="Oracle" />
  <img src="https://img.shields.io/badge/PolarDB_PG-v15-336791?style=flat-square&logo=postgresql&logoColor=white" alt="PolarDB" />
  <img src="https://img.shields.io/badge/Celery_Beat-增量同步-37814A?style=flat-square&logo=celery&logoColor=white" alt="Celery" />
  <img src="https://img.shields.io/badge/断点续传-支持-2563EB?style=flat-square" alt="Resume" />
  <img src="https://img.shields.io/badge/JWT-安全认证-DC2626?style=flat-square" alt="JWT" />
</p>

<br/>

<!-- 核心能力速览卡片 -->
<table align="center">
  <tr>
    <td align="center" width="25%">
      <h4>📋 表级迁移向导</h4>
      <sub>按表勾选 · 增量同步 · 目标环境配置</sub>
    </td>
    <td align="center" width="25%">
      <h4>☁️ 整库一键迁移</h4>
      <sub>多 Schema · 全对象编排 · 阶段进度</sub>
    </td>
    <td align="center" width="25%">
      <h4>🛠 目标环境 DDL</h4>
      <sub>建库 · 表空间 · 用户 · Schema</sub>
    </td>
    <td align="center" width="25%">
      <h4>📡 实时监控</h4>
      <sub>进度轮询 · 日志审计 · 主键对比</sub>
    </td>
  </tr>
</table>

<br/>

<!-- 平台核心指标 -->
<table align="center">
  <tr>
    <td align="center"><strong>11+</strong><br/><sub>迁移对象类型</sub></td>
    <td align="center"><strong>5</strong><br/><sub>表级向导步骤</sub></td>
    <td align="center"><strong>6</strong><br/><sub>整库编排阶段</sub></td>
    <td align="center"><strong>3</strong><br/><sub>增量同步模式</sub></td>
    <td align="center"><strong>∞</strong><br/><sub>断点续传支持</sub></td>
  </tr>
</table>

<br/>

---

## 📋 目录

> [!TIP]
> 建议首次阅读顺序：**产品概述** → **亮点功能 v2** → **快速开始** → **使用手册**

<details open>
<summary><b>📂 展开完整导航</b></summary>

<br/>

| 章节 | 说明 |
|:-----|:-----|
| [🎯 产品概述](#-产品概述) | 平台定位与核心能力矩阵 |
| [✨ 亮点功能 · v2](#-亮点功能--v2) | 表级向导 · 整库编排 · 目标环境 DDL |
| [📌 适用场景与版本](#-适用场景与版本) | 源端/目标端版本与典型场景 |
| [✨ 核心功能矩阵](#-核心功能矩阵) | 连接、对象、策略、可观测性 |
| [🏗 系统架构](#-系统架构) | 前后端分层与数据流 |
| [🗺 导航与路由地图](#-导航与路由地图) | 菜单与路由对照表 |
| [🚀 快速开始](#-快速开始) | 环境要求与一键启动 |
| [📖 使用手册](#-使用手册) | 三条上手路径与策略速查 |
| [🔌 API 速查](#-api-速查--新增) | v2 新增 REST 端点 |
| [🔧 开发指南](#-开发指南) | 技术栈与关键模块 |
| [📚 文档与支持](#-文档与支持) | 子文档索引 |
| [📄 许可证](#-许可证) | 版权信息 |

</details>

---

## 🎯 产品概述

**Oracle 到 PolarDB PostgreSQL 迁移平台** 是一套面向企业级场景的数据库迁移与数据同步解决方案。帮助客户将 Oracle 11g 及更高版本的结构与数据，安全、可控地迁移至阿里云 PolarDB PostgreSQL 兼容引擎，并支持**任务编排、目标环境预置、增量同步、断点续传**与全链路可观测。

```mermaid
flowchart TB
  R(("迁移平台"))
  R --> L1["连接层"]
  R --> L2["迁移层"]
  R --> L3["目标层"]
  R --> L4["运维层"]
  L1 --> L1A["甲骨文多源连接"]
  L1 --> L1B["云数据库多目标连接"]
  L1 --> L1C["连接健康检查"]
  L2 --> L2A["表级精迁向导"]
  L2 --> L2B["整库一键编排"]
  L2 --> L2C["单对象任务创建"]
  L3 --> L3A["选择已有库与模式"]
  L3 --> L3B["自动建库"]
  L3 --> L3C["自动建用户与模式"]
  L3 --> L3D["表空间管理"]
  L4 --> L4A["实时进度"]
  L4 --> L4B["结构化日志"]
  L4 --> L4C["断点续传"]
  L4 --> L4D["定时增量同步"]
```

<br/>

<table>
  <thead>
    <tr>
      <th align="center" width="18%">能力维度</th>
      <th>说明</th>
      <th align="center" width="12%">成熟度</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align="center"><strong>一站式</strong></td>
      <td>连接配置 → 对象选择 → 目标就绪 → 执行监控，全流程 Web 化</td>
      <td align="center">✅ 生产</td>
    </tr>
    <tr>
      <td align="center"><strong>可编排</strong></td>
      <td>单表、多表、整 Schema、<strong>整实例多 Schema</strong> 多粒度迁移</td>
      <td align="center">✅ 生产</td>
    </tr>
    <tr>
      <td align="center"><strong>可增量</strong></td>
      <td>水位列追加、主键对齐定时增删，配合 Celery Beat</td>
      <td align="center">✅ 生产</td>
    </tr>
    <tr>
      <td align="center"><strong>可观测</strong></td>
      <td>任务/对象/阶段三级进度，日志审计与失败诊断</td>
      <td align="center">✅ 生产</td>
    </tr>
    <tr>
      <td align="center"><strong>可续传</strong></td>
      <td>大表、多表、整库编排均支持断点恢复</td>
      <td align="center">✅ 生产</td>
    </tr>
  </tbody>
</table>

---

## ✨ 亮点功能 · v2

> [!IMPORTANT]
> 本版本重点交付：**表级迁移向导** · **整库一键迁移** · **PolarDB 目标环境 DDL 自动就绪**

<br/>

<table>
  <tr>
    <td width="33%" valign="top">
      <h4>📋 表级迁移向导</h4>
      <code>/task/table-migrate</code><br/><br/>
      五步向导收敛选表、配目标、定增量，适合核心业务表分批上云。
    </td>
    <td width="33%" valign="top">
      <h4>☁️ 整库一键迁移</h4>
      <code>/migration/full-database</code><br/><br/>
      自动发现多 Schema，按依赖顺序编排序列→表→视图→例程。
    </td>
    <td width="33%" valign="top">
      <h4>🛠 目标环境 DDL</h4>
      <code>TargetEnvWizard</code><br/><br/>
      Web 端一键建库/表空间/用户/Schema，无需反复登录控制台。
    </td>
  </tr>
</table>

<br/>

### 📋 表级迁移向导

**入口**：侧边栏 `迁移管理 → 表级迁移` · 路由 `/task/table-migrate`

五步向导，将「选表 + 配目标 + 定增量」收敛为一条清晰路径：

```mermaid
flowchart TB
  S1["步骤一 源端配置"]
  S2["步骤二 选择数据表"]
  S3["步骤三 目标环境"]
  S4["步骤四 增量策略"]
  S5["步骤五 确认提交"]
  S1 --> S2 --> S3 --> S4 --> S5
```

| 步骤 | 能力 | 说明 |
|:----:|:-----|:-----|
| ① | 源端 | 选择 Oracle 连接与 Schema，自动加载表列表 |
| ② | 选表 | 仅 `TABLE` 类型，支持搜索、全选、批量勾选 |
| ③ | 目标 | 复用 `TargetEnvWizard`：选已有或**新建**库/表空间/用户/Schema |
| ④ | 增量 | `none` 全量 · `timestamp` 水位列 · `pk_mirror` 主键对齐 + 定时 |
| ⑤ | 提交 | 可选 `prepare_target` 先执行 DDL，再创建 `table` 类型任务 |

> [!NOTE]
> **典型场景**：核心业务表分批上云、按表增量同步、目标库尚未在 PolarDB 控制台手工创建。

---

### ☁️ 整库一键迁移

**入口**：侧边栏 `迁移管理 → 整库一键迁移` · 路由 `/migration/full-database`

单 Oracle 连接下，自动发现全部非系统 Schema，按依赖顺序编排迁移：

```mermaid
flowchart TB
  subgraph discover ["发现阶段"]
    D1["扫描用户列表"]
    D2["统计各类对象数量"]
    D3["源模式与目标模式映射"]
  end
  subgraph prepare ["准备阶段"]
    P1["创建数据库"]
    P2["创建表空间"]
    P3["创建用户与模式"]
    P4["执行授权"]
  end
  subgraph migrate ["迁移阶段"]
    M1["序列"]
    M2["物理表"]
    M3["视图"]
    M4["物化视图"]
    M5["触发器导出"]
    M6["例程"]
  end
  D3 --> P1
  P4 --> M1
  M1 --> M2 --> M3 --> M4 --> M5 --> M6
```

| 编排阶段 | 行为 | 续传 |
|:--------:|:-----|:----:|
| 准备环境 | 按向导配置自动建库/用户/Schema | — |
| 序列 | 全 Schema 序列先行创建 | ✅ |
| 物理表 | 逐 Schema、逐表结构+数据迁移 | ✅ |
| 视图 | 定义或物化（复用现有 `migrate_view`） | ✅ |
| 物化视图 | MV 定义与数据 | ✅ |
| 触发器 | **导出源码模板**，不自动下发 DDL | ✅ |
| 例程 | 存储过程/函数基础语法转换 | ✅ |

任务详情页展示**多阶段进度条**、当前 Schema、已完成/失败对象列表，支持「继续迁移」断点续传。

---

### 🛠 目标环境自动就绪

通过 `TargetEnvWizard` 组件与后端 `target_provisioning` 模块，在 Web 端完成 PolarDB 侧环境准备，无需反复登录控制台：

```
┌─────────────────────────────────────────────────────────────┐
│  TargetEnvWizard · 目标环境配置面板                          │
├─────────────────────────────────────────────────────────────┤
│  📦 数据库    [ 选择已有 ▼ ] [ 新建 ▼ ]  名称 · 编码 UTF8    │
│  💾 表空间    [ 默认 ▼ ] [ 已有 ▼ ] [ 新建 + LOCATION 路径 ]  │
│  👤 用户      [ 跳过 ▼ ] [ 已有 ▼ ] [ 新建 + 密码 + CREATEDB ]│
│  📂 Schema    [ 已有 public ▼ ] [ 新建 + 所有者 ]            │
├─────────────────────────────────────────────────────────────┤
│  [ 🔧 测试并准备环境 ]  →  POST /api/target-env/prepare/    │
└─────────────────────────────────────────────────────────────┘
```

| 资源 | 模式 | 权限要求 |
|:-----|:-----|:---------|
| 数据库 | `existing` / `create` / `skip` | `CREATEDB` 或超级用户 |
| 表空间 | `skip` / `existing` / `create` | 超级用户 + 服务器目录路径 |
| 用户 | `skip` / `existing` / `create` | `CREATEROLE` 或超级用户 |
| Schema | `existing` / `create` | 目标库 `CREATE` 权限 |

> [!WARNING]
> 表空间创建需 PolarDB 实例文件系统路径；无超级用户权限时，可回退「使用默认表空间」仅完成库/用户/Schema 准备。

---

## 📌 适用场景与版本

<table>
  <thead>
    <tr>
      <th width="18%">维度</th>
      <th>说明</th>
      <th width="14%">推荐度</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>源端</strong></td>
      <td>Oracle Database <strong>11g+</strong>（如 11.2.0.4 Enterprise Edition），Schema = <code>ALL_USERS.USERNAME</code></td>
      <td>⭐⭐⭐⭐⭐</td>
    </tr>
    <tr>
      <td><strong>目标端</strong></td>
      <td>阿里云 <strong>PolarDB PostgreSQL</strong> 或兼容 PostgreSQL 15 的实例</td>
      <td>⭐⭐⭐⭐⭐</td>
    </tr>
    <tr>
      <td><strong>精迁场景</strong></td>
      <td>按表选择、增量同步、目标库/用户/Schema 尚未就绪</td>
      <td>⭐⭐⭐⭐</td>
    </tr>
    <tr>
      <td><strong>整库场景</strong></td>
      <td>单实例多 Schema、多对象类型一次性编排上云</td>
      <td>⭐⭐⭐⭐</td>
    </tr>
    <tr>
      <td><strong>归档场景</strong></td>
      <td>视图数据导出 SQLite，便于离线分析</td>
      <td>⭐⭐⭐</td>
    </tr>
  </tbody>
</table>

---

## ✨ 核心功能矩阵

### 🔗 连接与配置

| 模块 | 能力 | 标签 |
|:-----|:-----|:-----|
| Oracle 连接 | 多源库 CRUD、连接测试、Schema/用户/对象枚举 | `源端` |
| PolarDB 连接 | 多实例、SSL、多库列表、Schema/用户/表空间查询 | `目标端` |
| 任务级目标 | 连接 → 数据库 → Schema 三步选择；支持运行时切换目标库 | `编排` |
| 全局策略 | 默认大小写、冲突策略、批量大小（系统配置页） | `策略` |

### 📦 对象迁移能力

| 类型 | 标识 | 说明 | 版本 |
|:-----|:-----|:-----|:----:|
| 表 | `table` | 结构+数据+约束+索引；支持多表单任务、增量、行数校验 | — |
| 视图 | `view` | 物化到表 或 创建视图定义（NVL/SYSDATE 等基础转换） | — |
| 物化视图 | `materialized_view` | MV 定义与刷新逻辑 | — |
| 序列 | `sequence` | 先于表创建，保障主键自增 | — |
| 触发器 | `trigger` | 导出 Oracle 源码 + PL/pgSQL 模板（人工改写） | — |
| 例程 | `routine` | 存储过程/函数基础语法转换 | — |
| 所有表 | `all_tables` | 单 Schema 全表批量，FK 拓扑排序 | — |
| 全 Schema | `full_schema` | 序列 + 全表编排 | — |
| **整库** | `full_database` | 多 Schema · 全对象类型编排 | 🆕 |
| **表级批量** | `table_batch` | 向导创建的批量表任务（复用多表逻辑） | 🆕 |
| SQLite 导出 | `view_to_sqlite` | 视图数据落地本地 SQLite | — |

### ⚙️ 策略与增量

<table>
  <thead>
    <tr>
      <th width="22%">策略类别</th>
      <th>可选项</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>冲突处理</strong></td>
      <td><code>error</code> · <code>replace</code> · <code>skip</code> · <code>append</code> · <code>truncate</code></td>
    </tr>
    <tr>
      <td><strong>标识符大小写</strong></td>
      <td><code>lower</code> · <code>upper</code> · <code>preserve</code></td>
    </tr>
    <tr>
      <td><strong>增量模式</strong></td>
      <td><code>none</code> 全量 · <code>timestamp</code> 水位列 · <code>pk_mirror</code> 主键对齐</td>
    </tr>
    <tr>
      <td><strong>定时同步</strong></td>
      <td>Celery Beat，最小间隔可配（分钟级）</td>
    </tr>
  </tbody>
</table>

### 📊 可观测性

```
任务总进度 ───────────────────────────────────────────── 100%
  ├─ 对象/表级进度 ────────────────────────────────────  85%
  │    └─ 行级进度（大表 COUNT + 分批写入）────────────  72%
  └─ 整库阶段条：准备 → 序列 → 表 → 视图 → 触发器 → 例程
```

- **三级进度**：任务总进度 → 对象/表级进度 → 行级进度（大表 COUNT + 分批写入）
- **整库阶段条**：准备 → 序列 → 表 → 视图 → 触发器 → 例程
- **断点续传**：`all_tables` · `table` · `full_schema` · `full_database` · `table_batch`
- **主键对比**：监控页展示源/目标行数差异快照

---

## 🏗 系统架构

```mermaid
flowchart TB
  subgraph fe ["表现层"]
    Home["首页工作台"]
    TableWiz["表级迁移向导"]
    FullDB["整库一键迁移"]
    TargetWiz["目标环境向导"]
  end
  subgraph iface ["接口层"]
    TaskAPI["任务管理接口"]
    DDL["目标环境接口"]
    Discovery["库发现服务"]
  end
  subgraph core ["执行层"]
    Runner["任务分发"]
    FullOrch["整库编排"]
    Migrate["对象迁移"]
  end
  subgraph datalayer ["数据层"]
    SrcDB[(甲骨文源库)]
    TgtDB[(云原生目标库)]
  end
  TableWiz --> TaskAPI
  FullDB --> TaskAPI
  TargetWiz --> DDL
  FullDB --> Discovery
  TaskAPI --> Runner
  Runner --> FullOrch
  Runner --> Migrate
  Migrate --> SrcDB
  Migrate --> TgtDB
```

<br/>

<table>
  <tr>
    <th width="20%">分层</th>
    <th>职责</th>
    <th width="28%">关键技术</th>
  </tr>
  <tr>
    <td><strong>表现层</strong></td>
    <td>Vue 3 SPA · 侧边栏导航 · 主题切换 · 步骤条向导 · 阶段进度条</td>
    <td>Vue Router · Pinia · Bootstrap 5</td>
  </tr>
  <tr>
    <td><strong>接口层</strong></td>
    <td><code>/api/tasks</code> · <code>/api/create-table-migration</code> · <code>/api/target-env/...</code></td>
    <td>DRF · JWT · CORS</td>
  </tr>
  <tr>
    <td><strong>领域层</strong></td>
    <td>任务模型 · 目标配置 JSON · 编排状态 <code>view_progress</code></td>
    <td>Django ORM · JSONField</td>
  </tr>
  <tr>
    <td><strong>执行层</strong></td>
    <td>Celery Worker / 线程池 · 分批读写 · 类型映射 · 约束回放</td>
    <td>Celery · cx_Oracle · psycopg2</td>
  </tr>
  <tr>
    <td><strong>数据层</strong></td>
    <td>Oracle (cx_Oracle) ──► PolarDB (psycopg2) / SQLite</td>
    <td>连接池 · 凭据加密</td>
  </tr>
</table>

---

## 🗺 导航与路由地图

<table>
  <thead>
    <tr>
      <th>分组</th>
      <th>菜单</th>
      <th>路由</th>
      <th>说明</th>
      <th>标签</th>
    </tr>
  </thead>
  <tbody>
    <tr><td rowspan="1">工作台</td><td>首页</td><td><code>/</code></td><td>统计卡片 · 快捷入口 · 最近任务</td><td>—</td></tr>
    <tr><td rowspan="5">迁移管理</td><td>迁移任务</td><td><code>/tasks</code></td><td>分页列表 · 批量启停</td><td>—</td></tr>
    <tr><td>实时监控</td><td><code>/monitor</code></td><td>运行中任务 · 日志 · 主键对比</td><td>—</td></tr>
    <tr><td>创建任务</td><td><code>/task/create</code></td><td>通用多类型任务创建</td><td>—</td></tr>
    <tr><td><strong>表级迁移</strong></td><td><code>/task/table-migrate</code></td><td>五步向导 · 目标环境 · 增量</td><td>🆕 v2</td></tr>
    <tr><td><strong>整库一键迁移</strong></td><td><code>/migration/full-database</code></td><td>Discovery · 映射 · 一键编排</td><td>🆕 v2</td></tr>
    <tr><td rowspan="2">数据连接</td><td>Oracle 数据库</td><td><code>/oracle</code></td><td>源端连接 CRUD · Schema 浏览</td><td>—</td></tr>
    <tr><td>PolarDB-PG</td><td><code>/postgres</code></td><td>目标连接 CRUD · 库/Schema 浏览</td><td>—</td></tr>
    <tr><td>系统</td><td>系统配置</td><td><code>/config</code></td><td>迁移策略 · 系统参数</td><td>—</td></tr>
    <tr><td>—</td><td>任务详情</td><td><code>/task/:id</code></td><td>进度 · 日志 · 续传 · 阶段条</td><td>—</td></tr>
  </tbody>
</table>

---

## 🚀 快速开始

### 环境要求

<table>
  <thead>
    <tr>
      <th width="18%">类别</th>
      <th>要求</th>
      <th width="14%">必需</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>运行环境</strong></td>
      <td>Python 3.12+ · Node.js 18+</td>
      <td>✅</td>
    </tr>
    <tr>
      <td><strong>数据库驱动</strong></td>
      <td>cx_Oracle（Oracle）· psycopg2（PostgreSQL/PolarDB）</td>
      <td>✅</td>
    </tr>
    <tr>
      <td><strong>异步任务</strong></td>
      <td>Redis + Celery（生产环境异步任务与定时增量）</td>
      <td>可选</td>
    </tr>
    <tr>
      <td><strong>包管理</strong></td>
      <td>后端 <code>uv</code> · 前端 <code>pnpm</code></td>
      <td>✅</td>
    </tr>
  </tbody>
</table>

### 一键启动

```bash
# ══════════════════════════════════════════════
#  后端 · Django REST API
# ══════════════════════════════════════════════
uv pip install -r requirements.txt
uv run manage.py migrate          # 含 target_provisioning 等新字段
uv run manage.py createsuperuser  # 首次部署
uv run manage.py runserver 0.0.0.0:8000

# ══════════════════════════════════════════════
#  前端 · Vue 3 SPA
# ══════════════════════════════════════════════
cd frontend && pnpm install && pnpm dev
# → http://localhost:5173
```

> [!TIP]
> 生产环境建议同时启动 Celery Worker 与 Beat，以支持后台任务与定时增量同步。

### 推荐上手路径

```mermaid
flowchart TB
  A["步骤一 配置源端与目标端连接"] --> B{"选择迁移规模"}
  B -->|核心表迁移| C["步骤二 表级迁移向导"]
  B -->|整库迁移| D["步骤二 整库一键迁移"]
  B -->|单对象迁移| E["步骤二 通用创建任务"]
  C --> F["步骤三 准备目标环境"]
  D --> F
  F --> G["步骤四 启动并监控进度"]
  G --> H["步骤五 排障与续传校验"]
```

---

## 📖 使用手册

<table>
  <tr>
    <th width="28%">路径</th>
    <th>适用场景</th>
    <th>入口</th>
  </tr>
  <tr>
    <td><strong>路径 A · 表级迁移向导</strong></td>
    <td>按表精迁、增量同步、目标环境未就绪</td>
    <td><code>/task/table-migrate</code></td>
  </tr>
  <tr>
    <td><strong>路径 B · 整库一键迁移</strong></td>
    <td>单实例多 Schema、全对象类型编排</td>
    <td><code>/migration/full-database</code></td>
  </tr>
  <tr>
    <td><strong>路径 C · 通用创建任务</strong></td>
    <td>视图、例程、单序列、SQLite 导出</td>
    <td><code>/task/create</code></td>
  </tr>
</table>

<br/>

<details>
<summary><b>📋 路径 A · 表级迁移向导（展开步骤）</b></summary>

<br/>

1. 进入 **表级迁移**，选择 Oracle 连接与源 Schema。
2. 勾选需迁移的表（支持搜索与全选）。
3. 在 **目标环境** 面板选择 PolarDB 连接，按需**新建数据库/用户/Schema**，点击「测试并准备环境」。
4. 配置增量模式（可选水位列或主键对齐 + 定时）。
5. 确认后创建任务，在详情页启动并观察多表进度。

</details>

<details>
<summary><b>☁️ 路径 B · 整库一键迁移（展开步骤）</b></summary>

<br/>

1. 进入 **整库一键迁移**，选择 Oracle 连接，点击 **刷新发现**。
2. 查看各 Schema 对象统计，编辑 **Oracle Schema → 目标 Schema** 映射。
3. 配置 PolarDB 目标环境，勾选需迁移的对象类型（默认全选）。
4. 点击 **创建并立即启动**，在详情页查看阶段进度条。
5. 触发器阶段完成后，从日志复制 PL/pgSQL 模板，人工改写后于目标库执行。

</details>

<br/>

### 冲突策略速查

| 策略 | 行为 | 适用 | 风险 |
|:-----|:-----|:-----|:----:|
| `error` | 已存在则失败 | 首次迁移、严格校验 | 低 |
| `replace` | 删除后重建 | 结构变更需覆盖 | 中 |
| `skip` | 跳过已存在对象 | 增量补迁 | 低 |
| `append` | 仅追加数据 | 增量同步（主键对齐必选） | 中 |
| `truncate` | 清空后重导 | 周期性全量刷新 | 高 |

---

## 🔌 API 速查 · 新增

> [!IMPORTANT]
> 所有 API 均需 JWT 认证。凭据经 Fernet 加密存储，请勿在日志中输出明文密码。

<details>
<summary><b>展开完整新增端点列表</b></summary>

<br/>

| 方法 | 端点 | 说明 | 场景 |
|:-----|:-----|:-----|:-----|
| `GET` | `/api/oracle/discovery/?connection_id=` | 整库 Schema 与对象统计 | 整库发现 |
| `POST` | `/api/create-table-migration/` | 表级向导创建任务 | 表级精迁 |
| `POST` | `/api/create-full-database-migration/` | 整库编排创建任务 | 整库编排 |
| `POST` | `/api/target-env/prepare/` | 一键准备目标环境 | DDL 预置 |
| `GET` | `/api/polardb/tablespaces/?connection_id=` | 列出表空间 | 目标配置 |
| `POST` | `/api/polardb/databases/create/` | 创建数据库 | DDL |
| `POST` | `/api/polardb/tablespaces/create/` | 创建表空间 | DDL |
| `POST` | `/api/polardb/users/create/` | 创建用户/角色 | DDL |
| `POST` | `/api/polardb/schemas/create/` | 创建 Schema | DDL |

<br/>

**`target_provisioning` 配置示例**（存于 `MigrationTask.target_provisioning`）：

```json
{
  "database": { "mode": "create", "name": "appdb", "encoding": "UTF8" },
  "tablespace": { "mode": "skip" },
  "user": { "mode": "create", "username": "app", "password": "***" },
  "schema": { "mode": "create", "name": "app_schema", "owner": "app" },
  "schema_mappings": [
    { "source_schema": "HR", "target_schema": "hr" }
  ],
  "object_types": {
    "sequences": true, "tables": true, "views": true,
    "materialized_views": true, "triggers": true, "routines": true
  }
}
```

</details>

---

## 🔧 开发指南

### 技术栈

<table>
  <thead>
    <tr>
      <th width="50%">后端</th>
      <th>前端</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td valign="top">
        <ul>
          <li>Python 3.12 · Django 5.2 · DRF</li>
          <li>cx_Oracle · psycopg2 · Celery</li>
          <li>JWT · Fernet 凭据加密</li>
        </ul>
      </td>
      <td valign="top">
        <ul>
          <li>Vue 3 · TypeScript · Vite</li>
          <li>Bootstrap 5 · Vue Router</li>
          <li>Pinia · 主题 CSS 变量</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>

### 关键模块（v2 新功能）

| 文件 | 职责 | 层级 |
|:-----|:-----|:-----|
| `migration_app/target_provisioning.py` | PolarDB DDL：库/表空间/用户/Schema/授权 | 后端 |
| `migration_app/full_database.py` | 整库多阶段编排与 Discovery | 后端 |
| `migration_app/create_task.py` | `create_table_migration_plan` / `create_full_database_migration_plan` | 后端 |
| `frontend/src/components/TargetEnvWizard.vue` | 目标环境配置 UI | 前端 |
| `frontend/src/composables/useMigrationSource.ts` | 源端连接/Schema/对象复用逻辑 | 前端 |
| `frontend/src/views/TableMigrationView.vue` | 表级五步向导 | 前端 |
| `frontend/src/views/FullDatabaseMigrationView.vue` | 整库一键迁移页 | 前端 |

### 前端命令

```bash
cd frontend
pnpm install    # 安装依赖
pnpm dev        # 开发模式 → http://localhost:5173
pnpm build      # 生产构建
```

---

## 📚 文档与支持

<table>
  <thead>
    <tr>
      <th>文档</th>
      <th>说明</th>
      <th>受众</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="docs/文档索引.md">文档索引</a></td>
      <td>全部说明文档导航</td>
      <td>全员</td>
    </tr>
    <tr>
      <td><a href="docs/迁移进度与监控.md">迁移进度与监控</a></td>
      <td>进度计算、大表优化、轮询接口</td>
      <td>运维</td>
    </tr>
    <tr>
      <td><a href="docs/路由与前后端配置.md">路由与前后端配置</a></td>
      <td>API 端点、部署与代理</td>
      <td>开发</td>
    </tr>
    <tr>
      <td><a href="docs/颜色系统使用说明.md">颜色系统使用说明</a></td>
      <td>主题变量与 UI 规范</td>
      <td>前端</td>
    </tr>
    <tr>
      <td><a href="docs/需求与版本说明.md">需求与版本说明</a></td>
      <td>版本背景与技术选型</td>
      <td>产品</td>
    </tr>
    <tr>
      <td><strong>本 README</strong></td>
      <td>产品概述、v2 新功能、架构与上手路径</td>
      <td>全员</td>
    </tr>
  </tbody>
</table>

---

## 📄 许可证

© 2025–2026 Oracle 到 PolarDB 迁移工具 · 版权所有

---

<br/>

<p align="center">
  <strong>Oracle 至 PolarDB PostgreSQL</strong><br/>
  <sub>企业级迁移平台 · 表级精迁 · 整库编排 · 目标环境自动就绪</sub>
</p>

<br/>

<p align="center">
  <code>表级迁移</code> &nbsp;·&nbsp; <code>整库一键</code> &nbsp;·&nbsp; <code>增量同步</code> &nbsp;·&nbsp; <code>断点续传</code>
</p>

<p align="center">
  <sub>基于 Django、Vue 3 与 PolarDB PostgreSQL 构建</sub>
</p>
