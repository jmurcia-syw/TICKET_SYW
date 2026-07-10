import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Radio, Select, Space, Table, Tag, Tooltip, message } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { skillService } from '../services/resourceService'
import { catalogService } from '../services/catalogService'
import type { Skill, SkillType } from '../types/resource'
import type { CatalogItem } from '../types/catalog'
import ConfirmationModal from '../components/common/ConfirmationModal'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import { clientColumnFilter, clientTextColumnFilter } from '../components/common/columnFilters'
import { useAuthStore } from '../store/authStore'

interface SkillFormData {
  code: string
  label: string
  skill_type: SkillType
  tool_id?: string | null
  process_id?: string | null
}

const SKILL_TYPE_LABELS: Record<SkillType, string> = { funcional: 'Funcional', tecnico: 'Técnico' }
const SKILL_TYPE_COLORS: Record<SkillType, string> = { funcional: 'geekblue', tecnico: 'green' }

export default function SkillsPage() {
  const { hasPermission } = useAuthStore()
  const canCreate = hasPermission('skills', 'create')
  const canEdit = hasPermission('skills', 'edit')
  const canDelete = hasPermission('skills', 'deactivate')

  const [skills, setSkills] = useState<Skill[]>([])
  const [tools, setTools] = useState<CatalogItem[]>([])
  const [processes, setProcesses] = useState<CatalogItem[]>([])
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [form] = Form.useForm<SkillFormData>()

  const load = async () => {
    setLoading(true)
    try {
      const res = await skillService.list()
      setSkills(res.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    catalogService.list('tools').then(r => setTools(r.items)).catch(() => undefined)
    catalogService.list('processes').then(r => setProcesses(r.items)).catch(() => undefined)
  }, [])

  const openCreate = () => { form.resetFields(); setEditingId(null); setFormOpen(true) }

  const openEdit = (skill: Skill) => {
    setEditingId(skill.id)
    form.setFieldsValue({
      code: skill.code,
      label: skill.label,
      skill_type: skill.skill_type ?? 'tecnico',
      tool_id: skill.tool_id ?? undefined,
      process_id: skill.process_id ?? undefined,
    })
    setFormOpen(true)
  }

  const handleSubmit = async (values: SkillFormData) => {
    try {
      const payload = {
        label: values.label.trim(),
        skill_type: values.skill_type,
        tool_id: values.tool_id ?? null,
        process_id: values.process_id ?? null,
      }
      if (editingId) {
        await skillService.update(editingId, payload)
        message.success('Skill actualizado')
      } else {
        await skillService.create({ ...payload, code: values.code.trim().toUpperCase() })
        message.success('Skill creado')
      }
      setFormOpen(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar'
      message.error(msg)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await skillService.delete(id)
      message.success('Skill eliminado')
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'No se pudo eliminar el skill'
      message.error(msg)
    } finally {
      setConfirmDelete(null)
    }
  }

  const columns: ColumnsType<Skill> = [
    {
      title: 'Código', dataIndex: 'code', sorter: (a, b) => a.code.localeCompare(b.code),
      ...clientTextColumnFilter<Skill>('Buscar código...', r => r.code),
    },
    {
      title: 'Nombre', dataIndex: 'label',
      ...clientTextColumnFilter<Skill>('Buscar nombre...', r => r.label),
    },
    {
      title: 'Tipo', dataIndex: 'skill_type',
      render: (v: SkillType | undefined) => v
        ? <Tag color={SKILL_TYPE_COLORS[v]}>{SKILL_TYPE_LABELS[v]}</Tag> : '—',
      ...clientColumnFilter<Skill>(
        [{ text: 'Funcional', value: 'funcional' }, { text: 'Técnico', value: 'tecnico' }],
        (value, record) => record.skill_type === value,
      ),
    },
    { title: 'Herramienta', dataIndex: 'tool_name', render: (v: string | null) => v ?? '—' },
    { title: 'Proceso', dataIndex: 'process_name', render: (v: string | null) => v ?? '—' },
    {
      title: 'Estado', dataIndex: 'active', render: (v: boolean) => <StatusTag active={v ?? true} />,
      ...clientColumnFilter<Skill>(
        [{ text: 'Activo', value: 'true' }, { text: 'Inactivo', value: 'false' }],
        (value, record) => String(record.active ?? true) === value,
      ),
    },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, r: Skill) => (
        <Space>
          {canEdit && <Tooltip title="Editar"><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} /></Tooltip>}
          {canDelete && <Tooltip title="Eliminar"><Button size="small" danger icon={<DeleteOutlined />} onClick={() => setConfirmDelete(r.id)} /></Tooltip>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageToolbar
        filters={null}
        action={canCreate && <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo skill</Button>}
      />

      <Table rowKey="id" columns={columns} dataSource={skills} loading={loading} pagination={false} />

      <Modal title={editingId ? 'Editar skill' : 'Nuevo skill'} open={formOpen}
        onCancel={() => setFormOpen(false)} onOk={() => form.submit()} okText="Guardar">
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ skill_type: 'tecnico' }}>
          <Form.Item name="code" label="Código" rules={[{ required: true, message: 'El código es requerido' }]}>
            <Input placeholder="JDE_GL" disabled={!!editingId} />
          </Form.Item>
          <Form.Item name="label" label="Nombre descriptivo" rules={[{ required: true, message: 'El nombre es requerido' }]}>
            <Input placeholder="JD Edwards General Ledger" />
          </Form.Item>
          <Form.Item name="skill_type" label="Tipo" rules={[{ required: true, message: 'El tipo es obligatorio' }]}>
            <Radio.Group options={[
              { value: 'funcional', label: 'Funcional' },
              { value: 'tecnico', label: 'Técnico' },
            ]} />
          </Form.Item>
          <Space style={{ display: 'flex' }} align="start">
            <Form.Item name="tool_id" label="Herramienta (opcional)">
              <Select allowClear placeholder="Herramienta" style={{ width: 210 }}
                options={tools.map(t => ({ value: t.id, label: t.name }))} />
            </Form.Item>
            <Form.Item name="process_id" label="Proceso (opcional)">
              <Select allowClear placeholder="Proceso" style={{ width: 210 }}
                options={processes.map(p => ({ value: p.id, label: p.name }))} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      {confirmDelete && (
        <ConfirmationModal open title="Eliminar skill"
          description="¿Confirmas la eliminación de este skill? Esta acción no se puede deshacer."
          onConfirm={() => handleDelete(confirmDelete)} onCancel={() => setConfirmDelete(null)} />
      )}
    </div>
  )
}
