<template>
  <div id="app">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container-fluid">
        <a class="navbar-brand" href="/">Oracle到PolarDB-PG迁移平台</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item">
              <router-link class="nav-link" to="/">首页</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/tasks">迁移任务</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/task/create">创建任务</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/oracle">Oracle数据库</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/postgres">PostgreSQL数据库</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/config">系统配置</router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    
    <div class="container mt-4">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style>
#app {
  min-height: 100vh;
  background-color: #f8f9fa;
}
</style>