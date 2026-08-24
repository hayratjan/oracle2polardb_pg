import axios from 'axios'
import { tokenManager } from './auth'

const apiClient = axios.create({
  baseURL: (typeof (import.meta as any).env !== 'undefined' ? (import.meta as any).env.VITE_API_BASE_URL : undefined) || 'http://localhost:8000',
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
          const baseURL = (typeof (import.meta as any).env !== 'undefined' ? (import.meta as any).env.VITE_API_BASE_URL : undefined) || 'http://localhost:8000'
          const response = await axios.post(`${baseURL}/api/token/refresh/`, {
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