import { useCallback, useEffect, useMemo, useState } from 'react'
import { DragDropContext, Droppable, Draggable, type DropResult } from '@hello-pangea/dnd'
import { Empty, Input, Modal, Select, Spin, Tooltip, message } from 'antd'
import { FieldTimeOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import { resourceService } from '../services/resourceService'
import type { CommentType, EscalationLevel, Priority, TicketListItem, TicketStatus } from '../types/ticket'
import { STATUS_LABELS, PRIORITY_LABELS, formatMinutes } from '../types/ticket'
import type { Resource } from '../types/resource'
import { getKanbanTransition, reachableFrom } from '../config/kanbanTransitions'
import PriorityBadge from '../components/tickets/PriorityBadge'
import AssignModal from '../components/tickets/AssignModal'
import { avatarColor, initials, palette, TICKET_STATUS_CHIP } from '../theme'
import { useAuthStore } from '../store/authStore'

// Estados activos del ciclo de vida (docs/PROPUESTA_VISUAL.html — "Vista Kanban").
// CERRADO y CANCELADO son finales y no aportan al tablero operativo.
const BOARD_STATUSES: TicketStatus[] = [
  'nuevo', 'pre_analisis', 'contacto', 'en_analisis', 'en_ejecucion',
  'en_pruebas', 'pendiente_usuario', 'resuelto',
]
const LEVEL_OPTIONS: EscalationLevel[] = ['n1', 'n2', 'n3', 'n4']

// Espejo local de backend/domain/entities/comment.py::COMMENT_TYPE_LABELS — solo para
// los tipos que el Kanban puede disparar por arrastre.
const KANBAN_COMMENT_LABELS: Record<CommentType, string> = {
  asignado: 'Asignado', pre_analisis: 'Pre-Análisis',
  confirmacion_atencion: 'Confirmación de atención', solicitud_informacion: 'Solicitud de información',
  termina_analisis: 'Termina análisis', solicitud_cierre: 'Solicitud de cierre',
  respuesta_usuario: 'Respuesta de usuario', descripcion_solucion: 'Descripción solución',
  comentario_interno: 'Comentario interno', cancelacion: 'Cancelación',
}

export default function KanbanPage() {
  const navigate = useNavigate()
  const { hasPermission } = useAuthStore()
  const canDrag = hasPermission('tickets', 'transition') || hasPermission('tickets', 'assign')

  const [columns, setColumns] = useState<Record<TicketStatus, TicketListItem[]> | null>(null)
  const [loading, setLoading] = useState(false)
  const [resources, setResources] = useState<Resource[]>([])

  const [statusFilter, setStatusFilter] = useState<TicketStatus[]>([])
  const [assigneeFilter, setAssigneeFilter] = useState<string | undefined>()
  const [priorityFilter, setPriorityFilter] = useState<Priority | undefined>()
  const [levelFilter, setLevelFilter] = useState<EscalationLevel | undefined>()

  const [assignModal, setAssignModal] = useState<{ ticketId: string; mode: 'resolver' | 'pre_analysis' } | null>(null)
  const [commentModal, setCommentModal] = useState<{ ticketId: string; commentType: CommentType } | null>(null)
  const [commentBody, setCommentBody] = useState('')
  const [resolutionModal, setResolutionModal] = useState<{ ticketId: string } | null>(null)
  const [resolutionBody, setResolutionBody] = useState('El usuario rechazó la resolución')
  const [actionLoading, setActionLoading] = useState(false)

  const visibleStatuses = statusFilter.length ? statusFilter : BOARD_STATUSES

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const results = await Promise.all(
        BOARD_STATUSES.map(status => ticketService.list({
          status: [status], page_size: 50, sort: '-created_at',
          assignee_id: assigneeFilter, priority: priorityFilter, escalation_level: levelFilter,
        }))
      )
      const next = {} as Record<TicketStatus, TicketListItem[]>
      BOARD_STATUSES.forEach((status, i) => { next[status] = results[i].items })
      setColumns(next)
    } catch {
      message.error('No se pudo cargar el tablero Kanban')
    } finally {
      setLoading(false)
    }
  }, [assigneeFilter, priorityFilter, levelFilter])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    resourceService.list({ active: true, page_size: 100 }).then(r => setResources(r.items))
      .catch(() => message.error('No se pudo cargar la lista de recursos'))
  }, [])

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return
    const from = result.source.droppableId as TicketStatus
    const to = result.destination.droppableId as TicketStatus
    if (from === to) return
    const ticketId = result.draggableId

    const transition = getKanbanTransition(from, to)
    if (!transition) {
      const targets = reachableFrom(from).map(s => STATUS_LABELS[s])
      message.error(
        targets.length > 0
          ? `No puedes mover un ticket de "${STATUS_LABELS[from]}" directo a "${STATUS_LABELS[to]}". Desde aquí solo puede pasar a: ${targets.join(', ')}.`
          : `"${STATUS_LABELS[from]}" no tiene transiciones directas de arrastre disponibles.`
      )
      return
    }

    switch (transition.kind) {
      case 'testing':
        doTesting(ticketId, transition.direction)
        break
      case 'comment':
        setCommentBody('')
        setCommentModal({ ticketId, commentType: transition.commentType })
        break
      case 'assign':
        setAssignModal({ ticketId, mode: transition.mode })
        break
      case 'resolution':
        setResolutionBody('El usuario rechazó la resolución')
        setResolutionModal({ ticketId })
        break
    }
  }

  const doTesting = async (ticketId: string, direction: 'enter' | 'exit') => {
    try {
      await ticketService.toggleTesting(ticketId, direction)
      message.success(direction === 'enter' ? 'Ticket pasado a En Pruebas' : 'Ticket devuelto a En Ejecución')
      load()
    } catch (err: unknown) {
      message.error(apiError(err, 'No se pudo mover el ticket'))
    }
  }

  const submitComment = async () => {
    if (!commentModal) return
    if (!commentBody.trim()) {
      message.warning('El comentario no puede estar vacío')
      return
    }
    setActionLoading(true)
    try {
      await ticketService.addComment(commentModal.ticketId, commentModal.commentType, commentBody)
      message.success('Ticket avanzado')
      setCommentModal(null)
      load()
    } catch (err: unknown) {
      message.error(apiError(err, 'No se pudo registrar el comentario'))
    } finally {
      setActionLoading(false)
    }
  }

  const submitResolutionReject = async () => {
    if (!resolutionModal) return
    setActionLoading(true)
    try {
      await ticketService.recordResolution(resolutionModal.ticketId, false, resolutionBody)
      message.success('Ticket devuelto a En Ejecución')
      setResolutionModal(null)
      load()
    } catch (err: unknown) {
      message.error(apiError(err, 'No se pudo registrar la respuesta'))
    } finally {
      setActionLoading(false)
    }
  }

  const priorityOptions = useMemo(() => Object.entries(PRIORITY_LABELS).map(([value, label]) => ({ value, label })), [])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ margin: 0 }}>Tablero Kanban</h2>
          <span style={{ fontSize: 12, color: palette.slate500 }}>
            Arrastra una tarjeta a otra columna para avanzarla; solo se permiten los movimientos válidos del flujo.
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <Select mode="multiple" placeholder="Estados" allowClear style={{ minWidth: 170 }}
            value={statusFilter} onChange={setStatusFilter} maxTagCount={2}
            options={BOARD_STATUSES.map(s => ({ value: s, label: STATUS_LABELS[s] }))} />
          <Select placeholder="Asignado" allowClear showSearch optionFilterProp="label" style={{ width: 160 }}
            value={assigneeFilter} onChange={setAssigneeFilter}
            options={resources.map(r => ({ value: r.id, label: r.full_name }))} />
          <Select placeholder="Prioridad" allowClear style={{ width: 120 }}
            value={priorityFilter} onChange={setPriorityFilter} options={priorityOptions} />
          <Select placeholder="Nivel" allowClear style={{ width: 90 }}
            value={levelFilter} onChange={setLevelFilter}
            options={LEVEL_OPTIONS.map(l => ({ value: l, label: l.toUpperCase() }))} />
        </div>
      </div>

      {loading && !columns ? (
        <Spin style={{ display: 'block', margin: '80px auto' }} />
      ) : (
        <DragDropContext onDragEnd={handleDragEnd}>
          <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 8 }}>
            {visibleStatuses.map(status => {
              const chip = TICKET_STATUS_CHIP[status]
              const items = columns?.[status] ?? []
              return (
                <div key={status} style={{ minWidth: 260, flex: '0 0 260px' }}>
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '8px 12px', borderRadius: 8, marginBottom: 8,
                    background: chip.bg, color: chip.text,
                  }}>
                    <span style={{ fontSize: 13, fontWeight: 700 }}>{STATUS_LABELS[status]}</span>
                    <span style={{
                      minWidth: 20, textAlign: 'center', borderRadius: 999, fontSize: 12, fontWeight: 700,
                      background: 'rgba(255,255,255,0.6)', padding: '0 6px',
                    }}>
                      {items.length}
                    </span>
                  </div>

                  <Droppable droppableId={status}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.droppableProps}
                        style={{
                          display: 'flex', flexDirection: 'column', gap: 8, minHeight: 80,
                          maxHeight: 'calc(100vh - 260px)', overflowY: 'auto', padding: 2,
                          background: snapshot.isDraggingOver ? palette.brandOrange50 : 'transparent',
                          borderRadius: 8, transition: 'background 0.15s',
                        }}
                      >
                        {items.length === 0 && !snapshot.isDraggingOver && (
                          <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description={<span style={{ fontSize: 12, color: palette.slate400 }}>Sin tickets</span>}
                            style={{ margin: '8px 0' }}
                          />
                        )}
                        {items.map((t, index) => (
                          <Draggable key={t.id} draggableId={t.id} index={index} isDragDisabled={!canDrag}>
                            {(dragProvided, dragSnapshot) => (
                              <div
                                ref={dragProvided.innerRef}
                                {...dragProvided.draggableProps}
                                {...dragProvided.dragHandleProps}
                                onClick={() => !dragSnapshot.isDragging && navigate(`/tickets/${t.id}`, {
                                  state: { from: { pathname: '/kanban', label: 'Kanban' } },
                                })}
                                style={{
                                  cursor: canDrag ? 'grab' : 'pointer', borderRadius: 10, padding: 10,
                                  border: `1px solid ${palette.slate200}`, background: '#fff',
                                  boxShadow: dragSnapshot.isDragging ? '0 6px 16px rgba(0,0,0,0.16)' : '0 1px 2px rgba(0,0,0,0.04)',
                                  ...dragProvided.draggableProps.style,
                                }}
                              >
                                <div style={{ fontSize: 11, fontWeight: 700, color: palette.slate400, marginBottom: 2 }}>
                                  {t.ticket_number}
                                </div>
                                <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8, lineHeight: 1.3 }}>
                                  {t.title}
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                                  <PriorityBadge priority={t.priority} />
                                  <Tooltip title="Tiempo estimado de resolución">
                                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color: palette.slate500 }}>
                                      <FieldTimeOutlined /> {formatMinutes(t.estimated_resolution_minutes)}
                                    </span>
                                  </Tooltip>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                  {t.assignee ? (
                                    <>
                                      <div style={{
                                        width: 20, height: 20, borderRadius: '50%', display: 'flex', alignItems: 'center',
                                        justifyContent: 'center', background: avatarColor(t.assignee.id).bg,
                                        color: avatarColor(t.assignee.id).text, fontSize: 9, fontWeight: 700, flexShrink: 0,
                                      }}>
                                        {initials(t.assignee.full_name)}
                                      </div>
                                      <span style={{ fontSize: 12, color: palette.slate600 }}>{t.assignee.full_name}</span>
                                    </>
                                  ) : (
                                    <span style={{ fontSize: 12, color: palette.slate400 }}>Sin asignar</span>
                                  )}
                                </div>
                              </div>
                            )}
                          </Draggable>
                        ))}
                        {provided.placeholder}
                      </div>
                    )}
                  </Droppable>
                </div>
              )
            })}
          </div>
        </DragDropContext>
      )}

      <AssignModal
        ticketId={assignModal?.ticketId ?? null}
        forcedMode={assignModal?.mode}
        onClose={() => setAssignModal(null)}
        onAssigned={load}
      />

      <Modal
        title={commentModal ? `Registrar "${KANBAN_COMMENT_LABELS[commentModal.commentType]}"` : ''}
        open={!!commentModal}
        onCancel={() => setCommentModal(null)}
        confirmLoading={actionLoading}
        onOk={submitComment}
        okText="Registrar y avanzar"
      >
        <Input.TextArea rows={4} value={commentBody} onChange={e => setCommentBody(e.target.value)}
          placeholder="Escribe el comentario que respalda este cambio de estado..." autoFocus />
      </Modal>

      <Modal
        title="Rechazo de resolución"
        open={!!resolutionModal}
        onCancel={() => setResolutionModal(null)}
        confirmLoading={actionLoading}
        onOk={submitResolutionReject}
        okText="Devolver a En Ejecución"
        okButtonProps={{ danger: true }}
      >
        <Input.TextArea rows={3} value={resolutionBody} onChange={e => setResolutionBody(e.target.value)} />
      </Modal>
    </div>
  )
}

function apiError(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? fallback
}
