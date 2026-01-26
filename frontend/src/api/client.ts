import axios from 'axios'

const apiClient = axios.create({
  baseURL: (typeof (import.meta as any).env !== 'undefined' ? (import.meta as any).env.VITE_API_BASE_URL : undefined) || 'http://localhost:8000',
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default apiClient