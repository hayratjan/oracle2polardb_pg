import axios from 'axios'
import { tokenManager } from './auth'

// Vite 在构建期把 import.meta.env.VITE_API_BASE_URL 静态替换：变量未定义→undefined，
// 显式定义为空→""。空串必须表示"同源"（合并镜像里 Django 同域提供 /api/），
// 所以这里不能用 `|| 兜底`——那样同源构建仍会请求 http://localhost:8000。
const envBaseUrl =
  typeof (import.meta as any).env !== 'undefined' ? (import.meta as any).env.VITE_API_BASE_URL : undefined
const apiBaseUrl = envBaseUrl === undefined ? 'http://localhost:8000' : envBaseUrl

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
  // 注意：不能设 withCredentials —— 凭据式跨域请求要求后端返回精确来源而非
  // 通配符 Access-Control-Allow-Origin: *，开发环境的 * 会导致浏览器在预检
  // 通过后丢弃真实 POST（表现：OPTIONS 200 后无任何反应）。
  // 认证走 Authorization: Bearer 头，无需 cookie。
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use(
  (config) => {
    const token = tokenManager.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 登录/刷新端点自身的 401（用户名密码错误、凭据失效）不应触发 token 刷新重试，
    // 否则旧 refresh token 存在时会：刷新失败 → 强制跳回 /login 页面重载，
    // 表现为「点登录没有任何反应」。直接交还给调用方显示错误信息。
    const isAuthEndpoint =
      (originalRequest?.url || '').includes('/api/login/') ||
      (originalRequest?.url || '').includes('/api/token/')

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true

      try {
        const refreshToken = tokenManager.getRefreshToken()
        if (refreshToken) {
          const response = await axios.post(`${apiBaseUrl}/api/token/refresh/`, {
            refresh: refreshToken
          })

          if (response.data.access) {
            tokenManager.setTokens(response.data.access, refreshToken)
            originalRequest.headers.Authorization = `Bearer ${response.data.access}`
            return apiClient(originalRequest)
          }
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError)
        tokenManager.clearTokens()
        // 仅在不在登录页时才跳转，避免登录页强制刷新造成「无反应」观感
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = '/login'
        }
      }
    }

    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default apiClient