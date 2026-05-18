<template>
  <div class="task-list-view">
    <div class="page-header mb-4">
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <h1 class="mb-1">
            <i class="bi bi-list-task me-2" style="font-size: 32px;"></i>
            迁移任务
          </h1>
          <p class="text-muted mb-0">管理和监控数据库迁移任务</p>
        </div>
        <router-link to="/task/create" class="btn btn-sm btn-primary">
          <i class="bi bi-plus-circle me-2"></i>
          创建任务
        </router-link>
      </div>
    </div>
    
    <div class="card">
      <!-- 批量操作栏：有选中项时显示 -->
      <div v-if="selectedIds.size > 0" class="card-header d-flex align-items-center flex-wrap gap-2 batch-toolbar">
        <span class="text-muted">已选 <strong>{{ selectedIds.size }}</strong> 项</span>
        <button type="button" class="btn btn-sm btn-success" @click="batchStart" :disabled="batchStartDisabled">
          <i class="bi bi-play-fill me-1"></i>批量运行
        </button>
        <button type="button" class="btn btn-sm btn-danger" @click="batchDelete" :disabled="batchDeleteDisabled">
          <i class="bi bi-trash me-1"></i>批量删除
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="clearSelection">取消选择</button>
      </div>
      <div class="card-body">
        <div v-if="loading" class="text-center py-5">
          <div class="spinner-border text-primary" role="status"></div>
          <p class="mt-3 text-muted">加载任务列表...</p>
        </div>
        <div v-else-if="tasks.length > 0">
          <div class="table-responsive">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th style="width: 44px;">
                    <input type="checkbox" class="form-check-input" :checked="isAllSelected" :indeterminate="isIndeterminate"
                           @change="toggleSelectAll" title="全选" />
                  </th>
                  <th>
                    <i class="bi bi-file-text me-1"></i>
                    任务名称
                  </th>
                  <th>
                    <i class="bi bi-tag me-1"></i>
                    类型
                  </th>
                  <th>
                    <i class="bi bi-arrow-left-right me-1"></i>
                    迁移路径
                  </th>
                  <th>
                    <i class="bi bi-info-circle me-1"></i>
                    状态
                  </th>
                  <th>
                    <i class="bi bi-speedometer2 me-1"></i>
                    进度
                  </th>
                  <th>
                    <i class="bi bi-calendar3 me-1"></i>
                    创建时间
                  </th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="task in tasks" :key="task.id">
                  <td>
                    <input v-if="task.id && canSelectTask(task)" type="checkbox" class="form-check-input"
                           :checked="selectedIds.has(task.id)" @change="toggleSelect(task.id!)" />
                    <span v-else class="text-muted">—</span>
                  </td>
                  <td>
                    <router-link :to="`/task/${task.id}`" class="task-name-link">
                      {{ task.name }}
                    </router-link>
                  </td>
                  <td>
                    <span class="badge type-badge" :class="getTypeBadgeClass(task.task_type)">
                      {{ getTaskTypeText(task.task_type) }}
                    </span>
                  </td>
                  <td>
                    <div class="migration-path">
                      <div class="source-db">
                        <i class="bi bi-database me-1" style="font-size: 12px;"></i>
                        {{ task.source_db }}
                      </div>
                      <i class="bi bi-arrow-right mx-2" style="font-size: 16px;"></i>
                      <div class="target-db">
                        <i class="bi bi-server me-1" style="font-size: 12px;"></i>
                        {{ task.target_db }}
                      </div>
                    </div>
                  </td>
                  <td>
                    <span class="badge status-badge" :class="getStatusBadgeClass(task.status)">
                      <span class="status-dot"></span>
                      {{ getStatusText(task.status) }}
                    </span>
                  </td>
                  <td>
                    <div class="progress-wrapper">
                      <div class="progress">
                        <div class="progress-bar" :class="getProgressBarClass(task.status)"
                             :style="{ width: task.progress + '%' }"></div>
                      </div>
                      <span class="progress-text">{{ task.progress.toFixed(1) }}%</span>
                    </div>
                  </td>
                  <td>
                    <div class="text-muted small">
                      {{ formatDate(task.created_at) }}
                    </div>
                  </td>
                  <td>
                    <div class="btn-group btn-group-sm">
                      <router-link :to="`/task/${task.id}`" class="btn btn-sm btn-info" title="详情">
                        <i class="bi bi-eye" style="font-size: 14px;"></i>
                      </router-link>
                      <button v-if="task.status === 'pending' && task.id" @click="startTask(task.id)" 
                              class="btn btn-sm btn-success" title="开始">
                        <i class="bi bi-play-fill" style="font-size: 14px;"></i>
                      </button>
                      <button v-if="task.status === 'running' && task.id" @click="cancelTask(task.id)" 
                              class="btn btn-sm btn-warning" title="取消">
                        <i class="bi bi-x-circle-fill" style="font-size: 14px;"></i>
                      </button>
                      <button v-if="canResume(task) && task.id" @click="resumeTask(task.id)" 
                              class="btn btn-sm btn-success" title="继续迁移">
                        <i class="bi bi-skip-forward-fill" style="font-size: 14px;"></i>
                      </button>
                      <button v-if="canRerun(task.status) && task.id" @click="restartTask(task.id)" 
                              class="btn btn-sm btn-primary" title="从头重新运行">
                        <i class="bi bi-arrow-repeat" style="font-size: 14px;"></i>
                      </button>
                      <button v-if="task.id" @click="deleteTask(task.id)" class="btn btn-sm btn-danger" title="删除">
                        <i class="bi bi-trash" style="font-size: 14px;"></i>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- 分页 -->
          <div v-if="totalCount > 0" class="d-flex align-items-center justify-content-between flex-wrap gap-2 mt-3 pt-3 border-top pagination-bar">
            <div class="text-muted small">
              共 <strong>{{ totalCount }}</strong> 条，当前第 {{ rangeStart }}-{{ rangeEnd }} 条
            </div>
            <div class="d-flex align-items-center gap-2 flex-wrap">
              <button type="button" class="btn btn-sm btn-outline-primary" :disabled="!hasPrev" @click="goPage(currentPage - 1)">
                <i class="bi bi-chevron-left"></i> 上一页
              </button>
              <span class="small text-muted">第 {{ currentPage }} / {{ totalPages }} 页</span>
              <div class="d-flex align-items-center gap-1 jump-page-wrap">
                <span class="small text-muted">跳至</span>
                <input v-model.number="jumpPageInput" type="number" class="form-control form-control-sm jump-page-input"
                       min="1" :max="totalPages" placeholder="页" @keyup.enter="jumpToPage" />
                <span class="small text-muted">页</span>
                <button type="button" class="btn btn-sm btn-outline-secondary" @click="jumpToPage" title="跳转到指定页">跳转</button>
              </div>
              <button type="button" class="btn btn-sm btn-outline-primary" :disabled="!hasNext" @click="goPage(currentPage + 1)">
                下一页 <i class="bi bi-chevron-right"></i>
              </button>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-5 empty-state">
          <i class="bi bi-inbox mb-3" style="font-size: 80px;"></i>
          <h4 class="mb-3">暂无任务</h4>
          <p class="text-muted mb-4">还没有创建任何迁移任务</p>
          <router-link to="/task/create" class="btn btn-primary btn-sm">
            <i class="bi bi-plus-circle me-2"></i>
            创建第一个任务
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { migrationTaskApi } from '@/api'
import type { MigrationTask } from '@/api'

const pageSize = 20
const loading = ref(false)
const tasks = ref<MigrationTask[]>([])
const totalCount = ref(0)
const currentPage = ref(1)
/** 跳转页码输入框的值（用于跳转到指定页） */
const jumpPageInput = ref<number | ''>('')
/** 当前页选中的任务 id 集合（仅当前页） */
const selectedIds = ref<Set<number>>(new Set())

// 分页计算
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize)))
const hasPrev = computed(() => currentPage.value > 1)
const hasNext = computed(() => currentPage.value < totalPages.value)
const rangeStart = computed(() => (currentPage.value - 1) * pageSize + 1)
const rangeEnd = computed(() => Math.min(currentPage.value * pageSize, totalCount.value))

// 全选状态：当前页可选项是否全部选中
const selectableTasks = computed(() => tasks.value.filter(t => t.id && canSelectTask(t)))
const isAllSelected = computed(() =>
  selectableTasks.value.length > 0 && selectableTasks.value.every(t => selectedIds.value.has(t.id!)))
const isIndeterminate = computed(() => {
  const n = selectableTasks.value.filter(t => selectedIds.value.has(t.id!)).length
  return n > 0 && n < selectableTasks.value.length
})

// 批量运行：仅当存在可运行任务时可用（pending 或可重跑）
const canRerunStatus = (status: string) => ['failed', 'completed', 'partial', 'canceled', 'aborted'].includes(status)
const batchStartDisabled = computed(() =>
  ![...selectedIds.value].some(id => {
    const t = tasks.value.find(x => x.id === id)
    return t && (t.status === 'pending' || canRerunStatus(t.status))
  }))
// 批量删除：运行中的不能删，存在非运行中的即可点
const batchDeleteDisabled = computed(() =>
  ![...selectedIds.value].some(id => {
    const t = tasks.value.find(x => x.id === id)
    return t && t.status !== 'running'
  }))

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

const getTypeBadgeClass = (type: string) => {
  const classes: Record<string, string> = {
    table: 'bg-primary',
    materialized_view: 'bg-info',
    view: 'bg-secondary',
    routine: 'bg-warning',
    all_tables: 'bg-success',
    view_to_table: 'bg-dark',
    view_to_sqlite: 'bg-danger',
  }
  return classes[type] || 'bg-secondary'
}

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

const getProgressBarClass = (status: string) => {
  const classes: Record<string, string> = {
    pending: 'bg-secondary',
    running: 'bg-primary progress-bar-striped progress-bar-animated',
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
    partial: '已中断',
    canceled: '已取消',
    aborted: '异常停止',
  }
  return texts[status] || status
}

const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

/** 可勾选的任务：非运行中可删；待执行或可重跑可运行 */
function canSelectTask(task: MigrationTask): boolean {
  return !!task.id
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectableTasks.value.forEach(t => { if (t.id) selectedIds.value.delete(t.id) })
    selectedIds.value = new Set(selectedIds.value)
  } else {
    selectableTasks.value.forEach(t => { if (t.id) selectedIds.value.add(t.id) })
    selectedIds.value = new Set(selectedIds.value)
  }
}

function toggleSelect(id: number) {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
  selectedIds.value = new Set(selectedIds.value)
}

function clearSelection() {
  selectedIds.value = new Set()
}

const loadTasks = async (page = 1) => {
  loading.value = true
  try {
    const res = await migrationTaskApi.list({ page, page_size: pageSize })
    const data = res.data as { results?: MigrationTask[]; count?: number; next?: string | null; previous?: string | null }
    tasks.value = data.results || (Array.isArray(res.data) ? res.data : [])
    totalCount.value = data.count ?? tasks.value.length
    currentPage.value = page
    // 翻页后清空当前页选择（可选：也可保留 selectedIds 只对当前页生效，这里清空更清晰）
    selectedIds.value = new Set()
  } catch (error) {
    console.error('Failed to load tasks:', error)
  } finally {
    loading.value = false
  }
}

function goPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  loadTasks(page)
}

/** 跳转到指定页：根据输入框页码跳转，无效则恢复输入框为当前页 */
function jumpToPage() {
  const p = jumpPageInput.value
  const num = typeof p === 'number' && !Number.isNaN(p) ? Math.floor(p) : NaN
  if (num >= 1 && num <= totalPages.value) {
    loadTasks(num)
    jumpPageInput.value = ''
  } else {
    jumpPageInput.value = currentPage.value
  }
}

/** 批量运行选中的可运行任务 */
async function batchStart() {
  const ids = [...selectedIds.value].filter(id => {
    const t = tasks.value.find(x => x.id === id)
    return t && (t.status === 'pending' || canRerunStatus(t.status))
  })
  if (ids.length === 0) return
  if (!confirm(`确定要运行选中的 ${ids.length} 个任务吗？`)) return
  for (const id of ids) {
    try {
      await migrationTaskApi.start(id)
    } catch (e) {
      console.error('Failed to start task:', id, e)
    }
  }
  clearSelection()
  await loadTasks(currentPage.value)
}

/** 批量删除选中的非运行中任务 */
async function batchDelete() {
  const ids = [...selectedIds.value].filter(id => {
    const t = tasks.value.find(x => x.id === id)
    return t && t.status !== 'running'
  })
  if (ids.length === 0) return
  if (!confirm(`确定要删除选中的 ${ids.length} 个任务吗？运行中的任务将跳过。`)) return
  for (const id of ids) {
    try {
      await migrationTaskApi.delete(id)
    } catch (e) {
      console.error('Failed to delete task:', id, e)
    }
  }
  clearSelection()
  await loadTasks(currentPage.value)
}

const canRerun = (status: string) =>
  ['failed', 'completed', 'partial', 'canceled', 'aborted'].includes(status)

const canResume = (t: MigrationTask) =>
  ['failed', 'partial', 'canceled', 'aborted'].includes(t.status) &&
  ['all_tables', 'table', 'full_schema'].includes(t.task_type)

const startTask = async (id: number) => {
  if (!id) return
  try {
    await migrationTaskApi.start(id, { resume: false })
    await loadTasks(currentPage.value)
  } catch (error) {
    console.error('Failed to start task:', error)
  }
}

const resumeTask = async (id: number) => {
  if (!id) return
  if (!confirm('从上次断点继续迁移？已成功的表将跳过。')) return
  try {
    await migrationTaskApi.start(id, { resume: true })
    await loadTasks(currentPage.value)
  } catch (error) {
    console.error('Failed to resume task:', error)
  }
}

const restartTask = async (id: number) => {
  if (!id) return
  if (!confirm('确定从头重新运行？将清空已完成记录。')) return
  try {
    await migrationTaskApi.start(id, { resume: false })
    await loadTasks(currentPage.value)
  } catch (error) {
    console.error('Failed to restart task:', error)
  }
}

const cancelTask = async (id: number) => {
  if (!id) return
  if (!confirm('确定要取消此任务吗？')) return
  try {
    await migrationTaskApi.cancel(id)
    await loadTasks(currentPage.value)
  } catch (error) {
    console.error('Failed to cancel task:', error)
  }
}

const deleteTask = async (id: number) => {
  if (!id) return
  if (!confirm('确定要删除此任务吗？')) return
  try {
    await migrationTaskApi.delete(id)
    await loadTasks(currentPage.value)
  } catch (error) {
    console.error('Failed to delete task:', error)
  }
}

onMounted(() => {
  loadTasks(1)
})
</script>

<style scoped>
.task-list-view {
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

.task-name-link {
  text-decoration: none;
  font-weight: 600;
  color: var(--primary);
  transition: all 0.3s ease;
}

.task-name-link:hover {
  color: var(--secondary);
  transform: translateX(3px);
}

.type-badge {
  font-weight: 500;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
}

.status-badge {
  font-weight: 500;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
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

.migration-path {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.source-db,
.target-db {
  display: flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  border-radius: 0.375rem;
  background-color: var(--table-row-hover);
  color: var(--primary);
  font-weight: 500;
}

.target-db {
  background-color: var(--table-row-hover);
  color: var(--secondary);
}

.progress-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 150px;
}

.progress {
  flex: 1;
  height: 0.625rem;
  border-radius: 0.5rem;
  background-color: var(--border);
  overflow: hidden;
}

.progress-bar {
  border-radius: 0.5rem;
  transition: width 0.6s ease;
}

.progress-text {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--primary);
  min-width: 45px;
  text-align: right;
}

.btn-group .btn {
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  margin: 0 0.125rem;
}

.btn-group .btn:first-child {
  margin-left: 0;
}

.btn-group .btn:last-child {
  margin-right: 0;
}

.empty-state {
  padding: 4rem 2rem;
}

.empty-state svg {
  color: var(--border);
  margin-bottom: 1.5rem;
}

.empty-state h4 {
  color: var(--text);
  font-weight: 600;
}

.empty-state p {
  color: var(--text-muted);
  font-size: 1.1rem;
}

/* 批量操作栏 */
.batch-toolbar {
  background: var(--table-row-hover);
  border-bottom: 1px solid var(--border);
}

/* 分页栏 */
.pagination-bar {
  color: var(--text-muted);
}

.jump-page-wrap {
  margin-left: 0.25rem;
}

.jump-page-input {
  width: 4rem;
  text-align: center;
}

.table {
  margin-bottom: 0;
}

.table thead th {
  border: none;
  padding: 1rem;
  font-weight: 600;
  color: white;
  background: var(--gradient);
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table tbody td {
  padding: 1rem;
  vertical-align: middle;
  border-color: var(--border);
}

.table tbody tr {
  transition: all 0.3s ease;
}

.table tbody tr:hover {
  background-color: var(--table-row-hover);
  transform: scale(1.01);
  box-shadow: 0 4px 12px var(--shadow-light);
}

.table tbody tr:hover .task-name-link {
  color: var(--link-hover);
}
</style>
