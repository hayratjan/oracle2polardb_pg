import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { authApi, tokenManager } from '@/api/auth'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue')
  },
  {
    path: '/tasks',
    name: 'TaskList',
    component: () => import('@/views/TaskListView.vue')
  },
  {
    path: '/monitor',
    name: 'TaskMonitor',
    component: () => import('@/views/TaskMonitorView.vue')
  },
  {
    path: '/task/create',
    name: 'CreateTask',
    component: () => import('@/views/CreateTaskView.vue')
  },
  {
    path: '/task/table-migrate',
    name: 'TableMigration',
    component: () => import('@/views/TableMigrationView.vue')
  },
  {
    path: '/migration/full-database',
    name: 'FullDatabaseMigration',
    component: () => import('@/views/FullDatabaseMigrationView.vue')
  },
  {
    path: '/task/:id',
    name: 'TaskDetail',
    component: () => import('@/views/TaskDetailView.vue')
  },
  {
    path: '/oracle',
    name: 'OracleDatabase',
    component: () => import('@/views/OracleDatabaseView.vue')
  },
  {
    path: '/postgres',
    name: 'PostgresDatabase',
    component: () => import('@/views/PostgresDatabaseView.vue')
  },
  {
    path: '/config',
    name: 'Config',
    component: () => import('@/views/ConfigView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const isLoginPage = to.path === '/login' || to.path === '/login/'
  
  if (isLoginPage) {
    next()
    return
  }
  
  if (!tokenManager.isAuthenticated()) {
    console.log('未找到JWT token，重定向到登录页面')
    next('/login')
    return
  }
  
  try {
    const response = await authApi.checkAuth()
    if (response.authenticated) {
      next()
    } else {
      console.log('用户未登录，重定向到登录页面')
      tokenManager.clearTokens()
      next('/login')
    }
  } catch (error) {
    console.error('检查登录状态失败:', error)
    console.log('检查登录状态失败，重定向到登录页面')
    tokenManager.clearTokens()
    next('/login')
  }
})

router.afterEach(() => {
  window.scrollTo(0, 0)
})

export default router