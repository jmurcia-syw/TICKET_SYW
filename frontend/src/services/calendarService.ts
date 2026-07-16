import apiClient from './apiClient'
import type { Availability, AbsenceRequest, AbsenceRequestAttachment, Holiday, WorkSchedule, WorkScheduleSlot } from '../types/calendar'

export interface AbsenceRequestFormData {
  absence_type_id: string
  start_date: string
  end_date: string
  notes?: string | null
}

export type AbsenceRequestScope = 'own' | 'manager' | 'hr'

export const calendarService = {
  getAvailability: (resourceIds?: string[], at?: string) =>
    apiClient
      .get<{ items: Availability[] }>('/api/resources/availability', {
        params: {
          resource_ids: resourceIds?.length ? resourceIds.join(',') : undefined,
          at,
        },
      })
      .then(r => r.data.items),

  /** `skipErrorNotify`: usado para el probe de `scope=manager` — un 403 (no es Jefe de nadie)
   * es un resultado normal, no un error que deba mostrarse como toast (ver apiClient.ts). */
  listAbsenceRequests: (scope: AbsenceRequestScope = 'own', opts: { skipErrorNotify?: boolean } = {}) =>
    apiClient.get<{ items: AbsenceRequest[] }>('/api/absence-requests', {
      params: { scope },
      headers: opts.skipErrorNotify ? { 'X-Skip-Error-Notify': 'true' } : undefined,
    }).then(r => r.data.items),

  /** Con `files`, se envía como `multipart/form-data` (mismo criterio que `ticketService.create`). */
  createAbsenceRequest: (data: AbsenceRequestFormData, files: File[] = []) => {
    if (files.length === 0) {
      return apiClient.post<AbsenceRequest>('/api/absence-requests', data).then(r => r.data)
    }
    const form = new FormData()
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) form.set(key, String(value))
    })
    files.forEach(f => form.append('files', f))
    return apiClient.post<AbsenceRequest>('/api/absence-requests', form,
      { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data)
  },

  decideAbsenceRequest: (id: string, role: 'manager' | 'hr', decision: 'approved' | 'rejected') =>
    apiClient.patch<AbsenceRequest>(`/api/absence-requests/${id}/decision`, { role, decision }).then(r => r.data),

  uploadAbsenceAttachment: (requestId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<AbsenceRequestAttachment>(`/api/absence-requests/${requestId}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  downloadAbsenceAttachmentUrl: (requestId: string, attachmentId: string) =>
    `/api/absence-requests/${requestId}/attachments/${attachmentId}`,

  listHolidays: (country: string) =>
    apiClient.get<{ items: Holiday[] }>('/api/holidays', { params: { country } }).then(r => r.data.items),

  createHoliday: (data: { country: string; holiday_date: string; name: string }) =>
    apiClient.post<Holiday>('/api/holidays', data).then(r => r.data),

  setHolidayActive: (id: string, active: boolean) =>
    apiClient.patch<Holiday>(`/api/holidays/${id}/${active ? 'activate' : 'deactivate'}`).then(r => r.data),

  getWorkSchedule: (resourceId: string) =>
    apiClient.get<WorkSchedule>(`/api/resources/${resourceId}/work-schedule`).then(r => r.data),

  setWorkSchedule: (resourceId: string, slots: WorkScheduleSlot[]) =>
    apiClient.put<WorkSchedule>(`/api/resources/${resourceId}/work-schedule`, { items: slots }).then(r => r.data),
}
