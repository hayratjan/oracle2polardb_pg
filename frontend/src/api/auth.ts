import apiClient from './client'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  status: string
  message: string
  user?: {
    username: string
    email: string
  }
}

export interface LogoutResponse {
  status: string
  message: string
}

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/api/login/', data)
    return response.data
  },

  logout: async (): Promise<LogoutResponse> => {
    const response = await apiClient.post<LogoutResponse>('/api/logout/')
    return response.data
  }
}
