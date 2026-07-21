import { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Descriptions, Form, Input, Select, Space, Spin, Table, Tabs, Tag, Typography, message } from 'antd'
import { ClockCircleOutlined, EditOutlined, SaveOutlined, CloseOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import { resourceService } from '../services/resourceService'
import { ticketService } from '../services/ticketService'
import type { Resource, ResourceFormData } from '../types/resource'
import type { TicketListItem } from '../types/ticket'
import { useAuthStore } from '../store/authStore'
import { avatarColor, initials, palette, roleColor } from '../theme'
import StatusTag from '../components/common/StatusTag'
import TicketStatusTag from '../components/tickets/TicketStatusTag'
import PriorityBadge from '../components/tickets/PriorityBadge'
import WorkScheduleDrawer from '../components/resources/WorkScheduleDrawer'

type ProfileEditableFields = Pick<ResourceFormData,
  'full_name' | 'notes' | 'identification' | 'nationality' | 'birth_date' | 'marital_status' |
  'contract_type' | 'calendar_country' | 'education_level' | 'specialty' | 'seniority' |
  'certifications' | 'team'>

export default function MyProfilePage() {
  const navigate = useNavigate()
  const { role } = useAuthStore()
  const [resource, setResource] = useState<Resource | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState(false)
  const [form] = Form.useForm<ProfileEditableFields>()

  const [tickets, setTickets] = useState<TicketListItem[]>([])
  const [ticketsLoading, setTicketsLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await resourceService.me()
      setResource(data)
      setNotFound(false)
    } catch (err: unknown) {
      if ((err as { response?: { status?: number } }).response?.status === 404) {
        setNotFound(true)
      } else {
        message.error('No se pudo cargar tu perfil')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!resource) return
    setTicketsLoading(true)
    ticketService.list({ assignee_id: resource.id, page_size: 50, sort: '-created_at' })
      .then(r => setTickets(r.items))
      .catch(() => message.error('No se pudieron cargar tus tickets asignados'))
      .finally(() => setTicketsLoading(false))
  }, [resource])

  const startEdit = () => {
    if (!resource) return
    form.setFieldsValue(resource)
    setEditing(true)
  }

  const saveEdit = async (values: ProfileEditableFields) => {
    if (!resource) return
    try {
      const updated = await resourceService.update(resource.id, values)
      setResource(updated)
      setEditing(false)
      message.success('Perfil actualizado')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al actualizar'
      message.error(msg)
    }
  }

  const ticketColumns: ColumnsType<TicketListItem> = [
    { title: 'Número', dataIndex: 'ticket_number', width: 110,
      render: (v: string, t) => <a onClick={() => navigate(`/tickets/${t.id}`)}>{v}</a> },
    { title: 'Título', dataIndex: 'title', ellipsis: true },
    { title: 'Estado', dataIndex: 'status', width: 150,
      render: (s: TicketListItem['status']) => <TicketStatusTag status={s} /> },
    { title: 'Prioridad', dataIndex: 'priority', width: 90,
      render: (p: TicketListItem['priority']) => <PriorityBadge priority={p} /> },
    { title: 'Cliente', dataIndex: ['client', 'name'], width: 160, ellipsis: true },
  ]

  if (loading) return <Spin style={{ display: 'block', margin: '80px auto' }} />

  if (notFound) {
    return (
      <Alert
        type="info"
        showIcon
        message="Sin perfil de recurso vinculado"
        description="Tu cuenta todavía no tiene un perfil de recurso asociado (nombre, skills, historial de tickets). Contacta a un Admin o Coordinador para que lo vincule."
      />
    )
  }

  if (!resource) return null

  const color = avatarColor(resource.id)

  return (
    <div>
      {/* Header horizontal: avatar + datos de cuenta */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 20, padding: '20px 24px',
        background: '#fff', borderRadius: 12, border: `1px solid ${palette.slate200}`, marginBottom: 20,
      }}>
        <div style={{
          width: 72, height: 72, borderRadius: '50%', display: 'flex', alignItems: 'center',
          justifyContent: 'center', background: color.bg, color: color.text, fontWeight: 700, fontSize: 24,
          flexShrink: 0,
        }}>
          {initials(resource.full_name)}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <Typography.Title level={3} style={{ margin: 0 }}>{resource.full_name}</Typography.Title>
            <Tag color={roleColor(role?.name)}>{role?.name ?? '—'}</Tag>
            <StatusTag active={resource.active} />
          </div>
          <Space size="large" style={{ marginTop: 4, color: palette.slate500 }}>
            <span>{resource.email}</span>
            {resource.team && <span>Equipo: {resource.team}</span>}
            {resource.seniority && <span>{resource.seniority}</span>}
          </Space>
        </div>
      </div>

      <Tabs
        items={[
          {
            key: 'contacto',
            label: 'Datos de contacto',
            children: editing ? (
              <Form form={form} layout="vertical" onFinish={saveEdit}>
                <Space style={{ display: 'flex' }} align="start" wrap>
                  <Form.Item name="full_name" label="Nombre completo" rules={[{ required: true, message: 'El nombre es requerido' }]}>
                    <Input style={{ width: 220 }} />
                  </Form.Item>
                  <Form.Item name="identification" label="Identificación"><Input style={{ width: 150 }} /></Form.Item>
                  <Form.Item name="nationality" label="Nacionalidad"><Input style={{ width: 130 }} /></Form.Item>
                  <Form.Item name="birth_date" label="Fecha de nacimiento"><Input type="date" style={{ width: 150 }} /></Form.Item>
                </Space>
                <Space style={{ display: 'flex' }} align="start" wrap>
                  <Form.Item name="marital_status" label="Estado civil">
                    <Select allowClear style={{ width: 140 }} options={['Soltero/a', 'Casado/a', 'Unión libre', 'Divorciado/a', 'Viudo/a'].map(v => ({ value: v, label: v }))} />
                  </Form.Item>
                  <Form.Item name="contract_type" label="Tipo de contrato"><Input style={{ width: 150 }} /></Form.Item>
                  <Form.Item name="calendar_country" label="País calendario">
                    <Select allowClear style={{ width: 140 }} options={['Colombia', 'Argentina', 'Ecuador', 'Otro'].map(v => ({ value: v, label: v }))} />
                  </Form.Item>
                </Space>
                <Space style={{ display: 'flex' }} align="start" wrap>
                  <Form.Item name="education_level" label="Nivel de estudios"><Input style={{ width: 150 }} /></Form.Item>
                  <Form.Item name="specialty" label="Especialidad">
                    <Select allowClear style={{ width: 160 }} options={['Desarrollador', 'Funcional', 'Infraestructura', 'Otro'].map(v => ({ value: v, label: v }))} />
                  </Form.Item>
                  <Form.Item name="seniority" label="Seniority">
                    <Select allowClear style={{ width: 120 }} options={['Junior', 'Staff', 'Senior'].map(v => ({ value: v, label: v }))} />
                  </Form.Item>
                  <Form.Item name="team" label="Equipo"><Input style={{ width: 180 }} /></Form.Item>
                </Space>
                <Form.Item name="certifications" label="Certificaciones"><Input.TextArea rows={2} /></Form.Item>
                <Form.Item name="notes" label="Notas"><Input.TextArea rows={2} /></Form.Item>
                <Space>
                  <Button type="primary" icon={<SaveOutlined />} htmlType="submit">Guardar cambios</Button>
                  <Button icon={<CloseOutlined />} onClick={() => setEditing(false)}>Cancelar</Button>
                </Space>
              </Form>
            ) : (
              <>
                <Descriptions column={2} size="small" bordered style={{ maxWidth: 760 }}>
                  <Descriptions.Item label="Identificación">{resource.identification ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Nacionalidad">{resource.nationality ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Fecha de nacimiento">{resource.birth_date ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Estado civil">{resource.marital_status ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Tipo de contrato">{resource.contract_type ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="País calendario">{resource.calendar_country ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Nivel de estudios">{resource.education_level ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Especialidad">{resource.specialty ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Seniority">{resource.seniority ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Equipo">{resource.team ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Certificaciones" span={2}>{resource.certifications ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Notas" span={2}>{resource.notes ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Horario laboral" span={2}>
                    <Tag color={resource.schedule_mode === 'personalizado' ? 'gold' : 'blue'}>
                      {resource.schedule_mode === 'personalizado' ? 'Personalizado' : 'Heredado (Franja Horaria)'}
                    </Tag>
                  </Descriptions.Item>
                </Descriptions>
                <Space style={{ marginTop: 12 }}>
                  <Button icon={<EditOutlined />} onClick={startEdit}>Editar mis datos</Button>
                  <Button icon={<ClockCircleOutlined />} onClick={() => setEditingSchedule(true)}>
                    Editar mi horario laboral
                  </Button>
                </Space>
              </>
            ),
          },
          {
            key: 'skills',
            label: 'Skills',
            children: resource.skills.length > 0
              ? resource.skills.map(s => (
                  <Tag key={s.id} style={{ fontFamily: 'ui-monospace, SFMono-Regular, monospace', marginBottom: 6 }}>
                    {s.code} — {s.label}
                  </Tag>
                ))
              : <em style={{ color: palette.slate400 }}>Sin skills asignados. Un Admin o Coordinador puede asignártelos.</em>,
          },
          {
            key: 'tickets',
            label: `Tickets asignados${tickets.length ? ` (${tickets.length})` : ''}`,
            children: <Table rowKey="id" size="small" columns={ticketColumns} dataSource={tickets}
              loading={ticketsLoading} pagination={{ pageSize: 10 }}
              locale={{ emptyText: 'No tienes tickets asignados actualmente' }} />,
          },
        ]}
      />

      <WorkScheduleDrawer
        resourceId={editingSchedule ? resource.id : null}
        resourceName={resource.full_name}
        onClose={() => { setEditingSchedule(false); load() }}
      />
    </div>
  )
}
