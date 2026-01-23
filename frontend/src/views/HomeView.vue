<template>
  <div class="home-view">
    <h1>Oracle到PolarDB-PG迁移平台</h1>
    <p class="lead">欢迎使用Oracle到PolarDB-PG数据库迁移平台</p>
    
    <div class="row mt-4">
      <div class="col-md-4">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">迁移任务</h5>
            <p class="card-text">管理和监控数据库迁移任务</p>
            <router-link to="/tasks" class="btn btn-primary">查看任务</router-link>
          </div>
        </div>
      </div>
      
      <div class="col-md-4">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">创建任务</h5>
            <p class="card-text">创建新的数据库迁移任务</p>
            <router-link to="/task/create" class="btn btn-success">创建任务</router-link>
          </div>
        </div>
      </div>
      
      <div class="col-md-4">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">数据库连接</h5>
            <p class="card-text">管理Oracle和PostgreSQL数据库连接</p>
            <router-link to="/oracle" class="btn btn-info">管理连接</router-link>
          </div>
        </div>
      </div>
    </div>
    
    <div class="row mt-4">
      <div class="col-md-6">
        <div class="card">
          <div class="card-header">
            <h5>最近任务</h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center">
              <div class="spinner-border" role="status"></div>
            </div>
            <div v-else-if="recentTasks.length > 0">
              <ul class="list-group">
                <li v-for="task in recentTasks" :key="task.id" class="list-group-item">
                  <router-link :to="`/task/${task.id}`">{{ task.name }}</router-link>
                  <span class="badge ms-2" :class="getStatusBadgeClass(task.status)">
                    {{ getStatusText(task.status) }}
                  </span>
                </li>
              </ul>
            </div>
            <div v-else class="text-muted">
              暂无任务
            </div>
          </div>
        </div>
      </div>
      
      <div class="col-md-6">
        <div class="card">
          <div class="card-header">
            <h5>数据库连接</h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center">
              <div class="spinner-border" role="status"></div>
            </div>
            <div v-else>
              <h6>Oracle连接: {{ oracleConnections.length }}</h6>
              <h6>PostgreSQL连接: {{ postgresConnections.length }}</h6>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { migrationTaskApi, oracleConnectionApi, postgresConnectionApi } from '@/api'
import type { MigrationTask } from '@/api'

const loading = ref(false)
const recentTasks = ref<MigrationTask[]>([])
const oracleConnections = ref<any[]>([])
const postgresConnections = ref<any[]>([])

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

onMounted(async () => {
  loading.value = true
  try {
    const [tasksRes, oracleRes, postgresRes] = await Promise.all([
      migrationTaskApi.list(),
      oracleConnectionApi.list(),
      postgresConnectionApi.list(),
    ])
    recentTasks.value = tasksRes.data.results?.slice(0, 5) || tasksRes.data.slice(0, 5)
    oracleConnections.value = oracleRes.data.results || oracleRes.data
    postgresConnections.value = postgresRes.data.results || postgresRes.data
  } catch (error) {
    console.error('Failed to load data:', error)
  } finally {
    loading.value = false
  }
})
</script>