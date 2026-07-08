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

  update: (id: string, data: Partial<Pick<WorkSessionFormData,
    'duration_minutes' | 'note' | 'started_at' | 'ended_at'>>) =>
    apiClient.patch<WorkSessionListItem>(`/api/work-sessions/${id}`, data).then(r => r.data),

  remove: (id: string) =>
    apiClient.delete(`/api/work-sessions/${id}`).then(r => r.data),

  /** Resumen diario de un único recurso (propio, o explícito con `work_sessions:view_all`) —
   * forma de respuesta fija, distinta de `getOverview`. */
  getSummary: (params: { resource_id?: string; date_from: string; date_to: string }) =>
    apiClient.get<DailySummaryResponse>(
      `/api/work-sessions/summary?${buildParams(params)}`).then(r => r.data),

  /** Total del rango por cada recurso a la vez (`work_sessions:view_all`) — endpoint separado
   * de `getSummary`, no una segunda forma de respuesta bajo la misma URL. */
  getOverview: (params: { date_from: string; date_to: string }) =>
    apiClient.get<ResourcesOverviewResponse>(
      `/api/work-sessions/summary/overview?${buildParams(params)}`).then(r => r.data),
}
