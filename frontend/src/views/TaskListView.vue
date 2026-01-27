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
                      <button v-if="task.id" @click="deleteTask(task.id)" class="btn btn-sm btn-danger" title="删除">
                        <i class="bi bi-trash" style="font-size: 14px;"></i>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
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
import { ref, onMounted } from 'vue'
import { migrationTaskApi } from '@/api'
import type { MigrationTask } from '@/api'

const loading = ref(false)
const tasks = ref<MigrationTask[]>([])

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

const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await migrationTaskApi.list()
    tasks.value = res.data.results || res.data
  } catch (error) {
    console.error('Failed to load tasks:', error)
  } finally {
    loading.value = false
  }
}

const startTask = async (id: number) => {
  if (!id) return
  try {
    await migrationTaskApi.start(id)
    await loadTasks()
  } catch (error) {
    console.error('Failed to start task:', error)
  }
}

const cancelTask = async (id: number) => {
  if (!id) return
  if (!confirm('确定要取消此任务吗？')) return
  try {
    await migrationTaskApi.cancel(id)
    await loadTasks()
  } catch (error) {
    console.error('Failed to cancel task:', error)
  }
}

const deleteTask = async (id: number) => {
  if (!id) return
  if (!confirm('确定要删除此任务吗？')) return
  try {
    await migrationTaskApi.delete(id)
    await loadTasks()
  } catch (error) {
    console.error('Failed to delete task:', error)
  }
}

onMounted(() => {
  loadTasks()
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
  color: #764ba2;
}
</style>