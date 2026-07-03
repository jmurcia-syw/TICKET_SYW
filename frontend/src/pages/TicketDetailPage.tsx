import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Col, Descriptions, Divider, InputNumber, Row, Select, Space, Spin, Tag, message } from 'antd'
import { ArrowLeftOutlined, UserSwitchOutlined, SaveOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import { catalogService } from '../services/catalogService'
import type { TicketDetail, Priority, Severity } from '../types/ticket'
import { PRIORITY_LABELS, SEVERITY_LABELS, TICKET_TYPE_LABELS, STATUS_LABELS } from '../types/ticket'
import type { CatalogItem } from '../types/catalog'
import TicketStatusTag from '../components/tickets/TicketStatusTag'
import CommentThread from '../components/tickets/CommentThread'
import CommentComposer from '../components/tickets/CommentComposer'
import AssignModal from '../components/tickets/AssignModal'
import { useAuthStore } from '../store/authStore'

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
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tickets')}>Volver</Button>
        <h2 style={{ margin: 0 }}>{ticket.ticket_number} — {ticket.title}</h2>
        <TicketStatusTag status={ticket.status} />
        {canAssign && (ticket.status === 'nuevo' || ticket.status === 'pre_analisis') && (
          <Button type="primary" icon={<UserSwitchOutlined />} onClick={() => setAssignOpen(true)}>
            Asignar (Triage)
          </Button>
        )}
      </Space>

      <Row gutter={16}>
        <Col xs={24} lg={10}>
          <Card title="Clasificación" size="small">
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
                  : PRIORITY_LABELS[ticket.priority]}
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

          <Card title="Descripción" size="small" style={{ marginTop: 16 }}>
            <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{ticket.description}</p>
          </Card>

          <Card title="Historial de estados" size="small" style={{ marginTop: 16 }}>
            {ticket.transitions.length === 0
              ? <em>Sin transiciones todavía</em>
              : ticket.transitions.map(t => (
                <div key={t.id} style={{ fontSize: 12, marginBottom: 4 }}>
                  <Tag>{STATUS_LABELS[t.from_status as keyof typeof STATUS_LABELS] ?? t.from_status}</Tag>
                  →
                  <Tag>{STATUS_LABELS[t.to_status as keyof typeof STATUS_LABELS] ?? t.to_status}</Tag>
                  <span style={{ color: '#888' }}>{new Date(t.created_at).toLocaleString('es-CO')}</span>
                </div>
              ))}
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card title="Comentarios y acciones" size="small">
            <CommentThread ticketId={ticket.id} comments={ticket.comments} />
            <Divider style={{ margin: '12px 0' }} />
            <CommentComposer ticket={ticket} resolutionTypes={resolutionTypes} onUpdated={load} />
          </Card>
        </Col>
      </Row>

      <AssignModal ticketId={assignOpen ? ticket.id : null}
        onClose={() => setAssignOpen(false)} onAssigned={load} />
    </div>
  )
}
