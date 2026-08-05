import { useCallback, useEffect, useState } from 'react'
import { Button, Input, Modal, Select, Space, Table, Tag, Typography, message } from 'antd'
import { FileExcelOutlined, SaveOutlined, FolderOpenOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { reportService, downloadBlob } from '../services/reportService'
import { clientService } from '../services/clientService'
import { projectService } from '../services/projectService'
import { resourceService } from '../services/resourceService'
import type { ReportRow, ReportFilters, ReportAggregateFunction, ReportAggregateResult, ReportSavedView, ReportViewConfig } from '../types/report'
import { formatDuration } from '../types/workSession'
import PriorityBadge from '../components/tickets/PriorityBadge'
import type { Priority } from '../types/ticket'
import type { ClientListItem } from '../types/client'
import type { ProjectListItem } from '../types/project'
import type { Resource } from '../types/resource'
import PageToolbar from '../components/common/PageToolbar'
import ColumnPicker, { type ColumnDef } from '../components/reports/ColumnPicker'

function formatSeconds(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '—'
  return formatDuration(Math.round(seconds / 60))
}

/** Definición completa de columnas del reporte (FR-008/FR-009) — clave estable usada por
 * ColumnPicker y por las Vistas Personalizadas (US6) para guardar orden/visibilidad. */
const ALL_COLUMNS: ColumnDef[] = [
  { key: 'ticket_number', title: 'Ticket' },
  { key: 'title', title: 'Título' },
  { key: 'status', title: 'Estado' },
  { key: 'priority', title: 'Prioridad' },
  { key: 'client_name', title: 'Cliente' },
  { key: 'project_name', title: 'Proyecto' },
  { key: 'assignee_name', title: 'Encargado' },
  { key: 'tool_name', title: 'Herramienta' },
  { key: 'process_name', title: 'Proceso' },
  { key: 'skills', title: 'Skills' },
  { key: 'time_to_first_contact_seconds', title: 'Primer contacto' },
  { key: 'execution_time_seconds', title: 'Ejecución/Resolución' },
  { key: 'total_logged_minutes', title: 'Tiempo registrado' },
  { key: 'created_at', title: 'Creado' },
]

/** Columnas sobre las que FR-011 permite sum/avg/count (mismo criterio que el backend,
 * report_aggregation_service.NUMERIC_COLUMNS). */
const AGGREGATABLE_COLUMNS: { column: string; label: string }[] = [
  { column: 'total_logged_minutes', label: 'Tiempo registrado' },
  { column: 'time_to_first_contact_seconds', label: 'Primer contacto' },
  { column: 'execution_time_seconds', label: 'Ejecución/Resolución' },
]

const AGGREGATE_FUNCTION_LABELS: Record<ReportAggregateFunction, string> = {
  sum: 'Suma', avg: 'Promedio', count: 'Conteo',
}

function formatAggregateValue(column: string, fn: ReportAggregateFunction, value: number): string {
  if (fn === 'count') return String(value)
  if (column === 'total_logged_minutes') return formatDuration(Math.round(value))
  return formatSeconds(value)
}

function buildColumn(key: string, title: string): ColumnsType<ReportRow>[number] {
  switch (key) {
    case 'ticket_number':
      return { title, dataIndex: key, render: (v: number) => `TK-${String(v).padStart(6, '0')}` }
    case 'title':
      return { title, dataIndex: key, ellipsis: true }
    case 'priority':
      return { title, dataIndex: key, render: (p: Priority) => <PriorityBadge priority={p} /> }
    case 'skills':
      return {
        title, dataIndex: key,
        render: (skills: string[]) => <Space size={4} wrap>{skills.map(s => <Tag key={s}>{s}</Tag>)}</Space>,
      }
    case 'time_to_first_contact_seconds':
    case 'execution_time_seconds':
      return { title, dataIndex: key, render: formatSeconds }
    case 'total_logged_minutes':
      return { title, dataIndex: key, render: (m: number) => formatDuration(m) }
    case 'created_at':
      return { title, dataIndex: key, render: (v: string) => new Date(v).toLocaleDateString('es-CO') }
    default:
      return { title, dataIndex: key }
  }
}

export default function ReportsPage() {
  const [clients, setClients] = useState<ClientListItem[]>([])
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [resources, setResources] = useState<Resource[]>([])

  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [clientId, setClientId] = useState<string | undefined>()
  const [projectId, setProjectId] = useState<string | undefined>()
  const [assigneeId, setAssigneeId] = useState<string | undefined>()

  const [rows, setRows] = useState<ReportRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [loading, setLoading] = useState(false)

  const [columnOrder, setColumnOrder] = useState<string[]>(ALL_COLUMNS.map(c => c.key))
  const [visibility, setVisibility] = useState<Record<string, boolean>>(
    Object.fromEntries(ALL_COLUMNS.map(c => [c.key, true])),
  )

  const [aggFunctions, setAggFunctions] = useState<Partial<Record<string, ReportAggregateFunction>>>({})
  const [aggregates, setAggregates] = useState<ReportAggregateResult>({})

  const [savedViews, setSavedViews] = useState<ReportSavedView[]>([])
  const [saveModalOpen, setSaveModalOpen] = useState(false)
  const [viewName, setViewName] = useState('')
  const [savingView, setSavingView] = useState(false)

  const loadSavedViews = useCallback(() => {
    reportService.listViews().then(setSavedViews).catch(() => message.error('No se pudieron cargar las Vistas Personalizadas'))
  }, [])
  useEffect(() => { loadSavedViews() }, [loadSavedViews])

  useEffect(() => {
    clientService.list({ page_size: 200 }).then(r => setClients(r.items)).catch(() => message.error('No se pudo cargar la lista de clientes'))
    resourceService.list({ page_size: 200 }).then(r => setResources(r.items)).catch(() => message.error('No se pudo cargar la lista de recursos'))
  }, [])

  // spec 038 US4 (FR-016/FR-017): el selector de Proyecto se acota al Cliente elegido — sin
  // Cliente, sigue mostrando todos los proyectos (los Reportes no exigen Cliente primero, a
  // diferencia del alta de Ticket/Tarea).
  useEffect(() => {
    projectService.list({ page_size: 200, client_id: clientId }).then(r => setProjects(r.items))
      .catch(() => message.error('No se pudo cargar la lista de proyectos'))
  }, [clientId, message])

  const filters: ReportFilters = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    client_id: clientId,
    project_id: projectId,
    assignee_id: assigneeId,
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const aggregateParams = Object.entries(aggFunctions)
        .filter((entry): entry is [string, ReportAggregateFunction] => !!entry[1])
        .map(([column, fn]) => `${column}:${fn}`)
      const res = await reportService.listTickets(filters, page, pageSize, aggregateParams)
      setRows(res.items)
      setTotal(res.total)
      setAggregates(res.aggregates ?? {})
    } catch {
      message.error('No se pudo cargar el reporte de tickets')
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateFrom, dateTo, clientId, projectId, assigneeId, page, pageSize, aggFunctions])

  useEffect(() => { load() }, [load])

  const visibleColumnKeys = columnOrder.filter(key => visibility[key] ?? true)
  const columns: ColumnsType<ReportRow> = visibleColumnKeys
    .map(key => buildColumn(key, ALL_COLUMNS.find(c => c.key === key)?.title ?? key))

  const [exporting, setExporting] = useState(false)
  const handleExport = async () => {
    setExporting(true)
    try {
      const blob = await reportService.exportTickets(filters, visibleColumnKeys)
      downloadBlob(blob, 'reporte_tickets.xlsx')
    } catch (err: unknown) {
      // responseType 'blob' hace que el body de error también llegue como Blob, no JSON directo
      const errorBlob = (err as { response?: { data?: Blob } }).response?.data
      let msg = 'No se pudo exportar el reporte'
      if (errorBlob instanceof Blob) {
        try {
          const parsed = JSON.parse(await errorBlob.text())
          if (parsed?.message) msg = parsed.message
        } catch { /* keep default message */ }
      }
      message.error(msg)
    } finally {
      setExporting(false)
    }
  }

  // ── Vistas Personalizadas (spec 034, US6): columnas+orden, filtros y agregaciones ──────
  const buildCurrentConfig = (): ReportViewConfig => ({
    columns: ALL_COLUMNS.map(c => ({ key: c.key, visible: visibility[c.key] ?? true })),
    column_order: columnOrder,
    filters,
    aggregations: Object.entries(aggFunctions)
      .filter((entry): entry is [string, ReportAggregateFunction] => !!entry[1])
      .map(([column, fn]) => ({ column: column as ReportViewConfig['aggregations'][number]['column'], function: fn })),
  })

  const applyConfig = (config: ReportViewConfig) => {
    setPage(1)
    setColumnOrder(config.column_order)
    setVisibility(Object.fromEntries(config.columns.map(c => [c.key, c.visible])))
    setDateFrom(config.filters.date_from ?? '')
    setDateTo(config.filters.date_to ?? '')
    setClientId(config.filters.client_id)
    setProjectId(config.filters.project_id)
    setAssigneeId(config.filters.assignee_id)
    setAggFunctions(Object.fromEntries(config.aggregations.map(a => [a.column, a.function])))
  }

  const handleSaveView = async () => {
    const name = viewName.trim()
    if (!name) return
    setSavingView(true)
    try {
      await reportService.saveView(name, buildCurrentConfig())
      message.success('Vista Personalizada guardada')
      setSaveModalOpen(false)
      setViewName('')
      loadSavedViews()
    } catch {
      message.error('No se pudo guardar la Vista Personalizada')
    } finally {
      setSavingView(false)
    }
  }

  const handleLoadView = (viewId: string) => {
    const view = savedViews.find(v => v.id === viewId)
    if (view) applyConfig(view.config)
  }

  return (
    <div>
      <Typography.Title level={4}>Reportes</Typography.Title>
      <PageToolbar
        filters={<>
          <Input type="date" value={dateFrom} max={dateTo || undefined}
            onChange={(e) => { setPage(1); setDateFrom(e.target.value) }} style={{ width: 150 }} />
          <Input type="date" value={dateTo} min={dateFrom || undefined}
            onChange={(e) => { setPage(1); setDateTo(e.target.value) }} style={{ width: 150 }} />
          <Select placeholder="Cliente" allowClear showSearch optionFilterProp="label" style={{ width: 180 }}
            value={clientId}
            // spec 038 US4 (FR-017): cambiar de Cliente limpia el Proyecto ya elegido.
            onChange={(v) => { setPage(1); setClientId(v); setProjectId(undefined) }}
            options={clients.map(c => ({ value: c.id, label: c.name }))} />
          <Select placeholder="Proyecto" allowClear showSearch optionFilterProp="label" style={{ width: 180 }}
            value={projectId}
            onChange={(v) => { setPage(1); setProjectId(v) }}
            options={projects.map(p => ({ value: p.id, label: p.name }))} />
          <Select placeholder="Encargado" allowClear showSearch optionFilterProp="label" style={{ width: 200 }}
            onChange={(v) => { setPage(1); setAssigneeId(v) }}
            options={resources.map(r => ({ value: r.id, label: r.full_name }))} />
        </>}
        action={
          <Space>
            <Select
              placeholder={<><FolderOpenOutlined /> Vistas Personalizadas</>}
              allowClear
              style={{ width: 220 }}
              onChange={(v) => v && handleLoadView(v)}
              options={savedViews.map(v => ({ value: v.id, label: v.name }))}
            />
            <Button icon={<SaveOutlined />} onClick={() => setSaveModalOpen(true)}>Guardar vista</Button>
            <Button icon={<FileExcelOutlined />} loading={exporting} onClick={handleExport}>
              Exportar a Excel
            </Button>
            <ColumnPicker
              columns={columnOrder.map(key => ALL_COLUMNS.find(c => c.key === key)!).filter(Boolean)}
              visibility={visibility}
              onReorder={setColumnOrder}
              onToggle={(key, visible) => setVisibility(v => ({ ...v, [key]: visible }))}
            />
          </Space>
        }
      />
      <Space style={{ marginBottom: 16 }} wrap>
        <Typography.Text type="secondary">Agregaciones:</Typography.Text>
        {AGGREGATABLE_COLUMNS.map(({ column, label }) => (
          <Select
            key={column}
            placeholder={label}
            allowClear
            style={{ width: 190 }}
            value={aggFunctions[column]}
            onChange={(fn) => setAggFunctions(v => ({ ...v, [column]: fn }))}
            options={(Object.keys(AGGREGATE_FUNCTION_LABELS) as ReportAggregateFunction[])
              .map(fn => ({ value: fn, label: `${label}: ${AGGREGATE_FUNCTION_LABELS[fn]}` }))}
          />
        ))}
      </Space>
      <Table
        rowKey="ticket_id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        scroll={{ x: 'max-content' }}
        pagination={{
          current: page, pageSize, total, showSizeChanger: true,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
        locale={{ emptyText: 'No hay tickets que cumplan los filtros aplicados.' }}
        summary={() => Object.keys(aggregates).length === 0 ? null : (
          <Table.Summary.Row>
            {columns.map((col, index) => {
              const key = (col as { dataIndex?: string }).dataIndex
              const columnAggregates = key ? aggregates[key] : undefined
              return (
                <Table.Summary.Cell key={key ?? index} index={index}>
                  {columnAggregates && (
                    <Typography.Text strong>
                      {Object.entries(columnAggregates)
                        .map(([fn, value]) => `${AGGREGATE_FUNCTION_LABELS[fn as ReportAggregateFunction]}: ${formatAggregateValue(key!, fn as ReportAggregateFunction, value!)}`)
                        .join(' · ')}
                    </Typography.Text>
                  )}
                </Table.Summary.Cell>
              )
            })}
          </Table.Summary.Row>
        )}
      />

      <Modal
        title="Guardar Vista Personalizada"
        open={saveModalOpen}
        onCancel={() => setSaveModalOpen(false)}
        onOk={handleSaveView}
        okButtonProps={{ loading: savingView, disabled: !viewName.trim() }}
        okText="Guardar"
      >
        <Typography.Paragraph type="secondary">
          Guarda las columnas, filtros y agregaciones actuales. Si ya existe una vista con este
          nombre, se sobrescribe.
        </Typography.Paragraph>
        <Input
          placeholder="Nombre de la vista"
          value={viewName}
          onChange={(e) => setViewName(e.target.value)}
          onPressEnter={handleSaveView}
        />
      </Modal>
    </div>
  )
}
