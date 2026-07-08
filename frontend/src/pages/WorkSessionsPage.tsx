import { useCallback, useEffect, useState } from 'react'
import { Button, Popconfirm, Space, Table, Tooltip, Typography, Statistic, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { workSessionService } from '../services/workSessionService'
import { ticketService } from '../services/ticketService'
import { resourceService } from '../services/resourceService'
import type { WorkSessionListItem } from '../types/workSession'
import { formatDuration } from '../types/workSession'
import type { TicketListItem, TicketStatus } from '../types/ticket'
import WorkSessionForm from '../components/worksessions/WorkSessionForm'
import PageToolbar from '../components/common/PageToolbar'

const OPEN_STATUSES: TicketStatus[] = [
  'nuevo', 'pre_analisis', 'contacto', 'en_analisis', 'en_ejecucion', 'en_pruebas',
  'pendiente_usuario', 'resuelto',
]

const EDIT_WINDOW_DAYS = 7

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

/** Mismo criterio que `EDIT_WINDOW_DAYS` del backend (FR-007) — solo controla la UI;
 * la API vuelve a validar y es la fuente de verdad. */
function withinEditWindow(workDate: string): boolean {
  const diffMs = new Date(todayIso()).getTime() - new Date(workDate).getTime()
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24))
  return diffDays <= EDIT_WINDOW_DAYS
}

export default function WorkSessionsPage() {
  const [items, setItems] = useState<WorkSessionListItem[]>([])
  const [tickets, setTickets] = useState<TicketListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<WorkSessionListItem | null>(null)

  const loadToday = useCallback(async () => {
    setLoading(true)
    try {
      const today = todayIso()
      const sessions = await workSessionService.list({ date_from: today, date_to: today, page_size: 100 })
      setItems(sessions.items)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadTickets = useCallback(async () => {
    const resource = await resourceService.me()
    const list = await ticketService.list({ assignee_id: resource.id, status: OPEN_STATUSES, page_size: 100 })
    setTickets(list.items)
  }, [])

  useEffect(() => {
    loadToday()
    loadTickets()
  }, [loadToday, loadTickets])

  const totalMinutes = items.reduce((sum, item) => sum + item.duration_minutes, 0)

  const handleDelete = async (id: string) => {
    try {
      await workSessionService.remove(id)
      message.success('Registro eliminado')
      loadToday()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message
        ?? 'Error al eliminar el registro'
      message.error(msg)
    }
  }

  const columns: ColumnsType<WorkSessionListItem> = [
    { title: 'Ticket', dataIndex: 'ticket_number', key: 'ticket_number' },
    { title: 'Fecha', dataIndex: 'work_date', key: 'work_date' },
    {
      title: 'Duración', dataIndex: 'duration_minutes', key: 'duration_minutes',
      render: (minutes: number) => formatDuration(minutes),
    },
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

  return (
    <div>
      <Typography.Title level={3}>Registro de Tiempos</Typography.Title>
      <PageToolbar
        filters={<Statistic title="Total registrado hoy" value={formatDuration(totalMinutes)} />}
        action={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormOpen(true)}>
            Nuevo registro
          </Button>
        }
      />
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={items}
        pagination={false}
      />
      {items.length === 0 && !loading && (
        <Typography.Text type="secondary">Todavía no registraste tiempo hoy.</Typography.Text>
      )}
      <WorkSessionForm
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditing(null) }}
        onSaved={loadToday}
        tickets={tickets}
        editing={editing}
      />
    </div>
  )
}
