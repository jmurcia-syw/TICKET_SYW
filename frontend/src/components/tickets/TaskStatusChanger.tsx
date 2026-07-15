import { useState } from 'react'
import { Button, Modal, Select, Space, message } from 'antd'
import { SwapOutlined } from '@ant-design/icons'
import type { TicketDetail, TicketStatus } from '../../types/ticket'
import { STATUS_LABELS } from '../../types/ticket'
import { ticketService } from '../../services/ticketService'
import RichTextEditor, { isRichTextEmpty } from './RichTextEditor'

interface TaskStatusChangerProps {
  ticket: TicketDetail
  onUpdated: () => void
}

/** Cambio de estado libre de una Tarea/Subtarea (spec 009, FR-003/FR-004): cualquiera de los
 * 10 estados compartidos con Ticket, sin restricción de secuencia, con comentario obligatorio.
 * Reemplaza `TaskActions.tsx` (spec 008, ciclo de vida propio de 4 estados). */
export default function TaskStatusChanger({ ticket, onUpdated }: TaskStatusChangerProps) {
  const [open, setOpen] = useState(false)
  const [target, setTarget] = useState<TicketStatus | undefined>()
  const [comment, setComment] = useState('')
  const [commentKey, setCommentKey] = useState(0)
  const [loading, setLoading] = useState(false)

  const options = (ticket.valid_actions as TicketStatus[]).map(s => ({ value: s, label: STATUS_LABELS[s] }))

  const submit = async () => {
    if (!target) return
    if (isRichTextEmpty(comment)) {
      message.warning('El comentario es obligatorio para cambiar el estado')
      return
    }
    setLoading(true)
    try {
      await ticketService.changeStatus(ticket.id, target, comment)
      message.success(`Estado cambiado a "${STATUS_LABELS[target]}"`)
      setOpen(false)
      setComment(''); setCommentKey(k => k + 1)
      setTarget(undefined)
      onUpdated()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })
        .response?.data?.message ?? 'No se pudo cambiar el estado'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Space wrap>
        <Select
          placeholder="Cambiar estado a..." style={{ width: 220 }}
          value={target} options={options}
          onChange={v => { setTarget(v); setOpen(true) }}
        />
        <Button icon={<SwapOutlined />} onClick={() => target && setOpen(true)} disabled={!target}>
          Cambiar estado
        </Button>
      </Space>

      <Modal
        title={target ? `Cambiar estado a "${STATUS_LABELS[target]}"` : 'Cambiar estado'}
        open={open}
        onCancel={() => setOpen(false)}
        confirmLoading={loading}
        onOk={submit}
        okText="Confirmar"
      >
        <RichTextEditor
          key={commentKey} value={comment} onChange={setComment}
          placeholder="Comentario obligatorio que documenta el cambio de estado..."
        />
      </Modal>
    </>
  )
}
