export interface AppNotification {
  id: string
  event_type: 'assigned' | 'user_replied' | 'resolution_rejected' | 'closed' | 'close_eligible'
  message: string
  ticket: { id: string; ticket_number: string; title: string } | null
  read: boolean
  created_at: string
}

export interface NotificationsResponse {
  items: AppNotification[]
  total: number
  unread_count: number
}
