<template>
  <div class="home-view">
    <div class="hero-section">
      <div class="container">
        <div class="row align-items-center">
          <div class="col-lg-8">
            <h1 class="display-4 fw-bold mb-3">Oracle到PolarDB-PG迁移平台</h1>
            <p class="lead mb-4">高效、安全、可靠的数据库迁移解决方案</p>
            <div class="d-flex gap-3">
              <router-link to="/task/create" class="btn btn-sm btn-light btn-gradient">
                <i class="bi bi-rocket-takeoff me-2"></i>
                立即开始
              </router-link>
              <router-link to="/tasks" class="btn btn-sm btn-outline-light">
                查看任务
              </router-link>
            </div>
          </div>
          <div class="col-lg-4 d-none d-lg-block">
            <div class="hero-image">
              <i class="bi bi-gem floating" style="font-size: 200px; color: #667eea;"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="container mt-5">
      <div class="row g-4">
        <div class="col-md-4">
          <div class="card feature-card">
            <div class="card-body text-center">
              <div class="feature-icon mb-3">
                <i class="bi bi-list-task"></i>
              </div>
              <h5 class="card-title">迁移任务</h5>
              <p class="card-text">管理和监控数据库迁移任务，实时查看进度和状态</p>
              <router-link to="/tasks" class="btn btn-sm btn-primary mt-3">查看任务</router-link>
            </div>
          </div>
        </div>
        
        <div class="col-md-4">
          <div class="card feature-card">
            <div class="card-body text-center">
              <div class="feature-icon mb-3">
                <i class="bi bi-plus-circle"></i>
              </div>
              <h5 class="card-title">创建任务</h5>
              <p class="card-text">快速创建新的数据库迁移任务，支持多种迁移类型</p>
              <router-link to="/task/create" class="btn btn-sm btn-success mt-3">创建任务</router-link>
            </div>
          </div>
        </div>
        
        <div class="col-md-4">
          <div class="card feature-card">
            <div class="card-body text-center">
              <div class="feature-icon mb-3">
                <i class="bi bi-database-gear"></i>
              </div>
              <h5 class="card-title">管理连接</h5>
              <p class="card-text">配置和管理Oracle和PostgreSQL数据库连接</p>
              <router-link to="/oracle" class="btn btn-sm btn-info mt-3">管理连接</router-link>
            </div>
          </div>
        </div>
      </div>
      
      <div class="row mt-5 g-4">
        <div class="col-md-6">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">
                <i class="bi bi-clock-history me-2"></i>
                最近任务
              </h5>
            </div>
            <div class="card-body">
              <div v-if="loading" class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-muted">加载中...</p>
              </div>
              <div v-else-if="recentTasks.length > 0">
                <ul class="list-group list-group-flush">
                  <li v-for="task in recentTasks" :key="task.id" class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                      <router-link :to="`/task/${task.id}`" class="text-decoration-none fw-bold">
                        {{ task.name }}
                      </router-link>
                      <div class="small text-muted mt-1">
                        {{ formatDate(task.created_at) }}
                      </div>
                    </div>
                    <span class="badge" :class="getStatusBadgeClass(task.status)">
                      {{ getStatusText(task.status) }}
                    </span>
                  </li>
                </ul>
              </div>
              <div v-else class="text-center py-4 text-muted">
                <i class="bi bi-inbox mb-3"></i>
                <p>暂无任务</p>
                <router-link to="/task/create" class="btn btn-sm btn-primary mt-2">创建第一个任务</router-link>
              </div>
            </div>
          </div>
        </div>
        
        <div class="col-md-6">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">
                <i class="bi bi-diagram-3 me-2"></i>
                数据库连接
              </h5>
            </div>
            <div class="card-body">
              <div v-if="loading" class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-muted">加载中...</p>
              </div>
              <div v-else>
                <div class="row text-center">
                  <div class="col-6">
                    <div class="connection-stat">
                      <div class="stat-icon oracle-icon">
                        <i class="bi bi-database"></i>
                      </div>
                      <div class="stat-number">{{ oracleConnections.length }}</div>
                      <div class="stat-label">Oracle连接</div>
                    </div>
                  </div>
                  <div class="col-6">
                    <div class="connection-stat">
                      <div class="stat-icon postgres-icon">
                        <i class="bi bi-server"></i>
                      </div>
                      <div class="stat-number">{{ postgresConnections.length }}</div>
                      <div class="stat-label">PostgreSQL连接</div>
                    </div>
                  </div>
                </div>
                <div class="mt-4 text-center">
                  <router-link to="/oracle" class="btn btn-outline-primary me-2">管理Oracle</router-link>
                  <router-link to="/postgres" class="btn btn-outline-info">管理PostgreSQL</router-link>
                </div>
              </div>
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

<style scoped>
.home-view {
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

.hero-section {
  background: var(--gradient);
  color: white;
  padding: 4rem 0;
  border-radius: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 20px 60px var(--shadow);
}

.hero-section h1 {
  color: white;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.hero-section .lead {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.5rem;
}

.btn-gradient {
  background: var(--gradient-secondary);
  border: none;
  color: white;
}

.btn-gradient:hover {
  background: var(--gradient-secondary);
  color: white;
  transform: translateY(-3px);
  box-shadow: 0 10px 30px var(--shadow);
}

.hero-image {
  position: relative;
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-image i {
  filter: drop-shadow(0 20px 40px rgba(102, 126, 234, 0.4));
}

.floating {
  animation: floating 3s ease-in-out infinite;
}

@keyframes floating {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

.feature-card {
  height: 100%;
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 25px 80px var(--shadow);
}

.feature-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto;
  background: var(--gradient);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: all 0.3s ease;
}

.feature-card:hover .feature-icon {
  transform: scale(1.1) rotate(5deg);
}

.feature-icon svg {
  width: 40px;
  height: 40px;
}

.connection-stat {
  padding: 1.5rem;
  border-radius: 1rem;
  background: var(--table-row-hover);
  transition: all 0.3s ease;
}

.connection-stat:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px var(--shadow);
}

.stat-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 1rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.oracle-icon {
  background: var(--gradient-secondary);
}

.postgres-icon {
  background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);
}

.stat-number {
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--primary);
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.9rem;
  color: var(--text-muted);
  font-weight: 500;
}

.list-group-item {
  border: none;
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
  transition: all 0.3s ease;
}

.list-group-item:hover {
  background-color: var(--table-row-hover);
  transform: translateX(5px);
}
</style>