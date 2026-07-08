import { useCallback, useEffect, useState } from 'react'
import { Button, Space, Statistic } from 'antd'
import { HistoryOutlined } from '@ant-design/icons'
import { workSessionService } from '../../services/workSessionService'
import type { WorkSessionListItem, ConsumptionLevel } from '../../types/workSession'
import { formatDuration, earliestWorkDate, getConsumptionLevel } from '../../types/workSession'
import { useAuthStore } from '../../store/authStore'
import { palette } from '../../theme'
import TimeLogModal from './TimeLogModal'

interface TicketWorkSessionsProps {
  ticketId: string
  ticketNumber: string
  ticketTitle: string
  /** Tiempo estimado de solución (minutos, US2) — se muestra junto al total real registrado. */
  estimatedMinutes?: number | null
  /** Notifica a `TicketDetailPage` la fecha de inicio y el nivel de consumo derivados de los
   * registros de tiempo (Fase 2.2, US2), para mostrarlos junto a "Tiempo estimado de solución". */
  onSummary?: (summary: { startDate: string | null; consumptionLevel: ConsumptionLevel }) => void
  /** Modo colapsado (Fase 2.2, US1 — revelado fluido, ver `TicketDetailPage`): reemplaza los dos
   * `Statistic` por una línea compacta con el mismo total y acción. */
  compact?: boolean
  /** Se dispara cuando se cierra `TimeLogModal` (además de `onChanged`), para que
   * `TicketDetailPage` vuelva a expandir el resumen (FR-004). */
  onModalClose?: () => void
}

/** Resumen compacto de "Registro de tiempo" del ticket (Fase 2.2, US1) — abre `TimeLogModal`
 * en vez de mostrar el historial siempre visible. Reutiliza el motor de work_sessions de
 * Fase 2 / Fase 2.1. */
export default function TicketWorkSessions({
  ticketId, ticketNumber, ticketTitle, estimatedMinutes, onSummary, compact = false, onModalClose,
}: TicketWorkSessionsProps) {
  const { hasPermission } = useAuthStore()
  const canManage = hasPermission('work_sessions', 'manage')
  const [items, setItems] = useState<WorkSessionListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const sessions = await workSessionService.list({ ticket_id: ticketId, page_size: 100 })
      setItems(sessions.items)
    } finally {
      setLoading(false)
    }
  }, [ticketId])

  useEffect(() => { load() }, [load])

  const totalMinutes = items.reduce((sum, item) => sum + item.duration_minutes, 0)

  useEffect(() => {
    onSummary?.({
      startDate: earliestWorkDate(items),
      consumptionLevel: getConsumptionLevel(estimatedMinutes, totalMinutes),
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, estimatedMinutes, totalMinutes])

  const trigger = (
    <Button icon={<HistoryOutlined />} loading={loading} onClick={() => setModalOpen(true)}>
      {canManage ? 'Registrar tiempo' : 'Ver historial'}
    </Button>
  )

  return (
    <div>
      {compact ? (
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <span style={{ fontSize: 13, color: palette.slate600 }}>
            <strong style={{ color: palette.slate900 }}>{formatDuration(totalMinutes)}</strong> registradas
            {estimatedMinutes != null && ` · ${formatDuration(estimatedMinutes)} estimado`}
          </span>
          {trigger}
        </Space>
      ) : (
        <Space style={{ justifyContent: 'space-between', width: '100%' }} size="large">
          <Statistic
            title="Tiempo total registrado"
            value={formatDuration(totalMinutes)}
            valueStyle={{ fontSize: 28, fontWeight: 600, color: palette.slate900 }}
          />
          <Statistic
            title="Tiempo estimado"
            value={estimatedMinutes != null ? formatDuration(estimatedMinutes) : 'Sin estimar'}
            valueStyle={{ fontSize: 16, fontWeight: 500, color: palette.slate500 }}
          />
          {trigger}
        </Space>
      )}
      <TimeLogModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); onModalClose?.() }}
        ticketId={ticketId}
        ticketNumber={ticketNumber}
        ticketTitle={ticketTitle}
        canManage={canManage}
        onChanged={load}
      />
    </div>
  )
}
