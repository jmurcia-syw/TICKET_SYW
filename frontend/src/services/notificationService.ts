import apiClient from './apiClient'
import type { NotificationsResponse } from '../types/notification'

export const notificationService = {
  list: (unread = false, page = 1, pageSize = 20) =>
    apiClient.get<NotificationsResponse>('/api/notifications',
      { params: { unread, page, page_size: pageSize } }).then(r => r.data),

  markRead: (ids: string[]) =>
    apiClient.patch<{ updated: number }>('/api/notifications/read', { ids }).then(r => r.data),

  markAllRead: () =>
    apiClient.patch<{ updated: number }>('/api/notifications/read', { all: true }).then(r => r.data),
}
