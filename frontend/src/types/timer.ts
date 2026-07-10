export type TimerStatus = 'inactive' | 'running' | 'paused'

export interface Timer {
  status: TimerStatus
  ticket_id: string | null
  ticket_number: string | null
  total_seconds: number
  running_seconds: number
  stale: boolean
}
