<template>
  <div class="login-container">
    <canvas ref="particleCanvas" class="particle-background"></canvas>
    
    <div class="login-wrapper">
      <div class="login-card">
        <div class="login-header">
          <div class="logo-container">
            <img src="@/assets/logo.svg" alt="Logo" class="logo" />
          </div>
          <h1 class="login-title">Oracle到PolarDB-PG迁移平台</h1>
          <p class="login-subtitle">高效、安全、可靠的数据库迁移解决方案</p>
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
              required
            />
          </div>
          
          <div class="form-options">
            <label class="checkbox-label">
              <input type="checkbox" v-model="formData.remember" />
              <span>记住我</span>
            </label>
            <a href="#" class="forgot-password">忘记密码？</a>
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
            <a href="#" class="register-link">立即注册</a>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/auth'

const router = useRouter()

const particleCanvas = ref<HTMLCanvasElement | null>(null)
let animationFrameId: number | null = null

const formData = ref({
  username: '',
  password: '',
  remember: false
})

const isLoading = ref(false)
const errorMessage = ref('')

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  opacity: number
}

const particles: Particle[] = []
const PARTICLE_COUNT = 80
const CONNECTION_DISTANCE = 150

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
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 3 + 1,
      opacity: Math.random() * 0.5 + 0.2
    })
  }
}

const drawParticles = () => {
  const canvas = particleCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const computedStyle = getComputedStyle(document.documentElement)
  const primaryColor = computedStyle.getPropertyValue('--primary').trim()
  const primaryColorRgb = primaryColor.match(/\d+/g)

  particles.forEach((particle, index) => {
    particle.x += particle.vx
    particle.y += particle.vy

    if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1
    if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1

    ctx.beginPath()
    ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${primaryColorRgb ? primaryColorRgb.join(', ') : '102, 126, 234'}, ${particle.opacity})`
    ctx.fill()

    for (let j = index + 1; j < particles.length; j++) {
      const other = particles[j]
      const dx = particle.x - other.x
      const dy = particle.y - other.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < CONNECTION_DISTANCE) {
        const opacity = (1 - distance / CONNECTION_DISTANCE) * 0.3
        ctx.beginPath()
        ctx.moveTo(particle.x, particle.y)
        ctx.lineTo(other.x, other.y)
        ctx.strokeStyle = `rgba(${primaryColorRgb ? primaryColorRgb.join(', ') : '102, 126, 234'}, ${opacity})`
        ctx.lineWidth = 0.5
        ctx.stroke()
      }
    }
  })

  animationFrameId = requestAnimationFrame(drawParticles)
}

const handleResize = () => {
  const canvas = particleCanvas.value
  if (!canvas) return
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  initParticles()
}

const handleLogin = async () => {
  try {
    isLoading.value = true
    errorMessage.value = ''
    
    const response = await authApi.login({
      username: formData.value.username,
      password: formData.value.password
    })
    
    if (response.status === 'success') {
      if (formData.value.remember) {
        localStorage.setItem('rememberUser', formData.value.username)
      } else {
        localStorage.removeItem('rememberUser')
      }
      
      await new Promise(resolve => setTimeout(resolve, 500))
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
.login-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient);
  overflow: hidden;
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
  background: rgba(245, 101, 101, 0.1);
  border: 1px solid rgba(245, 101, 101, 0.3);
  color: var(--danger, #f56565);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.particle-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.login-wrapper {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 450px;
  padding: 20px;
}

.login-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 48px 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.6s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo-container {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.logo {
  width: 80px;
  height: 80px;
  filter: drop-shadow(0 4px 8px var(--shadow));
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text, #2d3748);
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--text-muted, #718096);
  margin: 0;
  font-weight: 400;
}

.login-form {
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text, #2d3748);
  margin-bottom: 8px;
}

.form-control {
  width: 100%;
  padding: 14px 16px;
  font-size: 15px;
  border: 2px solid var(--border, #e2e8f0);
  border-radius: 12px;
  background: var(--input-background, #ffffff);
  color: var(--text, #2d3748);
  transition: all 0.3s ease;
}

.form-control:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 4px var(--shadow);
}

.form-control::placeholder {
  color: var(--text-muted, #718096);
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
  color: var(--text, #2d3748);
  user-select: none;
}

.checkbox-label input[type="checkbox"] {
  margin-right: 8px;
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--primary);
}

.forgot-password {
  font-size: 14px;
  color: var(--primary);
  text-decoration: none;
  transition: all 0.3s ease;
}

.forgot-password:hover {
  color: var(--primary-hover);
  text-decoration: underline;
}

.btn-block {
  width: 100%;
}

.btn-lg {
  padding: 16px 24px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  background: var(--gradient);
  border: none;
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px var(--shadow);
}

.btn-lg:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--shadow);
  background: var(--gradient);
}

.btn-lg:active {
  transform: translateY(0);
}

.btn-lg:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.login-footer {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid var(--border, #e2e8f0);
}

.footer-text {
  font-size: 14px;
  color: var(--text-muted, #718096);
  margin: 0;
}

.register-link {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s ease;
}

.register-link:hover {
  color: var(--primary-hover);
  text-decoration: underline;
}

@media (max-width: 768px) {
  .login-wrapper {
    padding: 16px;
  }

  .login-card {
    padding: 32px 24px;
    border-radius: 20px;
  }

  .login-title {
    font-size: 24px;
  }

  .logo {
    width: 64px;
    height: 64px;
  }

  .form-control {
    padding: 12px 14px;
    font-size: 14px;
  }

  .btn-lg {
    padding: 14px 20px;
    font-size: 15px;
  }
}

@media (max-width: 480px) {
  .login-wrapper {
    padding: 12px;
  }

  .login-card {
    padding: 24px 20px;
    border-radius: 16px;
  }

  .login-title {
    font-size: 20px;
  }

  .login-subtitle {
    font-size: 13px;
  }

  .logo {
    width: 56px;
    height: 56px;
  }
}
</style>
