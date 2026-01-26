<template>
  <div id="app">
    <nav class="navbar navbar-expand-lg navbar-dark bg-gradient">
      <div class="container-fluid">
        <a class="navbar-brand d-flex align-items-center" href="/">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-database me-2" viewBox="0 0 16 16">
            <path d="M4.318 6.318a4.5 4.5 0 000 6.364L7.318 15.4a1.5 1.5 0 002.122 0l2.999-2.999a4.5 4.5 0 000-6.364L9.55 4.55a1.5 1.5 0 00-2.122 0L4.318 6.318zM5.732 7.732l2.999-2.999a.5.5 0 01.707 0l2.999 2.999a3.5 3.5 0 010 4.95l-2.999 2.999a.5.5 0 01-.707 0L5.732 12.682a3.5 3.5 0 010-4.95z"/>
          </svg>
          <span>Oracle到PolarDB-PG迁移平台</span>
        </a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav ms-auto">
            <li class="nav-item">
              <router-link class="nav-link" to="/">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-house-door me-1" viewBox="0 0 16 16">
                  <path d="M8.354 1.146a.5.5 0 00-.708 0l-6 6A.5.5 0 001.5 7.5v7a.5.5 0 00.5.5h4.5a.5.5 0 00.5-.5v-4h2v4a.5.5 0 00.5.5H14a.5.5 0 00.5-.5v-7a.5.5 0 00-.146-.354l-6-6z"/>
                </svg>
                首页
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/tasks">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-list-task me-1" viewBox="0 0 16 16">
                  <path fill-rule="evenodd" d="M2 2.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5V3a.5.5 0 00-.5-.5H2zM3 3H2v1h1V3z"/>
                  <path d="M5 3.5a.5.5 0 01.5-.5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5zM5.5 7a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM6 8H5v1h1V8z"/>
                  <path d="M8 7.5a.5.5 0 01.5-.5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5zm.5 4a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM9 13H8v1h1v-1z"/>
                </svg>
                迁移任务
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/task/create">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-plus-circle me-1" viewBox="0 0 16 16">
                  <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
                </svg>
                创建任务
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/oracle">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-database-gear me-1" viewBox="0 0 16 16">
                  <path d="M6.5 1A.5.5 0 017 .5h2a.5.5 0 01.5.5v1a.5.5 0 01-.5.5H7a.5.5 0 01-.5-.5v-1zM2.5 4.5A.5.5 0 013 4h10a.5.5 0 01.5.5v1a.5.5 0 01-.5.5H3a.5.5 0 01-.5-.5v-1zm6.5-.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM1 8a2 2 0 012-2h10a2 2 0 012 2v5a2 2 0 01-2 2H3a2 2 0 01-2-2V8zm1 0v5a1 1 0 001 1h10a1 1 0 001-1V8a1 1 0 00-1-1H3a1 1 0 00-1 1z"/>
                </svg>
                Oracle数据库
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/postgres">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-server me-1" viewBox="0 0 16 16">
                  <path d="M1.5 0h11.586a1.5 1.5 0 011.06.44l1.415 1.414A1.5 1.5 0 0116 2.914V14.5a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 010 14.5v-11A1.5 1.5 0 011.5 2zM1 1.5v1a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zm0 4v9a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-9a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zM2 7a1 1 0 011-1h10a1 1 0 011 1v2a1 1 0 01-1 1H3a1 1 0 01-1-1V7zm0 5a1 1 0 011-1h6a1 1 0 011 1v1a1 1 0 01-1 1H3a1 1 0 01-1-1v-1z"/>
                </svg>
                PostgreSQL数据库
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/config">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-gear me-1" viewBox="0 0 16 16">
                  <path d="M8 4.754a3.246 3.246 0 100 6.492 3.246 3.246 0 000-6.492zM5.754 8a2.246 2.246 0 114.492 0 2.246 2.246 0 01-4.492 0z"/>
                  <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 01-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 01-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 01.52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 011.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 011.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 01.52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 01-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 01-1.255-.52l-.094-.319z"/>
                </svg>
                系统配置
              </router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    
    <div class="container-fluid main-content">
      <div class="content-wrapper">
        <router-view />
      </div>
    </div>
    
    <footer class="footer mt-auto">
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
</script>

<style>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-attachment: fixed;
}

.bg-gradient {
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.navbar-brand {
  font-weight: 600;
  font-size: 1.25rem;
  letter-spacing: 0.5px;
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

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
}

.footer {
  background-color: rgba(30, 60, 114, 0.95);
  color: white;
  padding: 1.5rem 0;
  margin-top: 3rem;
  backdrop-filter: blur(10px);
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
  border: none;
  padding: 1rem 1.5rem;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.btn-success {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.btn-info {
  background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);
}

.btn-warning {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.btn-danger {
  background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
}

.table {
  border-radius: 0.75rem;
  overflow: hidden;
}

.table thead {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
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
  background-color: rgba(102, 126, 234, 0.1);
  transform: scale(1.01);
}

.form-control,
.form-select {
  border-radius: 0.5rem;
  border: 2px solid #e9ecef;
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
}

.form-control:focus,
.form-select:focus {
  border-color: #667eea;
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
  background-color: #e9ecef;
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
  background-color: rgba(102, 126, 234, 0.1);
  transform: translateX(5px);
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 700;
  color: #2d3748;
}

.lead {
  color: #4a5568;
  font-size: 1.25rem;
}
</style>