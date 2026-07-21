import { useEffect, useState } from 'react'
import { message } from 'antd'
import { resourceService } from '../../services/resourceService'
import { ticketService } from '../../services/ticketService'
import { calendarService } from '../../services/calendarService'
import type { Resource } from '../../types/resource'
import type { Availability } from '../../types/calendar'

interface ResourceCandidates {
  resources: Resource[]
  workload: Record<string, number>
  availability: Record<string, Availability>
}

/** Recursos activos + carga actual + disponibilidad (Triage Push, spec 010/020) — misma fuente
 * de datos reutilizada por la reasignación (spec 024, "las mismas sugerencias... como la
 * asignación inicial"). La disponibilidad es informativa (nunca bloquea, FR-015 de spec 020),
 * por eso su fallo se ignora en silencio igual que ya hacía `AssignModal`. */
export function useResourceCandidates(enabled: boolean): ResourceCandidates {
  const [resources, setResources] = useState<Resource[]>([])
  const [workload, setWorkload] = useState<Record<string, number>>({})
  const [availability, setAvailability] = useState<Record<string, Availability>>({})

  useEffect(() => {
    if (!enabled) return
    resourceService.list({ active: true, page_size: 100 }).then(r => setResources(r.items))
      .catch(() => message.error('No se pudo cargar la lista de recursos'))
    ticketService.panel().then(data => {
      const map: Record<string, number> = {}
      data.matrix.forEach(row => { map[row.resource.id] = row.total })
      setWorkload(map)
    }).catch(() => message.error('No se pudo cargar la carga de los resolutores'))
    calendarService.getAvailability().then(items => {
      const map: Record<string, Availability> = {}
      items.forEach(a => { map[a.resource_id] = a })
      setAvailability(map)
    }).catch(() => {})
  }, [enabled])

  return { resources, workload, availability }
}
