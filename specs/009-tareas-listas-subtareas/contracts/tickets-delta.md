# Contrato — Delta sobre `tickets`

Cambios sobre `/api/tickets` (Fase 1 a 3) — revierte parte del contrato de la spec `008` y agrega
soporte de Lista real y Subtarea. Sin namespace nuevo (Tarea/Subtarea siguen siendo un `tickets`
más, distinguido por `record_type_id` + `parent_task_id`).

## `POST /api/tickets`

**Input** (`TicketInput`) — cambios:

| Campo | Tipo | Requerido | Notas |
|-------|------|-----------|-------|
| `list_id` | string (UUID) | No | Reemplaza `list_name` (spec `008`). Solo tiene efecto en una Tarea; DEBE pertenecer al mismo `project_id` del registro (409 `list_mismatch` si no). |
| `parent_task_id` | string (UUID) | No | Marca el registro como Subtarea de la Tarea indicada. DEBE ser una Tarea (no otra Subtarea) del mismo `client_id`/`project_id` — 409 `nested_subtask_not_allowed` si el padre ya tiene `parent_task_id` propio. |
| `ticket_type`, `priority`, `severity`, `escalation_level` | string | Igual que Ticket | **Revierte spec `008`**: ya NO se ignoran en una Tarea — quedan disponibles para completar en el formulario reducido de creación como opcionales (FR-006); si se omiten, se siguen defaulteando en creación (`incident`/`medium`/`s3`) y quedan editables después desde el detalle. |

**Sin cambios**: `related_ticket_id` sigue validando mismo-Cliente (spec `008`, se mantiene). El
branch `is_encargado` sigue sin ofrecer Tarea.

## `PATCH /api/tickets/{id}`

**Input** — cambios en `PATCHABLE_FIELDS`:
- Se **retira** `list_name`, se **agrega** `list_id` (mismo validador de mismo-Proyecto que en `POST`).
- Se **agregan** `ticket_type`, `severity`, `escalation_level` como editables también para Tarea
  (antes solo aplicaban a Ticket — FR-006 revierte la Decisión 1 de la spec `008`).

**Sin cambios**: `status` sigue explícitamente rechazado en `PATCH` — usar
`PATCH /api/tickets/{id}/status` (ver más abajo). `parent_task_id` no es editable vía `PATCH`
(mover una Subtarea de padre no es un FR de esta spec).

**Nuevas respuestas de error**:
- `409 list_mismatch` — la Lista indicada pertenece a otro Proyecto.

## `PATCH /api/tickets/{id}/status` (nuevo — reemplaza `POST /{id}/task-transition` de la spec `008`)

Cambia el estado de una **Tarea o Subtarea** a cualquier valor del catálogo de 10 estados
compartido con Ticket, sin restricción de secuencia (research.md Decisión 1). El endpoint
`POST /api/tickets/{id}/task-transition` de la spec `008` se **elimina**.

**Input**:

```json
{ "status": "en_ejecucion", "comment": "Se retoma tras validar con el cliente" }
```

**Respuestas**:
- `200` — registro actualizado (mismo `TicketDetail` que `GET /api/tickets/{id}`), incluye la
  nueva fila de `ticket_status_transitions` y el `Comment` `comentario_interno` creado.
- `400 validation_error` — `status` ausente o fuera del catálogo de 10 valores; `comment` vacío.
- `403` — sin permiso `tickets:transition` (mismo permiso ya usado por los demás endpoints de
  acción de ciclo de vida — `/comments`, `/testing`, `/cancel` — no `tickets:edit`, que es solo
  para editar campos vía `PATCH /api/tickets/{id}`; un Resolutor tiene `transition` pero no
  `edit`, y es quien más usa este endpoint sobre sus propias Tareas).
- `404` — registro no encontrado.
- `409 not_a_task` — el registro es un Ticket puro (sigue usando exclusivamente los endpoints de
  acción existentes: `/assign`, `/comments`, `/testing`, `/resolution`, `/close`, `/cancel`).

## `GET /api/tickets/{id}` (detalle)

**Output** (`TicketDetail`) — campos nuevos/cambiados respecto a la spec `008`:

| Campo | Tipo | Notas |
|-------|------|-------|
| `list_id` / `list` | string \| null / `{id, name}` \| null | Reemplaza el `list_name` crudo por la referencia resuelta a `task_lists`. |
| `parent_task_id` | string \| null | Presente si el registro es una Subtarea. |
| `subtasks` | array de `TicketListItem` | Solo poblado cuando el registro es una Tarea (Nivel 4) — lista de sus Subtareas (Nivel 5). Vacío para Ticket y para Subtarea (no anida más). |
| `ticket_type`, `severity`, `escalation_level` | ya existían | Dejan de ocultarse para Tarea — el frontend ya no filtra estos campos por `isTask`. |

`status`/`status_label`: para Tarea/Subtarea, `status` vuelve a tomar cualquiera de los 10
valores del catálogo de Ticket (ya no `pendiente`/`en_progreso`/`hecha`).

`valid_actions`: para Ticket sigue siendo `ticket_fsm.valid_triggers(status)` (sin cambios). Para
Tarea/Subtarea, se reemplaza por la lista completa de los 10 estados posibles como destino
(cualquiera menos el actual) — el frontend ya no necesita distinguir "triggers" de "estados
destino": son lo mismo.

## `GET /api/tickets` (listado)

**Output** (`TicketListItem`) — campos nuevos:

| Campo | Tipo | Notas |
|-------|------|-------|
| `list_id` | string \| null | |
| `list_name` | string \| null | Resuelto (join a `task_lists.name`) — se mantiene el nombre de campo por compatibilidad con `MyTasksPage.tsx`, que ya agrupa por este valor. |
| `record_type` | string | Nombre resuelto ("Ticket"/"Tarea") — nuevo en el listado (antes solo en `related_from[]`), usado por el tag del Kanban. |
| `parent_task_id` | string \| null | |

**Filtro nuevo** (opcional, query param): `?parent_task_id=<uuid>` — para que
`SubtaskList.tsx` pida directamente las Subtareas de una Tarea sin depender del campo embebido
`subtasks` del detalle.
