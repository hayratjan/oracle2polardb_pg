<template>
  <div class="task-detail-view">
    <div class="page-header mb-4">
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <h1>
            <i class="bi bi-file-earmark-text me-2" style="font-size: 32px;"></i>
            任务详情
          </h1>
          <p class="text-muted mb-0">查看和管理迁移任务的详细信息</p>
        </div>
        <router-link to="/tasks" class="btn btn-sm btn-outline-secondary">
          <i class="bi bi-arrow-left me-1"></i>
          返回列表
        </router-link>
      </div>
    </div>
    
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="mt-3 text-muted">加载任务详情...</p>
    </div>
    
    <div v-else-if="task">
      <div class="row g-4">
        <div class="col-lg-8">
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="mb-0">
                <i class="bi bi-info-circle me-1" style="font-size: 20px;"></i>
                {{ task.name }}
              </h5>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-tag me-1" style="font-size: 16px;"></i>
                    任务类型
                  </label>
                  <div class="info-value">{{ getTaskTypeText(task.task_type) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-activity me-1" style="font-size: 16px;"></i>
                    状态
                  </label>
                  <div class="info-value">
                    <span class="badge status-badge" :class="getStatusBadgeClass(task.status)">
                      <span class="status-dot"></span>
                      {{ getStatusText(task.status) }}
                    </span>
                  </div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-database me-1" style="font-size: 16px;"></i>
                    源数据库
                  </label>
                  <div class="info-value">{{ task.source_db || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-server me-1" style="font-size: 16px;"></i>
                    目标概览
                  </label>
                  <div class="info-value">{{ task.target_db || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-diagram-3 me-1" style="font-size: 16px;"></i>
                    源Schema
                  </label>
                  <div class="info-value">{{ task.source_schema || '-' }}</div>
                </div>
                
                <!-- PolarDB 目标：连接、数据库、Schema -->
                <template v-if="task.task_type !== 'view_to_sqlite' && task.postgres_connection_name">
                  <div class="info-item">
                    <label class="info-label">
                      <i class="bi bi-link-45deg me-1" style="font-size: 16px;"></i>
                    PolarDB/PostgreSQL 连接
                    </label>
                    <div class="info-value">{{ task.postgres_connection_name || '-' }}</div>
                  </div>
                  <div class="info-item">
                    <label class="info-label">
                      <i class="bi bi-database me-1" style="font-size: 16px;"></i>
                    目标数据库
                    </label>
                    <div class="info-value">{{ task.postgres_database || '-' }}</div>
                  </div>
                  <div class="info-item">
                    <label class="info-label">
                      <i class="bi bi-diagram-3 me-1" style="font-size: 16px;"></i>
                    目标 Schema
                    </label>
                    <div class="info-value">{{ task.target_schema || '-' }}</div>
                  </div>
                </template>
                <div v-else class="info-item">
                  <label class="info-label">
                    <i class="bi bi-diagram-3 me-1" style="font-size: 16px;"></i>
                    目标Schema
                  </label>
                  <div class="info-value">{{ task.target_schema || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-box me-1" style="font-size: 16px;"></i>
                    源对象（表/视图）
                  </label>
                  <div class="info-value">
                    <template v-if="task.source_objects && task.source_objects.trim()">
                      <div v-if="sourceObjectsList.length > sourceListInlineMax" class="source-objects-compact">
                        <div class="text-muted small mb-1">
                          共 {{ sourceObjectsList.length }} 个对象（列表可滚动，避免一次渲染数千行顿卡）
                        </div>
                        <pre class="source-objects-monolist">{{ sourceObjectsMonolist }}</pre>
                      </div>
                      <template v-else>
                        <span v-for="(obj, i) in sourceObjectsList" :key="i">{{ obj }}{{ i < sourceObjectsList.length - 1 ? '、' : '' }}</span>
                      </template>
                    </template>
                    <template v-else>{{ task.source_object || '-' }}</template>
                  </div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-box me-1" style="font-size: 16px;"></i>
                    目标对象
                  </label>
                  <div class="info-value">{{ task.target_object || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-gear me-1" style="font-size: 16px;"></i>
                    冲突策略
                  </label>
                  <div class="info-value">{{ getConflictStrategyText(task.conflict_strategy) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-calendar-plus me-1" style="font-size: 16px;"></i>
                    创建时间
                  </label>
                  <div class="info-value">{{ formatDate(task.created_at) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-play-circle me-1" style="font-size: 16px;"></i>
                    开始时间
                  </label>
                  <div class="info-value">{{ formatDate(task.started_at) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-check-circle me-1" style="font-size: 16px;"></i>
                    完成时间
                  </label>
                  <div class="info-value">{{ formatDate(task.completed_at) }}</div>
                </div>
              </div>
              
              <div class="progress-section mt-4">
                <label class="form-label">
                  <i class="bi bi-bar-chart me-1" style="font-size: 16px;"></i>
                  进度
                </label>
                <div class="progress-wrapper">
                  <div class="progress">
                    <div class="progress-bar" :class="getProgressBarClass(task.status)"
                         :style="{ width: task.progress + '%' }"></div>
                  </div>
                  <span class="progress-text">{{ task.progress.toFixed(1) }}%</span>
                </div>
                <!-- 多表批量或「所有表」：view_progress 为 { current, total, current_table, failed_count } -->
                <div v-if="allTablesProgress" class="all-tables-progress mt-3 p-3 rounded bg-light">
                  <div class="d-flex align-items-center mb-1">
                    <i class="bi bi-collection me-2 text-primary"></i>
                    <span class="text-muted">当前进度：</span>
                    <strong class="ms-1">第 {{ allTablesProgress.current }} / {{ allTablesProgress.total }} 张表</strong>
                  </div>
                  <div v-if="allTablesProgress.current_table" class="text-muted small">
                    正在迁移：<code>{{ allTablesProgress.current_table }}</code>
                  </div>
                  <div v-if="allTablesProgress.failed_count != null && allTablesProgress.failed_count > 0" class="text-warning small mt-1">
                    已失败 {{ allTablesProgress.failed_count }} 张表
                  </div>
                </div>
                <!-- 表/视图级进度：非「所有表」汇总格式时显示各对象 progress、total_rows、migrated_rows -->
                <div v-else-if="viewProgressEntries.length" class="view-progress-list mt-3">
                  <div v-for="[objName, info] in viewProgressEntries" :key="objName" class="view-progress-item">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                      <span class="view-progress-name">
                        <i class="bi bi-table me-1"></i>{{ objName }}
                      </span>
                      <span class="view-progress-stats text-muted small">
                        <template v-if="info && typeof info === 'object' && info.total_rows != null">
                          已迁移 <strong>{{ formatNumber(info.migrated_rows) }}</strong> / {{ formatNumber(info.total_rows) }} 行
                        </template>
                        <template v-else-if="info && typeof info === 'object'">
                          已迁移 <strong>{{ formatNumber(info.migrated_rows) }}</strong> 行
                        </template>
                        <template v-else>—</template>
                        <template v-if="info && typeof info === 'object'"> · {{ (info.progress ?? 0).toFixed(1) }}%</template>
                      </span>
                    </div>
                    <div v-if="info && typeof info === 'object' && (info.progress != null || info.total_rows != null)" class="progress thin">
                      <div class="progress-bar" :class="getProgressBarClass(task.status)"
                           :style="{ width: (info.progress ?? 0) + '%' }"></div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="action-buttons mt-4">
                <button v-if="task.status === 'pending'" @click="startTask" 
                        class="btn btn-sm btn-success flex-grow-1">
                  <i class="bi bi-play-fill me-2" style="font-size: 18px;"></i>
                  开始任务
                </button>
                <button v-if="task.status === 'running'" @click="cancelTask" 
                        class="btn btn-sm btn-warning flex-grow-1">
                  <i class="bi bi-x-circle me-2" style="font-size: 18px;"></i>
                  取消任务
                </button>
                <button v-if="canRerun(task.status)" @click="startTask" 
                        class="btn btn-sm btn-primary flex-grow-1">
                  <i class="bi bi-arrow-repeat me-2" style="font-size: 18px;"></i>
                  重新运行
                </button>
                <button @click="refreshStatus" class="btn btn-sm btn-outline-info">
                  <i class="bi bi-arrow-clockwise me-2" style="font-size: 18px;"></i>
                  刷新状态
                </button>
                <button @click="deleteTask" class="btn btn-sm btn-outline-danger">
                  <i class="bi bi-trash me-2" style="font-size: 18px;"></i>
                  删除任务
                </button>
              </div>
            </div>
          </div>
          
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">
                <i class="bi bi-terminal me-1" style="font-size: 20px;"></i>
                日志
              </h5>
            </div>
            <div class="card-body">
              <div class="log-container">
                <pre class="log-content">{{ task.log || '暂无日志' }}</pre>
              </div>
            </div>
          </div>
        </div>
        
        <div class="col-lg-4">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">
                <i class="bi bi-gear me-1" style="font-size: 20px;"></i>
                任务操作
              </h5>
            </div>
            <div class="card-body">
              <div class="mb-4">
                <label class="form-label">
                  <i class="bi bi-arrow-repeat me-1" style="font-size: 16px;"></i>
                  切换目标数据库
                </label>
                <select v-model="selectedDatabase" class="form-select-sm mb-3">
                  <option value="">请选择数据库</option>
                  <option v-for="db in databases" :key="db" :value="db">{{ db }}</option>
                </select>
                <button @click="switchDatabase" class="btn btn-sm btn-primary w-100">
                  <i class="bi bi-arrow-repeat me-1" style="font-size: 16px;"></i>
                  确认切换
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { migrationTaskApi, databaseApi } from '@/api'
import type { MigrationTask } from '@/api'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const task = ref<MigrationTask | null>(null)
const databases = ref<string[]>([])
const selectedDatabase = ref('')
let statusInterval: number | null = null

// 源对象列表（表/视图）：来自 source_objects 或 source_object
const sourceListInlineMax = 40

const sourceObjectsList = computed(() => {
  if (!task.value) return []
  const so = task.value.source_objects?.trim()
  if (so) return so.split(/[,，]/).map((s: string) => s.trim()).filter(Boolean)
  if (task.value.source_object?.trim()) return [task.value.source_object.trim()]
  return []
})

/** 大量表名时用换行拼接，配合 pre 滚动，比数千个 span 轻量 */
const sourceObjectsMonolist = computed(() => sourceObjectsList.value.join('\n'))

// 「所有表」任务进度：view_progress 为 { current, total, current_table, failed_count } 时使用
const ALL_TABLES_KEYS = ['current', 'total', 'current_table', 'failed_count']
const allTablesProgress = computed(() => {
  const vp = task.value?.view_progress
  if (vp == null || typeof vp !== 'object' || Array.isArray(vp)) return null
  const raw = typeof vp === 'string' ? (() => { try { return JSON.parse(vp) } catch { return null } })() : vp
  if (raw == null || typeof raw !== 'object') return null
  if (raw.current != null && raw.total != null) {
    return {
      current: Number(raw.current),
      total: Number(raw.total),
      current_table: raw.current_table ?? '',
      failed_count: raw.failed_count != null ? Number(raw.failed_count) : 0,
    }
  }
  return null
})

// view_progress 条目列表，用于展示每个表/视图的 progress、total_rows、migrated_rows（排除「所有表」汇总字段）
const viewProgressEntries = computed(() => {
  let vp = task.value?.view_progress
  if (vp == null) return []
  if (typeof vp === 'string') {
    try {
      vp = JSON.parse(vp)
    } catch {
      return []
    }
  }
  if (typeof vp !== 'object' || Array.isArray(vp)) return []
  return Object.entries(vp).filter(([k]) => !ALL_TABLES_KEYS.includes(k))
})

const formatNumber = (n?: number | null) => {
  if (n == null || Number.isNaN(n)) return '-'
  return Number(n).toLocaleString('zh-CN')
}

const getTaskTypeText = (type: string) => {
  const texts: Record<string, string> = {
    table: '表',
    materialized_view: '物化视图',
    view: '视图',
    routine: '例程',
    all_tables: '所有表',
    view_to_table: '视图数据迁移到表',
    view_to_sqlite: '视图数据迁移到SQLite',
  }
  return texts[type] || type
}

const getStatusBadgeClass = (status: string) => {
  const classes: Record<string, string> = {
    pending: 'bg-secondary',
    running: 'bg-primary',
    completed: 'bg-success',
    failed: 'bg-danger',
    partial: 'bg-warning',
    canceled: 'bg-dark',
  }
  return classes[status] || 'bg-secondary'
}

const getProgressBarClass = (status: string) => {
  const classes: Record<string, string> = {
    pending: 'bg-secondary',
    running: 'bg-primary',
    completed: 'bg-success',
    failed: 'bg-danger',
    partial: 'bg-warning',
    canceled: 'bg-dark',
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
  }
  return texts[status] || status
}

const getConflictStrategyText = (strategy: string) => {
  const texts: Record<string, string> = {
    error: '遇到冲突时报错',
    replace: '删除并替换已存在对象',
    skip: '跳过已存在对象',
    append: '追加数据（仅适用于表）',
    truncate: '清空表并重新加载数据',
  }
  return texts[strategy] || strategy
}

const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

/**
 * 加载任务详情
 * @param showLoading 是否显示全屏加载（轮询刷新时传 false，避免整页闪烁）
 */
const loadTask = async (showLoading = true) => {
  if (showLoading) loading.value = true
  try {
    const res = await migrationTaskApi.get(Number(route.params.id))
    const data = res.data
    // 若已有任务数据且为后台刷新：只更新会变的字段，减少整块 DOM 重绘
    if (!showLoading && task.value && data) {
      task.value.status = data.status
      task.value.progress = data.progress ?? task.value.progress
      task.value.log = data.log
      task.value.view_progress = data.view_progress
      task.value.started_at = data.started_at
      task.value.completed_at = data.completed_at
      task.value.cancel_requested = data.cancel_requested
    } else {
      task.value = data
    }
  } catch (error) {
    console.error('Failed to load task:', error)
  } finally {
    if (showLoading) loading.value = false
  }
}

/** 轻量轮询：仅拉取状态/进度，不拉取完整 log，减少长时间任务时的响应体积与带宽 */
const loadTaskStatusLight = async () => {
  try {
    const res = await migrationTaskApi.statusLight(Number(route.params.id))
    const data = res.data
    if (task.value && data) {
      task.value.status = data.status
      task.value.progress = data.progress ?? task.value.progress
      task.value.view_progress = data.view_progress ?? task.value.view_progress
      task.value.started_at = data.started_at
      task.value.completed_at = data.completed_at
      task.value.cancel_requested = data.cancel_requested
    }
  } catch (error) {
    console.error('Failed to load task status:', error)
  }
}

const loadDatabases = async () => {
  if (!task.value?.postgres_connection) return
  
  try {
    const res = await databaseApi.getPostgresDatabases({
      connection_id: task.value.postgres_connection,
    })
    databases.value = res.data.databases || []
  } catch (error) {
    console.error('Failed to load databases:', error)
  }
}

const canRerun = (status: string) =>
  ['failed', 'completed', 'partial', 'canceled'].includes(status)

const startTask = async () => {
  try {
    await migrationTaskApi.start(Number(route.params.id))
    await loadTask()
  } catch (error) {
    console.error('Failed to start task:', error)
  }
}

const cancelTask = async () => {
  if (!confirm('确定要取消此任务吗？')) return
  try {
    await migrationTaskApi.cancel(Number(route.params.id))
    await loadTask()
  } catch (error) {
    console.error('Failed to cancel task:', error)
  }
}

const deleteTask = async () => {
  if (!confirm('确定要删除此任务吗？')) return
  try {
    await migrationTaskApi.delete(Number(route.params.id))
    router.push('/tasks')
  } catch (error) {
    console.error('Failed to delete task:', error)
  }
}

// 点击刷新：静默更新进度/状态/日志，不闪界面、不重新渲染整页
const refreshStatus = async () => {
  await loadTask(false)
}

const switchDatabase = async () => {
  if (!selectedDatabase.value) {
    alert('请选择数据库')
    return
  }
  
  try {
    await migrationTaskApi.switchDatabase(Number(route.params.id), {
      postgres_database: selectedDatabase.value,
    })
    await loadTask()
    alert('切换成功')
  } catch (error) {
    console.error('Failed to switch database:', error)
    alert('切换失败')
  }
}

onMounted(async () => {
  await loadTask()
  await loadDatabases()
  // 同步当前任务的目标数据库到切换下拉框
  if (task.value?.postgres_database) selectedDatabase.value = task.value.postgres_database
  
  if (task.value?.status === 'running') {
    // 使用轻量状态接口轮询（5 秒），减少大任务时的响应体积与服务器压力
    statusInterval = window.setInterval(async () => {
      await loadTaskStatusLight()
      if (task.value?.status !== 'running' && statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
        // 任务结束拉一次完整详情以拿到最终 log
        await loadTask(false)
      }
    }, 5000)
  }
})

onUnmounted(() => {
  if (statusInterval) {
    clearInterval(statusInterval)
  }
})
</script>

<style scoped>
.task-detail-view {
  animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-header h1 {
  display: flex;
  align-items: center;
  font-weight: 700;
  color: var(--text);
}

.page-header .text-muted {
  font-size: 1rem;
}

.card {
  border: none;
  border-radius: 1rem;
  box-shadow: 0 10px 40px var(--shadow);
  overflow: hidden;
}

.card-header {
  background: var(--gradient);
  color: white;
  font-weight: 600;
  border: none;
  padding: 1rem 1.5rem;
}

.card-header h5 {
  display: flex;
  align-items: center;
}

.card-body {
  padding: 1.5rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-label {
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
}

.info-value {
  color: var(--text);
  font-size: 1rem;
  padding: 0.5rem 0.75rem;
  background: var(--background);
  border-radius: 0.5rem;
  border-left: 3px solid var(--primary);
}

/* 任务详情：大量源表名可滚动展示 */
.source-objects-compact .source-objects-monolist {
  max-height: 14rem;
  overflow: auto;
  margin: 0;
  padding: 0.5rem 0.65rem;
  font-size: 0.8rem;
  line-height: 1.35;
  white-space: pre;
  word-break: break-all;
  background: var(--background);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 0.35rem;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  font-weight: 500;
  border-radius: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: white;
  margin-right: 0.5rem;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.progress-section {
  padding: 1.5rem;
  background: #f7fafc;
  border-radius: 0.5rem;
}

.progress-wrapper {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress {
  flex-grow: 1;
  height: 1.5rem;
  border-radius: 0.75rem;
  background: var(--border);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 0.75rem;
}

.progress-text {
  font-weight: 600;
  color: var(--primary);
  min-width: 60px;
  text-align: right;
}

.view-progress-list {
  border-top: 1px solid var(--border);
  padding-top: 1rem;
}

.view-progress-item {
  margin-bottom: 1rem;
}
.view-progress-item:last-child {
  margin-bottom: 0;
}

.view-progress-name {
  font-weight: 500;
  color: var(--text);
}

.view-progress-stats strong {
  color: var(--primary);
}

.progress.thin {
  height: 0.5rem;
  border-radius: 0.25rem;
  background: var(--border);
}

.action-buttons {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.log-container {
  background: var(--background);
  border-radius: 0.5rem;
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
}

.log-content {
  color: var(--text);
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.form-control,
.form-select {
  border-radius: 0.5rem;
  border: 2px solid var(--input-border);
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
}

.form-control:focus,
.form-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 0.2rem var(--shadow);
}

.form-label {
  font-weight: 600;
  color: var(--text);
  margin-bottom: 0.5rem;
}

.spinner-border {
  width: 3rem;
  height: 3rem;
}
</style>