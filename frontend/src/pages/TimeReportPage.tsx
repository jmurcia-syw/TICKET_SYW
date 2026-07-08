import { useCallback, useEffect, useState } from 'react'
import { Input, Select, Space, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { BarChartOutlined } from '@ant-design/icons'
import { workSessionService } from '../services/workSessionService'
import { resourceService } from '../services/resourceService'
import { useAuthStore } from '../store/authStore'
import type { DailySummaryDay, DailySummaryResponse } from '../types/workSession'
import { formatDuration } from '../types/workSession'
import type { Resource } from '../types/resource'
import PageToolbar from '../components/common/PageToolbar'
import StatCard from '../components/common/StatCard'
import { palette, vivid } from '../theme'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function isoDaysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

export default function TimeReportPage() {
  const { hasPermission } = useAuthStore()
  const canViewAll = hasPermission('work_sessions', 'view_all')

  const [resources, setResources] = useState<Resource[]>([])
  const [resourceId, setResourceId] = useState<string | undefined>()
  const [dateFrom, setDateFrom] = useState(isoDaysAgo(6))
  const [dateTo, setDateTo] = useState(todayIso())
  const [summary, setSummary] = useState<DailySummaryResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (canViewAll) {
      resourceService.list({ active: true, page_size: 100 }).then(r => {
        setResources(r.items)
        setResourceId(prev => prev ?? r.items[0]?.id)
      }).catch(() => message.error('No se pudo cargar la lista de recursos'))
    }
  }, [canViewAll])

  const load = useCallback(async () => {
    if (canViewAll && !resourceId) return
    setLoading(true)
    try {
      const data = await workSessionService.getSummary({
        resource_id: canViewAll ? resourceId : undefined, date_from: dateFrom, date_to: dateTo,
      })
      setSummary(data)
    } catch {
      message.error('No se pudo cargar el reporte de tiempos')
    } finally {
      setLoading(false)
    }
  }, [resourceId, dateFrom, dateTo, canViewAll])

  useEffect(() => { load() }, [load])

  const columns: ColumnsType<DailySummaryDay> = [
    { title: 'Fecha', dataIndex: 'work_date', key: 'work_date' },
    {
      title: 'Total', dataIndex: 'total_minutes', key: 'total_minutes',
      render: (minutes: number) => formatDuration(minutes),
    },
    {
      title: 'Estado', key: 'status',
      render: (_, day) => {
        const chip = day.sin_registro ? vivid.gold : vivid.green
        return (
          <span
            style={{
              display: 'inline-block', padding: '2px 10px', borderRadius: 999,
              fontSize: 12, fontWeight: 600, background: chip.bg, color: chip.text,
              whiteSpace: 'nowrap',
            }}
          >
            {day.sin_registro ? 'Sin registro' : 'Registrado'}
          </span>
        )
      },
    },
  ]

  return (
    <div>
      <Space align="center" style={{ marginBottom: 16 }}>
        <BarChartOutlined style={{ color: palette.brandOrange600, fontSize: 18 }} />
        <Typography.Title level={3} style={{ margin: 0 }}>Reporte de Tiempos</Typography.Title>
      </Space>
      <PageToolbar
        filters={
          <>
            {canViewAll && (
              <Select
                style={{ width: 240 }}
                value={resourceId}
                placeholder="Recurso"
                options={resources.map(r => ({ value: r.id, label: r.full_name }))}
                onChange={setResourceId}
              />
            )}
            <Input type="date" value={dateFrom} max={dateTo}
                  onChange={e => setDateFrom(e.target.value)} />
            <Input type="date" value={dateTo} max={todayIso()}
                  onChange={e => setDateTo(e.target.value)} />
          </>
        }
        action={
          <StatCard label="Total del período" value={summary ? formatDuration(summary.total_minutes) : '—'}
            icon={<BarChartOutlined />} color="purple" />
        }
      />
      <Table
        rowKey="work_date"
        loading={loading}
        columns={columns}
        dataSource={summary?.days ?? []}
        pagination={false}
        locale={{ emptyText: 'Sin datos para el rango seleccionado.' }}
      />
    </div>
  )
}
