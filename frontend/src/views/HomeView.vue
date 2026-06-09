<template>
  <div class="home-view">
    <!-- 欢迎横幅：左右分栏，填充右侧空白 -->
    <div class="welcome-banner">
      <div class="welcome-left">
        <div class="welcome-badge">
          <i class="bi bi-shield-check"></i>
          企业级数据库迁移平台
        </div>
        <h1 class="welcome-title">Oracle 到 PolarDB-PG 迁移平台</h1>
        <p class="welcome-desc">高效、安全、可靠的一站式迁移解决方案，支持结构迁移、数据同步与实时监控</p>
        <div class="welcome-actions">
          <router-link to="/task/create" class="btn btn-sm btn-primary">
            <i class="bi bi-plus-circle"></i>
            创建迁移任务
          </router-link>
          <router-link to="/tasks" class="btn btn-sm btn-outline-primary">
            <i class="bi bi-list-task"></i>
            查看任务列表
          </router-link>
          <router-link to="/monitor" class="btn btn-sm btn-outline-primary">
            <i class="bi bi-activity"></i>
            实时监控
          </router-link>
        </div>
      </div>

      <div class="welcome-right">
        <!-- 迁移流程示意 -->
        <div class="welcome-flow">
          <div class="flow-step">
            <div class="flow-step-icon oracle"><i class="bi bi-database-gear"></i></div>
            <span>Oracle</span>
          </div>
          <i class="bi bi-arrow-right flow-arrow"></i>
          <div class="flow-step">
            <div class="flow-step-icon engine"><i class="bi bi-arrow-left-right"></i></div>
            <span>迁移引擎</span>
          </div>
          <i class="bi bi-arrow-right flow-arrow"></i>
          <div class="flow-step">
            <div class="flow-step-icon postgres"><i class="bi bi-server"></i></div>
            <span>PolarDB-PG</span>
          </div>
        </div>
        <!-- 平台能力标签 -->
        <div class="welcome-tags">
          <span v-for="tag in platformTags" :key="tag" class="welcome-tag">
            <i class="bi bi-check2"></i>{{ tag }}
          </span>
        </div>
      </div>
    </div>

    <!-- 快捷统计 -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3" v-for="stat in statCards" :key="stat.label">
        <div class="stat-card-enterprise">
          <div class="stat-card-icon" :style="{ background: stat.bg, color: stat.color }">
            <i :class="['bi', stat.icon]"></i>
          </div>
          <div>
            <div class="stat-card-number">{{ stat.value }}</div>
            <div class="stat-card-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 功能入口：两行六宫格 -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-4" v-for="item in quickLinks" :key="item.to">
        <router-link :to="item.to" class="quick-link-card">
          <div class="quick-link-icon" :style="{ background: item.bg, color: item.color }">
            <i :class="['bi', item.icon]"></i>
          </div>
          <div class="quick-link-text">
            <div class="quick-link-title">{{ item.title }}</div>
            <div class="quick-link-desc">{{ item.desc }}</div>
          </div>
          <i class="bi bi-chevron-right quick-link-arrow"></i>
        </router-link>
      </div>
    </div>

    <!-- 主内容区：三栏布局 -->
    <div class="row g-3">
      <!-- 最近任务 -->
      <div class="col-lg-5">
        <div class="card h-100">
          <div class="card-header d-flex align-items-center justify-content-between">
            <span><i class="bi bi-clock-history me-2"></i>最近任务</span>
            <router-link to="/tasks" class="btn btn-sm btn-ghost">查看全部</router-link>
          </div>
          <div class="card-body p-0">
            <div v-if="loading" class="text-center py-5">
              <div class="spinner-border text-primary spinner-border-sm" role="status"></div>
              <p class="mt-2 text-muted small">加载中...</p>
            </div>
            <div v-else-if="recentTasks.length > 0" class="task-list">
              <div v-for="task in recentTasks" :key="task.id" class="task-list-item">
                <div class="task-list-info">
                  <router-link :to="`/task/${task.id}`" class="task-list-name">{{ task.name }}</router-link>
                  <span class="task-list-time">{{ formatDate(task.created_at) }}</span>
                </div>
                <span class="badge" :class="getStatusBadgeClass(task.status)">
                  {{ getStatusText(task.status) }}
                </span>
              </div>
            </div>
            <div v-else class="empty-state-enterprise py-4">
              <i class="bi bi-inbox empty-icon" style="font-size: 36px;"></i>
              <p class="mb-2">暂无任务</p>
              <router-link to="/task/create" class="btn btn-sm btn-primary">创建第一个任务</router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- 数据库连接 -->
      <div class="col-lg-3">
        <div class="card h-100">
          <div class="card-header">
            <i class="bi bi-diagram-3 me-2"></i>数据库连接
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center py-4">
              <div class="spinner-border text-primary spinner-border-sm" role="status"></div>
            </div>
            <div v-else>
              <div class="connection-item">
                <div class="connection-item-left">
                  <div class="connection-dot oracle-dot"></div>
                  <span>Oracle</span>
                </div>
                <span class="connection-count">{{ oracleConnections.length }} 个</span>
              </div>
              <div class="connection-item">
                <div class="connection-item-left">
                  <div class="connection-dot postgres-dot"></div>
                  <span>PolarDB-PG</span>
                </div>
                <span class="connection-count">{{ postgresConnections.length }} 个</span>
              </div>
              <div class="connection-actions mt-3">
                <router-link to="/oracle" class="btn btn-sm btn-outline-primary w-100 mb-2">
                  <i class="bi bi-database-gear"></i> 管理 Oracle
                </router-link>
                <router-link to="/postgres" class="btn btn-sm btn-outline-info w-100">
                  <i class="bi bi-server"></i> 管理 PolarDB-PG
                </router-link>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 平台概览：填充右侧空白 -->
      <div class="col-lg-4">
        <div class="card h-100 overview-card">
          <div class="card-header">
            <i class="bi bi-info-circle me-2"></i>平台概览
          </div>
          <div class="card-body">
            <ul class="overview-list">
              <li v-for="item in overviewItems" :key="item.title" class="overview-item">
                <div class="overview-icon" :style="{ background: item.bg, color: item.color }">
                  <i :class="['bi', item.icon]"></i>
                </div>
                <div class="overview-text">
                  <strong>{{ item.title }}</strong>
                  <span>{{ item.desc }}</span>
                </div>
              </li>
            </ul>
            <div class="overview-footer">
              <router-link to="/config" class="btn btn-sm btn-outline-secondary w-100">
                <i class="bi bi-gear"></i> 系统配置
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { migrationTaskApi, oracleConnectionApi, postgresConnectionApi } from '@/api'
import type { MigrationTask } from '@/api'

const loading = ref(false)
const recentTasks = ref<MigrationTask[]>([])
const oracleConnections = ref<any[]>([])
const postgresConnections = ref<any[]>([])

const runningCount = computed(() =>
  recentTasks.value.filter(t => t.status === 'running').length
)

/** 平台能力标签 */
const platformTags = [
  '全量 & 增量迁移',
  '断点续传',
  '实时监控',
  '多对象类型',
]

/** 统计卡片（动态数据） */
const statCards = computed(() => [
  { icon: 'bi-list-task', label: '最近任务', value: recentTasks.value.length, bg: 'rgba(37, 99, 235, 0.1)', color: 'var(--primary)' },
  { icon: 'bi-database', label: 'Oracle 连接', value: oracleConnections.value.length, bg: 'rgba(249, 115, 22, 0.1)', color: '#f97316' },
  { icon: 'bi-server', label: 'PolarDB-PG 连接', value: postgresConnections.value.length, bg: 'rgba(2, 132, 199, 0.1)', color: 'var(--info)' },
  { icon: 'bi-activity', label: '执行中任务', value: runningCount.value, bg: 'rgba(217, 119, 6, 0.1)', color: 'var(--warning)' },
])

/** 快捷入口配置 */
const quickLinks = [
  { to: '/tasks', icon: 'bi-list-task', title: '迁移任务', desc: '管理和监控迁移任务', bg: 'rgba(37, 99, 235, 0.1)', color: 'var(--primary)' },
  { to: '/task/table-migrate', icon: 'bi-table', title: '表级迁移', desc: '按表选择并配置目标环境', bg: 'rgba(99, 102, 241, 0.1)', color: '#6366f1' },
  { to: '/migration/full-database', icon: 'bi-cloud-arrow-up', title: '整库一键迁移', desc: '多 Schema 全对象编排', bg: 'rgba(168, 85, 247, 0.1)', color: '#a855f7' },
  { to: '/task/create', icon: 'bi-plus-circle', title: '创建任务', desc: '快速创建迁移任务', bg: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)' },
  { to: '/monitor', icon: 'bi-activity', title: '实时监控', desc: '查看执行中任务状态', bg: 'rgba(217, 119, 6, 0.1)', color: 'var(--warning)' },
  { to: '/oracle', icon: 'bi-database-gear', title: 'Oracle 管理', desc: '配置源端数据库连接', bg: 'rgba(249, 115, 22, 0.1)', color: '#f97316' },
  { to: '/postgres', icon: 'bi-server', title: 'PolarDB-PG', desc: '管理目标端数据库', bg: 'rgba(2, 132, 199, 0.1)', color: 'var(--info)' },
  { to: '/config', icon: 'bi-gear-wide-connected', title: '系统配置', desc: '迁移策略与全局设置', bg: 'rgba(100, 116, 139, 0.1)', color: 'var(--text-muted)' },
]

/** 平台概览条目 */
const overviewItems = [
  { icon: 'bi-layers', title: '多对象迁移', desc: '表、视图、序列、触发器、存储过程', bg: 'rgba(37, 99, 235, 0.1)', color: 'var(--primary)' },
  { icon: 'bi-arrow-repeat', title: '增量同步', desc: '按水位列或主键对齐定时增量', bg: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)' },
  { icon: 'bi-shield-lock', title: '安全可靠', desc: 'JWT 认证、连接加密、断点续传', bg: 'rgba(217, 119, 6, 0.1)', color: 'var(--warning)' },
  { icon: 'bi-graph-up', title: '数据对比', desc: '主键对齐行数对比与差异监控', bg: 'rgba(2, 132, 199, 0.1)', color: 'var(--info)' },
]

const getStatusBadgeClass = (status: string) => {
  const classes: Record<string, string> = {
    pending: 'bg-secondary',
    running: 'bg-primary',
    completed: 'bg-success',
    failed: 'bg-danger',
    partial: 'bg-warning',
    canceled: 'bg-dark',
    aborted: 'bg-danger',
  }
  return classes[status] || 'bg-secondary'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    partial: '部分完成',
    canceled: '已取消',
    aborted: '异常停止',
  }
  return texts[status] || status
}

const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

onMounted(async () => {
  loading.value = true
  try {
    const [tasksRes, oracleRes, postgresRes] = await Promise.all([
      migrationTaskApi.list(),
      oracleConnectionApi.list(),
      postgresConnectionApi.list(),
    ])
    const taskList = tasksRes.data.results ?? (Array.isArray(tasksRes.data) ? tasksRes.data : [])
    recentTasks.value = taskList.slice(0, 5)
    oracleConnections.value = oracleRes.data.results ?? (Array.isArray(oracleRes.data) ? oracleRes.data : [])
    postgresConnections.value = postgresRes.data.results ?? (Array.isArray(postgresRes.data) ? postgresRes.data : [])
  } catch (error) {
    console.error('加载首页数据失败:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.home-view {
  animation: fadeIn 0.3s ease;
  width: 100%;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ===== 欢迎横幅：左右分栏 ===== */
.welcome-banner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  align-items: center;
  background: var(--gradient);
  border-radius: 14px;
  padding: 32px 36px;
  margin-bottom: 24px;
  color: white;
  position: relative;
  overflow: hidden;
}

.welcome-banner::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 85% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 55%),
    radial-gradient(circle at 10% 90%, rgba(255, 255, 255, 0.06) 0%, transparent 40%);
  pointer-events: none;
}

.welcome-left,
.welcome-right {
  position: relative;
  z-index: 1;
}

.welcome-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 16px;
}

.welcome-title {
  font-size: 24px;
  font-weight: 800;
  color: white;
  margin: 0 0 10px;
  line-height: 1.3;
}

.welcome-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.88);
  margin: 0 0 20px;
  line-height: 1.6;
}

.welcome-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.welcome-actions .btn-outline-primary {
  border-color: rgba(255, 255, 255, 0.55);
  color: white;
  background: transparent;
}

.welcome-actions .btn-outline-primary:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: white;
  color: white;
}

/* 右侧：迁移流程 */
.welcome-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 12px;
  margin-bottom: 16px;
  backdrop-filter: blur(6px);
}

.flow-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
}

.flow-step-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  background: rgba(255, 255, 255, 0.2);
}

.flow-step-icon.oracle { background: rgba(249, 115, 22, 0.35); }
.flow-step-icon.engine { background: rgba(255, 255, 255, 0.25); }
.flow-step-icon.postgres { background: rgba(2, 132, 199, 0.35); }

.flow-arrow {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.7);
  flex-shrink: 0;
}

.welcome-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.welcome-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
}

/* ===== 快捷入口 ===== */
.quick-link-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  text-decoration: none;
  color: inherit;
  height: 100%;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.quick-link-card:hover {
  box-shadow: 0 4px 12px var(--shadow-light);
  border-color: var(--primary);
  color: inherit;
}

.quick-link-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.quick-link-text {
  flex: 1;
  min-width: 0;
}

.quick-link-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.quick-link-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.quick-link-arrow {
  color: var(--text-muted);
  font-size: 14px;
  flex-shrink: 0;
}

/* ===== 任务列表 ===== */
.task-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s ease;
}

.task-list-item:last-child {
  border-bottom: none;
}

.task-list-item:hover {
  background: var(--table-row-hover);
}

.task-list-info {
  min-width: 0;
}

.task-list-name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--primary);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-list-time {
  font-size: 12px;
  color: var(--text-muted);
}

/* ===== 连接概览 ===== */
.connection-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}

.connection-item:last-of-type {
  border-bottom: none;
}

.connection-item-left {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 500;
}

.connection-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.oracle-dot { background: #f97316; }
.postgres-dot { background: #0284c7; }

.connection-count {
  font-size: 13px;
  color: var(--text-muted);
}

.connection-actions {
  display: flex;
  flex-direction: column;
}

/* ===== 平台概览 ===== */
.overview-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.overview-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}

.overview-item:last-child {
  border-bottom: none;
}

.overview-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.overview-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.overview-text strong {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.overview-text span {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}

.overview-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

/* ===== 响应式 ===== */
@media (max-width: 991.98px) {
  .welcome-banner {
    grid-template-columns: 1fr;
    gap: 20px;
    padding: 24px;
  }

  .welcome-right {
    order: -1;
  }

  .welcome-flow {
    margin-bottom: 12px;
  }
}

@media (max-width: 575.98px) {
  .welcome-banner {
    padding: 20px 16px;
  }

  .welcome-title {
    font-size: 18px;
  }

  .welcome-actions .btn {
    flex: 1;
    justify-content: center;
  }

  .flow-step-icon {
    width: 40px;
    height: 40px;
    font-size: 18px;
  }

  .flow-step span {
    font-size: 10px;
  }

  .welcome-tags {
    gap: 6px;
  }

  .welcome-tag {
    font-size: 11px;
    padding: 4px 10px;
  }
}
</style>
