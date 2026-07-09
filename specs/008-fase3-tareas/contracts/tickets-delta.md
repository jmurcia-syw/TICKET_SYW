# Contrato — Delta sobre `tickets`

Cambios sobre el endpoint ya existente `/api/tickets` (Fase 1/2/2.1/2.2) + un endpoint de acción
nuevo. No se agrega un namespace nuevo (`Tarea` es un `tickets` más, distinguido por
`record_type_id`).

## `POST /api/tickets`

**Input** (`TicketInput`) — cambios:

| Campo | Tipo | Requerido | Notas |
|-------|------|-----------|-------|
| `record_type_id` | string (UUID) | No | Deja de rechazar el valor `Tarea` del catálogo (antes 409 `record_type_not_allowed` siempre que no fuera `Ticket`). Default sigue siendo `Ticket` si se omite. |
| `list_name` | string | No | Solo tiene efecto si el registro resultante es una Tarea; ignorado (pero aceptado) en un Ticket. |
| `ticket_type`, `priority`, `severity` | string | **Condicional** | Siguen requeridos si `record_type_id` resuelve a `Ticket` (o se omite). Si resuelve a `Tarea`, se **ignoran si vienen** y el backend los completa con los mismos defaults silenciosos ya usados para el alta de un Encargado (`incident`/`medium`/`s3`) — el cliente HTTP no necesita enviarlos. |
| `related_ticket_id` | string (UUID) | No | Sin cambio de forma; ahora además valida que pertenezca al mismo `client_id` (ver más abajo — corrige un gap de la Fase 1, aplica también a Tickets). |

**Nuevas respuestas de error**:
- `409 related_ticket_mismatch` — el "Registro relacionado" indicado pertenece a un Cliente
  distinto del `client_id` del registro que se está creando (Ticket o Tarea).

**Sin cambios**: el branch `is_encargado` (autoservicio) sigue sin leer `record_type_id` — un
Encargado nunca puede crear una Tarea, ver siempre nace `Ticket`.

## `PATCH /api/tickets/{id}`

**Input** — `list_name` se agrega a `PATCHABLE_FIELDS`.

**Nuevas respuestas de error**:
- `409 related_ticket_mismatch` — mismo criterio que en `POST`, ahora también en edición.
- `409 field_locked` — para una Tarea en estado `hecha`, `locked_fields` ahora puede incluir
  `title`, `description`, `priority`, `list_name`, `related_ticket_id` (ver data-model.md).

**Sin cambios**: `status` sigue explícitamente rechazado en `PATCH` (Ticket y Tarea por igual) —
usar el endpoint de transición correspondiente.

## `POST /api/tickets/{id}/task-transition` (nuevo)

Cambia el estado de una **Tarea** siguiendo `task_fsm.py` (ver data-model.md). Análogo a
`POST /api/tickets/{id}/cancel` ya existente para Ticket, pero **sin comentario obligatorio**
(SC-006).

**Input**:

```json
{ "trigger": "start" | "complete" | "cancel" | "reopen" }
```

**Respuestas**:
- `200` — Tarea actualizada (mismo `TicketDetail` que `GET /api/tickets/{id}`).
- `400 validation_error` — `trigger` ausente o desconocido.
- `403` — sin permiso `tickets:edit` (mismo permiso ya usado para `PATCH`, no uno nuevo — ver
  research.md Decisión 5).
- `404` — Tarea no encontrada.
- `409 not_a_task` — el registro indicado es un Ticket, no una Tarea (esta acción no aplica).
- `409 invalid_transition` — el `trigger` no es válido desde el estado actual (mismo formato de
  error ya usado por `ticket_fsm.apply()`, con `valid_actions` en el body).

## `GET /api/tickets/{id}` (detalle)

**Output** (`TicketDetail`) — campos nuevos:

| Campo | Tipo | Notas |
|-------|------|-------|
| `list_name` | string \| null | Crudo — ver data-model.md. |
| `related_from` | array de `{id, ticket_number, title, record_type}` | Relación inversa (FR-006): quién referencia a este registro como "Registro relacionado". |

`status`/`status_label` — sin cambio de forma; para una Tarea, `status` toma uno de
`pendiente`/`en_progreso`/`hecha`/`cancelado` y `status_label` la etiqueta española
correspondiente (`STATUS_LABELS` extendido).

## `GET /api/tickets` (listado)

Sin cambios de forma. `record_type_id` ya viene en cada item — el frontend lo usa para distinguir
visualmente Ticket de Tarea en las columnas de `TicketsPage.tsx`/`MyTasksPage.tsx` (FR-007), sin
tocar el contrato del endpoint.
