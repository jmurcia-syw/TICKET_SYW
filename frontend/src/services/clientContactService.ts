import apiClient from './apiClient'
import type { PaginatedResponse } from '../types/api'
import type { ClientContact, ClientContactCreateRequest, ClientContactCreateResponse } from '../types/clientContact'

export const clientContactService = {
  list: (params?: { client_id?: string; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<ClientContact>>('/api/client-contacts', { params }).then(r => r.data),

  create: (data: ClientContactCreateRequest) =>
    apiClient.post<ClientContactCreateResponse>('/api/client-contacts', data).then(r => r.data),
}
