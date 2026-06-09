<template>
  <div
    id="app"
    :class="{
      'is-login-page': isLoginPage,
      'sidebar-collapsed': sidebarCollapsed && !isLoginPage,
      'sidebar-mobile-open': mobileSidebarOpen && !isLoginPage,
    }"
  >
    <!-- 登录页：全屏展示 -->
    <template v-if="isLoginPage">
      <router-view />
    </template>

    <!-- 主布局：侧边栏 + 顶栏 + 内容区 -->
    <template v-else>
      <div
        v-if="mobileSidebarOpen"
        class="sidebar-overlay"
        @click="closeMobileSidebar"
      ></div>

      <AppSidebar
        :collapsed="sidebarCollapsed"
        :mobile-open="mobileSidebarOpen"
        @close-mobile="closeMobileSidebar"
      />

      <div class="app-main">
        <AppHeader
          :sidebar-collapsed="sidebarCollapsed"
          @toggle-sidebar="toggleSidebar"
          @toggle-mobile="toggleMobileSidebar"
        />

        <main class="app-content">
          <div class="content-container">
            <router-view />
          </div>
        </main>

        <footer class="app-footer">
          <span>&copy; 2025 Oracle到PolarDB-PG迁移平台</span>
          <span class="footer-sep d-none d-sm-inline">·</span>
          <span class="d-none d-sm-inline">高效、安全、可靠的数据库迁移解决方案</span>
        </footer>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'

const route = useRoute()
const isLoginPage = computed(() => route.path === '/login' || route.path === '/login/')

const sidebarCollapsed = ref(false)
const mobileSidebarOpen = ref(false)

/** 从 localStorage 恢复侧边栏折叠状态 */
onMounted(() => {
  const saved = localStorage.getItem('sidebarCollapsed')
  if (saved === 'true') sidebarCollapsed.value = true
})

/** 路由切换时关闭移动端侧边栏 */
watch(() => route.path, () => {
  mobileSidebarOpen.value = false
})

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebarCollapsed', String(sidebarCollapsed.value))
}

const toggleMobileSidebar = () => {
  mobileSidebarOpen.value = !mobileSidebarOpen.value
}

const closeMobileSidebar = () => {
  mobileSidebarOpen.value = false
}

/** 窗口变宽时自动关闭移动端抽屉 */
const handleResize = () => {
  if (window.innerWidth >= 992) {
    mobileSidebarOpen.value = false
  }
}

onMounted(() => window.addEventListener('resize', handleResize))
onUnmounted(() => window.removeEventListener('resize', handleResize))
</script>

<style>
/* ===== 应用根布局 ===== */
#app {
  width: 100%;
  min-height: 100vh;
  display: flex;
  background: var(--background);
  overflow-x: hidden;
}

/* 登录页：占满全屏，避免 flex 子项收缩导致右侧空白 */
#app.is-login-page {
  width: 100%;
  min-height: 100vh;
  min-height: 100dvh;
}

#app.is-login-page > * {
  flex: 1;
  width: 100%;
  min-width: 0;
}

/* 主内容区：随侧边栏宽度偏移 */
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  margin-left: var(--sidebar-width, 240px);
  transition: margin-left 0.25s ease;
  min-width: 0;
}

#app.sidebar-collapsed .app-main {
  margin-left: var(--sidebar-collapsed-width, 64px);
}

.app-content {
  flex: 1;
  padding: 20px 24px;
}

.content-container {
  width: 100%;
  max-width: none;
}

.app-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 12px 24px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  font-size: 12px;
  color: var(--text-muted);
}

.footer-sep {
  color: var(--border);
}

/* 移动端遮罩层 */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  z-index: 1035;
  background: var(--overlay, rgba(0, 0, 0, 0.45));
}

/* ===== 移动端布局 ===== */
@media (max-width: 991.98px) {
  .app-main {
    margin-left: 0 !important;
  }

  .app-content {
    padding: 16px;
  }
}

@media (max-width: 575.98px) {
  .app-content {
    padding: 12px;
  }
}

/* ===== 企业级组件覆写（去除过度动效） ===== */
.card {
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 1px 3px var(--shadow-light, rgba(0, 0, 0, 0.05));
  transition: box-shadow 0.2s ease;
  overflow: hidden;
}

.card:hover {
  box-shadow: 0 4px 12px var(--shadow-light, rgba(0, 0, 0, 0.08));
  transform: none;
}

.card-header {
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
  border-bottom: 1px solid var(--border);
  padding: 14px 20px;
  font-size: 15px;
}

.card-header h5,
.card-header h6 {
  color: var(--text);
  margin: 0;
}

.card-body {
  padding: 20px;
}

.table thead {
  background: var(--table-header-bg, var(--background));
  color: var(--text);
}

.table thead th {
  border: none;
  padding: 12px 16px;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-muted);
  text-transform: none;
  letter-spacing: 0;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.table tbody td {
  padding: 12px 16px;
  vertical-align: middle;
  border-color: var(--border);
  font-size: 14px;
}

.table tbody tr {
  transition: background-color 0.15s ease;
}

.table tbody tr:hover {
  background-color: var(--table-row-hover);
  transform: none;
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  color: var(--text);
}

.lead {
  color: var(--text-muted);
  font-size: 1.1rem;
}
</style>
