import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type { UserAdmin, UserCreateRequest, UserCreateResponse } from '../types/user'

export const userService = {
  list: (params?: { page?: number; page_size?: number; role?: string; active?: boolean }) =>
    apiClient.get<PaginatedResponse<UserAdmin>>('/api/users', { params }).then(r => r.data),

  me: () =>
    apiClient.get<UserAdmin>('/api/users/me').then(r => r.data),

  create: (data: UserCreateRequest) =>
    apiClient.post<UserCreateResponse>('/api/users', data).then(r => r.data),

  changeRole: (id: string, role_id: string) =>
    apiClient.patch<UserAdmin>(`/api/users/${id}/role`, { role_id }).then(r => r.data),

  deactivate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean }>(`/api/users/${id}/deactivate`).then(r => r.data),

  activate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean }>(`/api/users/${id}/activate`).then(r => r.data),

  resetPassword: (id: string) =>
    apiClient.patch<{ id: string; provisional_password: string }>(`/api/users/${id}/reset-password`).then(r => r.data),
}
