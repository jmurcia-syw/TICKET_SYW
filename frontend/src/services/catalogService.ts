import apiClient from './apiClient'
import type { CatalogItem, CatalogName } from '../types/catalog'

export const catalogService = {
  list: (catalog: CatalogName, active: 'true' | 'false' | 'all' = 'true') =>
    apiClient.get<{ items: CatalogItem[]; total: number }>(
      `/api/catalogs/${catalog}`, { params: { active } }).then(r => r.data),

  create: (catalog: CatalogName, name: string) =>
    apiClient.post<CatalogItem>(`/api/catalogs/${catalog}`, { name }).then(r => r.data),

  deactivate: (catalog: CatalogName, id: string) =>
    apiClient.patch<CatalogItem>(`/api/catalogs/${catalog}/${id}/deactivate`).then(r => r.data),

  activate: (catalog: CatalogName, id: string) =>
    apiClient.patch<CatalogItem>(`/api/catalogs/${catalog}/${id}/activate`).then(r => r.data),
}
