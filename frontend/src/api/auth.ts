import apiClient from './client'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  status: string
  message: string
  access?: string
  refresh?: string
  user?: {
    username: string
    email: string
  }
}

export interface LogoutResponse {
  status: string
  message: string
}

export interface CheckAuthResponse {
  status: string
  authenticated: boolean
  user?: {
    username: string
    email: string
  }
}

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/api/login/', data)
    return response.data
  },

  logout: async (): Promise<LogoutResponse> => {
    const refreshToken = tokenManager.getRefreshToken()
    const response = await apiClient.post<LogoutResponse>('/api/logout/', { refresh: refreshToken })
    tokenManager.clearTokens()
    return response.data
  },

  checkAuth: async (): Promise<CheckAuthResponse> => {
    const response = await apiClient.get<CheckAuthResponse>('/api/check-auth/')
    return response.data
  }
}

export const tokenManager = {
  getAccessToken: (): string | null => {
    return localStorage.getItem('access_token')
  },

  getRefreshToken: (): string | null => {
    return localStorage.getItem('refresh_token')
  },

  setTokens: (access: string, refresh: string): void => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  },

  clearTokens: (): void => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },

  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('access_token')
  }
}
