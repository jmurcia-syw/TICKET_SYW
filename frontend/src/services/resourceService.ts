import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type { Resource, ResourceFormData, Skill } from '../types/resource'

export const resourceService = {
  list: (params?: { page?: number; page_size?: number; search?: string; skill_code?: string; active?: boolean }) =>
    apiClient.get<PaginatedResponse<Resource>>('/api/resources', { params }).then(r => r.data),

  get: (id: string) =>
    apiClient.get<Resource>(`/api/resources/${id}`).then(r => r.data),

  create: (data: ResourceFormData) =>
    apiClient.post<Resource>('/api/resources', data).then(r => r.data),

  update: (id: string, data: Partial<ResourceFormData>) =>
    apiClient.patch<Resource>(`/api/resources/${id}`, data).then(r => r.data),

  updateSkills: (id: string, skill_ids: string[]) =>
    apiClient.patch<Resource>(`/api/resources/${id}/skills`, { skill_ids }).then(r => r.data),

  deactivate: (id: string) =>
    apiClient.patch<{ id: string; active: boolean }>(`/api/resources/${id}/deactivate`).then(r => r.data),
}

export const skillService = {
  list: (active?: boolean) =>
    apiClient.get<{ items: Skill[]; total: number }>('/api/skills', { params: { active } }).then(r => r.data),

  create: (data: { code: string; label: string }) =>
    apiClient.post<Skill>('/api/skills', data).then(r => r.data),

  delete: (id: string) =>
    apiClient.delete(`/api/skills/${id}`).then(r => r.data),
}
