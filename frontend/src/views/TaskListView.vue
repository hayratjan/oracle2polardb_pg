<template>
  <div class="task-list-view">
    <div class="page-header mb-4">
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <h1 class="mb-1">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-list-task me-2" viewBox="0 0 16 16">
              <path fill-rule="evenodd" d="M2 2.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5V3a.5.5 0 00-.5-.5H2zM3 3H2v1h1V3z"/>
              <path d="M5 3.5a.5.5 0 01.5-.5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5zM5.5 7a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM6 8H5v1h1V8z"/>
              <path d="M8 7.5a.5.5 0 01.5-.5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5zm.5 4a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM9 13H8v1h1v-1z"/>
            </svg>
            迁移任务
          </h1>
          <p class="text-muted mb-0">管理和监控数据库迁移任务</p>
        </div>
        <router-link to="/task/create" class="btn btn-sm btn-primary">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-plus-circle me-2" viewBox="0 0 16 16">
            <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
          </svg>
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
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-file-text me-1" viewBox="0 0 16 16">
                      <path d="M5 4a.5.5 0 00-.496.438l-.5 4A.5.5 0 004.5 9h3.5v2.5a.5.5 0 00.5.5H9v1h-1a.5.5 0 000 1h1a.5.5 0 00.5-.5V9h.5a.5.5 0 00.496-.438l.5-4A.5.5 0 0011 4H5zM4 14a1 1 0 011-1h6a1 1 0 011 1v1H4v-1z"/>
                    </svg>
                    任务名称
                  </th>
                  <th>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-tag me-1" viewBox="0 0 16 16">
                      <path d="M6 4.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM4.5 6a1.5 1.5 0 100 3 1.5 1.5 0 000-3zM6 8.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM4.5 10a1.5 1.5 0 100 3 1.5 1.5 0 000-3z"/>
                    </svg>
                    类型
                  </th>
                  <th>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-left-right me-1" viewBox="0 0 16 16">
                      <path fill-rule="evenodd" d="M1 11.5a.5.5 0 00.5.5h11.793l-3.147 3.146a.5.5 0 00.708.708l4-4a.5.5 0 000-.708l-4-4a.5.5 0 00-.708.708L13.293 11H1.5a.5.5 0 00-.5.5zm14-7a.5.5 0 00-.5-.5H2.707l3.147-3.146a.5.5 0 10-.708-.708l-4 4a.5.5 0 000 .708l4 4a.5.5 0 00.708-.708L2.707 4H14.5a.5.5 0 00.5-.5z"/>
                    </svg>
                    迁移路径
                  </th>
                  <th>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-info-circle me-1" viewBox="0 0 16 16">
                      <path d="M8 16A8 8 0 108 0a8 8 0 000 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 110-2 1 1 0 010 2z"/>
                    </svg>
                    状态
                  </th>
                  <th>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-speedometer2 me-1" viewBox="0 0 16 16">
                      <path d="M8 4a.5.5 0 01.5.5V6a.5.5 0 01-1 0V4.5A.5.5 0 018 4zM3.732 5.732a.5.5 0 01.707 0l.915.914a.5.5 0 11-.708.708l-.914-.915a.5.5 0 010-.707zM2 10a.5.5 0 01.5-.5h1.586a.5.5 0 010 1H2.5A.5.5 0 012 10zm9.5 0a.5.5 0 01.5-.5h1.5a.5.5 0 010 1H12a.5.5 0 01-.5-.5zm.754-4.246a.389.389 0 00-.527-.02L9.447 8.316a.5.5 0 00-.063.625l.8 1.6a.5.5 0 00.866.5l1.6-.8a.5.5 0 00.063-.625l-.8-1.6a.5.5 0 00-.466-.316z"/>
                      <path fill-rule="evenodd" d="M13.5 8a5.5 5.5 0 11-11 0 5.5 5.5 0 0111 0zM8 4a4 4 0 100 8 4 4 0 000-8z"/>
                    </svg>
                    进度
                  </th>
                  <th>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-calendar3 me-1" viewBox="0 0 16 16">
                      <path d="M14 0H2a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2V2a2 2 0 00-2-2zM1 3.857C1 3.384 1.448 3 2 3h12c.552 0 1 .384 1 .857v10.286c0 .473-.448.857-1 .857H2c-.552 0-1-.384-1-.857V3.857z"/>
                    </svg>
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
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" class="bi bi-database me-1" viewBox="0 0 16 16">
                          <path d="M4.318 6.318a4.5 4.5 0 000 6.364L7.318 15.4a1.5 1.5 0 002.122 0l2.999-2.999a4.5 4.5 0 000-6.364L9.55 4.55a1.5 1.5 0 00-2.122 0L4.318 6.318zM5.732 7.732l2.999-2.999a.5.5 0 01.707 0l2.999 2.999a3.5 3.5 0 010 4.95l-2.999 2.999a.5.5 0 01-.707 0L5.732 12.682a3.5 3.5 0 010-4.95z"/>
                        </svg>
                        {{ task.source_db }}
                      </div>
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-right mx-2" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M1 8a.5.5 0 01.5-.5h11.793l-3.147-3.146a.5.5 0 01.708-.708l4 4a.5.5 0 010 .708l-4 4a.5.5 0 01-.708-.708L13.293 8.5H1.5A.5.5 0 011 8z"/>
                      </svg>
                      <div class="target-db">
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" class="bi bi-server me-1" viewBox="0 0 16 16">
                          <path d="M1.5 0h11.586a1.5 1.5 0 011.06.44l1.415 1.414A1.5 1.5 0 0116 2.914V14.5a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 010 14.5v-11A1.5 1.5 0 011.5 2zM1 1.5v1a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zm0 4v9a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-9a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zM2 7a1 1 0 011-1h10a1 1 0 011 1v2a1 1 0 01-1 1H3a1 1 0 01-1-1V7zm0 5a1 1 0 011-1h6a1 1 0 011 1v1a1 1 0 01-1 1H3a1 1 0 01-1-1v-1z"/>
                        </svg>
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
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-eye" viewBox="0 0 16 16">
                          <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 011.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0114.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 011.172 8z"/>
                          <path d="M8 5.5a2.5 2.5 0 110 5 2.5 2.5 0 010-5zM4.5 8a3.5 3.5 0 117 0 3.5 3.5 0 01-7 0z"/>
                        </svg>
                      </router-link>
                      <button v-if="task.status === 'pending' && task.id" @click="startTask(task.id)" 
                              class="btn btn-sm btn-success" title="开始">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-play-fill" viewBox="0 0 16 16">
                          <path d="M11.596 8.697l-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 010 1.393z"/>
                        </svg>
                      </button>
                      <button v-if="task.status === 'running' && task.id" @click="cancelTask(task.id)" 
                              class="btn btn-sm btn-warning" title="取消">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-x-circle-fill" viewBox="0 0 16 16">
                          <path d="M16 8A8 8 0 110 8a8 8 0 0116 0zM5.354 4.646a.5.5 0 10-.708.708L7.293 8l-2.647 2.646a.5.5 0 00.708.708L8 8.707l2.646 2.647a.5.5 0 00.708-.708L8.707 8l2.647-2.646a.5.5 0 00-.708-.708L8 7.293 5.354 4.646z"/>
                        </svg>
                      </button>
                      <button v-if="task.id" @click="deleteTask(task.id)" class="btn btn-sm btn-danger" title="删除">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
                          <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
                          <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="text-center py-5 empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" fill="currentColor" class="bi bi-inbox mb-3" viewBox="0 0 16 16">
            <path d="M4.98 4a.5.5 0 00-.39.188L1.54 8H6a.5.5 0 01.5.5 1.5 1.5 0 003 0A.5.5 0 0110 8h4.46l-3.05-3.812A.5.5 0 0011.02 4H4.98zm9.954 5H10.45a2.5 2.5 0 01-4.9 0H1.066l.32 2.562a.5.5 0 00.497.438h12.234a.5.5 0 00.496-.438L14.933 9zM3.809 3.563A1.5 1.5 0 014.981 3h6.038a1.5 1.5 0 011.172.563l3.7 4.625a.5.5 0 01.105.374l-.39 3.124A1.5 1.5 0 0114.117 13H1.883a1.5 1.5 0 01-1.489-1.314l-.39-3.124a.5.5 0 01.105-.374l3.7-4.625z"/>
          </svg>
          <h4 class="mb-3">暂无任务</h4>
          <p class="text-muted mb-4">还没有创建任何迁移任务</p>
          <router-link to="/task/create" class="btn btn-primary btn-sm">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-plus-circle me-2" viewBox="0 0 16 16">
              <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
            </svg>
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
  color: #cbd5e0;
  margin-bottom: 1.5rem;
}

.empty-state h4 {
  color: #4a5568;
  font-weight: 600;
}

.empty-state p {
  color: #718096;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table tbody td {
  padding: 1rem;
  vertical-align: middle;
  border-color: #e2e8f0;
}

.table tbody tr {
  transition: all 0.3s ease;
}

.table tbody tr:hover {
  background-color: rgba(102, 126, 234, 0.05);
  transform: scale(1.01);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.table tbody tr:hover .task-name-link {
  color: #764ba2;
}
</style>