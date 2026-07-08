import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type {
  WorkSessionListItem, WorkSessionFormData, WorkSessionFilters,
  DailySummaryResponse, ResourcesOverviewResponse,
} from '../types/workSession'

function buildParams(filters: object): URLSearchParams {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  })
  return params
}

export const workSessionService = {
  list: (filters: WorkSessionFilters = {}) =>
    apiClient.get<PaginatedResponse<WorkSessionListItem>>(
      `/api/work-sessions?${buildParams(filters)}`).then(r => r.data),

  create: (data: WorkSessionFormData) =>
    apiClient.post<WorkSessionListItem>('/api/work-sessions', data).then(r => r.data),

  update: (id: string, data: Partial<Pick<WorkSessionFormData, 'duration_minutes' | 'note'>>) =>
    apiClient.patch<WorkSessionListItem>(`/api/work-sessions/${id}`, data).then(r => r.data),

  remove: (id: string) =>
    apiClient.delete(`/api/work-sessions/${id}`).then(r => r.data),

  getSummary: (params: { resource_id?: string; date_from: string; date_to: string }) =>
    apiClient.get<DailySummaryResponse | ResourcesOverviewResponse>(
      `/api/work-sessions/summary?${buildParams(params)}`).then(r => r.data),
}
