import { useCallback, useEffect, useState } from 'react'
import { Button, Space, Table, Tabs, Tag, Typography, message } from 'antd'
import { PlusOutlined, DownloadOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { calendarService } from '../services/calendarService'
import type { AbsenceRequest, AbsenceDecisionStatus } from '../types/calendar'
import { useAuthStore } from '../store/authStore'
import PageToolbar from '../components/common/PageToolbar'
import AbsenceRequestFormModal from '../components/calendar/AbsenceRequestFormModal'

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

export default function AbsenceRequestsPage() {
  const { hasPermission } = useAuthStore()
  const isHr = hasPermission('absence_requests', 'view_all')

  const [own, setOwn] = useState<AbsenceRequest[]>([])
  const [managerQueue, setManagerQueue] = useState<AbsenceRequest[]>([])
  const [hrQueue, setHrQueue] = useState<AbsenceRequest[]>([])
  const [showManagerTab, setShowManagerTab] = useState(false)
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [decidingId, setDecidingId] = useState<string | null>(null)

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
    {
      title: 'Horas', key: 'hours',
      render: (_: unknown, r: AbsenceRequest) => r.start_time && r.end_time
        ? `${r.start_time}-${r.end_time}` : <Typography.Text type="secondary">Día completo</Typography.Text>,
    },
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
      children: <Table rowKey="id" columns={statusColumns} dataSource={own} loading={loading} scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'Todavía no has enviado solicitudes.' }} />,
    },
    ...(showManagerTab ? [{
      key: 'manager',
      label: 'Aprobaciones — Jefe directo',
      children: <Table rowKey="id" columns={decisionColumns('manager')} dataSource={managerQueue} scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'No hay solicitudes de tu equipo.' }} />,
    }] : []),
    ...(isHr ? [{
      key: 'hr',
      label: 'Aprobaciones — RRHH',
      children: <Table rowKey="id" columns={decisionColumns('hr')} dataSource={hrQueue} scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'No hay solicitudes pendientes.' }} />,
    }] : []),
  ]

  return (
    <div>
      <PageToolbar
        filters={null}
        action={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            Nueva solicitud
          </Button>
        }
      />

      <Tabs items={tabs} />

      <AbsenceRequestFormModal open={createOpen} onClose={() => setCreateOpen(false)} onCreated={loadOwn} />
    </div>
  )
}
