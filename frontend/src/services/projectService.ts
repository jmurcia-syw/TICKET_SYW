import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type { ProjectListItem, ProjectFormData } from '../types/project'

export const projectService = {
  list: (params?: { page?: number; page_size?: number; client_id?: string; search?: string; active?: boolean }) =>
    apiClient.get<PaginatedResponse<ProjectListItem>>('/api/projects', { params }).then(r => r.data),

  get: (id: string) =>
    apiClient.get<ProjectListItem>(`/api/projects/${id}`).then(r => r.data),

  create: (data: ProjectFormData) =>
    apiClient.post<ProjectListItem>('/api/projects', data).then(r => r.data),

  update: (id: string, data: Partial<ProjectFormData>) =>
    apiClient.patch<ProjectListItem>(`/api/projects/${id}`, data).then(r => r.data),

  deactivate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean }>(`/api/projects/${id}/deactivate`).then(r => r.data),

  activate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean }>(`/api/projects/${id}/activate`).then(r => r.data),
}
