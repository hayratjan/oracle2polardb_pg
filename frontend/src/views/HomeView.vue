<template>
  <div class="home-view">
    <canvas ref="dataFlowCanvas" class="data-flow-bg" aria-hidden="true"></canvas>
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
              <i class="bi bi-gem floating hero-gem" style="font-size: 200px;"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="container mt-5 content-layer">
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
import { ref, onMounted, onUnmounted } from 'vue'
import { migrationTaskApi, oracleConnectionApi, postgresConnectionApi } from '@/api'
import type { MigrationTask } from '@/api'

const dataFlowCanvas = ref<HTMLCanvasElement | null>(null)
let animationFrameId: number | null = null

/** 从 CSS 变量解析主题色为 rgb 数组 */
function getThemeRgb(varName: string): [number, number, number] {
  const computedStyle = getComputedStyle(document.documentElement)
  const hex = computedStyle.getPropertyValue(varName).trim()
  if (!hex || hex.length < 4) return [102, 126, 234]
  const m = hex.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i)
  if (m) return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)]
  const rgb = hex.match(/\d+/g)
  if (rgb && rgb.length >= 3) return [Number(rgb[0]), Number(rgb[1]), Number(rgb[2])]
  return [102, 126, 234]
}

interface DataStream {
  y: number
  speed: number
  dashOffset: number
  packets: { offset: number; speed: number }[]
}

const streams: DataStream[] = []
const STREAM_COUNT = 10
const PACKETS_PER_STREAM = 4

function initDataFlow() {
  const canvas = dataFlowCanvas.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.scale(dpr, dpr)

  streams.length = 0
  for (let i = 0; i < STREAM_COUNT; i++) {
    const packets: { offset: number; speed: number }[] = []
    for (let j = 0; j < PACKETS_PER_STREAM; j++) {
      packets.push({
        offset: Math.random() * rect.width,
        speed: 0.8 + Math.random() * 1.2
      })
    }
    streams.push({
      y: (rect.height / (STREAM_COUNT + 1)) * (i + 1),
      speed: 0.3 + Math.random() * 0.4,
      dashOffset: Math.random() * 40,
      packets
    })
  }
}

function drawDataFlow() {
  const canvas = dataFlowCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const w = canvas.getBoundingClientRect().width
  const h = canvas.getBoundingClientRect().height
  const [pr, pg, pb] = getThemeRgb('--primary')
  const [sr, sg, sb] = getThemeRgb('--secondary')

  ctx.clearRect(0, 0, w, h)

  streams.forEach((stream) => {
    stream.dashOffset += stream.speed
    if (stream.dashOffset > 40) stream.dashOffset -= 40

    ctx.setLineDash([12, 20])
    ctx.lineDashOffset = -stream.dashOffset
    ctx.strokeStyle = `rgba(${pr}, ${pg}, ${pb}, 0.22)`
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, stream.y)
    ctx.lineTo(w, stream.y)
    ctx.stroke()

    stream.packets.forEach((p) => {
      p.offset += p.speed
      if (p.offset > w + 20) p.offset = -20
      const x = p.offset
      const glowR = 5
      const coreR = 1.5
      const gradient = ctx.createRadialGradient(x, stream.y, 0, x, stream.y, glowR)
      gradient.addColorStop(0, `rgba(${pr}, ${pg}, ${pb}, 0.85)`)
      gradient.addColorStop(0.5, `rgba(${sr}, ${sg}, ${sb}, 0.35)`)
      gradient.addColorStop(1, 'transparent')
      ctx.beginPath()
      ctx.arc(x, stream.y, glowR, 0, Math.PI * 2)
      ctx.fillStyle = gradient
      ctx.fill()
      ctx.beginPath()
      ctx.arc(x, stream.y, coreR, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(255, 255, 255, 0.95)`
      ctx.fill()
    })
  })

  animationFrameId = requestAnimationFrame(drawDataFlow)
}

function startDataFlow() {
  initDataFlow()
  drawDataFlow()
}

function stopDataFlow() {
  if (animationFrameId != null) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
}

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
  startDataFlow()
  window.addEventListener('resize', initDataFlow)
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

onUnmounted(() => {
  stopDataFlow()
  window.removeEventListener('resize', initDataFlow)
})
</script>

<style scoped>
.home-view {
  position: relative;
  animation: fadeIn 0.5s ease-in;
}

.data-flow-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  min-height: 100vh;
  pointer-events: none;
  z-index: 0;
}

.hero-section {
  position: relative;
  z-index: 1;
}

.content-layer {
  position: relative;
  z-index: 1;
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

.hero-image i,
.hero-gem {
  color: var(--primary);
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