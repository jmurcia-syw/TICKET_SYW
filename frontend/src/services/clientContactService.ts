import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type { ClientContact, ClientContactCreateRequest, ClientContactCreateResponse } from '../types/clientContact'
import type { ProjectListItem } from '../types/project'

export const clientContactService = {
  list: (params?: { client_id?: string; project_id?: string; email?: string; username?: string; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<ClientContact>>('/api/client-contacts', { params }).then(r => r.data),

  create: (data: ClientContactCreateRequest) =>
    apiClient.post<ClientContactCreateResponse>('/api/client-contacts', data).then(r => r.data),

  // Spec 010 (US2): proyectos vinculados del Usuario/cliente autenticado (autoservicio)
  myProjects: () =>
    apiClient.get<{ items: ProjectListItem[]; total: number }>('/api/client-contacts/me/projects').then(r => r.data),
}
