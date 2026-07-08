import { useEffect, useState } from 'react'
import { Form, Input, InputNumber, Modal, Segmented, Select, Space, message } from 'antd'
import type { TicketListItem } from '../../types/ticket'
import type { WorkSessionListItem } from '../../types/workSession'
import { workSessionService } from '../../services/workSessionService'

interface WorkSessionFormProps {
  open: boolean
  onClose: () => void
  onSaved: () => void
  tickets: TicketListItem[]
  editing?: WorkSessionListItem | null
}

type DurationMode = 'range' | 'manual'

interface FormValues {
  ticket_id: string
  work_date: string
  start_time?: string
  end_time?: string
  hours: number
  minutes: number
  note?: string
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function timeOf(iso: string | null): string | undefined {
  return iso ? iso.slice(11, 16) : undefined
}

/** Combina fecha (YYYY-MM-DD) + hora (HH:mm) en un ISO-8601 con la zona horaria del navegador. */
function toIsoDateTime(workDate: string, time: string): string {
  const offset = -new Date().getTimezoneOffset()
  const sign = offset >= 0 ? '+' : '-'
  const abs = Math.abs(offset)
  const tz = `${sign}${String(Math.floor(abs / 60)).padStart(2, '0')}:${String(abs % 60).padStart(2, '0')}`
  return `${workDate}T${time}:00${tz}`
}

export default function WorkSessionForm({ open, onClose, onSaved, tickets, editing }: WorkSessionFormProps) {
  const [form] = Form.useForm<FormValues>()
  const [mode, setMode] = useState<DurationMode>('range')

  useEffect(() => {
    if (!open) return
    if (editing) {
      const hasRange = !!editing.started_at && !!editing.ended_at
      setMode(hasRange ? 'range' : 'manual')
      form.setFieldsValue({
        ticket_id: editing.ticket_id,
        work_date: editing.work_date,
        start_time: timeOf(editing.started_at),
        end_time: timeOf(editing.ended_at),
        hours: Math.floor(editing.duration_minutes / 60),
        minutes: editing.duration_minutes % 60,
        note: editing.note ?? undefined,
      })
    } else {
      setMode('range')
      form.resetFields()
      form.setFieldsValue({ work_date: todayIso(), hours: 0, minutes: 0 })
    }
  }, [open, editing, form])

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload: {
      ticket_id: string; work_date: string; note?: string
      duration_minutes?: number; started_at?: string; ended_at?: string
    } = { ticket_id: values.ticket_id, work_date: values.work_date, note: values.note }

    if (mode === 'range') {
      if (!values.start_time || !values.end_time) {
        message.warning('Ingresá hora de inicio y de finalización, o cambiá a duración manual')
        return
      }
      payload.started_at = toIsoDateTime(values.work_date, values.start_time)
      payload.ended_at = toIsoDateTime(values.work_date, values.end_time)
    } else {
      const duration_minutes = (values.hours || 0) * 60 + (values.minutes || 0)
      if (duration_minutes <= 0) {
        message.warning('Ingresá al menos algunos minutos trabajados')
        return
      }
      payload.duration_minutes = duration_minutes
    }

    try {
      if (editing) {
        await workSessionService.update(editing.id, payload)
        message.success('Registro actualizado')
      } else {
        await workSessionService.create(payload as Parameters<typeof workSessionService.create>[0])
        message.success('Tiempo registrado')
      }
      onSaved()
      onClose()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message
        ?? 'Error al guardar el registro'
      message.error(msg)
    }
  }

  return (
    <Modal
      title={editing ? 'Editar registro de tiempo' : 'Nuevo registro de tiempo'}
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      okText={editing ? 'Guardar' : 'Registrar'}
      cancelText="Cancelar"
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item name="ticket_id" label="Ticket" rules={[{ required: true, message: 'Seleccioná un ticket' }]}>
          <Select
            disabled={!!editing}
            showSearch
            optionFilterProp="label"
            placeholder="Ticket asignado"
            options={tickets.map(t => ({ value: t.id, label: `${t.ticket_number} — ${t.title}` }))}
          />
        </Form.Item>
        <Form.Item name="work_date" label="Fecha" rules={[{ required: true, message: 'La fecha es requerida' }]}>
          <Input type="date" disabled={!!editing} max={todayIso()} />
        </Form.Item>

        <Form.Item label="Tiempo trabajado" required>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Segmented
              value={mode}
              onChange={v => setMode(v as DurationMode)}
              options={[
                { label: 'Hora de inicio/fin', value: 'range' },
                { label: 'Duración manual', value: 'manual' },
              ]}
            />
            {mode === 'range' ? (
              <Space.Compact block>
                <Form.Item name="start_time" noStyle>
                  <Input type="time" placeholder="Inicio" />
                </Form.Item>
                <Form.Item name="end_time" noStyle>
                  <Input type="time" placeholder="Fin" />
                </Form.Item>
              </Space.Compact>
            ) : (
              <Space.Compact block>
                <Form.Item name="hours" noStyle>
                  <InputNumber min={0} max={24} addonAfter="h" style={{ width: '50%' }} />
                </Form.Item>
                <Form.Item name="minutes" noStyle>
                  <InputNumber min={0} max={59} addonAfter="m" style={{ width: '50%' }} />
                </Form.Item>
              </Space.Compact>
            )}
          </Space>
        </Form.Item>

        <Form.Item name="note" label="Nota (opcional)">
          <Input.TextArea rows={2} maxLength={500} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
