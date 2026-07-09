# Data Model: Fase 3 — Manejo de Tareas

## Cambios de esquema

### `tickets` (columna nueva + CHECK ampliado)

| Columna | Tipo | Null | Notas |
|---------|------|------|-------|
| `list_name` | TEXT | Sí | Nombre de lista en texto libre (FR-010). `NULL` = grupo "Sin lista" en `MyTasksPage.tsx`. Solo tiene significado para `record_type = 'Tarea'`, pero no se restringe a nivel de esquema. |

Migración `023_tasks_status_list.py`:
1. `ALTER TABLE tickets ADD COLUMN list_name TEXT NULL` — sin índice (agrupamiento se resuelve en
   memoria sobre el array ya paginado de "Mis Tareas", no hay `GROUP BY` en servidor).
2. `ALTER TABLE tickets DROP CONSTRAINT ck_tickets_status` + recrear con los 3 valores nuevos:

   ```text
   status IN ('nuevo','pre_analisis','contacto','en_analisis','en_ejecucion','en_pruebas',
              'pendiente_usuario','resuelto','cerrado','cancelado',
              'pendiente','en_progreso','hecha')
   ```

   `cancelado` se **reutiliza** tal cual (ya está en la lista) — no se agrega `cancelada`.

Sin cambios en `ticket_type`, `priority`, `severity` (siguen `NOT NULL`, ver research.md Decisión
1 — se defaultean silenciosamente al crear una Tarea, igual que ya ocurre hoy para el alta de un
Encargado). Sin cambios de RLS: la política de `tickets` (`012_tickets_rls.py`) sigue cubriendo
la fila completa.

### Validaciones de negocio (no de esquema)

- **Registro relacionado del mismo Cliente** (FR-005, cierra un gap real de la Fase 1): si
  `related_ticket_id` viene informado (crear o editar, Ticket o Tarea), el registro relacionado
  resuelto DEBE tener `client_id == <registro>.client_id`. 409 `related_ticket_mismatch` si no.
  Se valida en `TicketService.validate_create`/`validate_patch` (ver research.md Decisión 4).
- **Registro relacionado no es él mismo**: ya cubierto por el CHECK
  `ck_tickets_related_not_self` a nivel de base de datos (migración `011`) — sin cambios.
- **Bloqueo por estado, Tarea**: `FIELD_LOCKS["hecha"] = {"title", "description", "priority",
  "list_name", "related_ticket_id"}` en `backend/domain/entities/ticket.py` (mismo mecanismo ya
  usado para `cerrado`/`cancelado` de Ticket). `FIELD_LOCKS["cancelado"]` ya existe y se reutiliza
  sin cambios (los campos que bloquea hoy — título, descripción, prioridad, etc. — aplican igual
  de bien a una Tarea cancelada). `FIELD_LOCKS["pendiente"] = FIELD_LOCKS["en_progreso"] = set()`
  (sin bloqueos adicionales a los `_BASE_LOCKED` ya comunes a todo registro).
- **Transición de estado de Tarea no pasa por `PATCH`**: igual que Ticket, `status` sigue
  rechazado explícitamente en `validate_patch`. El cambio de estado de una Tarea usa el nuevo
  endpoint de acción `POST /api/tickets/{id}/task-transition` (ver contracts/), que opera sobre
  `task_fsm.py` sin comentario obligatorio (SC-006).

## Dominio nuevo: `backend/domain/fsm/task_fsm.py`

Mismo patrón que `ticket_fsm.py` (`python-transitions`, Principio V), pero independiente:

| Trigger | Origen | Destino | Notas |
|---------|--------|---------|-------|
| `start` | `pendiente` | `en_progreso` | |
| `complete` | `en_progreso` | `hecha` | |
| `cancel` | `pendiente`, `en_progreso` | `cancelado` | Reutiliza el valor de estado, no el trigger de `ticket_fsm` (máquinas independientes). |
| `reopen` | `hecha`, `cancelado` | `en_progreso` | SC-006 — reapertura sin restricciones. |

Estado inicial de una Tarea: `pendiente` (el de un Ticket sigue siendo `nuevo`, sin cambios).

## Vista/serialización (API, sin tabla nueva)

### `TicketDetail` (campos nuevos)

| Campo | Tipo | Notas |
|-------|------|-------|
| `list_name` | string \| null | Crudo, editable vía `PATCH` (nuevo en `PATCHABLE_FIELDS`). |
| `related_from` | array de `{id, ticket_number, title, record_type}` | Relación inversa (FR-006): registros que tienen a este como `related_ticket_id`. Resuelto por `TicketRepository.list_related_from(ticket_id)`, sin migración (consulta directa por FK). |

`record_type_id`/`related_ticket_id`/`status`/`status_label` ya existen en la salida — sin
cambio de forma, solo de valores posibles (`status` ahora puede ser uno de los 4 estados de
Tarea; `status_label` se extiende con las etiquetas en español correspondientes en
`STATUS_LABELS`).

## Entidades ya existentes (sin cambios de estructura)

- **Catálogo `record_type` (`catalog_record_types`)**: sin cambios — `Ticket`/`Tarea` ya sembrados
  desde la migración `013`. Cambia únicamente la regla de negocio en
  `TicketService.resolve_record_type` (deja de rechazar `Tarea`).
- **Cliente / Proyecto / Encargado (`client_contacts`)**: sin cambios — una Tarea los usa
  exactamente igual que un Ticket (mismo modelo jerárquico Cliente → Proyecto).
