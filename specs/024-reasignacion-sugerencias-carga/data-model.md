# Data Model: Sugerencias de Carga y Disponibilidad en la Reasignación

No hay entidades ni tablas nuevas — esta feature es 100% de presentación frontend sobre datos ya
existentes (spec 010 "Panel de Asignación", spec 020 "Alerta de disponibilidad"). No se generan
`contracts/` nuevos: los tres endpoints reutilizados (`GET /api/resources`,
`GET /api/tickets/panel`, disponibilidad vía `calendarService.getAvailability()`) ya están
documentados en Swagger para la asignación inicial y no cambian su forma de respuesta.

## Estructuras de datos reutilizadas (frontend, ya existentes)

| Tipo | Origen | Campos relevantes para esta feature |
|------|--------|--------------------------------------|
| `Resource` (`frontend/src/types/resource.ts`) | `resourceService.list({active:true})` | `id`, `full_name`, `skills[]` |
| Fila de carga (`PanelData.matrix[]`) | `ticketService.panel()` | `resource.id`, `total` (tickets abiertos) |
| `Availability` (`frontend/src/types/calendar.ts`) | `calendarService.getAvailability()` | `resource_id`, `available`, `reason` (`AvailabilityReason`), `detail` |

## Piezas nuevas (sin persistencia, solo composición en memoria del cliente)

### Hook `useResourceCandidates`

Entrada: ninguna (se dispara cuando el modal que lo usa está abierto).
Salida: `{ resources: Resource[], workload: Record<string, number>, availability: Record<string, Availability> }`.

Combina las tres llamadas de arriba — mismo criterio y mismo momento de carga (al abrir el
modal) que ya usa `AssignModal` hoy.

### Componente `ResourceCandidateGrid`

Presentacional puro ("tonto", Principio II): recibe `resources` ya filtrados por el consumidor
(en `AssignModal` no se excluye ninguno; en `ReassignModal` se excluye el `currentAssigneeId`,
regla ya vigente de spec 023), `workload`, `availability`, `selected`, `onSelect`, `search`.
No sabe si está dentro de una asignación o una reasignación — esa distinción vive en el
componente padre, que decide qué candidatos pasar y qué hacer al seleccionar uno.
