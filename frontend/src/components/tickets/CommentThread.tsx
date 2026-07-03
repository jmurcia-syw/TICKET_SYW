import { Empty, Space, Tag, Timeline, Typography } from 'antd'
import { PaperClipOutlined, RobotOutlined } from '@ant-design/icons'
import type { TicketComment } from '../../types/ticket'
import { ticketService } from '../../services/ticketService'

const { Text, Link } = Typography

interface CommentThreadProps {
  ticketId: string
  comments: TicketComment[]
}

/** Hilo cronológico de comentarios tipificados con adjuntos descargables (US3). */
export default function CommentThread({ ticketId, comments }: CommentThreadProps) {
  if (comments.length === 0) {
    return <Empty description="Sin comentarios todavía" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }
  return (
    <Timeline
      items={comments.map(c => ({
        color: c.visibility === 'external' ? 'blue' : 'gray',
        children: (
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color={c.visibility === 'external' ? 'blue' : 'default'}>
                {c.comment_type_label}
              </Tag>
              {c.is_automatic && <Tag icon={<RobotOutlined />}>automático</Tag>}
              <Text type="secondary" style={{ fontSize: 12 }}>
                {new Date(c.created_at).toLocaleString('es-CO')}
                {' · '}{c.visibility === 'external' ? 'visible al cliente' : 'interno'}
              </Text>
            </Space>
            <Text>{c.body}</Text>
            {c.attachments.map(a => (
              <Link key={a.id} onClick={() => ticketService.downloadAttachment(ticketId, a.id, a.filename)}>
                <PaperClipOutlined /> {a.filename} ({(a.size_bytes / 1024).toFixed(0)} KB)
              </Link>
            ))}
          </Space>
        ),
      }))}
    />
  )
}
