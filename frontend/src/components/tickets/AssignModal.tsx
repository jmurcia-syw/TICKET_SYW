import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Input, Modal, Tag, Tooltip, message } from 'antd'
import { UserSwitchOutlined, ExperimentOutlined, BulbOutlined, FireOutlined } from '@ant-design/icons'
import { resourceService } from '../../services/resourceService'
import { ticketService } from '../../services/ticketService'
import type { Resource } from '../../types/resource'
import { avatarColor, initials, palette, vivid } from '../../theme'

interface AssignModalProps {
  ticketId: string | null
  onClose: () => void
  onAssigned: () => void
  /** Si viene de un arrastre en el Kanban, fuerza un único modo y oculta el otro botón. */
  forcedMode?: 'resolver' | 'pre_analysis'
}

const WORKLOAD_SCALE = 8 // referencia visual (no es un límite real de capacidad)

function workloadColor(count: number): string {
  if (count >= 6) return vivid.red.text
  if (count >= 3) return vivid.gold.text
  return vivid.green.text
}

/** Selector de resolutor con skills y carga real (Triage Push, US2). */
export default function AssignModal({ ticketId, onClose, onAssigned, forcedMode }: AssignModalProps) {
  const [resources, setResources] = useState<Resource[]>([])
  const [workload, setWorkload] = useState<Record<string, number>>({})
  const [selected, setSelected] = useState<string | undefined>()
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (ticketId) {
      setSelected(undefined)
      setSearch('')
      resourceService.list({ active: true, page_size: 100 }).then(r => setResources(r.items))
      ticketService.panel().then(data => {
        const map: Record<string, number> = {}
        data.matrix.forEach(row => { map[row.resource.id] = row.total })
        setWorkload(map)
      })
    }
  }, [ticketId])

  const sorted = useMemo(() => {
    const filtered = resources.filter(r => r.full_name.toLowerCase().includes(search.toLowerCase()))
    return [...filtered].sort((a, b) => (workload[a.id] ?? 0) - (workload[b.id] ?? 0))
  }, [resources, workload, search])

  const lightestLoadId = useMemo(() => {
    if (resources.length === 0) return null
    return [...resources].sort((a, b) => (workload[a.id] ?? 0) - (workload[b.id] ?? 0))[0]?.id ?? null
  }, [resources, workload])

  const doAssign = async (mode: 'resolver' | 'pre_analysis') => {
    if (!ticketId || !selected) {
      message.warning('Selecciona un recurso')
      return
    }
    setLoading(true)
    try {
      await ticketService.assign(ticketId, selected, mode)
      message.success(mode === 'resolver' ? 'Ticket asignado (→ Contacto)' : 'Enviado a Pre-Análisis (QM)')
      onAssigned()
      onClose()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al asignar'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title={forcedMode === 'pre_analysis' ? 'Enviar a Pre-Análisis (QM)' : 'Asignar ticket (Triage Push)'}
      open={!!ticketId}
      onCancel={onClose}
      width={680}
      footer={[
        <Button key="cancel" onClick={onClose}>Cancelar</Button>,
        ...(forcedMode !== 'resolver' ? [
          <Button key="qm" icon={<ExperimentOutlined />} loading={loading} disabled={!selected} onClick={() => doAssign('pre_analysis')}>
            Pre-Análisis (QM)
          </Button>,
        ] : []),
        ...(forcedMode !== 'pre_analysis' ? [
          <Button key="assign" type="primary" icon={<UserSwitchOutlined />} loading={loading} disabled={!selected}
            onClick={() => doAssign('resolver')}>
            Asignar resolutor
          </Button>,
        ] : []),
      ]}
    >
      <Alert
        type="info"
        showIcon
        icon={<BulbOutlined />}
        style={{ marginBottom: 12, background: '#F9F0FF', borderColor: '#EFDBFF' }}
        message="Sugerencia por IA — disponible en Fase 7 (Triage Agent)"
        description="Por ahora los resolutores se ordenan por menor carga actual. La recomendación automática por historial y patrones llegará con el AI Dispatcher."
      />

      <Input.Search
        placeholder="Buscar resolutor..."
        allowClear
        value={search}
        onChange={e => setSearch(e.target.value)}
        style={{ marginBottom: 12 }}
      />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10, maxHeight: 340, overflowY: 'auto', paddingRight: 4 }}>
        {sorted.map(r => {
          const count = workload[r.id] ?? 0
          const isSelected = selected === r.id
          const color = avatarColor(r.id)
          const isLightest = r.id === lightestLoadId
          return (
            <div
              key={r.id}
              onClick={() => setSelected(r.id)}
              style={{
                cursor: 'pointer', borderRadius: 10, padding: 12,
                border: `2px solid ${isSelected ? palette.teal600 : palette.slate200}`,
                background: isSelected ? palette.teal50 : '#fff',
                position: 'relative',
              }}
            >
              {isLightest && (
                <Tooltip title="Resolutor con menor carga actual">
                  <Tag color="success" style={{ position: 'absolute', top: -9, right: 8, fontSize: 10 }}>
                    Menor carga
                  </Tag>
                </Tooltip>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', background: color.bg, color: color.text, fontWeight: 700, fontSize: 12,
                }}>
                  {initials(r.full_name)}
                </div>
                <div style={{ fontWeight: 600, fontSize: 13, lineHeight: 1.2 }}>{r.full_name}</div>
              </div>
              <div style={{ marginBottom: 8, minHeight: 22 }}>
                {r.skills.length > 0
                  ? r.skills.slice(0, 3).map(s => (
                      <Tag key={s.id} style={{ fontSize: 10, marginBottom: 2 }}>{s.code}</Tag>
                    ))
                  : <em style={{ fontSize: 11, color: palette.slate400 }}>sin skills</em>}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: palette.slate500, marginBottom: 3 }}>
                <span>Carga actual</span>
                <span style={{ fontWeight: 700, color: workloadColor(count) }}>
                  {count >= 6 && <FireOutlined style={{ marginRight: 2 }} />}
                  {count}
                </span>
              </div>
              <div style={{ height: 5, background: palette.slate100, borderRadius: 3 }}>
                <div style={{
                  height: 5, borderRadius: 3, background: workloadColor(count),
                  width: `${Math.min(100, (count / WORKLOAD_SCALE) * 100)}%`,
                }} />
              </div>
            </div>
          )
        })}
        {sorted.length === 0 && <em style={{ color: palette.slate400 }}>Sin resolutores activos que coincidan</em>}
      </div>
    </Modal>
  )
}
