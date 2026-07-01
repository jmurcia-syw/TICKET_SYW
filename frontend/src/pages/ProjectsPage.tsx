import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Select, Space, Table, Tooltip, message } from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, PlayCircleOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { projectService } from '../services/projectService'
import { clientService } from '../services/clientService'
import type { ProjectListItem, ProjectFormData } from '../types/project'
import type { ClientListItem } from '../types/client'
import ConfirmationModal from '../components/common/ConfirmationModal'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import { palette } from '../theme'

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [clients, setClients] = useState<ClientListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [clientFilter, setClientFilter] = useState<string | undefined>()
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null)
  const [form] = Form.useForm<ProjectFormData>()

  const load = async () => {
    setLoading(true)
    try {
      const res = await projectService.list({ page, page_size: 20, client_id: clientFilter, search: search || undefined })
      setProjects(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    clientService.list({ active: true, page_size: 100 }).then(r => setClients(r.items))
  }, [])

  useEffect(() => { load() }, [page, clientFilter, search])

  const openCreate = () => { form.resetFields(); setEditingId(null); setFormOpen(true) }
  const openEdit = (p: ProjectListItem) => {
    form.setFieldsValue({ ...p, start_date: p.start_date, end_date_estimated: p.end_date_estimated ?? undefined })
    setEditingId(p.id)
    setFormOpen(true)
  }

  const handleSubmit = async (values: ProjectFormData) => {
    try {
      if (editingId) {
        await projectService.update(editingId, values)
        message.success('Proyecto actualizado')
      } else {
        await projectService.create(values)
        message.success('Proyecto creado')
      }
      setFormOpen(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar'
      message.error(msg)
    }
  }

  const handleDeactivate = async (id: string) => {
    await projectService.deactivate(id)
    message.success('Proyecto desactivado')
    setConfirmDeactivate(null)
    load()
  }

  const handleActivate = async (id: string) => {
    await projectService.activate(id)
    message.success('Proyecto activado')
    load()
  }

  const columns: ColumnsType<ProjectListItem> = [
    { title: 'Nombre', dataIndex: 'name', sorter: true },
    { title: 'Cliente', dataIndex: 'client_name' },
    { title: 'Inicio', dataIndex: 'start_date', render: (v: string) => <span className="tabular-nums">{v}</span> },
    { title: 'Fin estimado', dataIndex: 'end_date_estimated', render: (v: string | null) => <span className="tabular-nums">{v ?? '—'}</span> },
    { title: 'Estado', dataIndex: 'active', render: (v: boolean) => <StatusTag active={v} /> },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, r: ProjectListItem) => (
        <Space>
          <Tooltip title="Editar"><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} /></Tooltip>
          {r.active
            ? <Tooltip title="Desactivar"><Button size="small" danger icon={<StopOutlined />} onClick={() => setConfirmDeactivate(r.id)} /></Tooltip>
            : <Tooltip title="Activar"><Button size="small" icon={<PlayCircleOutlined style={{ color: palette.green600 }} />} onClick={() => handleActivate(r.id)} /></Tooltip>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageToolbar
        filters={<>
          <Input.Search placeholder="Buscar proyecto..." onSearch={setSearch} allowClear style={{ width: 220 }} />
          <Select placeholder="Filtrar por cliente" allowClear style={{ width: 200 }} onChange={setClientFilter}
            options={clients.map(c => ({ value: c.id, label: c.name }))} />
        </>}
        action={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo proyecto</Button>}
      />

      <Table rowKey="id" columns={columns} dataSource={projects} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />

      <Modal title={editingId ? 'Editar proyecto' : 'Nuevo proyecto'} open={formOpen} onCancel={() => setFormOpen(false)} onOk={() => form.submit()} okText="Guardar">
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="client_id" label="Cliente" rules={[{ required: true, message: 'El cliente es requerido' }]}>
            <Select options={clients.map(c => ({ value: c.id, label: c.name }))} placeholder="Seleccionar cliente" />
          </Form.Item>
          <Form.Item name="name" label="Nombre" rules={[{ required: true, message: 'El nombre es requerido' }]}><Input /></Form.Item>
          <Form.Item name="description" label="Descripción"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="start_date" label="Fecha de inicio" rules={[{ required: true, message: 'La fecha de inicio es requerida' }]}>
            <Input type="date" />
          </Form.Item>
          <Form.Item name="end_date_estimated" label="Fecha de fin estimada"><Input type="date" /></Form.Item>
        </Form>
      </Modal>

      {confirmDeactivate && (
        <ConfirmationModal
          open
          title="Desactivar proyecto"
          description="¿Confirmas la desactivación de este proyecto? No aparecerá en la creación de nuevos tickets."
          onConfirm={() => handleDeactivate(confirmDeactivate)}
          onCancel={() => setConfirmDeactivate(null)}
        />
      )}
    </div>
  )
}
