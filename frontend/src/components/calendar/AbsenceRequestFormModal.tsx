import { useEffect, useState } from 'react'
import { Button, Checkbox, Form, Input, Modal, Select, Space, Upload, message } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd'
import { calendarService } from '../../services/calendarService'
import { catalogService } from '../../services/catalogService'
import type { CatalogItem } from '../../types/catalog'

// Spec 022 (Historia 3, FR-017): formulario de solicitud de ausencia/permiso, con permisos
// parciales por horas opcionales (ej. cita médica de 2h) — mismo flujo de doble aprobación ya
// existente (spec 020), sin pasos adicionales para quien la solicita. Componente compartido
// entre AbsenceRequestsPage.tsx (RRHH > Permisos) y CalendarPage.tsx (RRHH > Calendario) para
// no duplicar el formulario.

interface FormValues {
  absence_type_id: string
  start_date: string
  end_date: string
  notes?: string
  partial: boolean
  start_time?: string
  end_time?: string
}

function apiError(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? fallback
}

interface AbsenceRequestFormModalProps {
  open: boolean
  onClose: () => void
  onCreated: () => void
}

export default function AbsenceRequestFormModal({ open, onClose, onCreated }: AbsenceRequestFormModalProps) {
  const [types, setTypes] = useState<CatalogItem[]>([])
  const [files, setFiles] = useState<UploadFile[]>([])
  const [form] = Form.useForm<FormValues>()
  const partial = Form.useWatch('partial', form)

  useEffect(() => {
    if (!open) return
    form.resetFields()
    setFiles([])
    catalogService.list('absence-types').then(r => setTypes(r.items))
      .catch(() => message.error('No se pudieron cargar los tipos de ausencia'))
  }, [open, form])

  const handleSubmit = async (values: FormValues) => {
    try {
      const rawFiles = files.map(f => f.originFileObj).filter((f): f is NonNullable<typeof f> => !!f)
      await calendarService.createAbsenceRequest({
        absence_type_id: values.absence_type_id,
        start_date: values.start_date,
        end_date: values.partial ? values.start_date : values.end_date,
        notes: values.notes || null,
        start_time: values.partial ? values.start_time : null,
        end_time: values.partial ? values.end_time : null,
      }, rawFiles)
      message.success('Solicitud enviada')
      onClose()
      onCreated()
    } catch (err: unknown) {
      message.error(apiError(err, 'Error al crear la solicitud'))
    }
  }

  return (
    <Modal title="Nueva solicitud de ausencia" open={open} onCancel={onClose}
      onOk={() => form.submit()} okText="Enviar" destroyOnHidden>
      <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ partial: false }}>
        <Form.Item name="absence_type_id" label="Tipo" rules={[{ required: true, message: 'El tipo es requerido' }]}>
          <Select options={types.map(t => ({ value: t.id, label: t.name }))} />
        </Form.Item>
        <Form.Item name="partial" valuePropName="checked">
          <Checkbox>Permiso parcial por horas (ej. cita médica de 2h, media jornada)</Checkbox>
        </Form.Item>
        <Form.Item name="start_date" label={partial ? 'Fecha' : 'Desde'}
          rules={[{ required: true, message: 'La fecha es requerida' }]}>
          <Input type="date" style={{ width: '100%' }} />
        </Form.Item>
        {partial ? (
          <Space style={{ display: 'flex' }}>
            <Form.Item name="start_time" label="Desde (hora)" rules={[{ required: true, message: 'Requerido' }]}>
              <Input type="time" style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="end_time" label="Hasta (hora)" rules={[{ required: true, message: 'Requerido' }]}>
              <Input type="time" style={{ width: 140 }} />
            </Form.Item>
          </Space>
        ) : (
          <Form.Item name="end_date" label="Hasta" rules={[{ required: true, message: 'La fecha de fin es requerida' }]}>
            <Input type="date" style={{ width: '100%' }} />
          </Form.Item>
        )}
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
  )
}
