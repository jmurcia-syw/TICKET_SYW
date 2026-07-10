import apiClient from './apiClient'
import type { Timer } from '../types/timer'

export const timerService = {
  getCurrent: () =>
    apiClient.get<Timer>('/api/timer').then(r => r.data),

  start: (ticketId: string) =>
    apiClient.post<Timer>('/api/timer/start', { ticket_id: ticketId }).then(r => r.data),

  pause: () =>
    apiClient.post<Timer>('/api/timer/pause').then(r => r.data),

  resume: () =>
    apiClient.post<Timer>('/api/timer/resume').then(r => r.data),

  finish: (note?: string) =>
    apiClient.post('/api/timer/finish', note ? { note } : {}).then(r => r.data),
}
