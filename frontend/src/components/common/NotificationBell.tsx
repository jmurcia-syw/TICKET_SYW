import { useCallback, useEffect, useState } from 'react'
import { Badge, Button, Dropdown, Empty, List, Typography } from 'antd'
import { BellOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { notificationService } from '../../services/notificationService'
import type { AppNotification } from '../../types/notification'

const POLL_MS = 60_000

/** Campana de notificaciones internas con polling (Decisión 7 de research.md). */
export default function NotificationBell() {
  const [items, setItems] = useState<AppNotification[]>([])
  const [unread, setUnread] = useState(0)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    try {
      const data = await notificationService.list(false, 1, 10)
      setItems(data.items)
      setUnread(data.unread_count)
    } catch {
      // silencioso: la campana no debe romper la navegación
    }
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(load, POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  const openNotification = async (n: AppNotification) => {
    if (!n.read) await notificationService.markRead([n.id])
    load()
    if (n.ticket) navigate(`/tickets/${n.ticket.id}`)
  }

  const dropdown = (
    <div style={{ width: 360, background: '#fff', boxShadow: '0 4px 16px rgba(0,0,0,0.12)', borderRadius: 8, padding: 8 }}>
      {items.length === 0
        ? <Empty description="Sin notificaciones" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        : (
          <>
            <List
              size="small"
              dataSource={items}
              renderItem={n => (
                <List.Item onClick={() => openNotification(n)} style={{ cursor: 'pointer', opacity: n.read ? 0.6 : 1 }}>
                  <List.Item.Meta
                    title={<Typography.Text strong={!n.read}>{n.message}</Typography.Text>}
                    description={new Date(n.created_at).toLocaleString('es-CO')}
                  />
                </List.Item>
              )}
            />
            {unread > 0 && (
              <Button type="link" block onClick={async () => { await notificationService.markAllRead(); load() }}>
                Marcar todas como leídas
              </Button>
            )}
          </>
        )}
    </div>
  )

  return (
    <Dropdown popupRender={() => dropdown} trigger={['click']} onOpenChange={open => { if (open) load() }}>
      <Badge count={unread} size="small">
        <Button type="text" icon={<BellOutlined style={{ fontSize: 18 }} />} />
      </Badge>
    </Dropdown>
  )
}
