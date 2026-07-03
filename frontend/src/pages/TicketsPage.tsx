import { useCallback, useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Select, Space, Table, Tooltip, message } from 'antd'
import { PlusOutlined, EyeOutlined, UserSwitchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import { clientService } from '../services/clientService'
import { projectService } from '../services/projectService'
import { catalogService } from '../services/catalogService'
import { resourceService } from '../services/resourceService'
import type {
  TicketListItem, TicketFormData, TicketStatus, Priority,
} from '../types/ticket'
import { STATUS_LABELS, TICKET_TYPE_LABELS, PRIORITY_LABELS, SEVERITY_LABELS } from '../types/ticket'
import type { CatalogItem } from '../types/catalog'
import type { ClientListItem } from '../types/client'
import type { ProjectListItem } from '../types/project'
import type { Resource } from '../types/resource'
import TicketStatusTag from '../components/tickets/TicketStatusTag'
import AssignModal from '../components/tickets/AssignModal'
import PageToolbar from '../components/common/PageToolbar'
import { useAuthStore } from '../store/authStore'

const statusOptions = Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))
const priorityOptions = Object.entries(PRIORITY_LABELS).map(([value, label]) => ({ value, label }))
const severityOptions = Object.entries(SEVERITY_LABELS).map(([value, label]) => ({ value, label }))
const typeOptions = Object.entries(TICKET_TYPE_LABELS).map(([value, label]) => ({ value, label }))

export default function TicketsPage() {
  const { hasPermission } = useAuthStore()
  const navigate = useNavigate()
  const canCreate = hasPermission('tickets', 'create')
  const canAssign = hasPermission('tickets', 'assign')

  const [tickets, setTickets] = useState<TicketListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<TicketStatus[]>([])
  const [clientFilter, setClientFilter] = useState<string | undefined>()
  const [priorityFilter, setPriorityFilter] = useState<Priority | undefined>()
  const [assigneeFilter, setAssigneeFilter] = useState<string | undefined>()
  const [assigningId, setAssigningId] = useState<string | null>(null)

  const [clients, setClients] = useState<ClientListItem[]>([])
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [tools, setTools] = useState<CatalogItem[]>([])
  const [processes, setProcesses] = useState<CatalogItem[]>([])
  const [resources, setResources] = useState<Resource[]>([])
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
        assignee_id: assigneeFilter,
      })
      setTickets(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }, [page, search, statusFilter, clientFilter, priorityFilter, assigneeFilter])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    clientService.list({ active: true, page_size: 100 }).then(r => setClients(r.items))
    catalogService.list('tools').then(r => setTools(r.items))
    catalogService.list('processes').then(r => setProcesses(r.items))
    resourceService.list({ active: true, page_size: 100 }).then(r => setResources(r.items))
  }, [])

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
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al crear el ticket'
      message.error(msg)
    }
  }

  const columns: ColumnsType<TicketListItem> = [
    { title: 'Número', dataIndex: 'ticket_number', width: 110,
      render: (v: string) => <span className="tabular-nums">{v}</span> },
    { title: 'Título', dataIndex: 'title', ellipsis: true },
    { title: 'Cliente', dataIndex: ['client', 'name'], width: 160, ellipsis: true },
    { title: 'Estado', dataIndex: 'status', width: 150,
      render: (s: TicketStatus) => <TicketStatusTag status={s} /> },
    { title: 'Prioridad', dataIndex: 'priority', width: 100,
      render: (p: Priority) => PRIORITY_LABELS[p] },
    { title: 'Sev.', dataIndex: 'severity', width: 70,
      render: (s: string) => s.toUpperCase() },
    { title: 'Asignado', dataIndex: ['assignee', 'full_name'], width: 160,
      render: (v: string | undefined) => v ?? <em>—</em> },
    {
      title: 'Acciones', key: 'actions', width: 110,
      render: (_: unknown, t: TicketListItem) => (
        <Space>
          <Tooltip title="Ver detalle">
            <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/tickets/${t.id}`)} />
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
      <PageToolbar
        filters={<>
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
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setFormOpen(true) }}>
            Nuevo ticket
          </Button>
        )}
      />

      <Table rowKey="id" columns={columns} dataSource={tickets} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />

      <Modal title="Nuevo ticket" open={formOpen} onCancel={() => setFormOpen(false)}
        onOk={() => form.submit()} okText="Crear ticket" width={640}>
        <Form form={form} layout="vertical" onFinish={handleCreate}
          initialValues={{ ticket_type: 'incident', priority: 'medium', severity: 's3', escalation_level: 'n2' }}>
          <Form.Item name="title" label="Título" rules={[{ required: true, message: 'El título es requerido' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Descripción" rules={[{ required: true, message: 'La descripción es requerida' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
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
        </Form>
      </Modal>

      <AssignModal ticketId={assigningId} onClose={() => setAssigningId(null)} onAssigned={load} />
    </div>
  )
}
