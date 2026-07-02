import apiClient from './apiClient'
import type { PermissionCatalogItem, PermissionFormData } from '../types/role'

export const permissionService = {
  list: () =>
    apiClient.get<{ items: PermissionCatalogItem[]; total: number }>('/api/permissions').then(r => r.data),

  create: (data: PermissionFormData) =>
    apiClient.post<PermissionCatalogItem>('/api/permissions', data).then(r => r.data),

  delete: (id: string) =>
    apiClient.delete(`/api/permissions/${id}`).then(r => r.data),
}
