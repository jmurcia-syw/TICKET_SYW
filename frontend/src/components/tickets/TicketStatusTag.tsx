import type { TicketStatus } from '../../types/ticket'
import { STATUS_LABELS } from '../../types/ticket'
import { TICKET_STATUS_CHIP } from '../../theme'

export default function TicketStatusTag({ status }: { status: TicketStatus }) {
  const chip = TICKET_STATUS_CHIP[status]
  return (
    <span
      style={{
        display: 'inline-block', padding: '2px 10px', borderRadius: 999,
        fontSize: 12, fontWeight: 600, background: chip.bg, color: chip.text,
        whiteSpace: 'nowrap',
      }}
    >
      {STATUS_LABELS[status]}
    </span>
  )
}
