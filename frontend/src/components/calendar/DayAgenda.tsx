import { useEffect, useState } from 'react'
import { List, Tag, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { ticketService } from '../../services/ticketService'
import type { TicketListItem, TicketStatus } from '../../types/ticket'
import { SEVERITY_LABELS } from '../../types/ticket'
import PriorityBadge from '../tickets/PriorityBadge'
import { palette, vivid } from '../../theme'

// Spec 022 (Historia 4, FR-015/FR-016): la vista de Día lista la agenda vigente del recurso
// (tickets abiertos actualmente asignados, sin filtro por una fecha propia del ticket — Ticket
// no tiene ese campo, ver spec.md Assumptions) ordenada estrictamente por Prioridad -> Severidad,
// resaltando P1/P2/S1/S2.

const OPEN_STATUSES: TicketStatus[] = [
  'nuevo', 'pre_analisis', 'contacto', 'en_analisis', 'en_ejecucion', 'en_pruebas', 'pendiente_usuario',
]

const PRIORITY_ORDER: Record<TicketListItem['priority'], number> = { critical: 0, high: 1, medium: 2, low: 3 }
const SEVERITY_ORDER: Record<TicketListItem['severity'], number> = { s1: 0, s2: 1, s3: 2, s4: 3 }

function isHighCriticality(t: TicketListItem): boolean {
  return (t.priority === 'critical' || t.priority === 'high') && (t.severity === 's1' || t.severity === 's2')
}

export default function DayAgenda({ resourceId }: { resourceId: string }) {
  const navigate = useNavigate()
  const [tickets, setTickets] = useState<TicketListItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    ticketService.list({ assignee_id: resourceId, status: OPEN_STATUSES, page_size: 100, sort: '-created_at' })
      .then(r => setTickets(r.items))
      .catch(() => message.error('No se pudo cargar la agenda del recurso'))
      .finally(() => setLoading(false))
  }, [resourceId])

  const sorted = [...tickets].sort((a, b) => {
    const byPriority = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
    if (byPriority !== 0) return byPriority
    return SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
  })

  return (
    <div style={{ border: `1px solid ${palette.slate200}`, borderRadius: 8, padding: 12, width: '100%' }}>
      <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
        Agenda del día — tickets abiertos por criticidad
      </Typography.Text>
      <List
        size="small"
        loading={loading}
        dataSource={sorted}
        locale={{ emptyText: 'Sin tickets abiertos asignados' }}
        renderItem={t => (
          <List.Item
            onClick={() => navigate(`/tickets/${t.id}`)}
            style={{ cursor: 'pointer', background: isHighCriticality(t) ? vivid.red.bg : undefined, paddingLeft: 8, paddingRight: 8 }}
          >
            <List.Item.Meta
              title={<span>
                <PriorityBadge priority={t.priority} />{' '}
                <Tag color={isHighCriticality(t) ? 'red' : 'default'}>{SEVERITY_LABELS[t.severity]}</Tag>{' '}
                {t.ticket_number} — {t.title}
              </span>}
              description={t.status_label}
            />
          </List.Item>
        )}
      />
    </div>
  )
}
