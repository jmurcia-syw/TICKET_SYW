// Fase 5 (spec 020): calendarios, festivos, horario laboral, ausencias y disponibilidad.
// Ver specs/020-calendarios-vacaciones-disponibilidad/contracts/calendar-disponibilidad.md
// Spec 021: festivos sincronizados por API, categorización y cumpleaños.
// Ver specs/021-festivos-api-cumpleanos/contracts/festivos-api-cumpleanos.md
// Spec 022: Franjas Horarias globales, SLA dinámico y calendario superpuesto.
// Ver specs/022-rrhh-calendario-sla-dinamico/contracts/rrhh-calendario-sla-dinamico.md

export type HolidayCategory = 'oficial' | 'regional_religioso'
export type HolidaySource = 'api' | 'manual'

export interface Holiday {
  id: string
  country: string
  holiday_date: string
  name: string
  active: boolean
  category: HolidayCategory
  source: HolidaySource
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
  /** Permiso parcial por horas (spec 022, FR-017) — ambos `null` = día completo. */
  start_time: string | null
  end_time: string | null
}

export type AvailabilityReason = 'outside_hours' | 'holiday' | 'absence' | null

export interface Availability {
  resource_id: string
  available: boolean
  reason: AvailabilityReason
  detail: string | null
}

// ── Franja Horaria global (spec 022, FR-001/FR-002) ──────────────────────────

export type ScheduleMode = 'heredado' | 'personalizado'

export interface WorkHourTemplate {
  id: string
  country: string
  name: string
  timezone: string
  active: boolean
  slots: WorkScheduleSlot[]
}

export interface WorkHourTemplateFormData {
  country: string
  name: string
  timezone: string
  slots: WorkScheduleSlot[]
}

export interface PersonalizedResource {
  resource_id: string
  full_name: string
  calendar_country: string | null
}

// ── SLA dinámico (spec 022, FR-006 a FR-010) — `SlaPauseReason` vive en './sla' junto con el
// resto del tipo `TicketSlaState` que ya expone el bloque `sla` del ticket. ─────────────────

export interface TicketWorkloadItem {
  ticket_id: string
  ticket_number: string
  priority: string
  severity: string
  remaining_minutes: number
}

export interface Workload {
  resource_id: string
  date: string
  committed_minutes: number
  available_minutes_remaining: number
  tickets: TicketWorkloadItem[]
}
