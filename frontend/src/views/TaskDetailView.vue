<template>
  <div class="task-detail-view">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h1>任务详情</h1>
      <div>
        <router-link to="/tasks" class="btn btn-secondary">返回列表</router-link>
      </div>
    </div>
    
    <div v-if="loading" class="text-center">
      <div class="spinner-border" role="status"></div>
    </div>
    
    <div v-else-if="task">
      <div class="row">
        <div class="col-md-8">
          <div class="card mb-4">
            <div class="card-header">
              <h5>{{ task.name }}</h5>
            </div>
            <div class="card-body">
              <table class="table table-bordered">
                <tr>
                  <th>任务类型</th>
                  <td>{{ getTaskTypeText(task.task_type) }}</td>
                </tr>
                <tr>
                  <th>状态</th>
                  <td>
                    <span class="badge" :class="getStatusBadgeClass(task.status)">
                      {{ getStatusText(task.status) }}
                    </span>
                  </td>
                </tr>
                <tr>
                  <th>源数据库</th>
                  <td>{{ task.source_db }}</td>
                </tr>
                <tr>
                  <th>目标数据库</th>
                  <td>{{ task.target_db }}</td>
                </tr>
                <tr>
                  <th>源Schema</th>
                  <td>{{ task.source_schema }}</td>
                </tr>
                <tr>
                  <th>目标Schema</th>
                  <td>{{ task.target_schema || '-' }}</td>
                </tr>
                <tr>
                  <th>源对象</th>
                  <td>{{ task.source_object || '-' }}</td>
                </tr>
                <tr>
                  <th>目标对象</th>
                  <td>{{ task.target_object || '-' }}</td>
                </tr>
                <tr>
                  <th>冲突策略</th>
                  <td>{{ getConflictStrategyText(task.conflict_strategy) }}</td>
                </tr>
                <tr>
                  <th>创建时间</th>
                  <td>{{ formatDate(task.created_at) }}</td>
                </tr>
                <tr>
                  <th>开始时间</th>
                  <td>{{ formatDate(task.started_at) }}</td>
                </tr>
                <tr>
                  <th>完成时间</th>
                  <td>{{ formatDate(task.completed_at) }}</td>
                </tr>
              </table>
              
              <div class="mb-3">
                <label class="form-label">进度</label>
                <div class="progress">
                  <div class="progress-bar" :class="getProgressBarClass(task.status)"
                       :style="{ width: task.progress + '%' }"></div>
                </div>
                <div class="text-center mt-1">{{ task.progress.toFixed(1) }}%</div>
              </div>
              
              <div class="d-flex gap-2">
                <button v-if="task.status === 'pending'" @click="startTask" 
                        class="btn btn-success">开始任务</button>
                <button v-if="task.status === 'running'" @click="cancelTask" 
                        class="btn btn-warning">取消任务</button>
                <button @click="refreshStatus" class="btn btn-info">刷新状态</button>
                <button @click="deleteTask" class="btn btn-danger">删除任务</button>
              </div>
            </div>
          </div>
          
          <div class="card">
            <div class="card-header">
              <h5>日志</h5>
            </div>
            <div class="card-body">
              <pre class="bg-light p-3" style="max-height: 400px; overflow-y: auto">{{ task.log || '暂无日志' }}</pre>
            </div>
          </div>
        </div>
        
        <div class="col-md-4">
          <div class="card">
            <div class="card-header">
              <h5>任务操作</h5>
            </div>
            <div class="card-body">
              <div class="mb-3">
                <label class="form-label">切换目标数据库</label>
                <select v-model="selectedDatabase" class="form-select mb-2">
                  <option value="">请选择数据库</option>
                  <option v-for="db in databases" :key="db" :value="db">{{ db }}</option>
                </select>
                <button @click="switchDatabase" class="btn btn-primary w-100">切换</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
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

const loadTask = async () => {
  loading.value = true
  try {
    const res = await migrationTaskApi.get(Number(route.params.id))
    task.value = res.data
  } catch (error) {
    console.error('Failed to load task:', error)
  } finally {
    loading.value = false
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

const refreshStatus = async () => {
  await loadTask()
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
  
  if (task.value?.status === 'running') {
    statusInterval = window.setInterval(async () => {
      await loadTask()
      if (task.value?.status !== 'running' && statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
    }, 3000)
  }
})

onUnmounted(() => {
  if (statusInterval) {
    clearInterval(statusInterval)
  }
})
</script>