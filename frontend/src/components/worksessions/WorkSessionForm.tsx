import { useEffect } from 'react'
import { Form, Input, InputNumber, Modal, Select, message } from 'antd'
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

interface FormValues {
  ticket_id: string
  work_date: string
  hours: number
  minutes: number
  note?: string
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export default function WorkSessionForm({ open, onClose, onSaved, tickets, editing }: WorkSessionFormProps) {
  const [form] = Form.useForm<FormValues>()

  useEffect(() => {
    if (!open) return
    if (editing) {
      form.setFieldsValue({
        ticket_id: editing.ticket_id,
        work_date: editing.work_date,
        hours: Math.floor(editing.duration_minutes / 60),
        minutes: editing.duration_minutes % 60,
        note: editing.note ?? undefined,
      })
    } else {
      form.resetFields()
      form.setFieldsValue({ work_date: todayIso(), hours: 0, minutes: 0 })
    }
  }, [open, editing, form])

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const duration_minutes = (values.hours || 0) * 60 + (values.minutes || 0)
    if (duration_minutes <= 0) {
      message.warning('Ingresá al menos algunos minutos trabajados')
      return
    }
    try {
      if (editing) {
        await workSessionService.update(editing.id, { duration_minutes, note: values.note })
        message.success('Registro actualizado')
      } else {
        await workSessionService.create({
          ticket_id: values.ticket_id, work_date: values.work_date,
          duration_minutes, note: values.note,
        })
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
      destroyOnClose
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
          <Input.Group compact>
            <Form.Item name="hours" noStyle rules={[{ required: true }]}>
              <InputNumber min={0} max={24} addonAfter="h" style={{ width: '50%' }} />
            </Form.Item>
            <Form.Item name="minutes" noStyle rules={[{ required: true }]}>
              <InputNumber min={0} max={59} addonAfter="m" style={{ width: '50%' }} />
            </Form.Item>
          </Input.Group>
        </Form.Item>
        <Form.Item name="note" label="Nota (opcional)">
          <Input.TextArea rows={2} maxLength={500} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
