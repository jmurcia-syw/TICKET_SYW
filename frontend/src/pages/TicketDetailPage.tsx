import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Col, Descriptions, Divider, InputNumber, Row, Select, Space, Spin, Tag, Tooltip, message } from 'antd'
import {
  UserSwitchOutlined, SaveOutlined, ClockCircleOutlined,
  FieldTimeOutlined, PlayCircleOutlined, HistoryOutlined, UnorderedListOutlined,
} from '@ant-design/icons'
import { useParams } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import { catalogService } from '../services/catalogService'
import { clientContactService } from '../services/clientContactService'
import type { TicketDetail, Priority, Severity } from '../types/ticket'
import { PRIORITY_LABELS, SEVERITY_LABELS, TICKET_TYPE_LABELS, formatMinutes } from '../types/ticket'
import type { ConsumptionLevel } from '../types/workSession'
import type { CatalogItem } from '../types/catalog'
import type { ClientContact } from '../types/clientContact'
import TicketStatusTag from '../components/tickets/TicketStatusTag'
import PriorityBadge from '../components/tickets/PriorityBadge'
import CommentThread from '../components/tickets/CommentThread'
import CommentComposer from '../components/tickets/CommentComposer'
import AssignModal from '../components/tickets/AssignModal'
import TicketWorkSessions from '../components/worksessions/TicketWorkSessions'
import TicketBreadcrumb from '../components/tickets/TicketBreadcrumb'
import { useAuthStore } from '../store/authStore'
import { palette, vivid } from '../theme'

/** Colores del indicador de consumo estimado vs. real (Fase 2.2, US2 — research.md Decisión 6):
 * reutiliza los tokens ya existentes de la paleta, sin ampliarla. */
const CONSUMPTION_COLOR: Record<ConsumptionLevel, string> = {
  success: palette.green600,
  warning: palette.amber600,
  error: palette.red600,
  none: palette.slate400,
}

const CONSUMPTION_LABEL: Record<ConsumptionLevel, string> = {
  success: 'Consumo dentro de lo estimado',
  warning: 'Cerca del tiempo estimado',
  error: 'Tiempo estimado superado',
  none: '',
}

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { hasPermission } = useAuthStore()
  const canAssign = hasPermission('tickets', 'assign')
  const canEdit = hasPermission('tickets', 'edit')

  const [ticket, setTicket] = useState<TicketDetail | null>(null)
  const [resolutionTypes, setResolutionTypes] = useState<CatalogItem[]>([])
  const [recordTypes, setRecordTypes] = useState<CatalogItem[]>([])
  const [assignOpen, setAssignOpen] = useState(false)
  const [estimateHours, setEstimateHours] = useState<number | null>(null)
  const [priority, setPriority] = useState<Priority>()
  const [severity, setSeverity] = useState<Severity>()
  const [contacts, setContacts] = useState<ClientContact[]>([])
  const [clientContactId, setClientContactId] = useState<string | undefined>()
  /** Revelado fluido del resumen de tiempo (Fase 2.2, US1 FR-004/FR-005): expandido por defecto
   * y al cerrar el modal de tiempo; se colapsa al hacer scroll hacia abajo, se re-expande al
   * volver a scrollear hacia arriba (ver research.md Decisión 2). */
  const [timeExpanded, setTimeExpanded] = useState(true)
  const [timeSummary, setTimeSummary] = useState<{ startDate: string | null; consumptionLevel: ConsumptionLevel }>(
    { startDate: null, consumptionLevel: 'none' },
  )

  useEffect(() => {
    let lastY = window.scrollY
    const onScroll = () => {
      const y = window.scrollY
      if (y > lastY && y > 80) setTimeExpanded(false)
      else if (y < lastY) setTimeExpanded(true)
      lastY = y
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const load = useCallback(async () => {
    if (!id) return
    try {
      const data = await ticketService.get(id)
      setTicket(data)
      setEstimateHours(
        data.estimated_resolution_minutes != null ? data.estimated_resolution_minutes / 60 : null,
      )
      setPriority(data.priority)
      setSeverity(data.severity)
      setClientContactId(data.client_contact_id ?? undefined)
    } catch {
      message.error('No se pudo cargar el ticket')
    }
  }, [id])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    catalogService.list('resolution-types').then(r => setResolutionTypes(r.items))
      .catch(() => message.error('No se pudo cargar el catálogo de tipos de resolución'))
    catalogService.list('record-types', 'all').then(r => setRecordTypes(r.items))
      .catch(() => message.error('No se pudo cargar el catálogo de tipo de registro'))
  }, [])
  useEffect(() => {
    if (ticket?.client?.id) {
      clientContactService.list({ client_id: ticket.client.id, page_size: 100 }).then(r => setContacts(r.items))
        .catch(() => message.error('No se pudo cargar la lista de encargados'))
    }
  }, [ticket?.client?.id])

  if (!ticket) return <Spin style={{ display: 'block', margin: '80px auto' }} />

  const locked = new Set(ticket.locked_fields)
  /** Fase 2.2, FR-009: no editable cuando el solicitante se resolvió automáticamente del
   * creador (Encargado, autoservicio) — solo editable cuando es una asignación manual o cuando
   * todavía no hay ninguna. */
  const encargadoAutoDerivado = !ticket.client_contact_id && !!ticket.requester?.is_encargado
  const encargadoEditable = canEdit && !locked.has('client_contact_id') && !encargadoAutoDerivado

  const saveEditable = async () => {
    try {
      const payload: Record<string, unknown> = {}
      if (!locked.has('estimated_resolution_minutes')) {
        payload.estimated_resolution_minutes = estimateHours != null ? Math.round(estimateHours * 60) : null
      }
      if (!locked.has('priority')) payload.priority = priority
      if (!locked.has('severity')) payload.severity = severity
      if (encargadoEditable) payload.client_contact_id = clientContactId ?? null
      await ticketService.update(ticket.id, payload)
      message.success('Ticket actualizado')
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al actualizar'
      message.error(msg)
    }
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap align="center">
        <TicketBreadcrumb />
        <span style={{ fontSize: 12, fontWeight: 700, color: vivid.blue.text, letterSpacing: 0.4 }}>
          {ticket.ticket_number}
        </span>
        <h2 style={{ margin: 0 }}>{ticket.title}</h2>
        <TicketStatusTag status={ticket.status} />
        <PriorityBadge priority={ticket.priority} full />
        {canAssign && (ticket.status === 'nuevo' || ticket.status === 'pre_analisis') && (
          <Button type="primary" icon={<UserSwitchOutlined />} onClick={() => setAssignOpen(true)}>
            Asignar (Triage)
          </Button>
        )}
      </Space>

      <Row gutter={16}>
        {/* ── Columna principal: descripción → resumen de tiempo → comentarios → actividad,
             en un único flujo consolidado (Fase 2.2, US1 FR-004) ── */}
        <Col xs={24} lg={14}>
          <Card title="Descripción" size="small">
            <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{ticket.description}</p>
          </Card>

          <Card
            size="small"
            title={<span><HistoryOutlined style={{ color: vivid.green.text, marginRight: 8 }} />Registros de tiempo</span>}
            style={{ marginTop: 16, transition: 'opacity 200ms cubic-bezier(0.23, 1, 0.32, 1)' }}
          >
            <TicketWorkSessions
              ticketId={ticket.id}
              ticketNumber={ticket.ticket_number}
              ticketTitle={ticket.title}
              estimatedMinutes={ticket.estimated_resolution_minutes}
              compact={!timeExpanded}
              onSummary={setTimeSummary}
              onModalClose={() => setTimeExpanded(true)}
            />
          </Card>

          <Card title="Comentarios y acciones" size="small" style={{ marginTop: 16 }}>
            <CommentThread ticketId={ticket.id} comments={ticket.comments} />
            <Divider style={{ margin: '12px 0' }} />
            <CommentComposer ticket={ticket} resolutionTypes={resolutionTypes} onUpdated={load} />
          </Card>

          <Card title="Historial de estados" size="small" style={{ marginTop: 16 }}>
            {ticket.transitions.length === 0
              ? <em>Sin transiciones todavía</em>
              : ticket.transitions.map(t => (
                <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, marginBottom: 6 }}>
                  <TicketStatusTag status={t.from_status as TicketDetail['status']} />
                  <span style={{ color: palette.slate400 }}>→</span>
                  <TicketStatusTag status={t.to_status as TicketDetail['status']} />
                  <span style={{ color: palette.slate400, marginLeft: 4 }}>{new Date(t.created_at).toLocaleString('es-CO')}</span>
                </div>
              ))}
          </Card>
        </Col>

        {/* ── Sidebar: SLA / Focus Room / Subtareas (placeholders) + clasificación ── */}
        <Col xs={24} lg={10}>
          <Card
            size="small"
            title={<span><ClockCircleOutlined style={{ color: vivid.red.text, marginRight: 8 }} />SLA</span>}
            style={{ borderColor: palette.slate200, background: palette.slate50 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
              <span style={{ fontSize: 22, fontWeight: 700, color: palette.slate400 }}>—:—:—</span>
              <Tooltip title="Tiempos de atención/análisis/resolución por prioridad — llega en Fase 4 (Gestión de SLAs)">
                <Tag>Próximamente · Fase 4</Tag>
              </Tooltip>
            </div>
            <div style={{ height: 6, background: palette.slate200, borderRadius: 3, marginBottom: 6 }}>
              <div style={{ height: 6, borderRadius: 3, background: palette.slate300, width: '0%' }} />
            </div>
            <div style={{ fontSize: 11, color: palette.slate400 }}>
              Contador de atención/análisis/resolución por prioridad y cliente
            </div>
          </Card>

          <Card
            size="small"
            title={<span><FieldTimeOutlined style={{ color: vivid.purple.text, marginRight: 8 }} />Sesión de trabajo (Focus Room)</span>}
            style={{ marginTop: 16, borderColor: palette.slate200, background: palette.slate50 }}
          >
            <div style={{ textAlign: 'center', padding: '4px 0 10px' }}>
              <div style={{ fontSize: 26, fontWeight: 700, color: palette.slate400, fontFamily: 'ui-monospace, monospace' }}>
                00:00:00
              </div>
              <div style={{ fontSize: 11, color: palette.slate400, marginBottom: 10 }}>
                Tiempo efectivo dedicado a este ticket
              </div>
              <Tooltip title="Modo de trabajo enfocado en un solo ticket, con asistente IA — llega en Fase 7">
                <Button size="small" icon={<PlayCircleOutlined />} disabled style={{ width: '100%' }}>
                  Iniciar sesión · Fase 7
                </Button>
              </Tooltip>
            </div>
          </Card>

          <Card title="Clasificación" size="small" style={{ marginTop: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Cliente">{ticket.client?.name}</Descriptions.Item>
              <Descriptions.Item label="Encargado solicitante">
                {encargadoEditable ? (
                  <Select
                    size="small" allowClear placeholder="Sin encargado asignado" style={{ width: 200 }}
                    value={clientContactId} onChange={setClientContactId}
                    options={contacts.map(c => ({ value: c.id, label: c.username }))}
                  />
                ) : ticket.requester?.is_encargado ? (
                  <span
                    style={{
                      display: 'inline-block', padding: '2px 10px', borderRadius: 999,
                      fontSize: 12, fontWeight: 600, background: vivid.purple.bg, color: vivid.purple.text,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {ticket.requester.name}
                  </span>
                ) : (
                  <em style={{ color: palette.slate400 }}>Sin encargado asignado</em>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Lista">
                <Tooltip title="Organización en listas — llega en Fase 3 (Manejo de Tareas)">
                  <span style={{ color: palette.slate400 }}>
                    Sin asignar <Tag style={{ marginLeft: 4 }}>Próximamente</Tag>
                  </span>
                </Tooltip>
              </Descriptions.Item>
              <Descriptions.Item label="Proyecto">{ticket.project?.name ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="Tipo de registro">
                {recordTypes.find(rt => rt.id === ticket.record_type_id)?.name ?? '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Tipo">{TICKET_TYPE_LABELS[ticket.ticket_type]}</Descriptions.Item>
              <Descriptions.Item label="Nivel de escalamiento">{ticket.escalation_level.toUpperCase()}</Descriptions.Item>
              <Descriptions.Item label="Asignado">{ticket.assignee?.full_name ?? 'Sin asignar'}</Descriptions.Item>
              <Descriptions.Item label="Prioridad">
                {canEdit && !locked.has('priority')
                  ? <Select size="small" value={priority} onChange={setPriority} style={{ width: 120 }}
                      options={Object.entries(PRIORITY_LABELS).map(([v, l]) => ({ value: v, label: l }))} />
                  : <PriorityBadge priority={ticket.priority} full />}
              </Descriptions.Item>
              <Descriptions.Item label="Severidad">
                {canEdit && !locked.has('severity')
                  ? <Select size="small" value={severity} onChange={setSeverity} style={{ width: 90 }}
                      options={Object.entries(SEVERITY_LABELS).map(([v, l]) => ({ value: v, label: l }))} />
                  : ticket.severity.toUpperCase()}
              </Descriptions.Item>
              <Descriptions.Item label="Fecha de inicio">
                {timeSummary.startDate
                  ? new Date(timeSummary.startDate).toLocaleDateString('es-CO')
                  : <em style={{ color: palette.slate400 }}>Aún sin iniciar</em>}
              </Descriptions.Item>
              <Descriptions.Item label="Tiempo estimado de solución">
                <Space size={8} align="center">
                  {canEdit && !locked.has('estimated_resolution_minutes')
                    ? <InputNumber size="small" min={0} step={0.5} addonAfter="h"
                        value={estimateHours} onChange={setEstimateHours} />
                    : (ticket.estimated_resolution_minutes != null
                        ? formatMinutes(ticket.estimated_resolution_minutes)
                        : 'Sin estimar')}
                  {timeSummary.consumptionLevel !== 'none' && (
                    <Tooltip title={CONSUMPTION_LABEL[timeSummary.consumptionLevel]}>
                      <span
                        style={{
                          display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                          background: CONSUMPTION_COLOR[timeSummary.consumptionLevel],
                        }}
                      />
                    </Tooltip>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Creado">{new Date(ticket.created_at).toLocaleString('es-CO')}</Descriptions.Item>
              {ticket.resolved_at && (
                <Descriptions.Item label="Resuelto">{new Date(ticket.resolved_at).toLocaleString('es-CO')}</Descriptions.Item>
              )}
              {ticket.closed_at && (
                <Descriptions.Item label="Cerrado">{new Date(ticket.closed_at).toLocaleString('es-CO')}</Descriptions.Item>
              )}
            </Descriptions>
            {canEdit && (!locked.has('priority') || !locked.has('severity') || !locked.has('estimated_resolution_minutes') || encargadoEditable) && (
              <Button size="small" icon={<SaveOutlined />} onClick={saveEditable} style={{ marginTop: 8 }}>
                Guardar cambios
              </Button>
            )}
          </Card>

          <Card
            size="small"
            title={<span><UnorderedListOutlined style={{ color: palette.slate400, marginRight: 8 }} />Subtareas</span>}
            style={{ marginTop: 16, borderColor: palette.slate200, background: palette.slate50 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, color: palette.slate400 }}>
                Este ticket todavía no admite subtareas
              </span>
              <Tooltip title="Desglose en subtareas — llega en Fase 3 (Manejo de Tareas)">
                <Tag>Próximamente · Fase 3</Tag>
              </Tooltip>
            </div>
          </Card>
        </Col>
      </Row>

      <AssignModal ticketId={assignOpen ? ticket.id : null}
        onClose={() => setAssignOpen(false)} onAssigned={load} />
    </div>
  )
}
