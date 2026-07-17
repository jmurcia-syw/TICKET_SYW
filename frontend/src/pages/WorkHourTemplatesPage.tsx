import { useEffect, useState } from 'react'
import { Button, Checkbox, Form, Input, Modal, Select, Space, Table, Tag, Tooltip, Typography, message } from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { calendarService } from '../services/calendarService'
import type { PersonalizedResource, WorkHourTemplate, WorkScheduleSlot } from '../types/calendar'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'

// Spec 022 (Historia 1): RRHH administra Franjas Horarias globales por país (herencia
// automática, FR-001 a FR-003) y ve quién quedó en modo Personalizado (FR-005). Mismo patrón
// de edición de horario semanal que WorkScheduleDrawer.tsx (spec 020) — inputs `time` planos,
// sin dependencia de calendario/hora nueva (Principio V).

const COUNTRY_OPTIONS = ['Colombia', 'Argentina', 'Ecuador', 'Otro']
const WEEKDAY_LABELS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
const DEFAULT_START = '08:00'
const DEFAULT_END = '17:00'

interface DayRow {
  enabled: boolean
  start_time: string
  end_time: string
}

function rowsFromSlots(slots: WorkScheduleSlot[] = []): DayRow[] {
  return WEEKDAY_LABELS.map((_, weekday) => {
    const slot = slots.find(s => s.weekday === weekday)
    return slot
      ? { enabled: true, start_time: slot.start_time, end_time: slot.end_time }
      : { enabled: false, start_time: DEFAULT_START, end_time: DEFAULT_END }
  })
}

export default function WorkHourTemplatesPage() {
  const [country, setCountry] = useState<string>(COUNTRY_OPTIONS[0])
  const [templates, setTemplates] = useState<WorkHourTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [personalized, setPersonalized] = useState<PersonalizedResource[]>([])
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [rows, setRows] = useState<DayRow[]>(rowsFromSlots())
  const [form] = Form.useForm<{ name: string; timezone: string }>()

  const loadTemplates = (c: string) => {
    setLoading(true)
    calendarService.listWorkHourTemplates(c)
      .then(setTemplates)
      .catch(() => message.error('No se pudieron cargar las Franjas Horarias'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadTemplates(country) }, [country])

  useEffect(() => {
    calendarService.listPersonalizedResources().then(setPersonalized)
      .catch(() => message.error('No se pudo cargar el listado de recursos Personalizados'))
  }, [])

  const updateRow = (weekday: number, patch: Partial<DayRow>) => {
    setRows(prev => prev.map((r, i) => (i === weekday ? { ...r, ...patch } : r)))
  }

  const openCreate = () => {
    setEditingId(null)
    form.setFieldsValue({ name: '', timezone: '' })
    setRows(rowsFromSlots())
    setFormOpen(true)
  }

  const openEdit = (template: WorkHourTemplate) => {
    setEditingId(template.id)
    form.setFieldsValue({ name: template.name, timezone: template.timezone })
    setRows(rowsFromSlots(template.slots))
    setFormOpen(true)
  }

  const handleSubmit = async (values: { name: string; timezone: string }) => {
    const slots: WorkScheduleSlot[] = rows
      .map((r, weekday) => ({ weekday, start_time: r.start_time, end_time: r.end_time, enabled: r.enabled }))
      .filter(r => r.enabled)
      .map(({ weekday, start_time, end_time }) => ({ weekday, start_time, end_time }))
    const invalid = slots.find(s => s.start_time >= s.end_time)
    if (invalid) {
      message.warning(`La hora de fin debe ser mayor a la de inicio (${WEEKDAY_LABELS[invalid.weekday]})`)
      return
    }
    try {
      if (editingId) {
        await calendarService.updateWorkHourTemplate(editingId, { name: values.name, timezone: values.timezone, slots })
        message.success('Franja Horaria actualizada')
      } else {
        await calendarService.createWorkHourTemplate({ country, name: values.name, timezone: values.timezone, slots })
        message.success('Franja Horaria creada')
      }
      setFormOpen(false)
      loadTemplates(country)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar'
      message.error(msg)
    }
  }

  const toggleActive = async (template: WorkHourTemplate) => {
    try {
      await calendarService.updateWorkHourTemplate(template.id, { active: !template.active })
      loadTemplates(country)
    } catch {
      message.error('No se pudo cambiar el estado')
    }
  }

  const columns: ColumnsType<WorkHourTemplate> = [
    { title: 'Nombre', dataIndex: 'name' },
    { title: 'Huso horario', dataIndex: 'timezone' },
    {
      title: 'Horario', key: 'slots',
      render: (_: unknown, t: WorkHourTemplate) => t.slots.length === 0
        ? <Typography.Text type="secondary">Sin franjas</Typography.Text>
        : t.slots.map(s => (
            <Tag key={s.weekday}>{WEEKDAY_LABELS[s.weekday].slice(0, 3)} {s.start_time}-{s.end_time}</Tag>
          )),
    },
    { title: 'Estado', dataIndex: 'active', render: (v: boolean) => <StatusTag active={v} /> },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, t: WorkHourTemplate) => (
        <Space>
          <Tooltip title="Editar"><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(t)} /></Tooltip>
          <Button size="small" onClick={() => toggleActive(t)}>{t.active ? 'Desactivar' : 'Activar'}</Button>
        </Space>
      ),
    },
  ]

  const personalizedColumns: ColumnsType<PersonalizedResource> = [
    { title: 'Recurso', dataIndex: 'full_name' },
    { title: 'País', dataIndex: 'calendar_country', render: (v: string | null) => v ?? '—' },
  ]

  return (
    <div>
      <Typography.Title level={4}>Franjas Horarias</Typography.Title>
      <Typography.Paragraph type="secondary">
        Plantillas globales de horario laboral por país. Todo recurso en modo "Heredado" sigue
        automáticamente los cambios de su Franja asignada.
      </Typography.Paragraph>

      <PageToolbar
        filters={
          <Select value={country} onChange={setCountry} style={{ width: 200 }}
            options={COUNTRY_OPTIONS.map(c => ({ value: c, label: c }))} />
        }
        action={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nueva Franja Horaria</Button>}
      />

      <Table rowKey="id" columns={columns} dataSource={templates} loading={loading} pagination={false} />

      <Typography.Title level={5} style={{ marginTop: 32 }}>Recursos en modo Personalizado</Typography.Title>
      <Typography.Paragraph type="secondary">
        Estos recursos editaron su propio horario y quedaron excluidos de las actualizaciones
        masivas de la Franja Horaria de su país.
      </Typography.Paragraph>
      <Table rowKey="resource_id" columns={personalizedColumns} dataSource={personalized} pagination={false}
        locale={{ emptyText: 'Ningún recurso tiene horario Personalizado' }} />

      <Modal title={editingId ? 'Editar Franja Horaria' : 'Nueva Franja Horaria'} open={formOpen}
        onCancel={() => setFormOpen(false)} onOk={() => form.submit()} okText="Guardar" width={640}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="name" label="Nombre" rules={[{ required: true, message: 'El nombre es requerido' }]}>
              <Input placeholder={`${country} — Estándar`} style={{ width: 260 }} />
            </Form.Item>
            <Form.Item name="timezone" label="Zona horaria (IANA)" rules={[{ required: true, message: 'La zona horaria es requerida' }]}>
              <Input placeholder="America/Bogota" style={{ width: 220 }} />
            </Form.Item>
          </Space>
          <Space direction="vertical" style={{ width: '100%' }} size={8}>
            {WEEKDAY_LABELS.map((label, weekday) => {
              const row = rows[weekday]
              return (
                <Space key={weekday} style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Checkbox checked={row.enabled} onChange={e => updateRow(weekday, { enabled: e.target.checked })} style={{ width: 100 }}>
                    {label}
                  </Checkbox>
                  <Input type="time" style={{ width: 110 }} disabled={!row.enabled}
                    value={row.start_time} onChange={e => updateRow(weekday, { start_time: e.target.value })} />
                  <Typography.Text type="secondary">a</Typography.Text>
                  <Input type="time" style={{ width: 110 }} disabled={!row.enabled}
                    value={row.end_time} onChange={e => updateRow(weekday, { end_time: e.target.value })} />
                </Space>
              )
            })}
          </Space>
        </Form>
      </Modal>
    </div>
  )
}
