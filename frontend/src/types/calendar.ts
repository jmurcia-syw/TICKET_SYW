// Fase 5 (spec 020): calendarios, festivos, horario laboral, ausencias y disponibilidad.
// Ver specs/020-calendarios-vacaciones-disponibilidad/contracts/calendar-disponibilidad.md

export interface Holiday {
  id: string
  country: string
  holiday_date: string
  name: string
  active: boolean
}

export interface WorkScheduleSlot {
  weekday: number // 0=lunes ... 6=domingo
  start_time: string // "HH:MM"
  end_time: string // "HH:MM"
}

export interface WorkSchedule {
  items: WorkScheduleSlot[]
  is_default: boolean
}

export interface AbsenceType {
  id: string
  name: string
  active: boolean
}

export type AbsenceDecisionStatus = 'pending' | 'approved' | 'rejected'

export interface AbsenceRequestAttachment {
  id: string
  filename: string
  content_type: string
  size_bytes: number
}

export interface AbsenceRequest {
  id: string
  resource: { id: string; full_name: string }
  absence_type: { id: string; name: string }
  start_date: string
  end_date: string
  manager_status: AbsenceDecisionStatus
  hr_status: AbsenceDecisionStatus
  overall_status: AbsenceDecisionStatus
  notes: string | null
  attachments: AbsenceRequestAttachment[]
  created_at: string
}

export type AvailabilityReason = 'outside_hours' | 'holiday' | 'absence' | null

export interface Availability {
  resource_id: string
  available: boolean
  reason: AvailabilityReason
  detail: string | null
}
