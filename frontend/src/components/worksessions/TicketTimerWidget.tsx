import { useCallback, useEffect, useRef, useState } from 'react'
import { Alert, Button, Input, Modal, Space, Tag, Tooltip, message } from 'antd'
import { PauseCircleOutlined, PlayCircleOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { timerService } from '../../services/timerService'
import type { Timer } from '../../types/timer'
import { palette } from '../../theme'

interface TicketTimerWidgetProps {
  ticketId: string
  /** Se dispara tras un "Terminar" exitoso, para que `TicketDetailPage` refresque el resumen
   * de `TicketWorkSessions` (componente hermano con su propio fetch — spec 012). */
  onFinished?: () => void
}

function formatHMS(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return [h, m, sec].map((n, i) => (i === 0 ? String(n) : String(n).padStart(2, '0'))).join(':')
}

function errorMessage(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? fallback
}

/** Cronómetro manual de tiempo (spec 012, provisional): iniciar/pausar/reanudar/terminar,
 * personal por recurso — solo ve y controla el suyo (FR-005). El tiempo mostrado se deriva de
 * `total_seconds` recibido del servidor en el último fetch más lo transcurrido localmente
 * (research.md Decisión 2), nunca de un contador propio del navegador. */
export default function TicketTimerWidget({ ticketId, onFinished }: TicketTimerWidgetProps) {
  const [timer, setTimer] = useState<Timer | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [finishOpen, setFinishOpen] = useState(false)
  const [note, setNote] = useState('')
  const [displaySeconds, setDisplaySeconds] = useState(0)
  const fetchedAtRef = useRef<number>(Date.now())

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const current = await timerService.getCurrent()
      setTimer(current)
      setDisplaySeconds(current.total_seconds)
      fetchedAtRef.current = Date.now()
    } finally {
      setLoading(false)
    }
  }, [])

  // Resincroniza al montar (incluida una recarga completa de la página — US2 FR-004).
  useEffect(() => { load() }, [load])

  // Tick visual local de 1s: solo redibuja el número, la fuente de verdad sigue siendo el
  // último `total_seconds` del servidor + lo transcurrido desde ese fetch.
  useEffect(() => {
    if (!timer || timer.status !== 'running') return
    const id = setInterval(() => {
      const elapsed = (Date.now() - fetchedAtRef.current) / 1000
      setDisplaySeconds(timer.total_seconds + elapsed)
    }, 1000)
    return () => clearInterval(id)
  }, [timer])

  const isActiveHere = timer && timer.status !== 'inactive' && timer.ticket_id === ticketId
  const isActiveElsewhere = timer && timer.status !== 'inactive' && timer.ticket_id !== ticketId

  const run = async (action: () => Promise<Timer>, successMsg?: string) => {
    setBusy(true)
    try {
      const updated = await action()
      setTimer(updated)
      setDisplaySeconds(updated.total_seconds)
      fetchedAtRef.current = Date.now()
      if (successMsg) message.success(successMsg)
    } catch (err) {
      message.error(errorMessage(err, 'No se pudo actualizar el cronómetro'))
    } finally {
      setBusy(false)
    }
  }

  const handleFinish = async () => {
    setBusy(true)
    try {
      await timerService.finish(note.trim() || undefined)
      message.success('Registro de tiempo creado a partir del cronómetro')
      setFinishOpen(false)
      setNote('')
      await load()
      onFinished?.()
    } catch (err) {
      message.error(errorMessage(err, 'No se pudo terminar el cronómetro'))
    } finally {
      setBusy(false)
    }
  }

  if (loading && !timer) return null

  return (
    <div>
      {isActiveElsewhere && (
        <Alert
          type="info" showIcon style={{ marginBottom: 8 }}
          message={`Tenés un cronómetro activo en el ticket ${timer?.ticket_number ?? ''} — termínalo o pausalo para iniciar uno acá.`}
        />
      )}
      {isActiveHere && timer?.stale && (
        <Alert
          type="warning" showIcon style={{ marginBottom: 8 }}
          message="Este cronómetro lleva corriendo varias horas sin pausarse — revisá si te olvidaste de pausarlo."
        />
      )}
      <Space align="center">
        <span style={{ fontVariantNumeric: 'tabular-nums', fontSize: 20, fontWeight: 600, color: palette.slate900 }}>
          {formatHMS(isActiveHere ? displaySeconds : 0)}
        </span>
        {isActiveHere && (
          <Tag color={timer?.status === 'running' ? 'green' : 'orange'}>
            {timer?.status === 'running' ? 'Corriendo' : 'Pausado'}
          </Tag>
        )}
        {!isActiveHere && !isActiveElsewhere && (
          <Button icon={<PlayCircleOutlined />} loading={busy}
            onClick={() => run(() => timerService.start(ticketId), 'Cronómetro iniciado')}>
            Iniciar
          </Button>
        )}
        {isActiveHere && timer?.status === 'running' && (
          <Button icon={<PauseCircleOutlined />} loading={busy}
            onClick={() => run(() => timerService.pause())}>
            Pausar
          </Button>
        )}
        {isActiveHere && timer?.status === 'paused' && (
          <Button icon={<PlayCircleOutlined />} loading={busy}
            onClick={() => run(() => timerService.resume())}>
            Reanudar
          </Button>
        )}
        {isActiveHere && (
          <Tooltip title="Genera un Registro de tiempo con lo acumulado">
            <Button type="primary" icon={<CheckCircleOutlined />} loading={busy}
              onClick={() => setFinishOpen(true)}>
              Terminar
            </Button>
          </Tooltip>
        )}
      </Space>

      <Modal
        title="Terminar cronómetro"
        open={finishOpen}
        onCancel={() => setFinishOpen(false)}
        onOk={handleFinish}
        confirmLoading={busy}
        okText="Terminar y registrar tiempo"
        cancelText="Cancelar"
      >
        <p>Se creará un Registro de tiempo de <strong>{formatHMS(displaySeconds)}</strong> en este ticket.</p>
        <Input.TextArea
          placeholder="Nota opcional"
          value={note}
          onChange={e => setNote(e.target.value)}
          rows={2}
        />
      </Modal>
    </div>
  )
}
