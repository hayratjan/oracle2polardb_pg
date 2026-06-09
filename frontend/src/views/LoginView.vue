<template>
  <div class="login-page">
    <canvas ref="particleCanvas" class="particle-background"></canvas>

    <!-- 顶部工具栏：主题切换 -->
    <div class="login-toolbar">
      <ThemeSwitcher variant="header" />
    </div>

    <div class="login-layout">
      <!-- 左侧：登录表单 -->
      <section class="login-form-panel">
        <div class="login-card">
          <div class="login-header">
            <div class="logo-container">
              <img src="@/assets/logo.svg" alt="Logo" class="logo" />
            </div>
            <h1 class="login-title">欢迎登录</h1>
            <p class="login-subtitle">Oracle 到 PolarDB-PG 企业级迁移平台</p>
          </div>

          <form @submit.prevent="handleLogin" class="login-form">
            <div v-if="errorMessage" class="alert alert-danger" role="alert">
              <i class="bi bi-exclamation-triangle me-2"></i>{{ errorMessage }}
            </div>

            <div class="form-group">
              <label class="form-label">
                <i class="bi bi-person me-2"></i>用户名
              </label>
              <input
                type="text"
                class="form-control"
                v-model="formData.username"
                placeholder="请输入用户名"
                autocomplete="username"
                required
              />
            </div>

            <div class="form-group">
              <label class="form-label">
                <i class="bi bi-lock me-2"></i>密码
              </label>
              <input
                type="password"
                class="form-control"
                v-model="formData.password"
                placeholder="请输入密码"
                autocomplete="current-password"
                required
              />
            </div>

            <div class="form-options">
              <label class="checkbox-label">
                <input type="checkbox" v-model="formData.remember" />
                <span>记住我</span>
              </label>
              <a href="#" class="forgot-password" @click.prevent>忘记密码？</a>
            </div>

            <button
              type="submit"
              class="btn btn-primary btn-block btn-lg"
              :disabled="isLoading"
            >
              <i v-if="isLoading" class="bi bi-arrow-repeat me-2 spin"></i>
              <i v-else class="bi bi-box-arrow-in-right me-2"></i>
              {{ isLoading ? '登录中...' : '登录' }}
            </button>
          </form>

          <div class="login-footer">
            <p class="footer-text">
              还没有账号？
              <a href="#" class="register-link" @click.prevent>联系管理员开通</a>
            </p>
          </div>
        </div>
      </section>

      <!-- 右侧：品牌与功能展示 -->
      <section class="login-brand-panel">
        <div class="brand-inner">
          <div class="brand-badge">
            <i class="bi bi-shield-check"></i>
            企业级数据库迁移方案
          </div>

          <h2 class="brand-title">高效 · 安全 · 可靠</h2>
          <p class="brand-desc">
            一站式完成 Oracle 到 PolarDB PostgreSQL 的结构迁移、数据同步与实时监控，助力企业平滑上云。
          </p>

          <!-- 迁移流程示意 -->
          <div class="migration-flow">
            <div class="flow-node">
              <div class="flow-icon oracle">
                <i class="bi bi-database-gear"></i>
              </div>
              <span>Oracle</span>
            </div>
            <div class="flow-arrow">
              <i class="bi bi-arrow-right"></i>
              <span class="flow-label">智能转换</span>
            </div>
            <div class="flow-node">
              <div class="flow-icon convert">
                <i class="bi bi-arrow-left-right"></i>
              </div>
              <span>迁移引擎</span>
            </div>
            <div class="flow-arrow">
              <i class="bi bi-arrow-right"></i>
              <span class="flow-label">实时同步</span>
            </div>
            <div class="flow-node">
              <div class="flow-icon postgres">
                <i class="bi bi-server"></i>
              </div>
              <span>PolarDB-PG</span>
            </div>
          </div>

          <!-- 核心能力 -->
          <ul class="feature-list">
            <li v-for="item in features" :key="item.title" class="feature-item">
              <div class="feature-icon">
                <i :class="['bi', item.icon]"></i>
              </div>
              <div class="feature-text">
                <strong>{{ item.title }}</strong>
                <span>{{ item.desc }}</span>
              </div>
            </li>
          </ul>

          <!-- 底部统计 -->
          <div class="brand-stats">
            <div v-for="stat in stats" :key="stat.label" class="stat-item">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi, tokenManager } from '@/api/auth'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'

const router = useRouter()

const particleCanvas = ref<HTMLCanvasElement | null>(null)
let animationFrameId: number | null = null

const formData = ref({
  username: '',
  password: '',
  remember: false,
})

const isLoading = ref(false)
const errorMessage = ref('')

/** 右侧展示的核心能力 */
const features = [
  { icon: 'bi-layers', title: '全量 & 增量迁移', desc: '支持表、视图、序列、触发器等多种对象类型' },
  { icon: 'bi-activity', title: '实时监控', desc: '任务进度、日志与对比结果一目了然' },
  { icon: 'bi-shield-lock', title: '安全可靠', desc: 'JWT 认证、连接加密与断点续传' },
  { icon: 'bi-gear-wide-connected', title: '灵活配置', desc: '冲突策略、标识符大小写等可自定义' },
]

/** 平台亮点数据 */
const stats = [
  { value: '10+', label: '对象类型' },
  { value: '24/7', label: '任务监控' },
  { value: '99.9%', label: '迁移可靠性' },
]

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  opacity: number
}

const particles: Particle[] = []
const PARTICLE_COUNT = 60
const CONNECTION_DISTANCE = 140

const initParticles = () => {
  const canvas = particleCanvas.value
  if (!canvas) return

  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  particles.length = 0
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      size: Math.random() * 2.5 + 1,
      opacity: Math.random() * 0.4 + 0.15,
    })
  }
}

const drawParticles = () => {
  const canvas = particleCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const primaryRgb = '37, 99, 235'

  particles.forEach((particle, index) => {
    particle.x += particle.vx
    particle.y += particle.vy

    if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1
    if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1

    ctx.beginPath()
    ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${primaryRgb}, ${particle.opacity})`
    ctx.fill()

    for (let j = index + 1; j < particles.length; j++) {
      const other = particles[j]
      const dx = particle.x - other.x
      const dy = particle.y - other.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < CONNECTION_DISTANCE) {
        const opacity = (1 - distance / CONNECTION_DISTANCE) * 0.25
        ctx.beginPath()
        ctx.moveTo(particle.x, particle.y)
        ctx.lineTo(other.x, other.y)
        ctx.strokeStyle = `rgba(${primaryRgb}, ${opacity})`
        ctx.lineWidth = 0.5
        ctx.stroke()
      }
    }
  })

  animationFrameId = requestAnimationFrame(drawParticles)
}

const handleResize = () => {
  initParticles()
}

const handleLogin = async () => {
  if (isLoading.value) return

  if (!formData.value.username || !formData.value.password) {
    errorMessage.value = '请输入用户名和密码'
    return
  }

  try {
    isLoading.value = true
    errorMessage.value = ''

    const response = await authApi.login({
      username: formData.value.username,
      password: formData.value.password,
    })

    if (response.status === 'success' && response.access && response.refresh) {
      tokenManager.setTokens(response.access, response.refresh)

      if (formData.value.remember) {
        localStorage.setItem('rememberUser', formData.value.username)
      } else {
        localStorage.removeItem('rememberUser')
      }

      await new Promise(resolve => setTimeout(resolve, 400))
      await router.push('/')
    } else {
      errorMessage.value = response.message || '登录失败，请重试'
    }
  } catch (error: any) {
    console.error('登录错误:', error)
    if (error.response?.data?.message) {
      errorMessage.value = error.response.data.message
    } else if (error.message) {
      errorMessage.value = error.message
    } else {
      errorMessage.value = '登录失败，请检查网络连接后重试'
    }
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  const rememberedUser = localStorage.getItem('rememberUser')
  if (rememberedUser) {
    formData.value.username = rememberedUser
    formData.value.remember = true
  }

  initParticles()
  drawParticles()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: var(--background);
  overflow: hidden;
}

.particle-background {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

.login-toolbar {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 10;
  display: flex;
  justify-content: flex-end;
  padding: 16px 24px;
  pointer-events: none;
}

.login-toolbar > * {
  pointer-events: auto;
}

.login-layout {
  position: relative;
  z-index: 1;
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 0;
}

/* ===== 左侧表单区 ===== */
.login-form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 40px 40px;
  background: var(--surface);
}

.login-card {
  width: 100%;
  max-width: 420px;
  animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo-container {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
}

.logo {
  width: 64px;
  height: 64px;
  filter: drop-shadow(0 4px 8px var(--shadow));
}

.login-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.login-form {
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
}

.form-control {
  width: 100%;
  padding: 12px 16px;
  font-size: 15px;
  border: 2px solid var(--border);
  border-radius: 10px;
  background: var(--input-background);
  color: var(--text);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-control:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 4px var(--focus-ring);
}

.form-control::placeholder {
  color: var(--text-muted);
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
  color: var(--text);
  user-select: none;
}

.checkbox-label input[type="checkbox"] {
  margin-right: 8px;
  width: 16px;
  height: 16px;
  accent-color: var(--primary);
}

.forgot-password {
  font-size: 14px;
  color: var(--primary);
  text-decoration: none;
}

.forgot-password:hover {
  color: var(--primary-hover);
  text-decoration: underline;
}

.alert {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  display: flex;
  align-items: center;
}

.alert-danger {
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.25);
  color: var(--danger);
}

.btn-block {
  width: 100%;
}

.btn-lg {
  padding: 14px 24px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 10px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.login-footer {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}

.footer-text {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.register-link {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}

.register-link:hover {
  text-decoration: underline;
}

/* ===== 右侧品牌区 ===== */
.login-brand-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 48px;
  background: var(--gradient);
  color: white;
  position: relative;
  overflow: hidden;
}

.login-brand-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(255, 255, 255, 0.12) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.08) 0%, transparent 40%);
  pointer-events: none;
}

.brand-inner {
  position: relative;
  z-index: 1;
  max-width: 480px;
  width: 100%;
  animation: fadeIn 0.6s ease-out 0.15s both;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

.brand-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 24px;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 24px;
  backdrop-filter: blur(8px);
}

.brand-title {
  font-size: 32px;
  font-weight: 800;
  margin: 0 0 12px;
  line-height: 1.25;
  color: white;
}

.brand-desc {
  font-size: 15px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.88);
  margin: 0 0 32px;
}

/* 迁移流程 */
.migration-flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 20px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 14px;
  margin-bottom: 28px;
  backdrop-filter: blur(8px);
}

.flow-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
}

.flow-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: rgba(255, 255, 255, 0.2);
}

.flow-icon.oracle { background: rgba(249, 115, 22, 0.35); }
.flow-icon.convert { background: rgba(255, 255, 255, 0.25); }
.flow-icon.postgres { background: rgba(2, 132, 199, 0.35); }

.flow-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 16px;
}

.flow-label {
  font-size: 10px;
  white-space: nowrap;
}

/* 特性列表 */
.feature-list {
  list-style: none;
  padding: 0;
  margin: 0 0 28px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.feature-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.feature-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feature-text strong {
  font-size: 14px;
  font-weight: 600;
}

.feature-text span {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  line-height: 1.4;
}

/* 统计数据 */
.brand-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 16px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
}

.stat-value {
  font-size: 22px;
  font-weight: 800;
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
  margin-top: 4px;
}

/* ===== 响应式 ===== */
@media (max-width: 991.98px) {
  .login-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .login-brand-panel {
    order: -1;
    padding: 32px 24px 28px;
  }

  .brand-inner {
    max-width: 100%;
  }

  .brand-title {
    font-size: 24px;
  }

  .brand-desc {
    font-size: 14px;
    margin-bottom: 20px;
  }

  .feature-list {
    display: none;
  }

  .brand-stats {
    display: none;
  }

  .migration-flow {
    margin-bottom: 0;
  }

  .login-form-panel {
    padding: 24px 20px 32px;
  }
}

@media (max-width: 575.98px) {
  .login-toolbar {
    padding: 12px 16px;
  }

  .login-title {
    font-size: 22px;
  }

  .logo {
    width: 52px;
    height: 52px;
  }

  .migration-flow {
    padding: 14px 10px;
    gap: 4px;
  }

  .flow-icon {
    width: 36px;
    height: 36px;
    font-size: 16px;
  }

  .flow-node span {
    font-size: 10px;
  }

  .flow-label {
    display: none;
  }
}
</style>
