import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Col, Row, Select, Table, Tooltip } from 'antd'
import { ReloadOutlined, UserSwitchOutlined, ApartmentOutlined, InboxOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import { ticketService } from '../services/ticketService'
import type { PanelData, PanelRow, TicketStatus, Priority } from '../types/ticket'
import { STATUS_LABELS, PRIORITY_LABELS } from '../types/ticket'
import AssignModal from '../components/tickets/AssignModal'
import PriorityBadge from '../components/tickets/PriorityBadge'
import PageToolbar from '../components/common/PageToolbar'
import { clientColumnFilter, clientTextColumnFilter } from '../components/common/columnFilters'
import { avatarColor, initials, palette, vivid } from '../theme'

const NON_FINAL: TicketStatus[] = [
  'nuevo', 'pre_analisis', 'contacto', 'en_analisis', 'en_ejecucion',
  'en_pruebas', 'pendiente_usuario', 'resuelto',
]

type UnassignedTicket = PanelData['unassigned_new'][number]

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
    {
      title: 'Resolutor', dataIndex: ['resource', 'full_name'], fixed: 'left', width: 190,
      ...clientTextColumnFilter<PanelRow>('Buscar resolutor...', r => r.resource.full_name),
      render: (_: unknown, row: PanelRow) => {
        const color = avatarColor(row.resource.id)
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 26, height: 26, borderRadius: '50%', display: 'flex', alignItems: 'center',
              justifyContent: 'center', background: color.bg, color: color.text, fontWeight: 700, fontSize: 11,
            }}>
              {initials(row.resource.full_name)}
            </div>
            <span>{row.resource.full_name}</span>
          </div>
        )
      },
    },
    ...visibleStatuses.map(s => ({
      title: STATUS_LABELS[s], key: s, width: 110, align: 'center' as const,
      render: (_: unknown, row: PanelRow) => {
        const count = row.counts[s] ?? 0
        return count > 0
          ? <Button type="link" size="small" style={{ fontWeight: 700, color: vivid.blue.text }}
              onClick={() => navigate(`/tickets?assignee=${row.resource.id}&status=${s}`)}>{count}</Button>
          : <span style={{ color: palette.slate300 }}>—</span>
      },
    })),
    { title: 'Total', dataIndex: 'total', width: 80, align: 'center',
      render: (v: number) => (
        <span style={{
          display: 'inline-block', minWidth: 26, padding: '2px 8px', borderRadius: 999,
          fontWeight: 700, background: vivid.blue.bg, color: vivid.blue.text,
        }}>{v}</span>
      ) },
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
          <Card
            size="small"
            title={<span><ApartmentOutlined style={{ color: vivid.blue.text, marginRight: 8 }} />Carga por resolutor y estado</span>}
          >
            <Table rowKey={r => r.resource.id} columns={matrixColumns} dataSource={data?.matrix ?? []}
              loading={loading} pagination={false} scroll={{ x: true }} size="small"
              locale={{ emptyText: 'Sin tickets asignados' }} />
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card
            size="small"
            title={
              <span>
                <InboxOutlined style={{ color: vivid.gold.text, marginRight: 8 }} />
                Pendientes de triage (NUEVO)
                <span style={{
                  marginLeft: 8, padding: '1px 8px', borderRadius: 999, fontSize: 12, fontWeight: 700,
                  background: vivid.gold.bg, color: vivid.gold.text,
                }}>{data?.unassigned_new.length ?? 0}</span>
              </span>
            }
          >
            <Table
              rowKey="id"
              size="small"
              loading={loading}
              dataSource={data?.unassigned_new ?? []}
              pagination={{ pageSize: 8 }}
              locale={{ emptyText: 'No hay tickets nuevos sin asignar 🎉' }}
              columns={([
                { title: 'Número', dataIndex: 'ticket_number', width: 100,
                  render: (v: string, t) => <a onClick={() => navigate(`/tickets/${t.id}`)}>{v}</a> },
                {
                  title: 'Título', dataIndex: 'title', ellipsis: true,
                  ...clientTextColumnFilter<UnassignedTicket>('Buscar título...', r => r.title),
                },
                {
                  title: 'Prioridad', dataIndex: 'priority', width: 90,
                  render: (p: Priority) => <PriorityBadge priority={p} />,
                  ...clientColumnFilter<UnassignedTicket>(
                    Object.entries(PRIORITY_LABELS).map(([value, text]) => ({ text, value })),
                    (value, record) => record.priority === value,
                  ),
                },
                {
                  title: 'Cliente', dataIndex: ['client', 'name'], width: 130, ellipsis: true,
                  ...clientTextColumnFilter<UnassignedTicket>(
                    'Buscar cliente...', r => r.client?.name ?? ''),
                },
                { title: '', key: 'assign', width: 60,
                  render: (_: unknown, t) => (
                    <Tooltip title="Asignar">
                      <Button size="small" type="primary" icon={<UserSwitchOutlined />}
                        onClick={() => setAssigningId(t.id)} />
                    </Tooltip>
                  ) },
              ] satisfies ColumnsType<UnassignedTicket>)}
            />
          </Card>
        </Col>
      </Row>

      <AssignModal ticketId={assigningId} onClose={() => setAssigningId(null)} onAssigned={load} />
    </div>
  )
}
