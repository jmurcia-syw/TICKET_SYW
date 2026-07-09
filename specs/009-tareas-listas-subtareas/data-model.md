# Data Model: Listas de Tareas, Subtareas, ciclo de vida unificado y fix de Registro de tiempo

## Tabla nueva: `task_lists` (Nivel 3 de la jerarquía)

| Columna | Tipo | Null | Notas |
|---------|------|------|-------|
| `id` | UUID | No | PK, `gen_random_uuid()` |
| `project_id` | UUID | No | FK `projects.id`, `ON DELETE CASCADE` |
| `name` | TEXT | No | Nombre de la Lista (p. ej. "F1: Definiciones y Alistamiento") |
| `position` | INTEGER | No | Orden de aparición en el sidebar, default `0` (creación = al final) |
| `created_at` / `updated_at` | TIMESTAMPTZ | No | Igual convención que el resto de tablas |

Índice `ix_task_lists_project_id` (`project_id`) — el sidebar siempre filtra por Proyecto.
RLS: hereda el alcance de `projects` (política ya existente vía `client_id`), sin política nueva
propia — se filtra a nivel de aplicación por `project_id` igual que `client_contacts`.

## `tickets` — columnas nuevas

| Columna | Tipo | Null | Notas |
|---------|------|------|-------|
| `list_id` | UUID | Sí | FK `task_lists.id`. Reemplaza `list_name` (spec `008`) como forma canónica de asociar una Tarea a una Lista. `NULL` = grupo "Sin lista" (mismo criterio ya usado en `MyTasksPage.tsx`). |
| `parent_task_id` | UUID | Sí | FK `tickets.id` (autorreferencial). No nulo = el registro es una Subtarea (Nivel 5) de la Tarea referenciada. |

`list_name` (columna de la spec `008`) se mantiene en el esquema físico sin `DROP COLUMN` (ver
research.md Decisión 4) pero deja de leerse/escribirse desde código nuevo — solo queda como
rastro histórico hasta una limpieza futura.

CHECK `ck_tickets_status` **vuelve** a los 10 valores originales de `011_create_tickets.py`
(`nuevo, pre_analisis, contacto, en_analisis, en_ejecucion, en_pruebas, pendiente_usuario,
resuelto, cerrado, cancelado`) — se retiran `pendiente`/`en_progreso`/`hecha` del CHECK, ya
migrados por el backfill de la migración `024` (research.md Decisión 4).

CHECK nuevo `ck_tickets_no_grandchild_subtask`: no se puede expresar en un CHECK declarativo
simple (requiere auto-consulta) — se aplica como validación de servicio (`TicketService
.validate_create`, FR-016), no de esquema.

### Validaciones de negocio (no de esquema)

- **Transición libre + comentario obligatorio de Tarea** (FR-003 a FR-005): reemplaza el gate de
  `task_fsm.py` de la spec `008`. `TicketService.free_transition_task()` valida
  `new_status in STATUSES` (los 10 valores compartidos con Ticket) y `comment_body` no vacío;
  sin restricción de secuencia (cualquier `from_status` → cualquier `to_status`, incluyendo
  retroceder o repetir el estado actual).
- **Campos de clasificación editables en Tarea** (FR-006): `FIELD_LOCKS` dejan de ocultar
  `ticket_type`/`severity`/`escalation_level` para Tarea — usa exactamente los mismos
  `FIELD_LOCKS` por estado que ya rigen para Ticket (se retira el bloque `FIELD_LOCKS["pendiente"]`
  / `["en_progreso"]` / `["hecha"]` propio de la spec `008`).
- **Lista debe pertenecer al mismo Proyecto** (FR-011): si `list_id` viene informado,
  `task_lists.project_id` DEBE == `ticket.project_id`. 409 `list_mismatch` si no — mismo patrón
  que `related_ticket_mismatch` (spec `008`).
- **Subtarea no puede tener Subtareas** (FR-016): si `parent_task_id` viene informado, el ticket
  referenciado DEBE tener `parent_task_id IS NULL`. 409 `nested_subtask_not_allowed` si no.
- **Subtarea hereda `list_id` de su padre en creación**: no editable independientemente después
  (Assumptions del spec) — se resuelve en el servicio de creación, no en el modelo.
- **Ownership de Registro de tiempo por creador** (FR-001, research.md Decisión 7):
  `WorkSessionService.assert_ticket_ownership()` acepta también al `Resource` vinculado a
  `ticket.created_by` cuando el registro es Tarea/Subtarea.

## Dominio retirado: `backend/domain/fsm/task_fsm.py`

Se elimina el archivo completo (4 estados/triggers de la spec `008`) y su endpoint
`POST /api/tickets/{id}/task-transition` — reemplazados por `free_transition_task()` y
`PATCH /api/tickets/{id}/status` (ver contracts/). `ticket_fsm.py` (10 estados, Ticket) no
cambia.

## Vista/serialización (API)

### `TicketListItem` (campos nuevos)

| Campo | Tipo | Notas |
|-------|------|-------|
| `list_id` | string \| null | Reemplaza `list_name` en la salida. |
| `list_name` | string \| null | Se mantiene solo como `task_lists.name` resuelto (join), para no romper consumidores existentes del campo. |
| `record_type` | string | Nombre resuelto ("Ticket"/"Tarea") — ya se resolvía en `related_from[]` (spec `008`); ahora se expone también en el listado principal, para el tag del Kanban (research.md Decisión 6). |
| `parent_task_id` | string \| null | Para que "Mis Tareas" y el Kanban puedan indentar/agrupar Subtareas bajo su Tarea padre. |

### `TicketDetail` (campos nuevos)

| Campo | Tipo | Notas |
|-------|------|-------|
| `list_id` / `list` | string \| null / `{id, name}` \| null | Editable vía `PATCH` (reemplaza `list_name` en `PATCHABLE_FIELDS`). |
| `parent_task_id` | string \| null | Editable solo en creación (no en `PATCH` — mover una Subtarea de padre no es un FR de esta spec). |
| `subtasks` | array de `TicketListItem` | Resuelto por `TicketRepository.list_subtasks(parent_task_id)` (consulta directa por FK, sin migración adicional — mismo patrón que `list_related_from`). |

## Entidad nueva: `TaskList` (dominio)

```python
@dataclass
class TaskList:
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    position: int = 0
    created_at: datetime = ...
    updated_at: datetime = ...
```

Sin FSM ni bloqueos de campo — CRUD simple (crear, listar por Proyecto, renombrar). Repositorio
`TaskListRepository` en `backend/infra/repositories/task_list_repo.py` (mismo patrón que
`client_contact_repo.py`).

## Entidades ya existentes (sin cambios de estructura)

- **`ticket_status_transitions`**: sin cambios de esquema — se reutiliza tal cual para registrar
  también las transiciones libres de Tarea (research.md Decisión 1). `comment_id` sigue siendo
  opcional a nivel de esquema pero la Tarea siempre lo completa (comentario obligatorio).
- **`ticket_comments`**: sin cambios — el comentario de cambio de estado de Tarea usa el tipo ya
  existente `comentario_interno` (research.md Decisión 5).
- **Catálogo `record_type` (`catalog_record_types`)**: sin cambios — "Tarea" ya sembrado desde la
  migración `013`. Una Subtarea reutiliza el mismo `record_type_id` "Tarea" (se distingue por
  `parent_task_id`, no por un tercer valor de catálogo).
