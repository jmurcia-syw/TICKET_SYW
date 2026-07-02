import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Select, Space, Table, Tag, Tooltip, message } from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, PlayCircleOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { resourceService, skillService } from '../services/resourceService'
import type { Resource, ResourceFormData, Skill } from '../types/resource'
import { useAuthStore } from '../store/authStore'
import ConfirmationModal from '../components/common/ConfirmationModal'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import { palette } from '../theme'

export default function ResourcesPage() {
  const { hasPermission, userId } = useAuthStore()
  // Admin, Coordinador y QM comparten el mismo acceso completo sobre Recursos (FR-013).
  const canManage = hasPermission('resources', 'create')
  const isOwnProfile = (r: Resource) => r.user_id === userId

  const [resources, setResources] = useState<Resource[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [skillFilter, setSkillFilter] = useState<string | undefined>()
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null)
  const [form] = Form.useForm<ResourceFormData>()

  const load = async () => {
    setLoading(true)
    try {
      const res = await resourceService.list({ page, page_size: 20, search: search || undefined, skill_code: skillFilter })
      setResources(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    skillService.list(true).then(r => setSkills(r.items))
  }, [])

  useEffect(() => { load() }, [page, skillFilter, search])

  const openCreate = () => { form.resetFields(); setEditingId(null); setFormOpen(true) }
  const openEdit = (r: Resource) => {
    form.setFieldsValue({ ...r, skill_ids: r.skills.map(s => s.id) })
    setEditingId(r.id)
    setFormOpen(true)
  }

  const handleSubmit = async (values: ResourceFormData) => {
    try {
      if (editingId) {
        await resourceService.update(editingId, { notes: values.notes })
        if (canManage && values.skill_ids) {
          await resourceService.updateSkills(editingId, values.skill_ids)
        }
        message.success('Recurso actualizado')
      } else {
        await resourceService.create(values)
        message.success('Recurso creado')
      }
      setFormOpen(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar'
      message.error(msg)
    }
  }

  const handleDeactivate = async (id: string) => {
    await resourceService.deactivate(id)
    message.success('Recurso desactivado')
    setConfirmDeactivate(null)
    load()
  }

  const handleActivate = async (id: string) => {
    await resourceService.activate(id)
    message.success('Recurso activado')
    load()
  }

  const columns: ColumnsType<Resource> = [
    { title: 'Nombre', dataIndex: 'full_name', sorter: true },
    { title: 'Email', dataIndex: 'email' },
    {
      title: 'Skills', dataIndex: 'skills',
      render: (s: Skill[]) => s.map(sk => (
        <Tag key={sk.id} style={{ fontFamily: 'ui-monospace, SFMono-Regular, monospace', letterSpacing: 0.3, color: palette.slate700, background: palette.slate100, borderColor: palette.slate200 }}>
          {sk.code}
        </Tag>
      )),
    },
    { title: 'Estado', dataIndex: 'active', render: (v: boolean) => <StatusTag active={v} /> },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, r: Resource) => (
        <Space>
          {(canManage || isOwnProfile(r)) && <Tooltip title="Editar"><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} /></Tooltip>}
          {canManage && (r.active
            ? <Tooltip title="Desactivar"><Button size="small" danger icon={<StopOutlined />} onClick={() => setConfirmDeactivate(r.id)} /></Tooltip>
            : <Tooltip title="Activar"><Button size="small" icon={<PlayCircleOutlined style={{ color: palette.green600 }} />} onClick={() => handleActivate(r.id)} /></Tooltip>)}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageToolbar
        filters={<>
          <Input.Search placeholder="Buscar recurso..." onSearch={setSearch} allowClear style={{ width: 220 }} />
          <Select placeholder="Filtrar por skill" allowClear style={{ width: 200 }} onChange={setSkillFilter}
            options={skills.map(s => ({ value: s.code, label: `${s.code} — ${s.label}` }))} />
        </>}
        action={canManage && <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo recurso</Button>}
      />

      <Table rowKey="id" columns={columns} dataSource={resources} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />

      <Modal title={editingId ? 'Editar recurso' : 'Nuevo recurso'} open={formOpen} onCancel={() => setFormOpen(false)} onOk={() => form.submit()} okText="Guardar">
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          {canManage && !editingId && (
            <>
              <Form.Item name="full_name" label="Nombre completo" rules={[{ required: true, message: 'El nombre es requerido' }]}><Input /></Form.Item>
              <Form.Item name="email" label="Email (@sywork.net)" rules={[{ required: true, message: 'El email es requerido' }, { pattern: /^[^@]+@sywork\.net$/, message: 'Debe ser @sywork.net' }]}><Input /></Form.Item>
            </>
          )}
          {canManage && (
            <Form.Item name="skill_ids" label="Skills">
              <Select mode="multiple" options={skills.map(s => ({ value: s.id, label: `${s.code} — ${s.label}` }))} placeholder="Seleccionar skills" />
            </Form.Item>
          )}
          <Form.Item name="notes" label="Notas"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      {confirmDeactivate && (
        <ConfirmationModal open title="Desactivar recurso"
          description="¿Confirmas la desactivación de este recurso? No aparecerá en sugerencias de asignación."
          onConfirm={() => handleDeactivate(confirmDeactivate)} onCancel={() => setConfirmDeactivate(null)} />
      )}
    </div>
  )
}
