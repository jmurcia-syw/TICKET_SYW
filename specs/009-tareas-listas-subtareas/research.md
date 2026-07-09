# Research: Listas de Tareas, Subtareas, ciclo de vida unificado y fix de Registro de tiempo

Todas las decisiones parten de inspeccionar el código ya existente (Fases 1-3, specs `002`-`008`)
para reutilizar al máximo (Principio V) y seguir el patrón ya usado en `007`/`008`.

## Decisión 1 — Ciclo de vida de la Tarea: transición libre reutilizando `ticket_status_transitions`, sin FSM

**Contexto**: la spec `008` implementó `backend/domain/fsm/task_fsm.py`, una `Machine` de
`python-transitions` con 4 estados y 4 triggers fijos, completamente separada de
`ticket_fsm.py`. La spec `009` exige que la Tarea use el mismo catálogo de 10 estados que el
Ticket (FR-003) pero sin la secuencia obligatoria de `ticket_fsm.py` (FR-004) — es decir, no hay
ningún grafo de transiciones válidas que modelar con `python-transitions`: **cualquier estado
puede alcanzar cualquier otro**. Una `Machine` con arcos "todos contra todos" (90 transiciones
para 10 estados) no aporta nada sobre una simple validación de pertenencia al catálogo.

**Decisión**: **no crear una FSM.** Se agrega `TicketService.free_transition_task(ticket, new_status,
comment_body, actor_id, tickets_repo, comments_repo)`, que:
1. Valida `new_status in STATUSES` (el mismo catálogo de 10 valores que ya usa `ticket_fsm.py`,
   importado de `backend/domain/entities/ticket.py`).
2. Exige `comment_body` no vacío (FR-005) — si viene vacío, `TicketBusinessError("comment_required", ...)`.
3. Crea un `Comment` de tipo `comentario_interno` (tipo ya existente desde Fase 1, sin tipo nuevo
   — ver Decisión 5) con el `body` recibido.
4. Inserta una fila en `ticket_status_transitions` (tabla ya existente, usada hoy solo por
   `ticket_fsm.py` vía el endpoint de acciones de Ticket) con `from_status`/`to_status`/
   `actor_id`/`comment_id` — el historial "Historial de estados" de `TicketDetailPage.tsx` ya
   renderiza esta tabla sin cambios, porque no distingue Ticket de Tarea.
5. Actualiza `tickets.status`.

`task_fsm.py` se **retira** (Decisión de Complexity Tracking en plan.md: comentario libre en vez
de tipo estructurado por transición — justificado porque no hay transiciones fijas que tipificar).

**Endpoint**: se reemplaza `POST /api/tickets/{id}/task-transition` (trigger fijo) por
`PATCH /api/tickets/{id}/status` con body `{"status": "<uno de los 10>", "comment": "..."}` —
rechaza con 409 `not_a_task` si el registro es un Ticket puro (que sigue usando exclusivamente
los endpoints de acción ya existentes: `/assign`, `/comments`, `/testing`, `/resolution`,
`/close`, `/cancel`).

**Alternativas descartadas**:
- Extender `ticket_fsm.py` con un modo "libre" bifurcado por `record_type`: descartado — mezclar
  una máquina de estados estricta con un modo sin restricciones en el mismo archivo es más
  frágil que un servicio separado y pequeño (mismo razonamiento que llevó a `task_fsm.py`
  separado en `008`, Decisión 2 de su research.md).
- Mantener `task_fsm.py` pero ampliarlo a 10 estados con una `Machine` "todos contra todos":
  descartado — `python-transitions` no aporta valor sobre una validación de pertenencia a lista,
  y una `Machine` de 90 arcos es puro ruido de mantenimiento.

## Decisión 2 — Lista de tareas: tabla `task_lists` real (reemplaza `list_name` de texto libre)

**Decisión**: tabla nueva `task_lists` (Nivel 3 de la jerarquía, `constitution.md`):
`id, project_id (FK projects.id), name (TEXT NOT NULL), position (INT), created_at, updated_at`.
`tickets` gana `list_id (FK task_lists.id, NULLABLE)` — reemplaza `list_name`. Se mantiene la
columna `list_name` en la tabla física (sin `DROP COLUMN`, ver Decisión 4 de migración) hasta
confirmar que ninguna vista depende de ella, pero deja de escribirse/leerse desde el código nuevo.

Endpoints nuevos (`backend/api/routes/task_lists.py`, mismo patrón que `client_contacts.py` de la
spec `007`): `GET /api/projects/{id}/task-lists`, `POST /api/projects/{id}/task-lists`,
`PATCH /api/task-lists/{id}`. Sin `DELETE` en esta fase (Edge Case del spec: eliminar una Lista
con Tareas se resuelve más adelante — no es un FR de esta spec, se documenta como límite
conocido).

**Alternativa descartada**: seguir con `list_name` de texto libre y solo agregar de-duplicación
en frontend: descartado explícitamente por el usuario, que pidió un desplegable izquierdo
administrable (`docs/mockup.html`), no una lista derivada de valores de texto.

## Decisión 3 — Subtarea: mismo registro `tickets`, autorreferencial vía `parent_task_id`

**Decisión**: columna nueva `tickets.parent_task_id` (`UUID`, `FK tickets.id`, `NULLABLE`). Una
Subtarea es una fila de `tickets` con `parent_task_id` apuntando a su Tarea padre — reutiliza
100% del modelo de Tarea (estado, comentarios, `assignee_id`, campos de clasificación,
`list_id` heredado del padre en el momento de creación, sin `list_id` propio editable). El
`record_type_id` de una Subtarea es el mismo "Tarea" — no se crea un tercer valor de catálogo
"Subtarea", porque a nivel de datos y de FSM se comporta idéntico (FR-014); solo la UI la
distingue por tener `parent_task_id` no nulo.

**Restricción de profundidad (FR-016)**: `TicketService.validate_create()` rechaza con
`TicketBusinessError("nested_subtask_not_allowed", ...)` si `parent_task_id` apunta a un ticket
que ya tiene su propio `parent_task_id` no nulo (evita Nivel 6).

**Alternativa descartada**: tabla `subtasks` separada — descartado por el mismo criterio que
"Tarea reutiliza `tickets`" del roadmap original (spec `008`): duplicar el modelo completo
(estado, comentarios, asignación, tiempo) en una tabla paralela es la complejidad que la
constitución ya evitó una vez.

## Decisión 4 — Migración de datos: `list_name` → `task_lists`, estados 4→10

**Contexto**: la migración `023` de la spec `008` ya está aplicada en el entorno de desarrollo,
con Tareas reales creadas usando `pendiente`/`en_progreso`/`hecha`/`cancelado` y `list_name` de
texto libre. FR-012 y FR-013 exigen migrar esos datos sin pérdida.

**Decisión**: migración `024_task_lists_and_subtasks.py`:
1. Crea `task_lists` y las columnas `tickets.list_id`, `tickets.parent_task_id`.
2. **Backfill de Listas**: `INSERT INTO task_lists (project_id, name) SELECT DISTINCT project_id,
   list_name FROM tickets WHERE list_name IS NOT NULL AND record_type_id = <id de 'Tarea'>` — una
   fila de `task_lists` por combinación única `(project_id, list_name)` ya usada.
3. **Backfill de `list_id`**: `UPDATE tickets SET list_id = task_lists.id FROM task_lists WHERE
   tickets.list_name = task_lists.name AND tickets.project_id = task_lists.project_id`.
4. **Migración de estados**: `UPDATE tickets SET status = CASE status WHEN 'pendiente' THEN
   'nuevo' WHEN 'en_progreso' THEN 'en_ejecucion' WHEN 'hecha' THEN 'cerrado' ELSE status END
   WHERE record_type_id = <id de 'Tarea'>` (mapeo ya acordado en Assumptions del spec: Pendiente→
   Nuevo, En progreso→En Ejecución, Hecha→Cerrado; Cancelada ya comparte valor `cancelado` con
   Ticket desde `023`, sin cambio).
5. Actualiza el CHECK `ck_tickets_status` — vuelve a los 10 valores originales de `011`, retira
   `pendiente`/`en_progreso`/`hecha` del CHECK (ya no son necesarios tras el backfill del punto 4).

**Riesgo aceptado**: es una migración de datos, no reversible de forma trivial (un `downgrade()`
no puede reconstruir qué Tareas estaban en `pendiente` vs `en_progreso` una vez colapsadas a
`nuevo`/`en_ejecucion`). Se documenta explícitamente en el docstring de la migración, mismo
criterio que otras migraciones de datos ya aplicadas en el proyecto (p. ej. `013_dynamic_record_type.py`).

## Decisión 5 — Comentario obligatorio de Tarea: reutilizar el tipo `comentario_interno`

**Decisión**: el comentario que documenta cada cambio de estado de Tarea (FR-005) usa el tipo
`comentario_interno`, ya existente en `COMMENT_TYPES` desde la Fase 1 y ya con visibilidad
`internal` — no se agrega un tipo nuevo. Este tipo ya es de propósito general (no está atado 1:1
a una transición de `ticket_fsm.py`, a diferencia de `confirmacion_atencion` o
`solicitud_cierre`), por lo que reutilizarlo no viola el espíritu del Principio VI (los tipos
siguen siendo datos estructurados, no texto libre sin clasificar) ni requiere tocar el catálogo.

**Comentarios simples sin cambio de estado (US5/FR-018)**: mismo tipo `comentario_interno`, sin
fila en `ticket_status_transitions` (solo se inserta esa fila cuando hay cambio de estado real).

## Decisión 6 — Kanban: la Tarea aparece "gratis" una vez que comparte estados; solo cambia el drag

**Contexto**: `frontend/src/pages/KanbanPage.tsx` ya carga tarjetas vía `ticketService.list({status:
[status], ...})` **sin filtrar por `record_type_id`** — hoy una Tarea no aparece porque sus
estados (`pendiente`/`en_progreso`/`hecha`) no están en `BOARD_STATUSES`. En cuanto la Decisión 4
migre sus estados al catálogo de 10 valores, las Tareas **ya aparecerán automáticamente** en las
columnas del Kanban sin tocar `load()` (FR-007 queda mayormente resuelto por la Decisión 4).

**Lo que sí cambia**: `handleDragEnd` usa hoy `getKanbanTransition(from, to)`
(`frontend/src/config/kanbanTransitions.ts`), que solo conoce los triggers fijos de
`ticket_fsm.py` y abre un modal de comentario *tipificado* según la transición. Para una tarjeta
de Tarea, el mismo `onDragEnd` debe detectar `record_type === 'Tarea'` (nuevo campo `record_type`
en `TicketListItem`, ya resuelto vía `related_from`/swagger existente) y, en vez de consultar
`getKanbanTransition`, abrir directamente el modal de comentario obligatorio y llamar
`ticketService.changeStatus(id, to, comment)` (Decisión 1) — cualquier columna destino es válida,
sin chequeo de transición.

**Distinción visual**: cada tarjeta agrega un `Tag` pequeño ("Tarea"/"Ticket") — dato ya
disponible sin round-trip adicional si `TicketListItem` expone `record_type` (nombre resuelto,
mismo patrón que `related_from[].record_type` de la spec `008`).

## Decisión 7 — Fix de Registro de tiempo: ownership también por creador, no solo por asignación

**Contexto** (investigado en esta misma sesión, live contra Docker): `WorkSessionService
.assert_ticket_ownership()` (`backend/domain/services/work_session_service.py:35`) solo permite
registrar tiempo si `resource_id` coincide con `ticket.assignee_id` o aparece en
`tickets_repo.list_assignments(ticket.id)` (historial de Triage Push). Una Tarea auto-asignada a
su creador en la creación (spec `008`, Decisión 7 de su research.md) ya cumple esta condición
**si** el creador tiene un `Resource` vinculado — el 403 reproducido en la investigación previa
correspondía a un usuario sin `Resource` vinculado (dato de entorno, no un defecto de lógica). El
gap real que sí introduce esta spec: una **Subtarea** puede tener un `assignee_id` distinto al de
su Tarea padre (FR-015) y el creador de la Tarea padre —dueño natural del trabajo global— no
queda automáticamente habilitado para registrar tiempo sobre las Subtareas que él mismo creó pero
asignó a otra persona.

**Decisión**: `assert_ticket_ownership` gana un chequeo adicional, aplicable únicamente cuando
`ticket.record_type` es Tarea/Subtarea: además de `assignee_id` e historial de asignaciones,
permite si `resource_id` corresponde al `Resource` vinculado a `ticket.created_by` (el creador
del registro). Sin cambios de comportamiento para Ticket (FR-002 — no regresión): un Ticket
normal nunca se crea con asignación automática, así que este chequeo adicional no le abre ninguna
puerta nueva en la práctica, pero se restringe explícitamente por tipo de registro para no
ampliar el alcance de seguridad de Ticket sin necesidad.

**Alternativa descartada**: quitar la restricción de ownership por completo para Tarea (cualquier
recurso interno registra tiempo en cualquier Tarea): descartado — FR-002 exige explícitamente que
se siga rechazando a un recurso sin relación alguna con el registro.
