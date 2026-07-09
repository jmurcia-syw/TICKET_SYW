import { useCallback, useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Row, Col, Segmented, Select, Space, Table, Tooltip, message } from 'antd'
import {
  PlusOutlined, EyeOutlined, UserSwitchOutlined, InboxOutlined, ThunderboltOutlined,
  ClockCircleOutlined, CheckCircleOutlined, FieldTimeOutlined,
} from '@ant-design/icons'
import type { ColumnsType, TableProps } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import { clientService } from '../services/clientService'
import { projectService } from '../services/projectService'
import { clientContactService } from '../services/clientContactService'
import { catalogService } from '../services/catalogService'
import { resourceService } from '../services/resourceService'
import { taskListService } from '../services/taskListService'
import type {
  TicketListItem, TicketFormData, TicketStatus, Priority, Severity,
} from '../types/ticket'
import { STATUS_LABELS, TICKET_TYPE_LABELS, PRIORITY_LABELS, SEVERITY_LABELS } from '../types/ticket'
import type { CatalogItem } from '../types/catalog'
import type { ClientListItem } from '../types/client'
import type { ProjectListItem } from '../types/project'
import type { Resource } from '../types/resource'
import type { ClientContact } from '../types/clientContact'
import type { TaskList } from '../types/taskList'
import TicketStatusTag from '../components/tickets/TicketStatusTag'
import PriorityBadge from '../components/tickets/PriorityBadge'
import AssignModal from '../components/tickets/AssignModal'
import PageToolbar from '../components/common/PageToolbar'
import StatCard from '../components/common/StatCard'
import SavedFiltersBar from '../components/tickets/SavedFiltersBar'
import { textColumnFilter, serverColumnFilter } from '../components/common/columnFilters'
import { useAuthStore } from '../store/authStore'
import type { TicketFilterCriteria } from '../store/savedFiltersStore'

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
  const [contacts, setContacts] = useState<ClientContact[]>([])
  const [tools, setTools] = useState<CatalogItem[]>([])
  const [processes, setProcesses] = useState<CatalogItem[]>([])
  const [resources, setResources] = useState<Resource[]>([])
  const [recordTypes, setRecordTypes] = useState<CatalogItem[]>([])
  const [formOpen, setFormOpen] = useState(false)
  const [taskLists, setTaskLists] = useState<TaskList[]>([])
  const [form] = Form.useForm<TicketFormData>()
  const selectedClientId = Form.useWatch('client_id', form)
  const selectedProjectId = Form.useWatch('project_id', form)
  const selectedRecordTypeId = Form.useWatch('record_type_id', form)
  /** Fase 3: "Tarea" oculta la clasificación de incidente y muestra "Lista" (FR-001/002/010).
   * spec 009: el formulario reducido se mantiene (Assumptions) — solo cambia "Lista" de texto
   * libre a una entidad real (`list_id`, acotada al Proyecto elegido). */
  const isTaskSelected = recordTypes.find(rt => rt.id === selectedRecordTypeId)?.name === 'Tarea'

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
    try {
      const [nuevo, enProgreso, pendienteUsuario, resuelto] = await Promise.all([
        ticketService.list({ status: ['nuevo'], page_size: 1 }).then(r => r.total),
        ticketService.list({ status: IN_PROGRESS_STATUSES, page_size: 1 }).then(r => r.total),
        ticketService.list({ status: ['pendiente_usuario'], page_size: 1 }).then(r => r.total),
        ticketService.list({ status: ['resuelto'], page_size: 1 }).then(r => r.total),
      ])
      setStats({ nuevo, enProgreso, pendienteUsuario, resuelto })
    } catch {
      message.error('No se pudieron cargar las estadísticas de tickets')
    }
  }, [])

  useEffect(() => { loadStats() }, [loadStats])

  useEffect(() => {
    if (isEncargado) return  // sin permiso sobre clients/catalogs/resources — alta simplificada
    clientService.list({ active: true, page_size: 100 }).then(r => setClients(r.items))
      .catch(() => message.error('No se pudo cargar la lista de clientes'))
    catalogService.list('tools').then(r => setTools(r.items))
      .catch(() => message.error('No se pudo cargar el catálogo de herramientas'))
    catalogService.list('processes').then(r => setProcesses(r.items))
      .catch(() => message.error('No se pudo cargar el catálogo de procesos'))
    resourceService.list({ active: true, page_size: 100 }).then(r => setResources(r.items))
      .catch(() => message.error('No se pudo cargar la lista de recursos'))
    // Fase 3: "Ticket" y "Tarea" son ambos creables — el default al abrir el form es "Ticket"
    // (no el primero alfabético, que sería "Tarea").
    catalogService.list('record-types').then(r => {
      setRecordTypes(r.items)
      const ticketType = r.items.find(rt => rt.name === 'Ticket') ?? r.items[0]
      if (ticketType) form.setFieldValue('record_type_id', ticketType.id)
    }).catch(() => message.error('No se pudo cargar el catálogo de tipo de registro'))
  }, [form, isEncargado])

  useEffect(() => {
    if (selectedClientId) {
      projectService.list({ client_id: selectedClientId, active: true, page_size: 100 })
        .then(r => setProjects(r.items))
        .catch(() => message.error('No se pudo cargar la lista de proyectos'))
      clientContactService.list({ client_id: selectedClientId, page_size: 100 })
        .then(r => setContacts(r.items))
        .catch(() => message.error('No se pudo cargar la lista de encargados'))
      form.setFieldValue('project_id', undefined)
      // Encargado (Fase 2.2): acotado al cliente elegido — se limpia al cambiar de cliente
      // para no dejar seleccionado uno de un cliente distinto (FR-005).
      form.setFieldValue('client_contact_id', undefined)
    } else {
      setProjects([])
      setContacts([])
    }
  }, [selectedClientId, form])

  useEffect(() => {
    if (selectedProjectId) {
      taskListService.listByProject(selectedProjectId).then(setTaskLists)
        .catch(() => message.error('No se pudo cargar la lista de Listas del proyecto'))
      form.setFieldValue('list_id', undefined)
    } else {
      setTaskLists([])
    }
  }, [selectedProjectId, form])

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

  const currentCriteria: TicketFilterCriteria = {
    search: search || undefined,
    status: statusFilter.length ? statusFilter : undefined,
    client_id: clientFilter,
    priority: priorityFilter,
    severity: severityFilter,
    assignee_id: assigneeFilter,
  }

  const applySavedFilter = (criteria: TicketFilterCriteria) => {
    setSearch(criteria.search ?? '')
    setStatusFilter(criteria.status ?? [])
    setClientFilter(criteria.client_id)
    setPriorityFilter(criteria.priority)
    setSeverityFilter(criteria.severity)
    setAssigneeFilter(criteria.assignee_id)
    setPage(1)
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

      {!isEncargado && (
        <div style={{ marginBottom: 12 }}>
          <SavedFiltersBar currentCriteria={currentCriteria} onApply={applySavedFilter} />
        </div>
      )}

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
            const ticketType = recordTypes.find(rt => rt.name === 'Ticket') ?? recordTypes[0]
            if (!isEncargado && ticketType) form.setFieldValue('record_type_id', ticketType.id)
            setFormOpen(true)
          }}>
            Nuevo ticket
          </Button>
        )}
      />

      <Table rowKey="id" columns={columns} dataSource={tickets} loading={loading}
        pagination={{ current: page, total, pageSize: 20 }} onChange={handleTableChange} />

      <Modal title="Nuevo ticket" open={formOpen} onCancel={() => setFormOpen(false)}
        onOk={() => form.submit()} okText="Crear ticket" width={isEncargado ? 480 : 760}>
        <Form form={form} layout="vertical" onFinish={handleCreate}
          initialValues={isEncargado ? {} : { ticket_type: 'incident', priority: 'medium', severity: 's3', escalation_level: 'n2' }}>
          <Form.Item name="title" label="Título" rules={[{ required: true, message: 'El título es requerido' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Descripción" rules={[{ required: true, message: 'La descripción es requerida' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          {!isEncargado && <>
            <Form.Item name="record_type_id" label="Tipo de registro"
              rules={[{ required: true, message: 'Selecciona el tipo de registro' }]}>
              <Segmented options={recordTypes.map(rt => ({ value: rt.id, label: rt.name }))} />
            </Form.Item>
            <Space style={{ display: 'flex' }} align="start" wrap>
              <Form.Item name="client_id" label="Cliente" rules={[{ required: true, message: 'El cliente es requerido' }]}>
                <Select showSearch optionFilterProp="label" placeholder="Cliente" style={{ width: 220 }}
                  options={clients.map(c => ({ value: c.id, label: c.name }))} />
              </Form.Item>
              <Form.Item name="project_id" label="Proyecto (opcional)">
                <Select allowClear placeholder={selectedClientId ? 'Proyecto' : 'Elige cliente primero'}
                  disabled={!selectedClientId} style={{ width: 220 }}
                  options={projects.map(p => ({ value: p.id, label: p.name }))} />
              </Form.Item>
              <Form.Item name="client_contact_id" label="Encargado (opcional)">
                <Select allowClear placeholder={
                  !selectedClientId ? 'Elige cliente primero'
                    : contacts.length === 0 ? 'Sin encargados registrados' : 'Encargado'
                } disabled={!selectedClientId || contacts.length === 0} style={{ width: 220 }}
                  options={contacts.map(c => ({ value: c.id, label: c.username }))} />
              </Form.Item>
              {isTaskSelected && (
                <Form.Item name="list_id" label="Lista (opcional)">
                  <Select allowClear placeholder={selectedProjectId ? 'Lista' : 'Elige proyecto primero'}
                    disabled={!selectedProjectId} style={{ width: 200 }}
                    options={taskLists.map(l => ({ value: l.id, label: l.name }))} />
                </Form.Item>
              )}
            </Space>
            <>
              <Space style={{ display: 'flex' }} align="start" wrap>
                <Form.Item name="ticket_type" label="Tipo" rules={isTaskSelected ? [] : [{ required: true }]}>
                  <Select style={{ width: 130 }} options={typeOptions} allowClear={isTaskSelected} />
                </Form.Item>
                <Form.Item name="priority" label="Prioridad" rules={isTaskSelected ? [] : [{ required: true }]}>
                  <Select style={{ width: 110 }} options={priorityOptions} allowClear={isTaskSelected} />
                </Form.Item>
                <Form.Item name="severity" label="Severidad" rules={isTaskSelected ? [] : [{ required: true }]}>
                  <Select style={{ width: 100 }} options={severityOptions} allowClear={isTaskSelected} />
                </Form.Item>
                <Form.Item name="escalation_level" label="Nivel">
                  <Select style={{ width: 90 }} allowClear={isTaskSelected}
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
            </>
          </>}
        </Form>
      </Modal>

      <AssignModal ticketId={assigningId} onClose={() => setAssigningId(null)} onAssigned={load} />
    </div>
  )
}
