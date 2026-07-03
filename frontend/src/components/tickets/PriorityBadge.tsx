import { PRIORITY_CHIP } from '../../theme'
import { PRIORITY_LABELS, type Priority } from '../../types/ticket'

const SHORT: Record<Priority, string> = { critical: 'P1', high: 'P2', medium: 'P3', low: 'P4' }

/** Badge sólido de prioridad (p1..p4), estilo docs/PROPUESTA_VISUAL.html. */
export default function PriorityBadge({ priority, full = false }: { priority: Priority; full?: boolean }) {
  const chip = PRIORITY_CHIP[priority]
  return (
    <span
      style={{
        display: 'inline-block', padding: '2px 8px', borderRadius: 4,
        fontSize: 11, fontWeight: 700, letterSpacing: 0.3,
        background: chip.bg, color: chip.text,
      }}
    >
      {SHORT[priority]}{full ? ` · ${PRIORITY_LABELS[priority]}` : ''}
    </span>
  )
}
