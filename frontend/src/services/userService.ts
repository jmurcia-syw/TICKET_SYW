import apiClient from './apiClient'
import type { PaginatedResponse, Role } from '../types/api'
import type { UserAdmin } from '../types/user'

export const userService = {
  list: (params?: { page?: number; page_size?: number; role?: Role; active?: boolean }) =>
    apiClient.get<PaginatedResponse<UserAdmin>>('/api/users', { params }).then(r => r.data),

  me: () =>
    apiClient.get<UserAdmin>('/api/users/me').then(r => r.data),

  changeRole: (id: string, role: Role) =>
    apiClient.patch<UserAdmin>(`/api/users/${id}/role`, { role }).then(r => r.data),

  deactivate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean }>(`/api/users/${id}/deactivate`).then(r => r.data),
}
