<template>
  <div id="app">
    <nav v-if="!isLoginPage" class="navbar navbar-expand-lg navbar-dark">
      <div class="container-fluid">
        <a class="navbar-brand d-flex align-items-center" href="/">
          <img src="@/assets/logo.svg" alt="Logo" width="25" height="25" style="margin: 8px;" />
          <span>Oracle到PolarDB-PG迁移平台</span>
        </a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav ms-auto">
            <li class="nav-item">
              <router-link class="nav-link" to="/">
                <i class="bi bi-house-door me-1"></i>
                首页
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/tasks">
                <i class="bi bi-list-task me-1"></i>
                迁移任务
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/task/create">
                <i class="bi bi-plus-circle me-1"></i>
                创建任务
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/oracle">
                <i class="bi bi-database-gear me-1"></i>
                Oracle数据库
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/postgres">
                <i class="bi bi-server me-1"></i>
                PostgreSQL数据库
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/config">
                <i class="bi bi-gear me-1"></i>
                系统配置
              </router-link>
            </li>
            <li class="nav-item ms-2">
              <ThemeSwitcher />
            </li>
            <li class="nav-item ms-2">
              <button class="btn btn-outline-light btn-sm" @click="handleLogout">
                <i class="bi bi-box-arrow-right me-1"></i>
                退出登录
              </button>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    
    <div :class="['container-fluid', 'main-content', { 'login-page': isLoginPage }]">
      <div class="content-wrapper">
        <router-view />
      </div>
    </div>
    
    <footer v-if="!isLoginPage" class="footer mt-auto">
      <div class="container">
        <div class="row">
          <div class="col-md-6 text-center text-md-start">
            <p class="mb-0">&copy; 2025 Oracle到PolarDB-PG迁移平台. 保留所有权利.</p>
          </div>
          <div class="col-md-6 text-center text-md-end">
            <p class="mb-0">高效、安全、可靠的数据库迁移解决方案</p>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'
import { authApi } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const isLoginPage = computed(() => route.path === '/login' || route.path === '/login/')

const handleLogout = async () => {
  try {
    await authApi.logout()
    localStorage.removeItem('rememberUser')
    router.push('/login')
  } catch (error) {
    console.error('登出失败:', error)
    router.push('/login')
  }
}
</script>

<style>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--background);
  background-attachment: fixed;
}

.navbar {
  background: var(--gradient) !important;
  transition: background 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.navbar-dark .navbar-brand {
  color: white !important;
}

.navbar-dark .nav-link {
  color: rgba(255, 255, 255, 0.9) !important;
}

.navbar-dark .nav-link:hover,
.navbar-dark .nav-link.router-link-active {
  color: white !important;
}

.navbar-brand {
  font-weight: 600;
  font-size: 1.25rem;
  letter-spacing: 0.5px;
}

.navbar-brand img {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
  transition: transform 0.3s ease;
}

.navbar-brand:hover img {
  transform: scale(1.05);
}

.nav-link {
  font-weight: 500;
  padding: 0.5rem 1rem !important;
  border-radius: 0.375rem;
  transition: all 0.3s ease;
  margin: 0 0.25rem;
}

.nav-link:hover,
.nav-link.router-link-active {
  background-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.nav-link.router-link-active {
  background-color: rgba(255, 255, 255, 0.2);
  font-weight: 600;
}

.main-content {
  flex: 1;
  padding: 2rem 1rem;
}

.main-content.login-page {
  padding: 0;
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
}

.footer {
  background: var(--gradient);
  color: white;
  padding: 1.5rem 0;
  margin-top: 3rem;
  backdrop-filter: blur(10px);
  transition: background 0.3s ease;
}

.footer p {
  margin: 0;
  font-size: 0.9rem;
  opacity: 0.9;
}

.card {
  border: none;
  border-radius: 1rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  overflow: hidden;
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.card-header {
  background: var(--gradient);
  color: white;
  font-weight: 600;
  border: none;
  padding: 1rem 1.5rem;
  transition: background 0.3s ease;
}

.card-body {
  padding: 1.5rem;
}

.btn {
  border-radius: 0.5rem;
  padding: 0.5rem 1.25rem;
  font-weight: 500;
  transition: all 0.3s ease;
  border: none;
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}

.btn-primary {
  background: var(--gradient);
  transition: background 0.3s ease;
}

.btn-success {
  background: var(--success);
}

.btn-info {
  background: var(--info);
}

.btn-warning {
  background: var(--warning);
}

.btn-danger {
  background: var(--danger);
}

.table {
  border-radius: 0.75rem;
  overflow: hidden;
}

.table thead {
  background: var(--gradient);
  color: white;
  transition: background 0.3s ease;
}

.table thead th {
  border: none;
  padding: 1rem;
  font-weight: 600;
}

.table tbody tr {
  transition: all 0.3s ease;
}

.table tbody tr:hover {
  background-color: var(--primary);
  opacity: 0.1;
  transform: scale(1.01);
}

.form-control,
.form-select {
  border-radius: 0.5rem;
  border: 2px solid var(--border);
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
}

.form-control:focus,
.form-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
}

.badge {
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  font-weight: 500;
}

.progress {
  height: 0.75rem;
  border-radius: 0.5rem;
  background-color: var(--border);
}

.progress-bar {
  border-radius: 0.5rem;
  transition: width 0.6s ease;
}

.spinner-border {
  width: 3rem;
  height: 3rem;
  border-width: 0.25em;
}

.list-group-item {
  border: none;
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
  transition: all 0.3s ease;
}

.list-group-item:hover {
  background-color: var(--primary);
  opacity: 0.1;
  transform: translateX(5px);
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 700;
  color: var(--text);
}

.lead {
  color: var(--text-muted);
  font-size: 1.25rem;
}
</style>