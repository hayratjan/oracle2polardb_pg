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
            <div class="stat-card-number">{{ (data.summary as any)[item.key] }}</div>
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
              <div v-if="selectedTask" class="px-3 py-2 border-bottom small log-meta-bar">
                <span class="badge me-1" :class="getStatusBadgeClass(selectedTask.status)">
                  {{ getStatusText(selectedTask.status) }}
                </span>
                <span class="text-muted">{{ formatViewProgress(selectedTask) }}</span>
                <span class="text-muted ms-2">共 {{ selectedLogTotalLines }} 行</span>
              </div>
              <!-- 日志工具栏：级别过滤 + 关键词搜索 + 自动滚动 + 复制 -->
              <div v-if="selectedTask" class="log-toolbar px-3 py-2 border-bottom">
                <div class="input-group input-group-sm">
                  <span class="input-group-text"><i class="bi bi-funnel"></i></span>
                  <select v-model="selectedLogLevelFilter" class="form-select">
                    <option value="">全部级别</option>
                    <option value="STEP">STEP · 阶段</option>
                    <option value="INFO">INFO · 信息</option>
                    <option value="OK">OK · 成功</option>
                    <option value="WARN">WARN · 警告</option>
                    <option value="ERROR">ERROR · 错误</option>
                    <option value="DATA">DATA · 数据</option>
                    <option value="SQL">SQL · 语句</option>
                    <option value="META">META · 元数据</option>
                  </select>
                  <input v-model="selectedLogSearchTerm" type="text" class="form-control" placeholder="搜索日志内容...">
                </div>
                <div class="btn-group btn-group-sm ms-2">
                  <button type="button" class="btn btn-outline-secondary" :class="{ active: autoScrollLog }" @click="autoScrollLog = !autoScrollLog" title="自动滚动到底部">
                    <i class="bi bi-arrow-down-circle"></i>
                  </button>
                  <button type="button" class="btn btn-outline-secondary" @click="scrollSelectedLogToBottom" title="跳到底部">
                    <i class="bi bi-chevron-double-down"></i>
                  </button>
                  <button type="button" class="btn btn-outline-secondary" @click="copySelectedLog" title="复制全文">
                    <i class="bi bi-clipboard"></i>
                  </button>
                </div>
              </div>
              <div ref="selectedLogContainer" class="log-panel flex-grow-1">
                <template v-if="filteredSelectedLogLines.length">
                  <div
                    v-for="(line, idx) in filteredSelectedLogLines"
                    :key="idx"
                    class="log-line"
                    :class="'log-' + line.level.toLowerCase()"
                  >
                    <span class="log-time">{{ line.time }}</span>
                    <span class="log-level-tag">[{{ line.level }}]</span>
                    <span class="log-text">{{ line.text }}</span>
                  </div>
                </template>
                <p v-else-if="selectedTask" class="text-muted small p-3 mb-0">没有匹配的日志行</p>
                <p v-else class="text-muted mb-0 p-3">点击左侧任务查看日志</p>
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
                <div class="log-line small" :class="'log-' + parseLogLevel(log).toLowerCase()">
                  <span class="log-level-tag">[{{ parseLogLevel(log) }}]</span>
                  <span class="log-text">{{ parseLogMessage(log) }}</span>
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
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

// ===== 日志面板相关 =====
const selectedLogLevelFilter = ref('')
const selectedLogSearchTerm = ref('')
const autoScrollLog = ref(true)
const selectedLogContainer = ref<HTMLElement | null>(null)

interface ParsedLogLine {
  level: string
  text: string
  time: string
}

const LEVEL_REGEX = /^\[(STEP|INFO|OK|WARN|ERROR|DATA|SQL|META)\]\s?(.*)$/

/** 解析单行日志文本，识别 [LEVEL] 前缀；无前缀时按内容启发式判断 */
function parsePlainLine(line: string): ParsedLogLine {
  const m = line.match(LEVEL_REGEX)
  if (m) return { level: m[1], text: m[2], time: '' }
  const upper = line.toUpperCase()
  if (line.startsWith('错误') || upper.includes('失败') || upper.includes('FAILED')) {
    return { level: 'ERROR', text: line, time: '' }
  }
  if (line.startsWith('警告') || upper.includes('WARN')) {
    return { level: 'WARN', text: line, time: '' }
  }
  if (line.startsWith('成功') || upper.includes('SUCCESS') || upper.includes('校验通过')) {
    return { level: 'OK', text: line, time: '' }
  }
  return { level: 'INFO', text: line, time: '' }
}

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

/**
 * 合并解析选中任务的日志行：
 * 1) 优先使用 log_tail 文本（按行拆分，解析 [LEVEL] 前缀）
 * 2) 若无 log_tail，则使用结构化日志 taskStructuredLogs（含时间戳）
 */
const parsedSelectedLogLines = computed<ParsedLogLine[]>(() => {
  const tail = selectedLogTail.value
  if (tail) {
    return tail.split('\n').filter(l => l.length > 0).map(parsePlainLine)
  }
  // 结构化日志（API 返回的带时间戳日志）
  return taskStructuredLogs.value.map(log => {
    const lvl = (log.level || 'INFO').toUpperCase()
    const msg = log.message || ''
    const m = msg.match(LEVEL_REGEX)
    if (m) {
      return { level: m[1], text: m[2], time: formatTime(log.created_at) }
    }
    return { level: lvl, text: msg, time: formatTime(log.created_at) }
  })
})

const selectedLogTotalLines = computed(() => parsedSelectedLogLines.value.length)

const filteredSelectedLogLines = computed<ParsedLogLine[]>(() => {
  let list = parsedSelectedLogLines.value
  if (selectedLogLevelFilter.value) {
    list = list.filter(l => l.level === selectedLogLevelFilter.value)
  }
  if (selectedLogSearchTerm.value.trim()) {
    const term = selectedLogSearchTerm.value.trim().toLowerCase()
    list = list.filter(l => l.text.toLowerCase().includes(term))
  }
  // 限制最多展示行数，避免大量日志拖慢渲染
  const MAX = 1500
  if (list.length > MAX) {
    return list.slice(-MAX)
  }
  return list
})

function scrollSelectedLogToBottom() {
  nextTick(() => {
    if (selectedLogContainer.value) {
      selectedLogContainer.value.scrollTop = selectedLogContainer.value.scrollHeight
    }
  })
}

async function copySelectedLog() {
  const text = selectedLogTail.value || parsedSelectedLogLines.value
    .map(l => l.time ? `${l.time} [${l.level}] ${l.text}` : `[${l.level}] ${l.text}`)
    .join('\n')
  if (!text) {
    alert('暂无日志可复制')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    alert('日志已复制到剪贴板')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    alert('日志已复制到剪贴板')
  }
}

/** 解析「运行日志流」中单条结构化日志的级别 */
function parseLogLevel(log: TaskMonitorLogEntry): string {
  const lvl = (log.level || 'INFO').toUpperCase()
  if (LEVEL_REGEX.test(lvl)) return lvl
  const msg = log.message || ''
  const m = msg.match(LEVEL_REGEX)
  if (m) return m[1]
  return lvl
}

/** 解析「运行日志流」中单条结构化日志的正文（去掉 [LEVEL] 前缀） */
function parseLogMessage(log: TaskMonitorLogEntry): string {
  const msg = log.message || ''
  const m = msg.match(LEVEL_REGEX)
  return m ? m[2] : msg
}

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

// 选中任务日志变化时自动滚动到底部
watch([selectedLogTail, taskStructuredLogs], () => {
  if (autoScrollLog.value) scrollSelectedLogToBottom()
})

watch(autoScrollLog, v => {
  if (v) scrollSelectedLogToBottom()
})

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

.log-meta-bar {
  background: var(--table-row-hover);
}

.log-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  background: #f8fafc;
}

.log-toolbar .input-group {
  flex: 1;
  min-width: 220px;
}

.log-panel {
  max-height: 420px;
  overflow-y: auto;
  background: #0f172a;
  color: #e2e8f0;
  padding: 0.75rem;
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.8rem;
  line-height: 1.55;
}

.log-panel::-webkit-scrollbar {
  width: 8px;
}

.log-panel::-webkit-scrollbar-track {
  background: #1e293b;
  border-radius: 4px;
}

.log-panel::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 4px;
}

.log-panel::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}

.log-line {
  padding: 0.15rem 0.5rem;
  border-left: 3px solid transparent;
  word-break: break-word;
  white-space: pre-wrap;
}

.log-line .log-time {
  color: #64748b;
  margin-right: 0.4rem;
  font-size: 0.72rem;
}

.log-line .log-text {
  color: #cbd5e1;
}

.log-level-tag {
  display: inline-block;
  min-width: 52px;
  font-weight: 600;
  margin-right: 0.35rem;
  font-size: 0.72rem;
}

/* STEP · 阶段（天蓝） */
.log-step {
  color: #38bdf8;
  border-left-color: #0ea5e9;
  background: rgba(14, 165, 233, 0.05);
}
.log-step .log-level-tag { color: #38bdf8; }

/* INFO · 信息（浅蓝） */
.log-info {
  color: #93c5fd;
}
.log-info .log-level-tag { color: #60a5fa; }

/* OK · 成功（绿） */
.log-ok {
  color: #86efac;
  border-left-color: #22c55e;
  background: rgba(34, 197, 94, 0.06);
}
.log-ok .log-level-tag { color: #4ade80; }

/* WARN · 警告（黄） */
.log-warn {
  color: #fde68a;
  border-left-color: #f59e0b;
  background: rgba(245, 158, 11, 0.06);
}
.log-warn .log-level-tag { color: #fbbf24; }

/* ERROR · 错误（红） */
.log-error {
  color: #fca5a5;
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}
.log-error .log-level-tag { color: #f87171; }

/* DATA · 数据（紫） */
.log-data {
  color: #d8b4fe;
  border-left-color: #a855f7;
  background: rgba(168, 85, 247, 0.05);
}
.log-data .log-level-tag { color: #c084fc; }

/* SQL · 语句（粉） */
.log-sql {
  color: #fbcfe8;
  border-left-color: #ec4899;
  background: rgba(236, 72, 153, 0.05);
}
.log-sql .log-level-tag { color: #f472b6; }

/* META · 元数据（灰） */
.log-meta {
  color: #cbd5e1;
  border-left-color: #64748b;
  background: rgba(100, 116, 139, 0.04);
}
.log-meta .log-level-tag { color: #94a3b8; }

/* 兼容旧级别名 */
.log-warning { color: #fde68a; border-left-color: #f59e0b; }
.log-err { color: #fca5a5; border-left-color: #ef4444; }

.log-pre {
  font-size: 0.8rem;
  white-space: pre-wrap;
  word-break: break-all;
  color: inherit;
  background: transparent;
}

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
