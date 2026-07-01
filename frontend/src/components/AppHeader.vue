<template>
  <header class="app-header">
    <div class="header-left">
      <!-- 移动端菜单按钮 -->
      <button
        type="button"
        class="btn-icon d-lg-none"
        aria-label="打开菜单"
        @click="emit('toggle-mobile')"
      >
        <i class="bi bi-list"></i>
      </button>
      <!-- 桌面端折叠按钮 -->
      <button
        type="button"
        class="btn-icon d-none d-lg-flex"
        aria-label="折叠侧边栏"
        @click="emit('toggle-sidebar')"
      >
        <i :class="sidebarCollapsed ? 'bi bi-layout-sidebar' : 'bi bi-layout-sidebar-inset'"></i>
      </button>

      <!-- 面包屑导航 -->
      <nav class="breadcrumb-nav" aria-label="面包屑">
        <router-link to="/" class="breadcrumb-item">首页</router-link>
        <template v-if="pageTitle !== '首页'">
          <i class="bi bi-chevron-right breadcrumb-sep"></i>
          <span class="breadcrumb-item current">{{ pageTitle }}</span>
        </template>
      </nav>
    </div>

    <div class="header-right">
      <ThemeSwitcher variant="header" />
      <button type="button" class="btn-logout" @click="handleLogout">
        <i class="bi bi-box-arrow-right"></i>
        <span class="d-none d-sm-inline">退出</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'
import { authApi } from '@/api/auth'

defineProps<{
  sidebarCollapsed: boolean
}>()

const emit = defineEmits<{
  'toggle-sidebar': []
  'toggle-mobile': []
}>()

const route = useRoute()
const router = useRouter()

/** 路由标题映射 */
const routeTitles: Record<string, string> = {
  '/': '首页',
  '/tasks': '迁移任务',
  '/monitor': '实时监控',
  '/task/create': '创建任务',
  '/task/table-migrate': '表级迁移',
  '/migration/full-database': '整库一键迁移',
  '/oracle': 'Oracle 数据库',
  '/postgres': 'PolarDB-PG 管理',
  '/config': '系统配置',
}

const pageTitle = computed(() => {
  if (route.path.startsWith('/task/') && route.params.id) {
    return '任务详情'
  }
  return routeTitles[route.path] || '迁移平台'
})

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

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 1030;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height, 56px);
  padding: 0 16px 0 12px;
  background: var(--header-bg, var(--gradient));
  border-bottom: 1px solid var(--header-border, rgba(255, 255, 255, 0.15));
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--header-text-muted, rgba(255, 255, 255, 0.78));
  font-size: 18px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.btn-icon:hover {
  background: var(--nav-hover-bg, rgba(255, 255, 255, 0.12));
  color: var(--header-text, #ffffff);
}

.breadcrumb-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}

.breadcrumb-item {
  font-size: 14px;
  color: var(--header-text-muted, rgba(255, 255, 255, 0.78));
  text-decoration: none;
  white-space: nowrap;
  transition: color 0.15s ease;
}

.breadcrumb-item:hover:not(.current) {
  color: var(--header-text, #ffffff);
}

.breadcrumb-item.current {
  color: var(--header-text, #ffffff);
  font-weight: 600;
}

.breadcrumb-sep {
  font-size: 10px;
  color: var(--header-text-muted, rgba(255, 255, 255, 0.6));
  flex-shrink: 0;
}

.btn-logout {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--header-border, rgba(255, 255, 255, 0.15));
  border-radius: 8px;
  background: transparent;
  color: var(--header-text-muted, rgba(255, 255, 255, 0.78));
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-logout:hover {
  border-color: var(--danger);
  color: #fff;
  background: var(--danger);
}

@media (max-width: 575.98px) {
  .breadcrumb-nav {
    display: none;
  }
}
</style>
