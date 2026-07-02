import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Space, Table, Tooltip, message } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { skillService } from '../services/resourceService'
import type { Skill } from '../types/resource'
import ConfirmationModal from '../components/common/ConfirmationModal'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import { useAuthStore } from '../store/authStore'

interface SkillFormData {
  code: string
  label: string
}

export default function SkillsPage() {
  const { hasPermission } = useAuthStore()
  const canCreate = hasPermission('skills', 'create')
  const canDelete = hasPermission('skills', 'deactivate')

  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
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

  useEffect(() => { load() }, [])

  const openCreate = () => { form.resetFields(); setFormOpen(true) }

  const handleSubmit = async (values: SkillFormData) => {
    try {
      await skillService.create({ code: values.code.trim().toUpperCase(), label: values.label.trim() })
      message.success('Skill creado')
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
    { title: 'Código', dataIndex: 'code', sorter: (a, b) => a.code.localeCompare(b.code) },
    { title: 'Nombre', dataIndex: 'label' },
    { title: 'Estado', dataIndex: 'active', render: (v: boolean) => <StatusTag active={v ?? true} /> },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, r: Skill) => (
        <Space>
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

      <Modal title="Nuevo skill" open={formOpen} onCancel={() => setFormOpen(false)} onOk={() => form.submit()} okText="Guardar">
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="code" label="Código" rules={[{ required: true, message: 'El código es requerido' }]}>
            <Input placeholder="JDE_GL" />
          </Form.Item>
          <Form.Item name="label" label="Nombre descriptivo" rules={[{ required: true, message: 'El nombre es requerido' }]}>
            <Input placeholder="JD Edwards General Ledger" />
          </Form.Item>
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
