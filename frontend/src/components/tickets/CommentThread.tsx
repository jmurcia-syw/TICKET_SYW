import { Empty, Space, Timeline, Typography } from 'antd'
import { PaperClipOutlined, RobotOutlined } from '@ant-design/icons'
import type { CommentType, TicketComment } from '../../types/ticket'
import { ticketService } from '../../services/ticketService'
import { vivid } from '../../theme'
import RichTextViewer from './RichTextViewer'

const { Text, Link } = Typography

interface CommentThreadProps {
  ticketId: string
  comments: TicketComment[]
}

// Colores por tipo de comentario — refuerza visualmente la matriz de estados (US3).
const TYPE_CHIP: Record<CommentType, { bg: string; text: string }> = {
  asignado: vivid.blue,
  pre_analisis: vivid.cyan,
  confirmacion_atencion: vivid.gold,
  solicitud_informacion: vivid.red,
  termina_analisis: vivid.purple,
  solicitud_cierre: vivid.green,
  respuesta_usuario: vivid.magenta,
  descripcion_solucion: vivid.green,
  comentario_interno: vivid.gray,
  cancelacion: vivid.red,
}

/** Hilo cronológico de comentarios tipificados con adjuntos descargables (US3). */
export default function CommentThread({ ticketId, comments }: CommentThreadProps) {
  if (comments.length === 0) {
    return <Empty description="Sin comentarios todavía" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }
  return (
    <Timeline
      items={comments.map(c => {
        const chip = TYPE_CHIP[c.comment_type] ?? vivid.gray
        return {
          color: c.visibility === 'external' ? chip.text : '#BFBFBF',
          children: (
            <Space direction="vertical" size={2} style={{ width: '100%' }}>
              <Space wrap size={6}>
                <span style={{
                  display: 'inline-block', padding: '1px 9px', borderRadius: 999,
                  fontSize: 11, fontWeight: 700, background: chip.bg, color: chip.text,
                }}>
                  {c.comment_type_label}
                </span>
                {c.is_automatic && (
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: 3, padding: '1px 8px', borderRadius: 999,
                    fontSize: 11, background: '#F5F5F5', color: '#595959',
                  }}>
                    <RobotOutlined /> automático
                  </span>
                )}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {new Date(c.created_at).toLocaleString('es-CO')}
                  {' · '}{c.visibility === 'external' ? 'visible al cliente' : 'interno'}
                </Text>
              </Space>
              <RichTextViewer html={c.body} />
              {c.attachments.map(a => (
                <Link key={a.id} onClick={() => ticketService.downloadAttachment(ticketId, a.id, a.filename)}>
                  <PaperClipOutlined /> {a.filename} ({(a.size_bytes / 1024).toFixed(0)} KB)
                </Link>
              ))}
            </Space>
          ),
        }
      })}
    />
  )
}
