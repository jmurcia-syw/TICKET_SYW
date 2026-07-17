import { useEffect, useState } from 'react'
import { Button, Form, Modal, Select, Space, Table, Tag, Tooltip, message } from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { slaService } from '../services/slaService'
import { projectService } from '../services/projectService'
import type { SlaRule, SlaRuleFormData } from '../types/sla'
import type { ProjectListItem } from '../types/project'
import { PRIORITY_LABELS } from '../types/ticket'
import SlaRuleForm from '../components/sla/SlaRuleForm'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import { useAuthStore } from '../store/authStore'

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'red', high: 'orange', medium: 'gold', low: 'default',
}

export default function SlaRulesPage() {
  const { hasPermission } = useAuthStore()
  const canManage = hasPermission('sla_rules', 'manage')

  const [rules, setRules] = useState<SlaRule[]>([])
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [projectFilter, setProjectFilter] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form] = Form.useForm<SlaRuleFormData>()
  const [formResetToken, setFormResetToken] = useState(0)

  const load = async (projectId?: string) => {
    setLoading(true)
    try {
      const res = await slaService.list({ project_id: projectId, page_size: 100 })
      setRules(res.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load(projectFilter)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectFilter])

  useEffect(() => {
    projectService.list({ page_size: 200, active: true }).then(r => setProjects(r.items)).catch(() => undefined)
  }, [])

  const openCreate = () => {
    form.resetFields()
    setEditingId(null)
    // Fuerza el remount de SlaRuleForm (spec 019, research.md Decisión 4) para que el estado
    // local de unidad/monto del campo de ejecución arranque limpio en cada apertura.
    setFormResetToken(t => t + 1)
    setFormOpen(true)
  }

  const openEdit = (rule: SlaRule) => {
    setEditingId(rule.id)
    form.setFieldsValue({
      project_id: rule.project_id,
      priority: rule.priority,
      contact_minutes: rule.contact_minutes,
      execution_minutes: rule.execution_minutes,
    })
    setFormResetToken(t => t + 1)
    setFormOpen(true)
  }

  const handleSubmit = async (values: SlaRuleFormData) => {
    try {
      if (editingId) {
        await slaService.update(editingId, {
          contact_minutes: values.contact_minutes,
          execution_minutes: values.execution_minutes,
        })
        message.success('Regla de SLA actualizada')
      } else {
        await slaService.create(values)
        message.success('Regla de SLA creada')
      }
      setFormOpen(false)
      load(projectFilter)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar'
      message.error(msg)
    }
  }

  const handleToggleActive = async (rule: SlaRule) => {
    try {
      await slaService.update(rule.id, { active: !rule.active })
      message.success(rule.active ? 'Regla desactivada' : 'Regla activada')
      load(projectFilter)
    } catch {
      message.error('No se pudo actualizar el estado')
    }
  }

  const columns: ColumnsType<SlaRule> = [
    { title: 'Proyecto', dataIndex: 'project_name', render: (v: string | null) => v ?? '—' },
    {
      title: 'Prioridad', dataIndex: 'priority',
      render: (v: keyof typeof PRIORITY_LABELS) => <Tag color={PRIORITY_COLORS[v]}>{PRIORITY_LABELS[v]}</Tag>,
    },
    { title: 'Contacto (min)', dataIndex: 'contact_minutes' },
    { title: 'Diagnóstico/Análisis/Ejecución (min)', dataIndex: 'execution_minutes' },
    {
      title: 'Estado', dataIndex: 'active', render: (v: boolean) => <StatusTag active={v} />,
    },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, r: SlaRule) => (
        <Space>
          {canManage && <Tooltip title="Editar"><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} /></Tooltip>}
          {canManage && (
            <Button size="small" onClick={() => handleToggleActive(r)}>
              {r.active ? 'Desactivar' : 'Activar'}
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageToolbar
        filters={(
          <Select
            allowClear
            placeholder="Filtrar por proyecto"
            style={{ width: 260 }}
            options={projects.map(p => ({ value: p.id, label: p.name }))}
            value={projectFilter}
            onChange={setProjectFilter}
          />
        )}
        action={canManage && <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nueva regla de SLA</Button>}
      />

      <Table rowKey="id" columns={columns} dataSource={rules} loading={loading} pagination={false} />

      <Modal title={editingId ? 'Editar regla de SLA' : 'Nueva regla de SLA'} open={formOpen}
        onCancel={() => setFormOpen(false)} onOk={() => form.submit()} okText="Guardar">
        <SlaRuleForm key={formResetToken} form={form} projects={projects} editing={!!editingId} onFinish={handleSubmit} />
      </Modal>
    </div>
  )
}
