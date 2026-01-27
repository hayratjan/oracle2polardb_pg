import axios from 'axios'
import { tokenManager } from './auth'

const apiClient = axios.create({
  baseURL: (typeof (import.meta as any).env !== 'undefined' ? (import.meta as any).env.VITE_API_BASE_URL : undefined) || 'http://localhost:8000',
  timeout: 30000,
  withCredentials: true,
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

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = tokenManager.getRefreshToken()
        if (refreshToken) {
          const response = await axios.post('http://localhost:8000/api/token/refresh/', {
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
        window.location.href = '/login'
      }
    }

    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default apiClient