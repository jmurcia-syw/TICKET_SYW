import { useEffect, useState } from 'react'
import { Alert, Button, Modal, Select, Space, Tag, message } from 'antd'
import { UserSwitchOutlined, ExperimentOutlined } from '@ant-design/icons'
import { resourceService } from '../../services/resourceService'
import { ticketService } from '../../services/ticketService'
import type { Resource } from '../../types/resource'

interface AssignModalProps {
  ticketId: string | null
  onClose: () => void
  onAssigned: () => void
}

/** Selector de resolutor con skills visibles (Triage Push, US2). */
export default function AssignModal({ ticketId, onClose, onAssigned }: AssignModalProps) {
  const [resources, setResources] = useState<Resource[]>([])
  const [selected, setSelected] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (ticketId) {
      resourceService.list({ active: true, page_size: 100 }).then(r => setResources(r.items))
      setSelected(undefined)
    }
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

  const selectedResource = resources.find(r => r.id === selected)

  return (
    <Modal
      title="Asignar ticket (Triage Push)"
      open={!!ticketId}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>Cancelar</Button>,
        <Button key="qm" icon={<ExperimentOutlined />} loading={loading} onClick={() => doAssign('pre_analysis')}>
          Pre-Análisis (QM)
        </Button>,
        <Button key="assign" type="primary" icon={<UserSwitchOutlined />} loading={loading}
          onClick={() => doAssign('resolver')}>
          Asignar resolutor
        </Button>,
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Select
          showSearch
          optionFilterProp="label"
          placeholder="Seleccionar recurso"
          style={{ width: '100%' }}
          value={selected}
          onChange={setSelected}
          options={resources.map(r => ({ value: r.id, label: r.full_name }))}
        />
        {selectedResource && (
          <div>
            <strong>Skills:</strong>{' '}
            {selectedResource.skills.length > 0
              ? selectedResource.skills.map(s => <Tag key={s.id}>{s.code}</Tag>)
              : <em>sin skills registrados</em>}
          </div>
        )}
        <Alert type="info" showIcon message="La decisión queda registrada con su contexto (skills, carga, prioridad, severidad) para el futuro Triage Agent." />
      </Space>
    </Modal>
  )
}
