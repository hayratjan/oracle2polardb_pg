<template>
  <div class="task-list-view">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h1>迁移任务</h1>
      <router-link to="/task/create" class="btn btn-primary">创建任务</router-link>
    </div>
    
    <div class="card">
      <div class="card-body">
        <div v-if="loading" class="text-center">
          <div class="spinner-border" role="status"></div>
        </div>
        <div v-else-if="tasks.length > 0">
          <table class="table table-striped">
            <thead>
              <tr>
                <th>任务名称</th>
                <th>类型</th>
                <th>源数据库</th>
                <th>目标数据库</th>
                <th>状态</th>
                <th>进度</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in tasks" :key="task.id">
                <td>
                  <router-link :to="`/task/${task.id}`">{{ task.name }}</router-link>
                </td>
                <td>{{ getTaskTypeText(task.task_type) }}</td>
                <td>{{ task.source_db }}</td>
                <td>{{ task.target_db }}</td>
                <td>
                  <span class="badge" :class="getStatusBadgeClass(task.status)">
                    {{ getStatusText(task.status) }}
                  </span>
                </td>
                <td>
                  <div class="progress" style="width: 100px">
                    <div class="progress-bar" :class="getProgressBarClass(task.status)"
                         :style="{ width: task.progress + '%' }"></div>
                  </div>
                  {{ task.progress.toFixed(1) }}%
                </td>
                <td>{{ formatDate(task.created_at) }}</td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <router-link :to="`/task/${task.id}`" class="btn btn-info">详情</router-link>
                    <button v-if="task.status === 'pending'" @click="startTask(task.id)" 
                            class="btn btn-success">开始</button>
                    <button v-if="task.status === 'running'" @click="cancelTask(task.id)" 
                            class="btn btn-warning">取消</button>
                    <button @click="deleteTask(task.id)" class="btn btn-danger">删除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="text-center text-muted">
          暂无任务
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
  try {
    await migrationTaskApi.start(id)
    await loadTasks()
  } catch (error) {
    console.error('Failed to start task:', error)
  }
}

const cancelTask = async (id: number) => {
  if (!confirm('确定要取消此任务吗？')) return
  try {
    await migrationTaskApi.cancel(id)
    await loadTasks()
  } catch (error) {
    console.error('Failed to cancel task:', error)
  }
}

const deleteTask = async (id: number) => {
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