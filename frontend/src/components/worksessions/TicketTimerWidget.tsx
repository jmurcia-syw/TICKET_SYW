import { useCallback, useEffect, useRef, useState } from 'react'
import { Alert, Button, Input, Modal, Space, Tag, Tooltip, message } from 'antd'
import { PauseCircleOutlined, PlayCircleOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { timerService } from '../../services/timerService'
import type { Timer } from '../../types/timer'
import { palette } from '../../theme'

interface TicketTimerWidgetProps {
  ticketId: string
  /** Estado actual del ticket (spec 028, OBS-0035) — con `'cerrado'` se deshabilita "Iniciar"
   * proactivamente en vez de depender solo del error `ticket_closed` del backend al intentarlo. */
  ticketStatus?: string
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

function errorCode(err: unknown): string | undefined {
  // El contrato estandar (spec 013, backend/api/errors.py) siempre entrega `code` en
  // MAYUSCULAS ("NO_RESOURCE_PROFILE") — se normaliza a minuscula para comparar contra el
  // código de dominio original (ej. "no_resource_profile").
  const data = (err as { response?: { data?: { code?: string; error?: string } } }).response?.data
  return (data?.code ?? data?.error)?.toLowerCase()
}

/** Cronómetro manual de tiempo (spec 012, provisional): iniciar/pausar/reanudar/terminar,
 * personal por recurso — solo ve y controla el suyo (FR-005). El tiempo mostrado se deriva de
 * `total_seconds` recibido del servidor en el último fetch más lo transcurrido localmente
 * (research.md Decisión 2), nunca de un contador propio del navegador. */
export default function TicketTimerWidget({ ticketId, ticketStatus, onFinished }: TicketTimerWidgetProps) {
  const [timer, setTimer] = useState<Timer | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [finishOpen, setFinishOpen] = useState(false)
  const [note, setNote] = useState('')
  const [noteError, setNoteError] = useState<string | undefined>()
  const [displaySeconds, setDisplaySeconds] = useState(0)
  const [noResourceProfile, setNoResourceProfile] = useState(false)
  const fetchedAtRef = useRef<number>(Date.now())

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const current = await timerService.getCurrent()
      setTimer(current)
      setDisplaySeconds(current.total_seconds)
      fetchedAtRef.current = Date.now()
    } catch (err) {
      // OBS-0050/OBS-0054: un usuario sin perfil de recurso (Admin/Coordinador/QM) no debe ver
      // ningún error — el cronómetro es personal de quien registra tiempo, se oculta sin más.
      if (errorCode(err) === 'no_resource_profile') {
        setNoResourceProfile(true)
      }
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
  const isClosed = ticketStatus === 'cerrado'

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
    // spec 038 US4 (FR-020): "Terminar" genera un Registro de tiempo igual que la carga manual
    // (`TicketTimerService.finish()` reutiliza `WorkSessionService.create()` tal cual) — la
    // descripción pasa a ser obligatoria ahí también, ya no "Nota opcional".
    if (!note.trim()) {
      setNoteError('La descripción es requerida')
      return
    }
    setBusy(true)
    try {
      await timerService.finish(note.trim())
      message.success('Registro de tiempo creado a partir del cronómetro')
      setFinishOpen(false)
      setNote('')
      setNoteError(undefined)
      await load()
      onFinished?.()
    } catch (err) {
      message.error(errorMessage(err, 'No se pudo terminar el cronómetro'))
    } finally {
      setBusy(false)
    }
  }

  if (noResourceProfile) return null
  if (loading && !timer) return null

  return (
    <div>
      {isClosed && !isActiveHere && (
        <Alert
          type="info" showIcon style={{ marginBottom: 8 }}
          message="Este ticket ya está cerrado — no admite nuevos registros de tiempo."
        />
      )}
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
          <Tooltip title={isClosed ? 'Ticket cerrado: no admite nuevos registros de tiempo' : undefined}>
            <Button icon={<PlayCircleOutlined />} loading={busy} disabled={isClosed}
              onClick={() => run(() => timerService.start(ticketId), 'Cronómetro iniciado')}>
              Iniciar
            </Button>
          </Tooltip>
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
        onCancel={() => { setFinishOpen(false); setNoteError(undefined) }}
        onOk={handleFinish}
        confirmLoading={busy}
        okText="Terminar y registrar tiempo"
        cancelText="Cancelar"
      >
        <p>Se creará un Registro de tiempo de <strong>{formatHMS(displaySeconds)}</strong> en este ticket.</p>
        <Input.TextArea
          placeholder="Descripción"
          value={note}
          onChange={e => { setNote(e.target.value); if (noteError) setNoteError(undefined) }}
          rows={2}
          status={noteError ? 'error' : undefined}
        />
        {noteError && <div style={{ color: palette.red600, fontSize: 12, marginTop: 4 }}>{noteError}</div>}
      </Modal>
    </div>
  )
}
