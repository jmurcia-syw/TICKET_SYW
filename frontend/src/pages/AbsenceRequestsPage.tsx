import { useCallback, useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Select, Space, Table, Tabs, Tag, Typography, Upload, message } from 'antd'
import { PlusOutlined, UploadOutlined, DownloadOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile } from 'antd'
import { calendarService } from '../services/calendarService'
import { catalogService } from '../services/catalogService'
import type { AbsenceRequest, AbsenceDecisionStatus } from '../types/calendar'
import type { CatalogItem } from '../types/catalog'
import { useAuthStore } from '../store/authStore'
import PageToolbar from '../components/common/PageToolbar'

// Fase 5 (spec 020, Historia 2): solicitud y aprobación en cadena de ausencias — Jefe directo +
// RRHH, cada uno decide de forma independiente (FR-008 a FR-012a).

const STATUS_COLORS: Record<AbsenceDecisionStatus, string> = {
  pending: 'gold',
  approved: 'green',
  rejected: 'red',
}
const STATUS_LABELS: Record<AbsenceDecisionStatus, string> = {
  pending: 'Pendiente',
  approved: 'Aprobado',
  rejected: 'Rechazado',
}

function apiError(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? fallback
}

interface CreateFormValues {
  absence_type_id: string
  start_date: string
  end_date: string
  notes?: string
}

export default function AbsenceRequestsPage() {
  const { hasPermission } = useAuthStore()
  const isHr = hasPermission('absence_requests', 'view_all')

  const [own, setOwn] = useState<AbsenceRequest[]>([])
  const [managerQueue, setManagerQueue] = useState<AbsenceRequest[]>([])
  const [hrQueue, setHrQueue] = useState<AbsenceRequest[]>([])
  const [showManagerTab, setShowManagerTab] = useState(false)
  const [types, setTypes] = useState<CatalogItem[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [files, setFiles] = useState<UploadFile[]>([])
  const [decidingId, setDecidingId] = useState<string | null>(null)
  const [form] = Form.useForm<CreateFormValues>()

  const loadOwn = useCallback(async () => {
    setLoading(true)
    try {
      setOwn(await calendarService.listAbsenceRequests('own'))
    } catch {
      message.error('No se pudieron cargar tus solicitudes')
    } finally {
      setLoading(false)
    }
  }, [])

  // 403 esperado si el usuario no es Jefe de nadie (contracts/calendar-disponibilidad.md) — la
  // pestaña simplemente no se muestra, sin mostrar error.
  const loadManager = useCallback(async () => {
    try {
      setManagerQueue(await calendarService.listAbsenceRequests('manager', { skipErrorNotify: true }))
      setShowManagerTab(true)
    } catch {
      setShowManagerTab(false)
    }
  }, [])

  const loadHr = useCallback(async () => {
    if (!isHr) return
    try {
      setHrQueue(await calendarService.listAbsenceRequests('hr'))
    } catch {
      message.error('No se pudo cargar la cola de RRHH')
    }
  }, [isHr])

  useEffect(() => { loadOwn() }, [loadOwn])
  useEffect(() => { loadManager() }, [loadManager])
  useEffect(() => { loadHr() }, [loadHr])
  useEffect(() => {
    catalogService.list('absence-types').then(r => setTypes(r.items))
      .catch(() => message.error('No se pudieron cargar los tipos de ausencia'))
  }, [])

  const handleCreate = async (values: CreateFormValues) => {
    try {
      const rawFiles = files.map(f => f.originFileObj).filter((f): f is NonNullable<typeof f> => !!f)
      await calendarService.createAbsenceRequest({
        absence_type_id: values.absence_type_id,
        start_date: values.start_date,
        end_date: values.end_date,
        notes: values.notes || null,
      }, rawFiles)
      message.success('Solicitud enviada')
      setCreateOpen(false)
      form.resetFields()
      setFiles([])
      loadOwn()
    } catch (err: unknown) {
      message.error(apiError(err, 'Error al crear la solicitud'))
    }
  }

  const decide = async (id: string, role: 'manager' | 'hr', decision: 'approved' | 'rejected') => {
    setDecidingId(id)
    try {
      await calendarService.decideAbsenceRequest(id, role, decision)
      message.success(decision === 'approved' ? 'Solicitud aprobada' : 'Solicitud rechazada')
      if (role === 'manager') loadManager()
      else loadHr()
    } catch (err: unknown) {
      message.error(apiError(err, 'No se pudo registrar la decisión'))
    } finally {
      setDecidingId(null)
    }
  }

  const statusColumns: ColumnsType<AbsenceRequest> = [
    { title: 'Tipo', dataIndex: 'absence_type', render: (t: AbsenceRequest['absence_type']) => t.name },
    { title: 'Desde', dataIndex: 'start_date' },
    { title: 'Hasta', dataIndex: 'end_date' },
    { title: 'Jefe directo', dataIndex: 'manager_status', render: (s: AbsenceDecisionStatus) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s]}</Tag> },
    { title: 'RRHH', dataIndex: 'hr_status', render: (s: AbsenceDecisionStatus) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s]}</Tag> },
    { title: 'Estado general', dataIndex: 'overall_status', render: (s: AbsenceDecisionStatus) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s]}</Tag> },
    {
      title: 'Adjuntos', dataIndex: 'attachments',
      render: (attachments: AbsenceRequest['attachments'], record: AbsenceRequest) => attachments.length === 0
        ? <Typography.Text type="secondary">Sin adjuntos</Typography.Text>
        : <Space direction="vertical" size={0}>
            {attachments.map(a => (
              <a key={a.id} href={calendarService.downloadAbsenceAttachmentUrl(record.id, a.id)} target="_blank" rel="noreferrer">
                <DownloadOutlined /> {a.filename}
              </a>
            ))}
          </Space>,
    },
  ]

  const decisionColumns = (role: 'manager' | 'hr'): ColumnsType<AbsenceRequest> => [
    { title: 'Solicitante', dataIndex: 'resource', render: (r: AbsenceRequest['resource']) => r.full_name },
    ...statusColumns,
    {
      title: 'Acciones',
      render: (_: unknown, record: AbsenceRequest) => {
        const pending = role === 'manager' ? record.manager_status === 'pending' : record.hr_status === 'pending'
        if (!pending) return <Typography.Text type="secondary">Ya decidido</Typography.Text>
        return (
          <Space>
            <Button size="small" type="primary" icon={<CheckOutlined />} loading={decidingId === record.id}
              onClick={() => decide(record.id, role, 'approved')}>Aprobar</Button>
            <Button size="small" danger icon={<CloseOutlined />} loading={decidingId === record.id}
              onClick={() => decide(record.id, role, 'rejected')}>Rechazar</Button>
          </Space>
        )
      },
    },
  ]

  const tabs = [
    {
      key: 'own',
      label: 'Mis solicitudes',
      children: <Table rowKey="id" columns={statusColumns} dataSource={own} loading={loading}
        locale={{ emptyText: 'Todavía no has enviado solicitudes.' }} />,
    },
    ...(showManagerTab ? [{
      key: 'manager',
      label: 'Aprobaciones — Jefe directo',
      children: <Table rowKey="id" columns={decisionColumns('manager')} dataSource={managerQueue}
        locale={{ emptyText: 'No hay solicitudes de tu equipo.' }} />,
    }] : []),
    ...(isHr ? [{
      key: 'hr',
      label: 'Aprobaciones — RRHH',
      children: <Table rowKey="id" columns={decisionColumns('hr')} dataSource={hrQueue}
        locale={{ emptyText: 'No hay solicitudes pendientes.' }} />,
    }] : []),
  ]

  return (
    <div>
      <PageToolbar
        filters={null}
        action={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setFiles([]); setCreateOpen(true) }}>
            Nueva solicitud
          </Button>
        }
      />

      <Tabs items={tabs} />

      <Modal title="Nueva solicitud de ausencia" open={createOpen} onCancel={() => setCreateOpen(false)}
        onOk={() => form.submit()} okText="Enviar">
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="absence_type_id" label="Tipo" rules={[{ required: true, message: 'El tipo es requerido' }]}>
            <Select options={types.map(t => ({ value: t.id, label: t.name }))} />
          </Form.Item>
          <Form.Item name="start_date" label="Desde" rules={[{ required: true, message: 'La fecha de inicio es requerida' }]}>
            <Input type="date" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="end_date" label="Hasta" rules={[{ required: true, message: 'La fecha de fin es requerida' }]}>
            <Input type="date" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="Notas">
            <Input.TextArea rows={3} placeholder="Comentario opcional" />
          </Form.Item>
          <Form.Item label="Adjuntos (ej. certificado de incapacidad)">
            <Upload multiple beforeUpload={() => false} fileList={files} onChange={({ fileList }) => setFiles(fileList)}>
              <Button icon={<UploadOutlined />}>Adjuntar (máx 10 MB c/u)</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
