import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type { ClientListItem, ClientDetail, ClientFormData, ClientSystem, ClientSystemFormData } from '../types/client'

export const clientService = {
  list: (params?: { page?: number; page_size?: number; search?: string; active?: boolean }) =>
    apiClient.get<PaginatedResponse<ClientListItem>>('/api/clients', { params }).then(r => r.data),

  get: (id: string) =>
    apiClient.get<ClientDetail>(`/api/clients/${id}`).then(r => r.data),

  create: (data: ClientFormData) =>
    apiClient.post<ClientDetail>('/api/clients', data).then(r => r.data),

  update: (id: string, data: Partial<ClientFormData>) =>
    apiClient.patch<ClientDetail>(`/api/clients/${id}`, data).then(r => r.data),

  deactivate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean; active_projects_count?: number; warning?: string }>(`/api/clients/${id}/deactivate`).then(r => r.data),

  activate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean }>(`/api/clients/${id}/activate`).then(r => r.data),

  listSystems: (clientId: string) =>
    apiClient.get<ClientSystem[]>(`/api/clients/${clientId}/systems`).then(r => r.data),

  addSystem: (clientId: string, data: ClientSystemFormData) =>
    apiClient.post<ClientSystem>(`/api/clients/${clientId}/systems`, data).then(r => r.data),

  deleteSystem: (clientId: string, systemId: string) =>
    apiClient.delete(`/api/clients/${clientId}/systems/${systemId}`).then(r => r.data),
}
