# Data Model: Refactorización visual y de navegación del detalle del Ticket

Esta funcionalidad no crea ni modifica ninguna tabla, columna ni entidad de dominio en el
backend. Todo lo descrito a continuación son **conceptos de vista (view-model) o de estado de
cliente**, derivados de datos que ya existen.

## Entidades ya existentes (sin cambios de esquema)

### Ticket
- Sin campos nuevos. Se sigue usando `estimated_resolution_minutes` (ya existente) y
  `created_at`/`transitions` (sin relación con la nueva "fecha de inicio").

### Registro de tiempo (Work Session)
- Sin campos nuevos. Se sigue usando `work_date`, `started_at`, `ended_at`, `duration_minutes`,
  `note`, `resource_name`, `ticket_id` (Fase 2 / Fase 2.1).

## Conceptos derivados (calculados en el frontend, no persistidos)

### Fecha de inicio del ticket (view-model)
| Campo | Origen | Notas |
|-------|--------|-------|
| `startDate` | `MIN(work_date)` (o `started_at` si existe) sobre los `work_sessions` del ticket | `null`/ausente si el ticket no tiene ningún registro de tiempo todavía → UI muestra "Aún sin iniciar" |

### Indicador de consumo de tiempo (view-model)
| Campo | Cálculo | Notas |
|-------|---------|-------|
| `estimatedMinutes` | `ticket.estimated_resolution_minutes` | ya existente, puede ser `null` |
| `actualMinutes` | `SUM(work_sessions.duration_minutes)` del ticket | ya calculado hoy en `TicketWorkSessions` (`totalMinutes`) |
| `consumptionRatio` | `actualMinutes / estimatedMinutes` | solo si `estimatedMinutes != null` y `> 0` |
| `consumptionLevel` | `< 0.8` → `success`; `0.8–1.0` → `warning`; `> 1.0` → `error`; sin estimado → `none` | ver research.md Decisión 6 |

## Nueva entidad de estado de cliente: Filtro guardado (Saved Filter)

Vive únicamente en `frontend/src/store/savedFiltersStore.ts` (Zustand + `persist` en
`localStorage`), namespaced por `userId`. No tiene tabla ni endpoint de backend.

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | `string` (uuid o timestamp) | identificador local |
| `name` | `string` | nombre visible, único por usuario (FR-016) |
| `criteria` | objeto de criterios de filtro (mismo shape que usan hoy `TicketsPage`/`MyTasksPage`: `status`, `client_id`, `priority`, `severity`, `assignee_id`, `search`) | criterios literales, salvo el caso especial de abajo |
| `builtIn` | `boolean` | `true` únicamente para el preset "Asignado a mí"; no eliminable (FR-015) |
| `ownerUserId` | `string` | para namespacing entre cuentas que comparten navegador |

**Regla especial — "Asignado a mí" (`builtIn: true`)**: no guarda un `assignee_id` fijo; al
aplicarse, se resuelve en runtime vía `resourceService.me()` (igual que ya hace
`WorkSessionsPage.tsx`), de forma que sigue siendo correcto aunque cambie el recurso asociado al
usuario.

## Lista / Subtarea (placeholder visual, Historia 4)

No es una entidad de datos en esta funcionalidad. Es únicamente un rótulo visual ("Próximamente")
en el detalle del ticket y en "Mis Tareas" — mismo patrón ya usado por los placeholders de
"SLA" y "Sesión de trabajo (Focus Room)" en `TicketDetailPage.tsx`. Su modelo de datos real
(`task_lists`, jerarquía de subtareas) ya está anticipado en `constitution.md` (Fase 3 del
roadmap) y queda fuera de esta funcionalidad.
