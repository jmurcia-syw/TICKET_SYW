import { useCallback, useEffect, useState } from 'react'
import { Button, Popconfirm, Space, Table, Tooltip, Statistic, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { workSessionService } from '../../services/workSessionService'
import type { WorkSessionListItem } from '../../types/workSession'
import { formatDuration } from '../../types/workSession'
import type { TicketListItem } from '../../types/ticket'
import { useAuthStore } from '../../store/authStore'
import WorkSessionForm from './WorkSessionForm'

interface TicketWorkSessionsProps {
  ticketId: string
  ticketNumber: string
  ticketTitle: string
  /** Tiempo estimado de solución (minutos, US2) — se muestra junto al total real registrado. */
  estimatedMinutes?: number | null
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

/** Historial + alta/edición/borrado de "Registros de tiempo" embebido en el detalle del
 * ticket (Fase 2.1, US1) — estilo Teamwork. Reutiliza el motor de work_sessions de Fase 2. */
export default function TicketWorkSessions({ ticketId, ticketNumber, ticketTitle, estimatedMinutes }: TicketWorkSessionsProps) {
  const { hasPermission } = useAuthStore()
  const canManage = hasPermission('work_sessions', 'manage')
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

  useEffect(() => { load() }, [load])

  const totalMinutes = items.reduce((sum, item) => sum + item.duration_minutes, 0)

  const handleDelete = async (id: string) => {
    try {
      await workSessionService.remove(id)
      message.success('Registro eliminado')
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message
        ?? 'Error al eliminar el registro'
      message.error(msg)
    }
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
    {
      title: 'Acciones', key: 'actions',
      render: (_, record) => {
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
    },
  ]

  const soloTicket: TicketListItem[] = [
    { id: ticketId, ticket_number: ticketNumber, title: ticketTitle } as TicketListItem,
  ]

  return (
    <div>
      <Space style={{ marginBottom: 12, justifyContent: 'space-between', width: '100%' }} size="large">
        <Statistic title="Tiempo total registrado" value={formatDuration(totalMinutes)} />
        <Statistic
          title="Tiempo estimado"
          value={estimatedMinutes != null ? formatDuration(estimatedMinutes) : 'Sin estimar'}
        />
        {canManage && (
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setFormOpen(true)}>
            Registrar tiempo
          </Button>
        )}
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={items}
        pagination={false}
        locale={{ emptyText: 'Todavía no hay tiempo registrado en este ticket.' }}
      />
      {canManage && (
        <WorkSessionForm
          open={formOpen}
          onClose={() => { setFormOpen(false); setEditing(null) }}
          onSaved={load}
          tickets={soloTicket}
          editing={editing}
        />
      )}
    </div>
  )
}
