export interface WorkSessionListItem {
  id: string
  resource_id: string
  resource_name: string | null
  ticket_id: string
  ticket_number: string | null
  work_date: string
  duration_minutes: number
  started_at: string | null
  ended_at: string | null
  note: string | null
  created_by: string
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface WorkSessionFormData {
  ticket_id: string
  work_date: string
  duration_minutes?: number
  started_at?: string
  ended_at?: string
  note?: string
  resource_id?: string
}

export interface WorkSessionFilters {
  resource_id?: string
  ticket_id?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export interface DailySummaryDay {
  work_date: string
  total_minutes: number
  sin_registro: boolean
}

export interface DailySummaryResponse {
  resource_id: string
  resource_name: string | null
  range: { date_from: string; date_to: string }
  days: DailySummaryDay[]
  total_minutes: number
}

export interface ResourceSummaryRow {
  resource_id: string
  resource_name: string | null
  total_minutes: number
}

export interface ResourcesOverviewResponse {
  range: { date_from: string; date_to: string }
  resources: ResourceSummaryRow[]
}

/** minutos → "1h 30m" / "45m", para mostrar el resumen diario. */
export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`
}
