<template>
  <div class="task-monitor-view">
    <PageHeader
      title="实时任务监控"
      subtitle="仅展示当前执行中的迁移任务及其对比、日志与操作记录"
      icon="bi-activity"
    >
      <template #actions>
        <span v-if="lastRefresh" class="text-muted small d-none d-md-inline">
          <i class="bi bi-clock me-1"></i>
          更新于 {{ formatDate(lastRefresh) }}
        </span>
        <div class="form-check form-switch mb-0">
          <input id="autoRefresh" v-model="autoRefresh" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="autoRefresh">自动刷新 ({{ refreshSec }}s)</label>
        </div>
        <button type="button" class="btn btn-sm btn-outline-primary" :disabled="loading" @click="loadMonitor">
          <i class="bi bi-arrow-clockwise" :class="{ spin: loading }"></i>
          刷新
        </button>
      </template>
    </PageHeader>

    <div v-if="data && !loading" class="row g-3 mb-4">
      <div class="col-6 col-md-3" v-for="item in summaryCards" :key="item.key">
        <div class="stat-card-enterprise">
          <div class="stat-card-icon" :style="{ background: item.bg, color: item.color }">
            <i :class="['bi', item.icon]"></i>
          </div>
          <div>
            <div class="stat-card-number">{{ data.summary[item.key as keyof typeof data.summary] }}</div>
            <div class="stat-card-label">{{ item.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading && !data" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="mt-3 text-muted">加载监控数据...</p>
    </div>

    <template v-else-if="data">
      <div v-if="liveTasks.length === 0" class="card mb-4 empty-live-card">
        <div class="card-body text-center py-5">
          <i class="bi bi-check-circle text-muted mb-3" style="font-size: 3rem;"></i>
          <h5 class="mb-2">当前无执行中的任务</h5>
          <p class="text-muted mb-0">任务启动后将自动出现在此页面；历史任务请前往「迁移任务」查看</p>
        </div>
      </div>

      <div v-else class="row g-4">
        <div class="col-lg-7">
          <div class="card h-100 border-primary">
            <div class="card-header">
              <h5 class="mb-0">
                <span class="pulse-dot me-2"></span>
                <i class="bi bi-list-task me-1"></i>
                实时任务 ({{ liveTasks.length }})
              </h5>
            </div>
            <div class="card-body p-0 task-list-scroll">
              <table class="table table-hover table-sm mb-0 monitor-task-table">
                <thead class="sticky-top">
                  <tr>
                    <th>名称</th>
                    <th>迁移路径</th>
                    <th>进度</th>
                    <th>明细</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="t in liveTasks"
                    :key="t.id"
                    class="task-row"
                    :class="{ 'table-active': selectedTaskId === t.id }"
                    @click="selectTask(t)"
                  >
                    <td>
                      <router-link :to="`/task/${t.id}`" class="task-link" @click.stop>{{ t.name }}</router-link>
                      <span class="badge bg-primary ms-1">执行中</span>
                    </td>
                    <td class="small text-muted">{{ t.source_db }} → {{ t.target_db }}</td>
                    <td style="min-width: 120px;">
                      <div class="progress" style="height: 6px;">
                        <div
                          class="progress-bar progress-bar-striped progress-bar-animated"
                          :style="{ width: (t.progress || 0) + '%' }"
                        />
                      </div>
                      <span class="small">{{ (t.progress || 0).toFixed(1) }}%</span>
                    </td>
                    <td class="small">{{ formatViewProgress(t) }}</td>
                    <td>
                      <router-link :to="`/task/${t.id}`" class="btn btn-sm btn-outline-info" @click.stop>详情</router-link>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="col-lg-5">
          <div
            :key="selectedTaskId ?? 'none'"
            class="card h-100"
          >
            <div class="card-header">
              <h5 class="mb-0">
                <i class="bi bi-terminal me-1"></i>
                {{ selectedTask ? selectedTask.name : '运行日志' }}
              </h5>
            </div>
            <div class="card-body p-0 d-flex flex-column log-card-body">
              <div v-if="selectedTask" class="px-3 py-2 border-bottom small log-meta">
                <span class="badge me-1" :class="getStatusBadgeClass(selectedTask.status)">
                  {{ getStatusText(selectedTask.status) }}
                </span>
                <span class="text-muted">{{ formatViewProgress(selectedTask) }}</span>
              </div>
              <div class="log-panel flex-grow-1 p-3">
                <template v-if="selectedLogTail">
                  <pre class="log-pre mb-0">{{ selectedLogTail }}</pre>
                </template>
                <template v-else-if="taskStructuredLogs.length">
                  <div
                    v-for="log in taskStructuredLogs"
                    :key="log.id"
                    class="log-line mb-1"
                    :class="'log-' + (log.level || 'info').toLowerCase()"
                  >
                    <span class="log-time">{{ formatTime(log.created_at) }}</span>
                    <span class="log-level">[{{ log.level }}]</span>
                    {{ log.message }}
                  </div>
                </template>
                <p v-else class="text-muted mb-0">点击左侧任务查看日志</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="liveTasks.length > 0" class="card mt-4">
        <div class="card-header">
          <h5 class="mb-0"><i class="bi bi-arrow-left-right me-1"></i>数据库数据对比监控</h5>
          <small class="opacity-75 ms-2">执行中任务的主键对齐：源/目标行数与待同步差量</small>
        </div>
        <div class="card-body p-0">
          <div v-if="data.compare_snapshots.length === 0" class="text-center text-muted py-4">
            暂无主键对齐对比记录
          </div>
          <div v-else class="table-responsive">
            <table class="table table-hover mb-0">
              <thead>
                <tr>
                  <th>任务</th>
                  <th>对象</th>
                  <th>源行数</th>
                  <th>目标行数</th>
                  <th>差异</th>
                  <th>待删除</th>
                  <th>待插入</th>
                  <th>一致性</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="c in data.compare_snapshots"
                  :key="'cmp-' + c.task_id"
                >
                  <td>
                    <router-link :to="`/task/${c.task_id}`" class="task-link">{{ c.task_name }}</router-link>
                  </td>
                  <td class="small">{{ c.source_object || c.source_schema }}</td>
                  <td>{{ c.source_rows ?? '—' }}</td>
                  <td>{{ c.target_rows ?? '—' }}</td>
                  <td>
                    <span v-if="c.row_diff !== undefined" :class="c.row_diff === 0 ? 'text-success' : 'text-warning'">
                      {{ c.row_diff > 0 ? '+' : '' }}{{ c.row_diff }}
                    </span>
                    <span v-else>—</span>
                  </td>
                  <td>{{ c.to_delete ?? '—' }}</td>
                  <td>{{ c.to_insert ?? '—' }}</td>
                  <td>
                    <span v-if="c.is_consistent" class="badge bg-success">一致</span>
                    <span v-else class="badge bg-warning text-dark">待同步</span>
                  </td>
                  <td>
                    <span class="badge" :class="getStatusBadgeClass(c.status || '')">{{ getStatusText(c.status || '') }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-if="liveTasks.length > 0" class="row g-4 mt-1">
        <div class="col-lg-6">
          <div class="card h-100">
            <div class="card-header"><h5 class="mb-0"><i class="bi bi-journal-text me-1"></i>运行日志流</h5></div>
            <div class="card-body log-stream p-0">
              <div
                v-for="log in data.recent_logs"
                :key="'log-' + log.id"
                class="log-stream-item px-3 py-2 border-bottom"
              >
                <div class="d-flex justify-content-between small text-muted mb-1">
                  <router-link :to="`/task/${log.task_id}`" class="task-link">{{ log.task_name }}</router-link>
                  <span>{{ formatTime(log.created_at) }}</span>
                </div>
                <div class="log-line small" :class="'log-' + (log.level || 'info').toLowerCase()">
                  <span class="log-level">[{{ log.level }}]</span> {{ log.message }}
                </div>
              </div>
              <p v-if="!data.recent_logs.length" class="text-muted text-center py-4 mb-0">暂无日志</p>
            </div>
          </div>
        </div>

        <div class="col-lg-6">
          <div class="card h-100">
            <div class="card-header"><h5 class="mb-0"><i class="bi bi-clock-history me-1"></i>最近操作</h5></div>
            <ul class="list-group list-group-flush recent-ops-scroll">
              <li
                v-for="op in data.recent_operations"
                :key="'op-' + op.id"
                class="list-group-item"
              >
                <div class="d-flex justify-content-between align-items-start gap-2">
                  <div class="flex-grow-1">
                    <router-link :to="`/task/${op.task_id}`" class="task-link fw-semibold">{{ op.task_name }}</router-link>
                    <div class="small mt-1 text-break">{{ op.message }}</div>
                  </div>
                  <span class="text-muted small text-nowrap">{{ formatTime(op.created_at) }}</span>
                </div>
              </li>
            </ul>
            <p v-if="!data.recent_operations.length" class="text-muted text-center py-4 mb-0">暂无操作记录</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { migrationTaskApi } from '@/api'
import type { TaskMonitorResponse, TaskMonitorItem, TaskMonitorLogEntry } from '@/api'
import PageHeader from '@/components/PageHeader.vue'

const refreshSec = 4
const loading = ref(false)
const autoRefresh = ref(true)
const data = ref<TaskMonitorResponse | null>(null)
const lastRefresh = ref<string>('')
const selectedTaskId = ref<number | null>(null)
const taskStructuredLogs = ref<TaskMonitorLogEntry[]>([])
let timer: ReturnType<typeof setInterval> | null = null

/** 当前执行中的实时任务列表 */
const liveTasks = computed(() => data.value?.running_tasks ?? data.value?.tasks ?? [])

/** 监控概览统计卡片配置 */
const summaryCards = [
  { key: 'running', label: '执行中', icon: 'bi-activity', bg: 'rgba(37, 99, 235, 0.1)', color: 'var(--primary)' },
  { key: 'pending', label: '待执行', icon: 'bi-hourglass-split', bg: 'rgba(100, 116, 139, 0.1)', color: 'var(--text-muted)' },
  { key: 'completed', label: '已完成', icon: 'bi-check-circle', bg: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)' },
  { key: 'failed', label: '失败', icon: 'bi-x-circle', bg: 'rgba(220, 38, 38, 0.1)', color: 'var(--danger)' },
]

const selectedTask = computed(() => {
  if (!selectedTaskId.value || !data.value) return null
  return liveTasks.value.find(t => t.id === selectedTaskId.value) ?? null
})

const selectedLogTail = computed(() => selectedTask.value?.log_tail || '')

async function loadTaskLogs(taskId: number) {
  try {
    const res = await migrationTaskApi.logs(taskId, { page_size: 40 })
    taskStructuredLogs.value = (res.data.results || []) as TaskMonitorLogEntry[]
  } catch {
    taskStructuredLogs.value = []
  }
}

function selectTask(t: TaskMonitorItem) {
  selectedTaskId.value = t.id
  if (!t.log_tail) loadTaskLogs(t.id)
  else taskStructuredLogs.value = []
}

async function loadMonitor() {
  loading.value = true
  try {
    const res = await migrationTaskApi.monitor({ task_limit: 50, log_limit: 80, compare_limit: 30 })
    data.value = res.data
    lastRefresh.value = res.data.server_time || new Date().toISOString()
    const running = res.data.running_tasks?.length ? res.data.running_tasks : res.data.tasks
    if (!running.length) {
      selectedTaskId.value = null
      taskStructuredLogs.value = []
    } else if (!selectedTaskId.value || !running.some(t => t.id === selectedTaskId.value)) {
      selectTask(running[0])
    } else {
      const still = running.find(t => t.id === selectedTaskId.value)
      if (still && !still.log_tail) loadTaskLogs(still.id)
    }
  } catch (e) {
    console.error('加载监控数据失败', e)
  } finally {
    loading.value = false
  }
}

function setupTimer() {
  if (timer) clearInterval(timer)
  if (autoRefresh.value) timer = setInterval(() => loadMonitor(), refreshSec * 1000)
}

watch(autoRefresh, setupTimer)

onMounted(() => {
  loadMonitor()
  setupTimer()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const getStatusBadgeClass = (status: string) => {
  const m: Record<string, string> = {
    pending: 'bg-secondary',
    running: 'bg-primary',
    completed: 'bg-success',
    failed: 'bg-danger',
    partial: 'bg-warning text-dark',
    canceled: 'bg-dark',
    aborted: 'bg-danger',
  }
  return m[status] || 'bg-secondary'
}

const getStatusText = (status: string) => {
  const m: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    partial: '部分完成',
    canceled: '已取消',
    aborted: '异常停止',
  }
  return m[status] || status
}

const getIncrementalLabel = (t: TaskMonitorItem) => {
  if (t.incremental_mode === 'pk_mirror') return '主键对齐'
  if (t.incremental_mode === 'timestamp') return '水位列'
  if (t.schedule_enabled) return '定时'
  return '全量'
}

const formatDate = (s?: string) => (s ? new Date(s).toLocaleString('zh-CN') : '-')

const formatTime = (s?: string) => {
  if (!s) return ''
  return new Date(s).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatViewProgress(t: TaskMonitorItem): string {
  const vp = t.view_progress
  if (!vp || typeof vp !== 'object') return '—'
  if ('current' in vp && 'total' in vp) {
    const cur = vp.current as number
    const tot = vp.total as number
    const tbl = vp.current_table as string
    if (tbl && typeof vp[tbl] === 'object') {
      const inner = vp[tbl] as Record<string, unknown>
      if (inner.migrated_rows != null && inner.total_rows != null) {
        const pct = inner.progress != null ? ` ${Number(inner.progress).toFixed(0)}%` : ''
        return `${tbl} ${inner.migrated_rows}/${inner.total_rows} 行${pct}（${cur}/${tot} 表）`
      }
    }
    return tbl ? `表 ${cur}/${tot}：${tbl}` : `表 ${cur}/${tot}`
  }
  const keys = Object.keys(vp)
  if (keys.length === 1 && typeof vp[keys[0]] === 'object') {
    const inner = vp[keys[0]] as Record<string, unknown>
    if (inner.migrated_rows != null && inner.total_rows != null) {
      return `${inner.migrated_rows}/${inner.total_rows} 行`
    }
  }
  return '—'
}
</script>

<style scoped>
.task-monitor-view {
  animation: fadeIn 0.4s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-header h1 {
  display: flex;
  align-items: center;
  font-weight: 700;
  color: var(--text);
}

.stat-card .stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--primary);
}

.stat-card .stat-label {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.pulse-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #fff;
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

.task-link {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}

.task-link:hover {
  text-decoration: underline;
}

.task-list-scroll {
  max-height: 480px;
  overflow-y: auto;
}

.log-card-body {
  min-height: 320px;
}

.log-meta {
  background: var(--table-row-hover);
}

.log-panel {
  max-height: 400px;
  overflow-y: auto;
  background: var(--log-bg, #1e1e2e);
  color: var(--log-fg, #cdd6f4);
}

.log-pre {
  font-size: 0.8rem;
  white-space: pre-wrap;
  word-break: break-all;
  color: inherit;
  background: transparent;
}

.log-line {
  font-size: 0.8rem;
  font-family: ui-monospace, monospace;
}

.log-time {
  color: #6c7086;
  margin-right: 0.5rem;
}

.log-level {
  color: #89b4fa;
  margin-right: 0.35rem;
}

.log-error,
.log-err { color: #f38ba8; }
.log-warning,
.log-warn { color: #fab387; }
.log-info { color: #a6e3a1; }

.monitor-task-table thead th {
  background: var(--gradient);
  color: white;
  font-size: 0.8rem;
}

.task-row {
  cursor: pointer;
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.sticky-top {
  position: sticky;
  top: 0;
  z-index: 1;
}

.log-stream,
.recent-ops-scroll {
  max-height: 360px;
  overflow-y: auto;
}

.log-stream-item:hover {
  background: var(--table-row-hover);
}
</style>
