import type { TicketListItem } from '../../types/ticket'
import { vivid, palette } from '../../theme'

const LABELS: Record<TicketListItem['sla']['status'], string> = {
  sin_sla: 'Sin SLA', corriendo: 'Corriendo', pausado: 'Pausado',
  vencido: 'Vencido', detenido: 'Detenido',
}

const CHIPS: Record<TicketListItem['sla']['status'], { bg: string; text: string }> = {
  sin_sla: { bg: palette.slate100, text: palette.slate500 },
  corriendo: { bg: vivid.green.bg, text: vivid.green.text },
  pausado: { bg: vivid.orange.bg, text: vivid.orange.text },
  vencido: { bg: vivid.red.bg, text: vivid.red.text },
  detenido: { bg: palette.slate100, text: palette.slate500 },
}

/** Indicador de SLA por fila en el listado de Tickets (Historia 3, spec 014, FR-008). */
export default function SlaStatusTag({ status }: { status: TicketListItem['sla']['status'] }) {
  const chip = CHIPS[status]
  return (
    <span
      style={{
        display: 'inline-block', padding: '2px 10px', borderRadius: 999,
        fontSize: 12, fontWeight: 600, background: chip.bg, color: chip.text,
        whiteSpace: 'nowrap',
      }}
    >
      {LABELS[status]}
    </span>
  )
}
