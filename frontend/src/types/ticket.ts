export type TicketStatus =
  | 'nuevo' | 'pre_analisis' | 'contacto' | 'en_analisis' | 'en_ejecucion'
  | 'en_pruebas' | 'pendiente_usuario' | 'resuelto' | 'cerrado' | 'cancelado'

export type TicketType = 'incident' | 'evolutive' | 'preventive'
export type Priority = 'critical' | 'high' | 'medium' | 'low'
export type Severity = 's1' | 's2' | 's3' | 's4'
export type EscalationLevel = 'n1' | 'n2' | 'n3' | 'n4'

export const STATUS_LABELS: Record<TicketStatus, string> = {
  nuevo: 'Nuevo', pre_analisis: 'Pre-Análisis', contacto: 'Contacto',
  en_analisis: 'En Análisis', en_ejecucion: 'En Ejecución', en_pruebas: 'En Pruebas',
  pendiente_usuario: 'Pendiente de Usuario', resuelto: 'Resuelto',
  cerrado: 'Cerrado', cancelado: 'Cancelado',
}

export const TICKET_TYPE_LABELS: Record<TicketType, string> = {
  incident: 'Incidente', evolutive: 'Evolutivo', preventive: 'Preventivo',
}

export const PRIORITY_LABELS: Record<Priority, string> = {
  critical: 'Crítica', high: 'Alta', medium: 'Media', low: 'Baja',
}

export const SEVERITY_LABELS: Record<Severity, string> = {
  s1: 'S1', s2: 'S2', s3: 'S3', s4: 'S4',
}

export interface EntityRef {
  id: string
  name: string
}

export interface ResourceRef {
  id: string
  full_name: string
}

export interface TicketListItem {
  id: string
  ticket_number: string
  record_type_id: string
  ticket_type: TicketType
  title: string
  status: TicketStatus
  status_label: string
  priority: Priority
  severity: Severity
  escalation_level: EscalationLevel
  client: EntityRef | null
  project: EntityRef | null
  assignee: ResourceRef | null
  estimated_resolution_minutes: number | null
  created_at: string
}

/** "125" min → "2h 05m"; null → '—'. Usado en el tablero Kanban. */
export function formatMinutes(minutes: number | null): string {
  if (minutes == null) return '—'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`
}

export type CommentType =
  | 'asignado' | 'pre_analisis' | 'confirmacion_atencion' | 'solicitud_informacion'
  | 'termina_analisis' | 'solicitud_cierre' | 'respuesta_usuario'
  | 'descripcion_solucion' | 'comentario_interno' | 'cancelacion'

export interface TicketAttachment {
  id: string
  filename: string
  content_type: string
  size_bytes: number
}

export interface TicketComment {
  id: string
  comment_type: CommentType
  comment_type_label: string
  visibility: 'internal' | 'external'
  body: string
  author_id: string
  is_automatic: boolean
  attachments: TicketAttachment[]
  created_at: string
}

export interface TicketTransition {
  id: string
  from_status: string
  to_status: string
  actor_id: string
  comment_id: string | null
  created_at: string
}

export interface TicketAssignment {
  id: string
  assigner_id: string
  assignee_id: string
  resulting_status: string
  context: {
    assignee_skills: string[]
    assignee_open_tickets: number
    ticket_priority: string
    ticket_severity: string
  }
  created_at: string
}

export interface TicketDetail extends TicketListItem {
  description: string
  tool_id: string | null
  process_id: string | null
  estimated_resolution_minutes: number | null
  resolution_type_id: string | null
  related_ticket_id: string | null
  created_by: string
  resolved_at: string | null
  resolution_accepted_at: string | null
  closed_at: string | null
  locked_fields: string[]
  close_eligible: boolean
  valid_actions: string[]
  comments: TicketComment[]
  transitions: TicketTransition[]
  assignments: TicketAssignment[]
}

export interface TicketFormData {
  title: string
  description: string
  ticket_type: TicketType
  priority: Priority
  severity: Severity
  client_id: string
  project_id?: string | null
  tool_id?: string | null
  process_id?: string | null
  record_type_id?: string | null
  escalation_level?: EscalationLevel
  related_ticket_id?: string | null
}

export interface TicketFilters {
  page?: number
  page_size?: number
  search?: string
  client_id?: string
  project_id?: string
  status?: TicketStatus[]
  priority?: Priority
  severity?: Severity
  ticket_type?: TicketType
  assignee_id?: string
  escalation_level?: EscalationLevel
  sort?: string
}

export interface PanelRow {
  resource: ResourceRef
  counts: Partial<Record<TicketStatus, number>>
  total: number
}

export interface PanelData {
  matrix: PanelRow[]
  unassigned_new: Array<{
    id: string
    ticket_number: string
    title: string
    priority: Priority
    severity: Severity
    client: EntityRef | null
    created_at: string
  }>
  statuses: TicketStatus[]
  status_labels: Record<string, string>
}
