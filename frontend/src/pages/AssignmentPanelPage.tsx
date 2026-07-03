import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Col, Row, Select, Table, Tag, Tooltip } from 'antd'
import { ReloadOutlined, UserSwitchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import type { PanelData, PanelRow, TicketStatus } from '../types/ticket'
import { STATUS_LABELS, PRIORITY_LABELS } from '../types/ticket'
import AssignModal from '../components/tickets/AssignModal'
import PageToolbar from '../components/common/PageToolbar'

const NON_FINAL: TicketStatus[] = [
  'nuevo', 'pre_analisis', 'contacto', 'en_analisis', 'en_ejecucion',
  'en_pruebas', 'pendiente_usuario', 'resuelto',
]

export default function AssignmentPanelPage() {
  const [data, setData] = useState<PanelData | null>(null)
  const [statuses, setStatuses] = useState<TicketStatus[]>([])
  const [loading, setLoading] = useState(false)
  const [assigningId, setAssigningId] = useState<string | null>(null)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await ticketService.panel(statuses.length ? statuses : undefined))
    } finally {
      setLoading(false)
    }
  }, [statuses])

  useEffect(() => { load() }, [load])

  const visibleStatuses = statuses.length ? statuses : NON_FINAL

  const matrixColumns: ColumnsType<PanelRow> = [
    { title: 'Resolutor', dataIndex: ['resource', 'full_name'], fixed: 'left', width: 180 },
    ...visibleStatuses.map(s => ({
      title: STATUS_LABELS[s], key: s, width: 110, align: 'center' as const,
      render: (_: unknown, row: PanelRow) => {
        const count = row.counts[s] ?? 0
        return count > 0
          ? <Button type="link" size="small"
              onClick={() => navigate(`/tickets?assignee=${row.resource.id}&status=${s}`)}>{count}</Button>
          : <span style={{ color: '#ccc' }}>—</span>
      },
    })),
    { title: 'Total', dataIndex: 'total', width: 80, align: 'center',
      render: (v: number) => <strong>{v}</strong> },
  ]

  return (
    <div>
      <PageToolbar
        filters={
          <Select mode="multiple" placeholder="Filtrar estados" allowClear style={{ minWidth: 260 }}
            value={statuses} onChange={setStatuses} maxTagCount={3}
            options={NON_FINAL.map(s => ({ value: s, label: STATUS_LABELS[s] }))} />
        }
        action={<Button icon={<ReloadOutlined />} onClick={load}>Actualizar</Button>}
      />

      <Row gutter={16}>
        <Col xs={24} xl={14}>
          <Card title="Carga por resolutor y estado" size="small">
            <Table rowKey={r => r.resource.id} columns={matrixColumns} dataSource={data?.matrix ?? []}
              loading={loading} pagination={false} scroll={{ x: true }} size="small"
              locale={{ emptyText: 'Sin tickets asignados' }} />
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card title={`Pendientes de triage (NUEVO) — ${data?.unassigned_new.length ?? 0}`} size="small">
            <Table
              rowKey="id"
              size="small"
              loading={loading}
              dataSource={data?.unassigned_new ?? []}
              pagination={{ pageSize: 8 }}
              locale={{ emptyText: 'No hay tickets nuevos sin asignar 🎉' }}
              columns={[
                { title: 'Número', dataIndex: 'ticket_number', width: 100,
                  render: (v: string, t) => <a onClick={() => navigate(`/tickets/${t.id}`)}>{v}</a> },
                { title: 'Título', dataIndex: 'title', ellipsis: true },
                { title: 'Prioridad', dataIndex: 'priority', width: 90,
                  render: (p: keyof typeof PRIORITY_LABELS) => <Tag>{PRIORITY_LABELS[p]}</Tag> },
                { title: 'Cliente', dataIndex: ['client', 'name'], width: 130, ellipsis: true },
                { title: '', key: 'assign', width: 60,
                  render: (_: unknown, t) => (
                    <Tooltip title="Asignar">
                      <Button size="small" type="primary" icon={<UserSwitchOutlined />}
                        onClick={() => setAssigningId(t.id)} />
                    </Tooltip>
                  ) },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <AssignModal ticketId={assigningId} onClose={() => setAssigningId(null)} onAssigned={load} />
    </div>
  )
}
