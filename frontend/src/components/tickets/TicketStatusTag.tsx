import { Tag } from 'antd'
import type { TicketStatus } from '../../types/ticket'
import { STATUS_LABELS } from '../../types/ticket'

const STATUS_TAG_COLORS: Record<TicketStatus, string> = {
  nuevo: 'blue',
  pre_analisis: 'geekblue',
  contacto: 'cyan',
  en_analisis: 'purple',
  en_ejecucion: 'orange',
  en_pruebas: 'gold',
  pendiente_usuario: 'magenta',
  resuelto: 'green',
  cerrado: 'default',
  cancelado: 'red',
}

export default function TicketStatusTag({ status }: { status: TicketStatus }) {
  return <Tag color={STATUS_TAG_COLORS[status]}>{STATUS_LABELS[status]}</Tag>
}
