<template>
  <aside class="app-sidebar" :class="{ collapsed, 'mobile-open': mobileOpen }">
    <!-- 品牌区 -->
    <div class="sidebar-brand">
      <router-link to="/" class="brand-link" @click="emit('close-mobile')">
        <img src="@/assets/logo.svg" alt="Logo" class="brand-logo" />
        <span v-show="!collapsed || mobileOpen" class="brand-text">迁移平台</span>
      </router-link>
    </div>

    <!-- 导航菜单 -->
    <nav class="sidebar-nav">
      <div v-for="group in navGroups" :key="group.label" class="nav-group">
        <div v-if="!collapsed || mobileOpen" class="nav-group-label">{{ group.label }}</div>
        <ul class="nav-list">
          <li v-for="item in group.items" :key="item.to">
            <router-link
              :to="item.to"
              class="nav-item"
              :class="{ active: isActive(item.to) }"
              :title="collapsed && !mobileOpen ? item.label : undefined"
              @click="emit('close-mobile')"
            >
              <i :class="['bi', item.icon, 'nav-icon']"></i>
              <span v-show="!collapsed || mobileOpen" class="nav-label">{{ item.label }}</span>
            </router-link>
          </li>
        </ul>
      </div>
    </nav>

    <!-- 底部版本信息 -->
    <div v-show="!collapsed || mobileOpen" class="sidebar-footer">
      <span class="version-text">v1.0 · 企业版</span>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

defineProps<{
  collapsed: boolean
  mobileOpen: boolean
}>()

const emit = defineEmits<{
  'close-mobile': []
}>()

const route = useRoute()

/** 侧边栏导航分组 */
const navGroups = [
  {
    label: '工作台',
    items: [
      { to: '/', label: '首页', icon: 'bi-house-door' },
    ],
  },
  {
    label: '迁移管理',
    items: [
      { to: '/tasks', label: '迁移任务', icon: 'bi-list-task' },
      { to: '/monitor', label: '实时监控', icon: 'bi-activity' },
      { to: '/task/create', label: '创建任务', icon: 'bi-plus-circle' },
      { to: '/task/table-migrate', label: '表级迁移', icon: 'bi-table' },
      { to: '/migration/full-database', label: '整库一键迁移', icon: 'bi-cloud-arrow-up' },
    ],
  },
  {
    label: '数据连接',
    items: [
      { to: '/oracle', label: 'Oracle 数据库', icon: 'bi-database-gear' },
      { to: '/postgres', label: 'PolarDB-PG', icon: 'bi-server' },
    ],
  },
  {
    label: '系统',
    items: [
      { to: '/config', label: '系统配置', icon: 'bi-gear' },
    ],
  },
]

/** 判断当前路由是否激活 */
function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(path + '/')
}
</script>

<style scoped>
.app-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 1040;
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width, 240px);
  height: 100vh;
  background: var(--sidebar-bg, var(--surface));
  border-right: 1px solid var(--border);
  transition: width 0.25s ease, transform 0.25s ease;
  overflow: hidden;
}

.sidebar-brand {
  flex-shrink: 0;
  height: var(--header-height, 56px);
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
}

.brand-link {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text);
  overflow: hidden;
}

.brand-logo {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

.brand-text {
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: 0.3px;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 8px;
}

.nav-group {
  margin-bottom: 8px;
}

.nav-group-label {
  padding: 8px 12px 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  white-space: nowrap;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  margin: 2px 0;
  border-radius: 8px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.15s ease, color 0.15s ease;
  white-space: nowrap;
}

.nav-item:hover {
  background: var(--table-row-hover);
  color: var(--text);
}

.nav-item.active {
  background: var(--sidebar-active-bg, rgba(102, 126, 234, 0.12));
  color: var(--primary);
  font-weight: 600;
}

.nav-icon {
  font-size: 16px;
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}

.sidebar-footer {
  flex-shrink: 0;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
}

.version-text {
  font-size: 11px;
  color: var(--text-muted);
}

/* 折叠态：仅显示图标 */
.app-sidebar.collapsed {
  width: var(--sidebar-collapsed-width, 64px);
}

.app-sidebar.collapsed .nav-group-label {
  display: none;
}

.app-sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 10px;
}

.app-sidebar.collapsed .sidebar-brand {
  justify-content: center;
  padding: 0 8px;
}

/* 移动端：抽屉式侧边栏 */
@media (max-width: 991.98px) {
  .app-sidebar {
    transform: translateX(-100%);
    width: var(--sidebar-width, 260px);
    box-shadow: none;
  }

  .app-sidebar.mobile-open {
    transform: translateX(0);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);
  }

  .app-sidebar.collapsed {
    width: var(--sidebar-width, 260px);
  }
}
</style>
