import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type {
  ClientListItem, ClientDetail, ClientFormData, ClientSystem, ClientSystemFormData,
  ClientAccess, ClientAccessFormData, ClientAccessAttachment,
} from '../types/client'

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
    apiClient.get<{ items: ClientSystem[]; total: number }>(`/api/clients/${clientId}/systems`)
      .then(r => r.data.items),

  addSystem: (clientId: string, data: ClientSystemFormData) =>
    apiClient.post<ClientSystem>(`/api/clients/${clientId}/systems`, data).then(r => r.data),

  deleteSystem: (clientId: string, systemId: string) =>
    apiClient.delete(`/api/clients/${clientId}/systems/${systemId}`).then(r => r.data),

  listAccess: (clientId: string) =>
    apiClient.get<{ items: ClientAccess[] }>(`/api/clients/${clientId}/access`).then(r => r.data.items),

  addAccess: (clientId: string, data: ClientAccessFormData) =>
    apiClient.post<ClientAccess>(`/api/clients/${clientId}/access`, data).then(r => r.data),

  updateAccess: (clientId: string, accessId: string, data: Partial<ClientAccessFormData>) =>
    apiClient.patch<ClientAccess>(`/api/clients/${clientId}/access/${accessId}`, data).then(r => r.data),

  deleteAccess: (clientId: string, accessId: string) =>
    apiClient.delete(`/api/clients/${clientId}/access/${accessId}`).then(r => r.data),

  listAccessAttachments: (clientId: string) =>
    apiClient.get<{ items: ClientAccessAttachment[] }>(`/api/clients/${clientId}/access-attachments`).then(r => r.data.items),

  uploadAccessAttachment: (clientId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<ClientAccessAttachment>(`/api/clients/${clientId}/access-attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  deleteAccessAttachment: (clientId: string, attachmentId: string) =>
    apiClient.delete(`/api/clients/${clientId}/access-attachments/${attachmentId}`).then(r => r.data),

  downloadAccessAttachmentUrl: (clientId: string, attachmentId: string) =>
    `/api/clients/${clientId}/access-attachments/${attachmentId}`,
}
