import { useEffect, useState } from 'react'
import { Button, Collapse, Divider, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Tooltip, message } from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, PlayCircleOutlined, DollarOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { resourceService, skillService } from '../services/resourceService'
import type { Resource, ResourceFormData, Skill, ResourceCompensation, CompensationFormData } from '../types/resource'
import { useAuthStore } from '../store/authStore'
import ConfirmationModal from '../components/common/ConfirmationModal'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import { palette } from '../theme'

export default function ResourcesPage() {
  const { hasPermission, userId } = useAuthStore()
  // Admin, Coordinador y QM comparten el mismo acceso completo sobre Recursos (FR-013).
  const canManage = hasPermission('resources', 'create')
  const canViewCompensation = hasPermission('compensation', 'view')
  const canEditCompensation = hasPermission('compensation', 'edit')
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
  const [compOpen, setCompOpen] = useState<Resource | null>(null)
  const [compensation, setCompensation] = useState<ResourceCompensation | null>(null)
  const [form] = Form.useForm<ResourceFormData>()
  const [compForm] = Form.useForm<CompensationFormData>()

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

  const openCompensation = async (r: Resource) => {
    setCompOpen(r)
    compForm.resetFields()
    setCompensation(null)
    try {
      const comp = await resourceService.getCompensation(r.id)
      setCompensation(comp)
      compForm.setFieldsValue(comp)
    } catch {
      // 404 = sin compensación registrada aún; el formulario queda vacío
    }
  }

  const handleSaveCompensation = async (values: CompensationFormData) => {
    if (!compOpen) return
    try {
      const saved = await resourceService.saveCompensation(compOpen.id, values)
      setCompensation(saved)
      compForm.setFieldsValue(saved)
      message.success('Compensación guardada')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar la compensación'
      message.error(msg)
    }
  }

  const handleSubmit = async (values: ResourceFormData) => {
    const profileFields = {
      notes: values.notes,
      identification: values.identification,
      nationality: values.nationality,
      birth_date: values.birth_date,
      marital_status: values.marital_status,
      contract_type: values.contract_type,
      calendar_country: values.calendar_country,
      education_level: values.education_level,
      specialty: values.specialty,
      seniority: values.seniority,
      certifications: values.certifications,
      team: values.team,
      manager_id: values.manager_id ?? null,
    }
    try {
      if (editingId) {
        await resourceService.update(editingId, profileFields)
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
          {canViewCompensation && <Tooltip title="Compensación"><Button size="small" icon={<DollarOutlined />} onClick={() => openCompensation(r)} /></Tooltip>}
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
          <Collapse
            ghost
            items={[{
              key: 'profile',
              label: 'Perfil extendido (SDD V3)',
              children: (
                <>
                  <Space style={{ display: 'flex' }} align="start">
                    <Form.Item name="identification" label="Identificación"><Input style={{ width: 150 }} /></Form.Item>
                    <Form.Item name="nationality" label="Nacionalidad"><Input style={{ width: 130 }} /></Form.Item>
                    <Form.Item name="birth_date" label="Fecha de nacimiento"><Input type="date" style={{ width: 150 }} /></Form.Item>
                  </Space>
                  <Space style={{ display: 'flex' }} align="start">
                    <Form.Item name="marital_status" label="Estado civil">
                      <Select allowClear style={{ width: 140 }} options={['Soltero/a', 'Casado/a', 'Unión libre', 'Divorciado/a', 'Viudo/a'].map(v => ({ value: v, label: v }))} />
                    </Form.Item>
                    <Form.Item name="contract_type" label="Tipo de contrato"><Input style={{ width: 150 }} /></Form.Item>
                    <Form.Item name="calendar_country" label="País calendario">
                      <Select allowClear style={{ width: 140 }} options={['Colombia', 'Argentina', 'Ecuador', 'Otro'].map(v => ({ value: v, label: v }))} />
                    </Form.Item>
                  </Space>
                  <Space style={{ display: 'flex' }} align="start">
                    <Form.Item name="education_level" label="Nivel de estudios"><Input style={{ width: 150 }} /></Form.Item>
                    <Form.Item name="specialty" label="Especialidad">
                      <Select allowClear style={{ width: 160 }} options={['Desarrollador', 'Funcional', 'Infraestructura', 'Otro'].map(v => ({ value: v, label: v }))} />
                    </Form.Item>
                    <Form.Item name="seniority" label="Seniority">
                      <Select allowClear style={{ width: 120 }} options={['Junior', 'Staff', 'Senior'].map(v => ({ value: v, label: v }))} />
                    </Form.Item>
                  </Space>
                  <Form.Item name="certifications" label="Certificaciones"><Input.TextArea rows={2} /></Form.Item>
                  <Space style={{ display: 'flex' }} align="start">
                    <Form.Item name="team" label="Equipo"><Input style={{ width: 180 }} /></Form.Item>
                    <Form.Item name="manager_id" label="Jefe directo">
                      <Select
                        allowClear
                        showSearch
                        optionFilterProp="label"
                        placeholder="Seleccionar jefe"
                        style={{ width: 220 }}
                        options={resources
                          .filter(res => res.active && res.id !== editingId)
                          .map(res => ({ value: res.id, label: res.full_name }))}
                      />
                    </Form.Item>
                  </Space>
                </>
              ),
            }]}
          />
          <Form.Item name="notes" label="Notas"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Compensación — ${compOpen?.full_name ?? ''}`}
        open={!!compOpen}
        onCancel={() => setCompOpen(null)}
        footer={canEditCompensation
          ? [
              <Button key="cancel" onClick={() => setCompOpen(null)}>Cerrar</Button>,
              <Button key="save" type="primary" onClick={() => compForm.submit()}>Guardar</Button>,
            ]
          : [<Button key="cancel" onClick={() => setCompOpen(null)}>Cerrar</Button>]}
      >
        <Form form={compForm} layout="vertical" onFinish={handleSaveCompensation} disabled={!canEditCompensation}>
          <Space style={{ display: 'flex' }} align="start">
            <Form.Item name="base_salary" label="Salario base"><InputNumber min={0} style={{ width: 150 }} /></Form.Item>
            <Form.Item name="total_salary" label="Salario total (con beneficios)"><InputNumber min={0} style={{ width: 180 }} /></Form.Item>
          </Space>
          <Space style={{ display: 'flex' }} align="start">
            <Form.Item name="overhead" label="Overhead / costos adicionales"><InputNumber min={0} style={{ width: 180 }} /></Form.Item>
            <Form.Item name="currency" label="Moneda" initialValue="USD">
              <Select style={{ width: 100 }} options={['USD', 'COP', 'ARS'].map(v => ({ value: v, label: v }))} />
            </Form.Item>
          </Space>
        </Form>
        <Divider style={{ margin: '8px 0' }} />
        <div>
          <strong>Costo hora calculado:</strong>{' '}
          {compensation?.hourly_cost != null
            ? `${compensation.hourly_cost.toLocaleString('en-US')} ${compensation.currency}/h`
            : '— (se calcula al guardar el salario total)'}
        </div>
      </Modal>

      {confirmDeactivate && (
        <ConfirmationModal open title="Desactivar recurso"
          description="¿Confirmas la desactivación de este recurso? No aparecerá en sugerencias de asignación."
          onConfirm={() => handleDeactivate(confirmDeactivate)} onCancel={() => setConfirmDeactivate(null)} />
      )}
    </div>
  )
}
