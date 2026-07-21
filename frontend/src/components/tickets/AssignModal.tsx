import { useEffect, useState } from 'react'
import { Alert, Button, Modal, message } from 'antd'
import { UserSwitchOutlined, ExperimentOutlined, BulbOutlined } from '@ant-design/icons'
import { ticketService } from '../../services/ticketService'
import { useResourceCandidates } from './useResourceCandidates'
import ResourceCandidateGrid from './ResourceCandidateGrid'

interface AssignModalProps {
  ticketId: string | null
  onClose: () => void
  onAssigned: () => void
  /** Si viene de un arrastre en el Kanban, fuerza un único modo y oculta el otro botón. */
  forcedMode?: 'resolver' | 'pre_analysis'
}

/** Selector de resolutor con skills y carga real (Triage Push, US2). */
export default function AssignModal({ ticketId, onClose, onAssigned, forcedMode }: AssignModalProps) {
  const { resources, workload, availability } = useResourceCandidates(!!ticketId)
  const [selected, setSelected] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (ticketId) setSelected(undefined)
  }, [ticketId])

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

      <ResourceCandidateGrid
        resources={resources}
        workload={workload}
        availability={availability}
        selected={selected}
        onSelect={setSelected}
      />
    </Modal>
  )
}
