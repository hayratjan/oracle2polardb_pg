import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { authApi } from '@/api/auth'

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
    path: '/task/create',
    name: 'CreateTask',
    component: () => import('@/views/CreateTaskView.vue')
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

router.beforeEach(async (to, _from, next) => {
  const isLoginPage = to.path === '/login' || to.path === '/login/'
  
  if (isLoginPage) {
    next()
    return
  }
  
  try {
    const response = await authApi.checkAuth()
    if (response.authenticated) {
      next()
    } else {
      next('/login')
    }
  } catch (error) {
    console.error('检查登录状态失败:', error)
    next('/login')
  }
})

router.afterEach(() => {
  window.scrollTo(0, 0)
})

export default router