import apiClient from './apiClient'
import type { AuthUser } from '../store/authStore'

export interface LoginResponse {
  access_token: string
  user: AuthUser
}

export interface MeResponse {
  user: AuthUser
}

export const authService = {
  login: (username_or_email: string, password: string) =>
    apiClient.post<LoginResponse>('/api/auth/login', { username_or_email, password }).then(r => r.data),

  google: (id_token: string) =>
    apiClient.post<LoginResponse>('/api/auth/google', { id_token }).then(r => r.data),

  me: () =>
    apiClient.get<MeResponse>('/api/auth/me').then(r => r.data),
}
