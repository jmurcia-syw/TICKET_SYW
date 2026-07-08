import { useState } from 'react'
import { Button, Input, Modal, Space, Tag, Tooltip, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useAuthStore } from '../../store/authStore'
import { useSavedFiltersStore, type SavedFilter, type TicketFilterCriteria } from '../../store/savedFiltersStore'
import { resourceService } from '../../services/resourceService'

interface SavedFiltersBarProps {
  /** Combinación de criterios activa en la pantalla (Tickets o Mis Tareas), para poder
   * guardarla con un nombre (FR-013). */
  currentCriteria: TicketFilterCriteria
  /** Aplica los criterios de un filtro guardado a la pantalla actual. */
  onApply: (criteria: TicketFilterCriteria) => void
}

/** Barra de filtros guardados (Fase 2.2, US3) — compartida entre `TicketsPage` y `MyTasksPage`
 * (FR-014): aplicar, guardar y eliminar filtros nombrados y reutilizables. */
export default function SavedFiltersBar({ currentCriteria, onApply }: SavedFiltersBarProps) {
  const { userId } = useAuthStore()
  const { listFilters, addFilter, removeFilter } = useSavedFiltersStore()
  const filters = userId ? listFilters(userId) : []

  const [saveOpen, setSaveOpen] = useState(false)
  const [name, setName] = useState('')

  const handleApply = async (filter: SavedFilter) => {
    const criteria = { ...filter.criteria }
    if (criteria.assignee_id === '__me__') {
      const resource = await resourceService.me()
      criteria.assignee_id = resource.id
    }
    onApply(criteria)
  }

  const handleSave = () => {
    if (!userId) return
    const result = addFilter(userId, name, currentCriteria)
    if (!result.ok) {
      message.error(result.error)
      return
    }
    message.success('Filtro guardado')
    setSaveOpen(false)
    setName('')
  }

  return (
    <Space wrap>
      {filters.map(f => (
        <Tag
          key={f.id}
          style={{ cursor: 'pointer' }}
          onClick={() => handleApply(f)}
          closable={!f.builtIn}
          onClose={e => { e.preventDefault(); if (userId) removeFilter(userId, f.id) }}
        >
          {f.name}
        </Tag>
      ))}
      <Tooltip title="Guardar la combinación de filtros actual como un nuevo filtro reutilizable">
        <Button size="small" icon={<PlusOutlined />} onClick={() => { setName(''); setSaveOpen(true) }}>
          Guardar filtro
        </Button>
      </Tooltip>

      <Modal
        title="Guardar filtro" open={saveOpen} onCancel={() => setSaveOpen(false)}
        onOk={handleSave} okText="Guardar" cancelText="Cancelar"
      >
        <Input
          placeholder="Nombre del filtro" value={name}
          onChange={e => setName(e.target.value)} onPressEnter={handleSave}
        />
      </Modal>
    </Space>
  )
}
