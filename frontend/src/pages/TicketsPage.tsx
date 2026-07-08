import { useCallback, useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Row, Col, Select, Space, Table, Tooltip, message } from 'antd'
import {
  PlusOutlined, EyeOutlined, UserSwitchOutlined, InboxOutlined, ThunderboltOutlined,
  ClockCircleOutlined, CheckCircleOutlined, FieldTimeOutlined,
} from '@ant-design/icons'
import type { ColumnsType, TableProps } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import { clientService } from '../services/clientService'
import { projectService } from '../services/projectService'
import { catalogService } from '../services/catalogService'
import { resourceService } from '../services/resourceService'
import type {
  TicketListItem, TicketFormData, TicketStatus, Priority, Severity,
} from '../types/ticket'
import { STATUS_LABELS, TICKET_TYPE_LABELS, PRIORITY_LABELS, SEVERITY_LABELS } from '../types/ticket'
import type { CatalogItem } from '../types/catalog'
import type { ClientListItem } from '../types/client'
import type { ProjectListItem } from '../types/project'
import type { Resource } from '../types/resource'
import TicketStatusTag from '../components/tickets/TicketStatusTag'
import PriorityBadge from '../components/tickets/PriorityBadge'
import AssignModal from '../components/tickets/AssignModal'
import PageToolbar from '../components/common/PageToolbar'
import StatCard from '../components/common/StatCard'
import { textColumnFilter, serverColumnFilter } from '../components/common/columnFilters'
import { useAuthStore } from '../store/authStore'

const IN_PROGRESS_STATUSES: TicketStatus[] = ['contacto', 'en_analisis', 'en_ejecucion', 'en_pruebas']

const statusOptions = Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))
const priorityOptions = Object.entries(PRIORITY_LABELS).map(([value, label]) => ({ value, label }))
const severityOptions = Object.entries(SEVERITY_LABELS).map(([value, label]) => ({ value, label }))
const typeOptions = Object.entries(TICKET_TYPE_LABELS).map(([value, label]) => ({ value, label }))

export default function TicketsPage() {
  const { hasPermission, role } = useAuthStore()
  const navigate = useNavigate()
  const canCreate = hasPermission('tickets', 'create')
  const canAssign = hasPermission('tickets', 'assign')
  /** Encargado (Fase 2.1 US3): alta simplificada (solo título/descripción), sin acceso a
   * catálogos/clientes/recursos internos — el backend ya filtra su listado a lo propio. */
  const isEncargado = role?.name === 'Encargado'

  const [tickets, setTickets] = useState<TicketListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<TicketStatus[]>([])
  const [clientFilter, setClientFilter] = useState<string | undefined>()
  const [priorityFilter, setPriorityFilter] = useState<Priority | undefined>()
  const [severityFilter, setSeverityFilter] = useState<Severity | undefined>()
  const [assigneeFilter, setAssigneeFilter] = useState<string | undefined>()
  const [assigningId, setAssigningId] = useState<string | null>(null)
  const [stats, setStats] = useState<{ nuevo: number; enProgreso: number; pendienteUsuario: number; resuelto: number } | null>(null)

  const [clients, setClients] = useState<ClientListItem[]>([])
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [tools, setTools] = useState<CatalogItem[]>([])
  const [processes, setProcesses] = useState<CatalogItem[]>([])
  const [resources, setResources] = useState<Resource[]>([])
  const [recordTypes, setRecordTypes] = useState<CatalogItem[]>([])
  const [formOpen, setFormOpen] = useState(false)
  const [form] = Form.useForm<TicketFormData>()
  const selectedClientId = Form.useWatch('client_id', form)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await ticketService.list({
        page, page_size: 20,
        search: search || undefined,
        status: statusFilter.length ? statusFilter : undefined,
        client_id: clientFilter,
        priority: priorityFilter,
        severity: severityFilter,
        assignee_id: assigneeFilter,
      })
      setTickets(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }, [page, search, statusFilter, clientFilter, priorityFilter, severityFilter, assigneeFilter])

  useEffect(() => { load() }, [load])

  const loadStats = useCallback(async () => {
    const [nuevo, enProgreso, pendienteUsuario, resuelto] = await Promise.all([
      ticketService.list({ status: ['nuevo'], page_size: 1 }).then(r => r.total),
      ticketService.list({ status: IN_PROGRESS_STATUSES, page_size: 1 }).then(r => r.total),
      ticketService.list({ status: ['pendiente_usuario'], page_size: 1 }).then(r => r.total),
      ticketService.list({ status: ['resuelto'], page_size: 1 }).then(r => r.total),
    ])
    setStats({ nuevo, enProgreso, pendienteUsuario, resuelto })
  }, [])

  useEffect(() => { loadStats() }, [loadStats])

  useEffect(() => {
    if (isEncargado) return  // sin permiso sobre clients/catalogs/resources — alta simplificada
    clientService.list({ active: true, page_size: 100 }).then(r => setClients(r.items))
    catalogService.list('tools').then(r => setTools(r.items))
    catalogService.list('processes').then(r => setProcesses(r.items))
    resourceService.list({ active: true, page_size: 100 }).then(r => setResources(r.items))
    // Solo "Ticket" es creable en esta fase (FR-030); "Tarea" queda reservado para Fase 3
    // aunque el catálogo ya lo tenga sembrado.
    catalogService.list('record-types').then(r => {
      const creatable = r.items.filter(rt => rt.name === 'Ticket')
      setRecordTypes(creatable)
      if (creatable[0]) form.setFieldValue('record_type_id', creatable[0].id)
    })
  }, [form, isEncargado])

  useEffect(() => {
    if (selectedClientId) {
      projectService.list({ client_id: selectedClientId, active: true, page_size: 100 })
        .then(r => setProjects(r.items))
      form.setFieldValue('project_id', undefined)
    } else {
      setProjects([])
    }
  }, [selectedClientId, form])

  const handleCreate = async (values: TicketFormData) => {
    try {
      const created = await ticketService.create(values)
      message.success(`Ticket ${created.ticket_number} creado`)
      setFormOpen(false)
      form.resetFields()
      load()
      loadStats()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al crear el ticket'
      message.error(msg)
    }
  }

  const handleTableChange: TableProps<TicketListItem>['onChange'] = (pagination, filters) => {
    setPage(pagination.current || 1)
    setClientFilter((filters.client?.[0] as string) || undefined)
    setStatusFilter((filters.status as TicketStatus[] | null) || [])
    setPriorityFilter((filters.priority?.[0] as Priority) || undefined)
    setSeverityFilter((filters.severity?.[0] as Severity) || undefined)
    setAssigneeFilter((filters.assignee?.[0] as string) || undefined)
  }

  const columns: ColumnsType<TicketListItem> = [
    { title: 'Número', dataIndex: 'ticket_number', width: 110,
      render: (v: string) => <span className="tabular-nums">{v}</span> },
    {
      title: 'Título', dataIndex: 'title', ellipsis: true,
      ...textColumnFilter('Buscar título o número...', search, setSearch),
    },
    {
      title: 'Cliente', dataIndex: ['client', 'name'], key: 'client', width: 160, ellipsis: true,
      ...serverColumnFilter(clients.map(c => ({ text: c.name, value: c.id })), clientFilter),
    },
    {
      title: 'Estado', dataIndex: 'status', key: 'status', width: 150,
      render: (s: TicketStatus) => <TicketStatusTag status={s} />,
      filters: statusOptions.map(o => ({ text: o.label, value: o.value })),
      filteredValue: statusFilter.length ? statusFilter : null,
      onFilter: () => true,
    },
    {
      title: 'Prioridad', dataIndex: 'priority', key: 'priority', width: 90,
      render: (p: Priority) => <PriorityBadge priority={p} />,
      ...serverColumnFilter(priorityOptions.map(o => ({ text: o.label, value: o.value })), priorityFilter),
    },
    {
      title: 'Sev.', dataIndex: 'severity', key: 'severity', width: 70,
      render: (s: string) => s.toUpperCase(),
      ...serverColumnFilter(severityOptions.map(o => ({ text: o.label, value: o.value })), severityFilter),
    },
    {
      title: 'Asignado', dataIndex: ['assignee', 'full_name'], key: 'assignee', width: 160,
      render: (v: string | undefined) => v ?? <em>—</em>,
      ...serverColumnFilter(resources.map(r => ({ text: r.full_name, value: r.id })), assigneeFilter),
    },
    {
      title: 'Acciones', key: 'actions', width: 110,
      render: (_: unknown, t: TicketListItem) => (
        <Space>
          <Tooltip title="Ver detalle">
            <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/tickets/${t.id}`, {
              state: { from: { pathname: '/tickets', label: 'Tickets' } },
            })} />
          </Tooltip>
          {canAssign && (t.status === 'nuevo' || t.status === 'pre_analisis') && (
            <Tooltip title="Asignar (Triage)">
              <Button size="small" icon={<UserSwitchOutlined />} onClick={() => setAssigningId(t.id)} />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col xs={12} md={8} lg={4}>
          <StatCard label="Nuevos" value={stats?.nuevo ?? '—'} icon={<InboxOutlined />} color="blue" sub="Pendientes de triage" />
        </Col>
        <Col xs={12} md={8} lg={4}>
          <StatCard label="En progreso" value={stats?.enProgreso ?? '—'} icon={<ThunderboltOutlined />} color="orange" sub="Contacto → En pruebas" />
        </Col>
        <Col xs={12} md={8} lg={4}>
          <StatCard label="Pend. usuario" value={stats?.pendienteUsuario ?? '—'} icon={<ClockCircleOutlined />} color="magenta" sub="SLA pausado (Fase 4)" />
        </Col>
        <Col xs={12} md={8} lg={4}>
          <StatCard label="Resueltos" value={stats?.resuelto ?? '—'} icon={<CheckCircleOutlined />} color="green" sub="Pendientes de cierre" />
        </Col>
        <Col xs={12} md={8} lg={4}>
          <StatCard label="Vencen hoy" value="—" icon={<FieldTimeOutlined />} color="red" placeholder
            placeholderHint="Contador de SLA — llega en Fase 4 (Gestión de SLAs)" />
        </Col>
      </Row>

      <PageToolbar
        filters={isEncargado
          ? <Input.Search placeholder="Buscar por título o número..." onSearch={setSearch} allowClear style={{ width: 240 }} />
          : <>
              <Input.Search placeholder="Buscar por título o número..." onSearch={setSearch} allowClear style={{ width: 240 }} />
              <Select mode="multiple" placeholder="Estados" allowClear style={{ minWidth: 180 }}
                value={statusFilter} onChange={setStatusFilter} options={statusOptions} maxTagCount={2} />
              <Select placeholder="Cliente" allowClear showSearch optionFilterProp="label" style={{ width: 170 }}
                onChange={setClientFilter} options={clients.map(c => ({ value: c.id, label: c.name }))} />
              <Select placeholder="Prioridad" allowClear style={{ width: 120 }}
                onChange={setPriorityFilter} options={priorityOptions} />
              <Select placeholder="Asignado" allowClear showSearch optionFilterProp="label" style={{ width: 160 }}
                onChange={setAssigneeFilter} options={resources.map(r => ({ value: r.id, label: r.full_name }))} />
            </>}
        action={canCreate && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => {
            form.resetFields()
            if (!isEncargado && recordTypes[0]) form.setFieldValue('record_type_id', recordTypes[0].id)
            setFormOpen(true)
          }}>
            Nuevo ticket
          </Button>
        )}
      />

      <Table rowKey="id" columns={columns} dataSource={tickets} loading={loading}
        pagination={{ current: page, total, pageSize: 20 }} onChange={handleTableChange} />

      <Modal title="Nuevo ticket" open={formOpen} onCancel={() => setFormOpen(false)}
        onOk={() => form.submit()} okText="Crear ticket" width={isEncargado ? 480 : 640}>
        <Form form={form} layout="vertical" onFinish={handleCreate}
          initialValues={isEncargado ? {} : { ticket_type: 'incident', priority: 'medium', severity: 's3', escalation_level: 'n2' }}>
          <Form.Item name="title" label="Título" rules={[{ required: true, message: 'El título es requerido' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Descripción" rules={[{ required: true, message: 'La descripción es requerida' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          {!isEncargado && <>
            <Space style={{ display: 'flex' }} align="start">
              <Form.Item name="client_id" label="Cliente" rules={[{ required: true, message: 'El cliente es requerido' }]}>
                <Select showSearch optionFilterProp="label" placeholder="Cliente" style={{ width: 260 }}
                  options={clients.map(c => ({ value: c.id, label: c.name }))} />
              </Form.Item>
              <Form.Item name="project_id" label="Proyecto (opcional)">
                <Select allowClear placeholder={selectedClientId ? 'Proyecto' : 'Elige cliente primero'}
                  disabled={!selectedClientId} style={{ width: 260 }}
                  options={projects.map(p => ({ value: p.id, label: p.name }))} />
              </Form.Item>
            </Space>
            <Space style={{ display: 'flex' }} align="start" wrap>
              <Form.Item name="record_type_id" label="Tipo de registro"
                rules={[{ required: true, message: 'Selecciona el tipo de registro' }]}>
                <Select style={{ width: 130 }}
                  options={recordTypes.map(rt => ({ value: rt.id, label: rt.name }))} />
              </Form.Item>
              <Form.Item name="ticket_type" label="Tipo" rules={[{ required: true }]}>
                <Select style={{ width: 130 }} options={typeOptions} />
              </Form.Item>
              <Form.Item name="priority" label="Prioridad" rules={[{ required: true }]}>
                <Select style={{ width: 110 }} options={priorityOptions} />
              </Form.Item>
              <Form.Item name="severity" label="Severidad" rules={[{ required: true }]}>
                <Select style={{ width: 100 }} options={severityOptions} />
              </Form.Item>
              <Form.Item name="escalation_level" label="Nivel">
                <Select style={{ width: 90 }}
                  options={['n1', 'n2', 'n3', 'n4'].map(v => ({ value: v, label: v.toUpperCase() }))} />
              </Form.Item>
            </Space>
            <Space style={{ display: 'flex' }} align="start">
              <Form.Item name="tool_id" label="Herramienta">
                <Select allowClear placeholder="Herramienta" style={{ width: 200 }}
                  options={tools.map(t => ({ value: t.id, label: t.name }))} />
              </Form.Item>
              <Form.Item name="process_id" label="Proceso">
                <Select allowClear placeholder="Proceso" style={{ width: 200 }}
                  options={processes.map(p => ({ value: p.id, label: p.name }))} />
              </Form.Item>
            </Space>
          </>}
        </Form>
      </Modal>

      <AssignModal ticketId={assigningId} onClose={() => setAssigningId(null)} onAssigned={load} />
    </div>
  )
}
