import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type { SlaRule, SlaRuleFormData, SlaRulePatchData } from '../types/sla'

export const slaService = {
  list: (params?: { project_id?: string; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<SlaRule>>('/api/sla-rules', { params }).then(r => r.data),

  create: (data: SlaRuleFormData) =>
    apiClient.post<SlaRule>('/api/sla-rules', data).then(r => r.data),

  update: (id: string, data: SlaRulePatchData) =>
    apiClient.patch<SlaRule>(`/api/sla-rules/${id}`, data).then(r => r.data),
}
