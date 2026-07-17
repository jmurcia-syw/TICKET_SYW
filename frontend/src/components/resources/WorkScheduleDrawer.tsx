import { useEffect, useState } from 'react'
import { Alert, Button, Checkbox, Drawer, Input, Space, Typography, message } from 'antd'
import { calendarService } from '../../services/calendarService'
import type { WorkScheduleSlot } from '../../types/calendar'

// Fase 5 (spec 020, Historia 4): horario laboral semanal por recurso (FR-006). `weekday`:
// 0=lunes ... 6=domingo, igual que el backend (availability_service.py).
const WEEKDAY_LABELS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
const DEFAULT_START = '08:00'
const DEFAULT_END = '17:00'

interface DayRow {
  enabled: boolean
  start_time: string
  end_time: string
}

function emptyRows(): DayRow[] {
  return Array.from({ length: 7 }, (_, weekday) => ({
    enabled: weekday < 5, // lunes-viernes marcados por defecto al editar desde cero
    start_time: DEFAULT_START,
    end_time: DEFAULT_END,
  }))
}

interface WorkScheduleDrawerProps {
  resourceId: string | null
  resourceName?: string
  onClose: () => void
}

/** Editor de horario laboral semanal por recurso (Fase 5, spec 020, Historia 4). */
export default function WorkScheduleDrawer({ resourceId, resourceName, onClose }: WorkScheduleDrawerProps) {
  const [rows, setRows] = useState<DayRow[]>(emptyRows())
  const [isDefault, setIsDefault] = useState(true)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!resourceId) return
    setLoading(true)
    calendarService.getWorkSchedule(resourceId).then(data => {
      setIsDefault(data.is_default)
      const next = emptyRows().map(r => ({ ...r, enabled: false }))
      data.items.forEach(item => {
        next[item.weekday] = { enabled: true, start_time: item.start_time, end_time: item.end_time }
      })
      setRows(next)
    }).catch(() => message.error('No se pudo cargar el horario laboral')).finally(() => setLoading(false))
  }, [resourceId])

  const updateRow = (weekday: number, patch: Partial<DayRow>) => {
    setRows(prev => prev.map((r, i) => (i === weekday ? { ...r, ...patch } : r)))
  }

  const handleSave = async () => {
    if (!resourceId) return
    const slots: WorkScheduleSlot[] = rows
      .map((r, weekday) => ({ weekday, start_time: r.start_time, end_time: r.end_time, enabled: r.enabled }))
      .filter(r => r.enabled)
      .map(({ weekday, start_time, end_time }) => ({ weekday, start_time, end_time }))
    const invalid = slots.find(s => s.start_time >= s.end_time)
    if (invalid) {
      message.warning(`La hora de fin debe ser mayor a la de inicio (${WEEKDAY_LABELS[invalid.weekday]})`)
      return
    }
    setSaving(true)
    try {
      const updated = await calendarService.setWorkSchedule(resourceId, slots)
      setIsDefault(updated.is_default)
      message.success('Horario laboral guardado')
      onClose()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar el horario'
      message.error(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Drawer
      title={resourceName ? `Horario laboral — ${resourceName}` : 'Horario laboral'}
      open={!!resourceId}
      onClose={onClose}
      width={420}
      footer={
        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
          <Button onClick={onClose}>Cancelar</Button>
          <Button type="primary" loading={saving} onClick={handleSave}>Guardar</Button>
        </Space>
      }
    >
      {isDefault && (
        <Alert
          type="info" showIcon style={{ marginBottom: 16 }}
          message="Usando el horario por defecto (lunes a viernes, 08:00-17:00). Ajusta las franjas para personalizarlo."
        />
      )}
      <Space direction="vertical" style={{ width: '100%' }} size={12}>
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
      {loading && <Typography.Text type="secondary">Cargando…</Typography.Text>}
    </Drawer>
  )
}
