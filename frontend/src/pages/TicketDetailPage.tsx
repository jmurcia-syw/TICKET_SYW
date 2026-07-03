import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Col, Descriptions, Divider, InputNumber, Row, Select, Space, Spin, Tag, Tooltip, message } from 'antd'
import {
  ArrowLeftOutlined, UserSwitchOutlined, SaveOutlined, ClockCircleOutlined,
  FieldTimeOutlined, PlayCircleOutlined,
} from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import { catalogService } from '../services/catalogService'
import type { TicketDetail, Priority, Severity } from '../types/ticket'
import { PRIORITY_LABELS, SEVERITY_LABELS, TICKET_TYPE_LABELS } from '../types/ticket'
import type { CatalogItem } from '../types/catalog'
import TicketStatusTag from '../components/tickets/TicketStatusTag'
import PriorityBadge from '../components/tickets/PriorityBadge'
import CommentThread from '../components/tickets/CommentThread'
import CommentComposer from '../components/tickets/CommentComposer'
import AssignModal from '../components/tickets/AssignModal'
import { useAuthStore } from '../store/authStore'
import { palette, vivid } from '../theme'

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { hasPermission } = useAuthStore()
  const canAssign = hasPermission('tickets', 'assign')
  const canEdit = hasPermission('tickets', 'edit')

  const [ticket, setTicket] = useState<TicketDetail | null>(null)
  const [resolutionTypes, setResolutionTypes] = useState<CatalogItem[]>([])
  const [assignOpen, setAssignOpen] = useState(false)
  const [estimate, setEstimate] = useState<number | null>(null)
  const [priority, setPriority] = useState<Priority>()
  const [severity, setSeverity] = useState<Severity>()

  const load = useCallback(async () => {
    if (!id) return
    const data = await ticketService.get(id)
    setTicket(data)
    setEstimate(data.estimated_resolution_minutes)
    setPriority(data.priority)
    setSeverity(data.severity)
  }, [id])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    catalogService.list('resolution-types').then(r => setResolutionTypes(r.items))
  }, [])

  if (!ticket) return <Spin style={{ display: 'block', margin: '80px auto' }} />

  const locked = new Set(ticket.locked_fields)

  const saveEditable = async () => {
    try {
      const payload: Record<string, unknown> = {}
      if (!locked.has('estimated_resolution_minutes')) payload.estimated_resolution_minutes = estimate
      if (!locked.has('priority')) payload.priority = priority
      if (!locked.has('severity')) payload.severity = severity
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
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tickets')}>Volver</Button>
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
        {/* ── Columna principal: descripción + comentarios ── */}
        <Col xs={24} lg={14}>
          <Card title="Descripción" size="small">
            <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{ticket.description}</p>
          </Card>

          <Card title="Comentarios y acciones" size="small" style={{ marginTop: 16 }}>
            <CommentThread ticketId={ticket.id} comments={ticket.comments} />
            <Divider style={{ margin: '12px 0' }} />
            <CommentComposer ticket={ticket} resolutionTypes={resolutionTypes} onUpdated={load} />
          </Card>
        </Col>

        {/* ── Sidebar: SLA / Focus Room (placeholders) + clasificación + historial ── */}
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
              <Descriptions.Item label="Proyecto">{ticket.project?.name ?? '—'}</Descriptions.Item>
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
              <Descriptions.Item label="Tiempo estimado (min)">
                {canEdit && !locked.has('estimated_resolution_minutes')
                  ? <InputNumber size="small" min={0} value={estimate} onChange={setEstimate} />
                  : (ticket.estimated_resolution_minutes ?? '—')}
              </Descriptions.Item>
              <Descriptions.Item label="Creado">{new Date(ticket.created_at).toLocaleString('es-CO')}</Descriptions.Item>
              {ticket.resolved_at && (
                <Descriptions.Item label="Resuelto">{new Date(ticket.resolved_at).toLocaleString('es-CO')}</Descriptions.Item>
              )}
              {ticket.closed_at && (
                <Descriptions.Item label="Cerrado">{new Date(ticket.closed_at).toLocaleString('es-CO')}</Descriptions.Item>
              )}
            </Descriptions>
            {canEdit && (!locked.has('priority') || !locked.has('severity') || !locked.has('estimated_resolution_minutes')) && (
              <Button size="small" icon={<SaveOutlined />} onClick={saveEditable} style={{ marginTop: 8 }}>
                Guardar cambios
              </Button>
            )}
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
      </Row>

      <AssignModal ticketId={assignOpen ? ticket.id : null}
        onClose={() => setAssignOpen(false)} onAssigned={load} />
    </div>
  )
}
