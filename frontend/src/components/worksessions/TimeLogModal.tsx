import { useCallback, useEffect, useState } from 'react'
import { Button, Modal, Popconfirm, Space, Table, Tooltip, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, EditOutlined, DeleteOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { workSessionService } from '../../services/workSessionService'
import type { WorkSessionListItem } from '../../types/workSession'
import { formatDuration } from '../../types/workSession'
import type { TicketListItem } from '../../types/ticket'
import WorkSessionForm from './WorkSessionForm'

interface TimeLogModalProps {
  open: boolean
  onClose: () => void
  ticketId: string
  ticketNumber: string
  ticketTitle: string
  /** Permiso `work_sessions:manage` (US1 FR-010): sin él, el modal es de solo lectura. */
  canManage: boolean
  /** Notifica al resumen compacto del ticket (`TicketWorkSessions`) que debe recalcular sus
   * totales tras un alta/edición/borrado. */
  onChanged: () => void
}

const EDIT_WINDOW_DAYS = 7

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

/** Mismo criterio que `EDIT_WINDOW_DAYS` del backend — solo controla la UI; la API vuelve a
 * validar y es la fuente de verdad. */
function withinEditWindow(workDate: string): boolean {
  const diffMs = new Date(todayIso()).getTime() - new Date(workDate).getTime()
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24))
  return diffDays <= EDIT_WINDOW_DAYS
}

function formatTimeRange(item: WorkSessionListItem): string | null {
  if (!item.started_at || !item.ended_at) return null
  const start = item.started_at.slice(11, 16)
  const end = item.ended_at.slice(11, 16)
  return `${start} – ${end}`
}

/** Modal único de "Registro de tiempo" del ticket (Fase 2.2, US1) — reemplaza la tabla siempre
 * visible: historial correlacionado al ticket + alta/edición/borrado embebidos, sin abrir un
 * segundo modal (ver research.md Decisión 5). */
export default function TimeLogModal({ open, onClose, ticketId, ticketNumber, ticketTitle, canManage, onChanged }: TimeLogModalProps) {
  const [items, setItems] = useState<WorkSessionListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<WorkSessionListItem | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const sessions = await workSessionService.list({ ticket_id: ticketId, page_size: 100 })
      setItems(sessions.items)
    } finally {
      setLoading(false)
    }
  }, [ticketId])

  useEffect(() => { if (open) load() }, [open, load])
  useEffect(() => { if (!open) setFormOpen(false) }, [open])

  const handleDelete = async (id: string) => {
    try {
      await workSessionService.remove(id)
      message.success('Registro eliminado')
      load()
      onChanged()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message
        ?? 'Error al eliminar el registro'
      message.error(msg)
    }
  }

  const handleSaved = () => {
    load()
    onChanged()
  }

  const columns: ColumnsType<WorkSessionListItem> = [
    { title: 'Fecha', dataIndex: 'work_date', key: 'work_date' },
    {
      title: 'Horario', key: 'time_range',
      render: (_, record) => formatTimeRange(record) ?? '—',
    },
    {
      title: 'Duración', dataIndex: 'duration_minutes', key: 'duration_minutes',
      render: (minutes: number) => formatDuration(minutes),
    },
    { title: 'Quién', dataIndex: 'resource_name', key: 'resource_name' },
    { title: 'Nota', dataIndex: 'note', key: 'note', ellipsis: true },
    ...(canManage ? [{
      title: 'Acciones', key: 'actions',
      render: (_: unknown, record: WorkSessionListItem) => {
        const editable = withinEditWindow(record.work_date)
        return (
          <Space>
            <Tooltip title={editable ? 'Editar' : 'Ventana de edición de 7 días expirada'}>
              <Button
                size="small" icon={<EditOutlined />} disabled={!editable}
                onClick={() => { setEditing(record); setFormOpen(true) }}
              />
            </Tooltip>
            <Popconfirm
              title="¿Eliminar este registro de tiempo?"
              disabled={!editable}
              onConfirm={() => handleDelete(record.id)}
              okText="Eliminar" cancelText="Cancelar"
            >
              <Tooltip title={editable ? 'Eliminar' : 'Ventana de edición de 7 días expirada'}>
                <Button size="small" danger icon={<DeleteOutlined />} disabled={!editable} />
              </Tooltip>
            </Popconfirm>
          </Space>
        )
      },
    }] : []),
  ]

  const soloTicket: TicketListItem[] = [
    { id: ticketId, ticket_number: ticketNumber, title: ticketTitle } as TicketListItem,
  ]

  return (
    <Modal
      title={formOpen
        ? (editing ? 'Editar registro de tiempo' : 'Nuevo registro de tiempo')
        : `Registro de tiempo — ${ticketNumber}`}
      open={open}
      onCancel={onClose}
      footer={null}
      width={640}
      destroyOnHidden
    >
      {formOpen ? (
        <div>
          <Button
            type="link" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0, marginBottom: 8 }}
            onClick={() => { setFormOpen(false); setEditing(null) }}
          >
            Volver al historial
          </Button>
          <WorkSessionForm
            embedded
            open={formOpen}
            onClose={() => { setFormOpen(false); setEditing(null) }}
            onSaved={handleSaved}
            tickets={soloTicket}
            editing={editing}
          />
        </div>
      ) : (
        <div>
          {canManage && (
            <Button
              type="primary" icon={<PlusOutlined />} style={{ marginBottom: 12 }}
              onClick={() => { setEditing(null); setFormOpen(true) }}
            >
              Registrar tiempo
            </Button>
          )}
          <Table
            rowKey="id"
            size="small"
            loading={loading}
            columns={columns}
            dataSource={items}
            pagination={false}
            locale={{ emptyText: 'Todavía no hay tiempo registrado en este ticket.' }}
          />
        </div>
      )}
    </Modal>
  )
}
