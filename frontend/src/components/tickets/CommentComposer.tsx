import { useState } from 'react'
import { Button, Input, Modal, Select, Space, Upload, message } from 'antd'
import { SendOutlined, UploadOutlined, ExperimentOutlined, CheckOutlined,
         CloseOutlined, StopOutlined, LockOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd'
import type { CommentType, TicketDetail } from '../../types/ticket'
import type { CatalogItem } from '../../types/catalog'
import { ticketService } from '../../services/ticketService'
import { useAuthStore } from '../../store/authStore'

// Tipos de comentario manuales disponibles por acción FSM válida
const COMMENT_OPTIONS: Array<{ type: CommentType; label: string; action: string | null }> = [
  { type: 'confirmacion_atencion', label: 'Confirmación de atención (→ En Análisis)', action: 'confirmacion_atencion' },
  { type: 'termina_analisis', label: 'Termina análisis (→ En Ejecución)', action: 'termina_analisis' },
  { type: 'solicitud_informacion', label: 'Solicitud de información (→ Pendiente de Usuario)', action: 'solicitud_informacion' },
  { type: 'solicitud_cierre', label: 'Solicitud de cierre (→ Resuelto)', action: 'solicitud_cierre' },
  { type: 'respuesta_usuario', label: 'Respuesta de usuario (→ En Ejecución)', action: 'respuesta_usuario' },
  { type: 'comentario_interno', label: 'Comentario interno (sin cambio de estado)', action: null },
]

interface CommentComposerProps {
  ticket: TicketDetail
  resolutionTypes: CatalogItem[]
  onUpdated: () => void
}

/** Composer de comentarios tipificados + botones de acciones de estado (US3). */
export default function CommentComposer({ ticket, resolutionTypes, onUpdated }: CommentComposerProps) {
  const { hasPermission } = useAuthStore()
  const [commentType, setCommentType] = useState<CommentType>('comentario_interno')
  const [body, setBody] = useState('')
  const [files, setFiles] = useState<UploadFile[]>([])
  const [sending, setSending] = useState(false)
  const [closeOpen, setCloseOpen] = useState(false)
  const [closeType, setCloseType] = useState<string>()
  const [closeBody, setCloseBody] = useState('')
  const [cancelOpen, setCancelOpen] = useState(false)
  const [cancelBody, setCancelBody] = useState('')

  const isFinal = ticket.status === 'cerrado' || ticket.status === 'cancelado'
  const validActions = new Set(ticket.valid_actions)
  const options = COMMENT_OPTIONS.filter(o => o.action === null || validActions.has(o.action))

  const apiError = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? fallback

  const send = async () => {
    if (!body.trim()) {
      message.warning('El comentario no puede estar vacío')
      return
    }
    setSending(true)
    try {
      const rawFiles = files.map(f => f.originFileObj).filter((f): f is NonNullable<typeof f> => !!f)
      await ticketService.addComment(ticket.id, commentType, body, rawFiles)
      setBody(''); setFiles([]); setCommentType('comentario_interno')
      message.success('Comentario registrado')
      onUpdated()
    } catch (err: unknown) {
      message.error(apiError(err, 'Error al registrar el comentario'))
    } finally {
      setSending(false)
    }
  }

  const runAction = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn()
      message.success(ok)
      onUpdated()
    } catch (err: unknown) {
      message.error(apiError(err, 'La acción no pudo completarse'))
    }
  }

  if (isFinal) {
    return <em>El ticket está en estado final ({ticket.status_label}); no admite más acciones.</em>
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Space wrap>
        {validActions.has('enter_testing') && (
          <Button icon={<ExperimentOutlined />}
            onClick={() => runAction(() => ticketService.toggleTesting(ticket.id, 'enter'), 'Ticket en pruebas')}>
            Pasar a pruebas
          </Button>
        )}
        {validActions.has('exit_testing') && (
          <Button icon={<ExperimentOutlined />}
            onClick={() => runAction(() => ticketService.toggleTesting(ticket.id, 'exit'), 'Ticket en ejecución')}>
            Volver a ejecución
          </Button>
        )}
        {ticket.status === 'resuelto' && (
          <>
            <Button icon={<CheckOutlined />} type="primary" ghost
              onClick={() => runAction(() => ticketService.recordResolution(ticket.id, true), 'Resolución aceptada — puedes cerrar el ticket')}>
              Usuario acepta resolución
            </Button>
            <Button icon={<CloseOutlined />} danger ghost
              onClick={() => runAction(() => ticketService.recordResolution(ticket.id, false, 'El usuario rechazó la resolución'), 'Ticket devuelto a En Ejecución')}>
              Usuario rechaza
            </Button>
            <Button icon={<LockOutlined />} type="primary" disabled={!ticket.close_eligible}
              title={ticket.close_eligible ? '' : 'Requiere aceptación del usuario o 3+ días sin respuesta'}
              onClick={() => setCloseOpen(true)}>
              Cerrar ticket
            </Button>
          </>
        )}
        {hasPermission('tickets', 'cancel') && (
          <Button icon={<StopOutlined />} danger onClick={() => setCancelOpen(true)}>Cancelar ticket</Button>
        )}
      </Space>

      <Select value={commentType} onChange={setCommentType} style={{ width: '100%' }}
        options={options.map(o => ({ value: o.type, label: o.label }))} />
      <Input.TextArea rows={3} value={body} onChange={e => setBody(e.target.value)}
        placeholder="Escribe el comentario..." />
      <Space>
        <Upload multiple beforeUpload={() => false} fileList={files}
          onChange={({ fileList }) => setFiles(fileList)}>
          <Button icon={<UploadOutlined />}>Adjuntar (máx 10 MB c/u)</Button>
        </Upload>
        <Button type="primary" icon={<SendOutlined />} loading={sending} onClick={send}>
          Registrar comentario
        </Button>
      </Space>

      <Modal title="Cerrar ticket" open={closeOpen} onCancel={() => setCloseOpen(false)}
        okText="Cerrar ticket" onOk={async () => {
          if (!closeType || !closeBody.trim()) {
            message.warning('Tipo de resolución y descripción de la solución son requeridos')
            return
          }
          await runAction(() => ticketService.close(ticket.id, closeType, closeBody), 'Ticket cerrado')
          setCloseOpen(false)
        }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Select placeholder="Tipo de resolución" style={{ width: '100%' }} value={closeType}
            onChange={setCloseType}
            options={resolutionTypes.map(t => ({ value: t.id, label: t.name }))} />
          <Input.TextArea rows={3} placeholder="Descripción de la solución (obligatoria)"
            value={closeBody} onChange={e => setCloseBody(e.target.value)} />
        </Space>
      </Modal>

      <Modal title="Cancelar ticket" open={cancelOpen} onCancel={() => setCancelOpen(false)}
        okText="Cancelar ticket" okButtonProps={{ danger: true }} onOk={async () => {
          if (!cancelBody.trim()) {
            message.warning('El motivo de cancelación es requerido')
            return
          }
          await runAction(() => ticketService.cancel(ticket.id, cancelBody), 'Ticket cancelado')
          setCancelOpen(false)
        }}>
        <Input.TextArea rows={3} placeholder="Motivo de la cancelación (obligatorio)"
          value={cancelBody} onChange={e => setCancelBody(e.target.value)} />
      </Modal>
    </Space>
  )
}
