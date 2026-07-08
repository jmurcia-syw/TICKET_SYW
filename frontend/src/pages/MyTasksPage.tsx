import { useCallback, useEffect, useState } from 'react'
import { Button, Table, Tooltip, message } from 'antd'
import { EyeOutlined, UnorderedListOutlined } from '@ant-design/icons'
import type { ColumnsType, TableProps } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import { resourceService } from '../services/resourceService'
import type { TicketListItem, TicketStatus, Priority, Severity } from '../types/ticket'
import TicketStatusTag from '../components/tickets/TicketStatusTag'
import PriorityBadge from '../components/tickets/PriorityBadge'
import SavedFiltersBar from '../components/tickets/SavedFiltersBar'
import type { TicketFilterCriteria } from '../store/savedFiltersStore'
import { palette } from '../theme'

/** "Mis Tareas" (Fase 2.2, US3): arranca con el filtro "Asignado a mí" preaplicado (FR-012),
 * resuelto vía `resourceService.me()` — mismo patrón que ya usa `WorkSessionsPage.tsx`. Comparte
 * el mecanismo de filtros guardados con `TicketsPage` (FR-014). */
export default function MyTasksPage() {
  const navigate = useNavigate()
  const [tickets, setTickets] = useState<TicketListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  /** `null` mientras se resuelve el preset "Asignado a mí" por defecto al montar. */
  const [criteria, setCriteria] = useState<TicketFilterCriteria | null>(null)

  useEffect(() => {
    resourceService.me().then(resource => setCriteria({ assignee_id: resource.id }))
      .catch(() => message.error('No se pudo resolver tu recurso asociado'))
  }, [])

  const load = useCallback(async () => {
    if (!criteria) return
    setLoading(true)
    try {
      const res = await ticketService.list({
        page, page_size: 20,
        search: criteria.search,
        status: criteria.status,
        client_id: criteria.client_id,
        priority: criteria.priority,
        severity: criteria.severity,
        assignee_id: criteria.assignee_id,
      })
      setTickets(res.items)
      setTotal(res.total)
    } catch {
      message.error('No se pudieron cargar tus tareas')
    } finally {
      setLoading(false)
    }
  }, [criteria, page])

  useEffect(() => { load() }, [load])

  const applySavedFilter = (c: TicketFilterCriteria) => {
    setCriteria(c)
    setPage(1)
  }

  const handleTableChange: TableProps<TicketListItem>['onChange'] = (pagination) => {
    setPage(pagination.current || 1)
  }

  const columns: ColumnsType<TicketListItem> = [
    { title: 'Número', dataIndex: 'ticket_number', width: 110,
      render: (v: string) => <span className="tabular-nums">{v}</span> },
    { title: 'Título', dataIndex: 'title', ellipsis: true },
    { title: 'Cliente', dataIndex: ['client', 'name'], key: 'client', width: 160, ellipsis: true },
    {
      title: 'Estado', dataIndex: 'status', key: 'status', width: 150,
      render: (s: TicketStatus) => <TicketStatusTag status={s} />,
    },
    {
      title: 'Prioridad', dataIndex: 'priority', key: 'priority', width: 90,
      render: (p: Priority) => <PriorityBadge priority={p} />,
    },
    { title: 'Sev.', dataIndex: 'severity', key: 'severity', width: 70, render: (s: Severity) => s.toUpperCase() },
    {
      title: 'Acciones', key: 'actions', width: 80,
      render: (_: unknown, t: TicketListItem) => (
        <Tooltip title="Ver detalle">
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/tickets/${t.id}`, {
            state: { from: { pathname: '/my-tasks', label: 'Mis Tareas' } },
          })} />
        </Tooltip>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <UnorderedListOutlined style={{ color: palette.brandOrange600, fontSize: 18 }} />
        <h2 style={{ margin: 0 }}>Mis Tareas</h2>
      </div>
      {/* Agrupamiento en una única lista por ahora — la organización por listas llega en
          Fase 3 (Manejo de Tareas), ver constitution.md (Fase 2.2, US4 — premisa visual). */}
      <p style={{ color: palette.slate500, fontSize: 12, marginTop: 4, marginBottom: 16 }}>
        Tus tickets asignados, en una sola lista por ahora — el agrupamiento por listas llega en Fase 3.
      </p>

      <div style={{ marginBottom: 12 }}>
        <SavedFiltersBar currentCriteria={criteria ?? {}} onApply={applySavedFilter} />
      </div>

      <Table
        rowKey="id" columns={columns} dataSource={tickets} loading={loading || !criteria}
        pagination={{ current: page, total, pageSize: 20 }} onChange={handleTableChange}
      />
    </div>
  )
}
