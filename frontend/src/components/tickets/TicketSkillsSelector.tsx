import { useEffect, useState } from 'react'
import { Select, Space, Tag, message } from 'antd'
import { skillService } from '../../services/resourceService'
import { ticketService } from '../../services/ticketService'
import type { Skill } from '../../types/resource'
import type { TicketSkillRef } from '../../types/ticket'
import { palette } from '../../theme'

interface TicketSkillsSelectorProps {
  ticketId: string
  skills: TicketSkillRef[]
  /** Habilita edición (rol con `tickets:edit`). Sin importar `ticket.status` (spec 011 FR-002) —
   * a diferencia de otros campos de clasificación, este selector nunca se deshabilita por
   * estado. */
  editable: boolean
  onUpdated?: (skills: TicketSkillRef[]) => void
}

/** Skills requeridas del ticket, opcional (spec 011): multi-select sobre el catálogo activo de
 * Skills, con guardado inmediato por cada cambio (reemplazo total vía
 * `PATCH /api/tickets/{id}/skills`) — no pasa por el flujo de "Guardar cambios" del resto de la
 * clasificación porque el endpoint dedicado ya funciona en cualquier estado del ticket. */
export default function TicketSkillsSelector({ ticketId, skills, editable, onUpdated }: TicketSkillsSelectorProps) {
  const [catalog, setCatalog] = useState<Skill[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!editable) return
    skillService.list(true).then(r => setCatalog(r.items))
      .catch(() => message.error('No se pudo cargar el catálogo de skills'))
  }, [editable])

  const handleChange = async (skillIds: string[]) => {
    setSaving(true)
    try {
      const updated = await ticketService.updateTicketSkills(ticketId, skillIds)
      onUpdated?.(updated.skills)
    } catch {
      message.error('No se pudieron actualizar las Skills requeridas')
    } finally {
      setSaving(false)
    }
  }

  if (!editable) {
    return skills.length > 0 ? (
      <Space size={[4, 4]} wrap>
        {skills.map(s => <Tag key={s.id}>{s.code}</Tag>)}
      </Space>
    ) : (
      <em style={{ color: palette.slate400 }}>Sin Skills requeridas</em>
    )
  }

  return (
    <Select
      mode="multiple" size="small" style={{ minWidth: 220 }} allowClear
      loading={saving} placeholder="Sin Skills requeridas"
      value={skills.map(s => s.id)}
      options={catalog.map(s => ({ value: s.id, label: `${s.code} — ${s.label}` }))}
      onChange={handleChange}
    />
  )
}
