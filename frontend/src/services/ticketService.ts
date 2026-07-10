import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type {
  TicketListItem, TicketDetail, TicketFormData, TicketFilters, PanelData, CommentType, TicketStatus,
} from '../types/ticket'

function buildParams(filters: TicketFilters): URLSearchParams {
  const params = new URLSearchParams()
  const { status, ...rest } = filters
  Object.entries(rest).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  })
  status?.forEach(s => params.append('status', s))
  return params
}

export const ticketService = {
  list: (filters: TicketFilters = {}) =>
    apiClient.get<PaginatedResponse<TicketListItem>>(`/api/tickets?${buildParams(filters)}`).then(r => r.data),

  get: (id: string) =>
    apiClient.get<TicketDetail>(`/api/tickets/${id}`).then(r => r.data),

  create: (data: TicketFormData) =>
    apiClient.post<TicketDetail>('/api/tickets', data).then(r => r.data),

  update: (id: string, data: Partial<TicketFormData> & { estimated_resolution_minutes?: number | null }) =>
    apiClient.patch<TicketDetail>(`/api/tickets/${id}`, data).then(r => r.data),

  /** Reemplaza el set completo de Skills requeridas (spec 011) — funciona en cualquier estado
   * del ticket, sin transición ni comentario. */
  updateTicketSkills: (id: string, skillIds: string[]) =>
    apiClient.patch<TicketDetail>(`/api/tickets/${id}/skills`, { skill_ids: skillIds }).then(r => r.data),

  assign: (id: string, assignee_id: string, mode: 'resolver' | 'pre_analysis') =>
    apiClient.post<{ ticket: TicketDetail; assignment: { id: string } }>(
      `/api/tickets/${id}/assign`, { assignee_id, mode }).then(r => r.data),

  addComment: (id: string, comment_type: CommentType, body: string, files: File[] = []) => {
    if (files.length === 0) {
      return apiClient.post(`/api/tickets/${id}/comments`, { comment_type, body }).then(r => r.data)
    }
    const form = new FormData()
    form.set('comment_type', comment_type)
    form.set('body', body)
    files.forEach(f => form.append('files', f))
    return apiClient.post(`/api/tickets/${id}/comments`, form,
      { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data)
  },

  toggleTesting: (id: string, direction: 'enter' | 'exit') =>
    apiClient.post(`/api/tickets/${id}/testing`, { direction }).then(r => r.data),

  recordResolution: (id: string, accepted: boolean, body?: string) =>
    apiClient.post(`/api/tickets/${id}/resolution`, { accepted, body }).then(r => r.data),

  close: (id: string, resolution_type_id: string, body: string) =>
    apiClient.post<TicketDetail>(`/api/tickets/${id}/close`, { resolution_type_id, body }).then(r => r.data),

  cancel: (id: string, body: string) =>
    apiClient.post<TicketDetail>(`/api/tickets/${id}/cancel`, { body }).then(r => r.data),

  changeStatus: (id: string, status: TicketStatus, comment: string) =>
    apiClient.patch<TicketDetail>(`/api/tickets/${id}/status`, { status, comment }).then(r => r.data),

  attachmentUrl: (ticketId: string, attachmentId: string) =>
    `${apiClient.defaults.baseURL}/api/tickets/${ticketId}/attachments/${attachmentId}`,

  downloadAttachment: async (ticketId: string, attachmentId: string, filename: string) => {
    const response = await apiClient.get(`/api/tickets/${ticketId}/attachments/${attachmentId}`,
      { responseType: 'blob' })
    const url = URL.createObjectURL(response.data as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  },

  panel: (statuses?: string[]) => {
    const params = new URLSearchParams()
    statuses?.forEach(s => params.append('statuses', s))
    return apiClient.get<PanelData>(`/api/assignment-panel?${params}`).then(r => r.data)
  },
}
