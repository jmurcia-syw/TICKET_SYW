import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type { RoleDetail, RoleFormData, RolePermissionsUpdate } from '../types/role'

export const roleService = {
  list: (params?: { page?: number; page_size?: number; active?: boolean }) =>
    apiClient.get<PaginatedResponse<RoleDetail>>('/api/roles', { params }).then(r => r.data),

  get: (id: string) =>
    apiClient.get<RoleDetail>(`/api/roles/${id}`).then(r => r.data),

  create: (data: RoleFormData) =>
    apiClient.post<RoleDetail>('/api/roles', data).then(r => r.data),

  update: (id: string, data: Partial<RoleFormData>) =>
    apiClient.patch<RoleDetail>(`/api/roles/${id}`, data).then(r => r.data),

  replacePermissions: (id: string, permission_ids: string[]) =>
    apiClient.put<RoleDetail>(`/api/roles/${id}/permissions`, { permission_ids } satisfies RolePermissionsUpdate).then(r => r.data),

  deactivate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean }>(`/api/roles/${id}/deactivate`).then(r => r.data),

  activate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean }>(`/api/roles/${id}/activate`).then(r => r.data),
}
