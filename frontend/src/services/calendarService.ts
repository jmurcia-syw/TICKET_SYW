import apiClient from './apiClient'
import type {
  Availability, AbsenceRequest, AbsenceRequestAttachment, Holiday, HolidayCategory, WorkSchedule,
  WorkScheduleSlot, WorkHourTemplate, WorkHourTemplateFormData, PersonalizedResource, Workload,
} from '../types/calendar'

export interface AbsenceRequestFormData {
  absence_type_id: string
  start_date: string
  end_date: string
  notes?: string | null
  /** Permiso parcial por horas (spec 022, FR-017) — omitir ambos para día completo. */
  start_time?: string | null
  end_time?: string | null
}

export type AbsenceRequestScope = 'own' | 'manager' | 'hr'

/** Dedup de solicitudes concurrentes por país — la pestaña Equipo del calendario puede montar
 * varios `HolidayCalendar` para el mismo país a la vez; sin esto cada uno dispara su propio
 * GET /api/holidays (que además puede sincronizar contra la API externa en la primera carga). */
const _holidayRequestCache = new Map<string, Promise<Holiday[]>>()

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

  listHolidays: (country: string) => {
    const cached = _holidayRequestCache.get(country)
    if (cached) return cached
    const promise = apiClient
      .get<{ items: Holiday[] }>('/api/holidays', { params: { country } })
      .then(r => r.data.items)
      .finally(() => _holidayRequestCache.delete(country))
    _holidayRequestCache.set(country, promise)
    return promise
  },

  createHoliday: (data: { country: string; holiday_date: string; name: string; category?: HolidayCategory }) =>
    apiClient.post<Holiday>('/api/holidays', data).then(r => r.data),

  updateHoliday: (id: string, data: { name?: string; holiday_date?: string; category?: HolidayCategory }) =>
    apiClient.patch<Holiday>(`/api/holidays/${id}`, data).then(r => r.data),

  setHolidayActive: (id: string, active: boolean) =>
    apiClient.patch<Holiday>(`/api/holidays/${id}/${active ? 'activate' : 'deactivate'}`).then(r => r.data),

  getWorkSchedule: (resourceId: string) =>
    apiClient.get<WorkSchedule>(`/api/resources/${resourceId}/work-schedule`).then(r => r.data),

  setWorkSchedule: (resourceId: string, slots: WorkScheduleSlot[]) =>
    apiClient.put<WorkSchedule>(`/api/resources/${resourceId}/work-schedule`, { items: slots }).then(r => r.data),

  // ── Franjas Horarias globales (spec 022, FR-001 a FR-005) ──────────────────

  listWorkHourTemplates: (country: string) =>
    apiClient.get<{ items: WorkHourTemplate[] }>('/api/work-hour-templates', { params: { country } })
      .then(r => r.data.items),

  createWorkHourTemplate: (data: WorkHourTemplateFormData) =>
    apiClient.post<WorkHourTemplate>('/api/work-hour-templates', data).then(r => r.data),

  updateWorkHourTemplate: (id: string, data: Partial<WorkHourTemplateFormData> & { active?: boolean }) =>
    apiClient.patch<WorkHourTemplate>(`/api/work-hour-templates/${id}`, data).then(r => r.data),

  listPersonalizedResources: () =>
    apiClient.get<{ items: PersonalizedResource[] }>('/api/work-hour-templates/personalized')
      .then(r => r.data.items),

  assignWorkHourTemplate: (resourceId: string, templateId: string) =>
    apiClient.patch(`/api/resources/${resourceId}/work-hour-template`, { work_hour_template_id: templateId })
      .then(r => r.data),

  // ── Carga de trabajo (spec 022, FR-007) ────────────────────────────────────

  getWorkload: (resourceId: string, date?: string) =>
    apiClient.get<Workload>(`/api/resources/${resourceId}/workload`, { params: { date } }).then(r => r.data),
}
