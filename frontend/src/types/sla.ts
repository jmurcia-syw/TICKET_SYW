import type { Priority } from './ticket'

export interface SlaRule {
  id: string
  project_id: string
  project_name: string | null
  priority: Priority
  contact_minutes: number
  execution_minutes: number
  active: boolean
  created_at: string
}

export interface SlaRuleFormData {
  project_id: string
  priority: Priority
  contact_minutes: number
  execution_minutes: number
}

export interface SlaRulePatchData {
  contact_minutes?: number
  execution_minutes?: number
  active?: boolean
}

/** Bloque `sla` expuesto en el detalle/listado de tickets (Historia 2/3, aún no consumido en
 * esta entrega — se agrega ya para que TicketDetailPage/TicketsPage lo tipen sin `any`). */
export type SlaPhase = 'contacto' | 'ejecucion' | 'cerrado'
export type SlaStatus = 'sin_sla' | 'corriendo' | 'pausado' | 'vencido' | 'detenido'
export type SlaContactResult = 'pendiente' | 'cumplido' | 'vencido'
/** Motivo de la pausa (spec 022, motor de SLA dinámico) — `null` si `status != 'pausado'`;
 * `'ticket_status'` si la pausa es por estado del ticket (comportamiento ya existente);
 * `'outside_hours' | 'holiday' | 'absence'` si es por disponibilidad real del recurso asignado. */
export type SlaPauseReason = 'outside_hours' | 'holiday' | 'absence' | 'ticket_status' | null

export interface TicketSlaState {
  phase: SlaPhase | null
  status: SlaStatus
  phase_limit_minutes: number | null
  consumed_seconds: number
  rule_id: string | null
  contact_result?: SlaContactResult | null
  contact_consumed_seconds?: number | null
  pause_reason?: SlaPauseReason
}
