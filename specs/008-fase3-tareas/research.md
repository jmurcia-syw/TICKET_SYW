# Research: Fase 3 — Manejo de Tareas

Todas las decisiones parten de inspeccionar el código ya existente (fases 1-2.2) para reutilizar
al máximo, en línea con el Principio V (cero dependencias/estructuras nuevas no justificadas) y
con el patrón ya usado en la spec `007` (reutilizar infraestructura reservada de fases previas).

## Decisión 1 — Cómo evitar tocar `ticket_type`/`priority`/`severity` (NOT NULL sin default)

**Contexto**: FR-002 exige que el formulario de Tarea no obligue a completar tipo de incidente,
severidad, herramienta ni proceso. Las columnas `ticket_type` y `severity` son `NOT NULL` sin
`server_default` en el esquema (`011_create_tickets.py`) — relajarlas a nullable implicaría una
migración de columna + ajustar el CHECK de cada una + tocar el tipado de la entidad `Ticket`
(hoy `ticket_type: str` y `severity: str`, no `Optional`), con impacto sobre todo el código que
ya asume que un Ticket siempre tiene esos tres valores (filtros, Swagger, tests existentes).

**Decisión**: **No tocar el esquema.** Reutilizar exactamente el patrón que ya existe para el
alta simplificada de un Encargado en `POST /api/tickets` (`backend/api/routes/tickets.py:447`):
cuando `is_encargado` es `true`, el backend ya defaultea silenciosamente
`ticket_type, priority, severity = "incident", "medium", "s3"` sin pedírselos al usuario. Para
una Tarea se aplica el mismo default silencioso (branch nuevo junto al de `is_encargado`, no en
reemplazo). El usuario nunca ve esos campos en el formulario de Tarea; el backend los completa.

**Alternativas consideradas**:
- Migración para hacer `ticket_type`/`severity` nullable: descartada — mayor blast radius (CHECK
  constraints, tipado de la entidad, código que itera esos campos) para un beneficio que el
  default silencioso ya cubre sin tocar una sola tabla existente.
- Tabla `tasks` separada de `tickets`: descartada explícitamente por el propio roadmap ("misma
  tabla que tickets").

## Decisión 2 — Ciclo de vida de la Tarea: FSM nueva y separada

**Decisión** (confirmada con el usuario en `/speckit-specify`): FSM propia y simple —
**Pendiente → En progreso → Hecha**, con **Cancelada** alcanzable desde Pendiente o En progreso,
y reapertura (Hecha o Cancelada → En progreso) en cualquier momento (SC-006). Vive en
`backend/domain/fsm/task_fsm.py`, mismo patrón que `ticket_fsm.py` (usa `python-transitions`,
Principio V — sin librería nueva), pero **completamente independiente**: no comparte
`TRANSITIONS` ni triggers con `ticket_fsm.py`. `ticket_fsm.py` sigue rigiendo únicamente los
registros con `record_type = 'Ticket'`.

**Nuevos valores de `status`**: se agregan `pendiente`, `en_progreso`, `hecha` al CHECK
`ck_tickets_status` (migración nueva). Se **reutiliza** el valor `cancelado` ya existente (mismo
significado conceptual para ambos tipos de registro — no se crea `cancelada` como valor
duplicado). El estado inicial de una Tarea es `pendiente` (el de un Ticket sigue siendo `nuevo`).

**Por qué una FSM separada y no extender `ticket_fsm.py`**: los 10 estados del Ticket están
acoplados a comentarios tipificados orientados a cliente (`solicitud_informacion`,
`solicitud_cierre`, etc. — Principio VI) que no tienen sentido para trabajo interno sin cliente
esperando respuesta (ver spec, FR-009 y SC-006: "sin ningún paso intermedio obligatorio de tipo
Ticket"). Mezclar ambos flujos en una sola máquina de estados obligaría a bifurcar cada
transición por `record_type`, más frágil que dos máquinas independientes y pequeñas.

**Endpoint nuevo**: `POST /api/tickets/{id}/task-transition` con body `{"trigger": "start" |
"complete" | "cancel" | "reopen"}` — mismo patrón que los endpoints de acción ya existentes
(`/cancel`, `/testing`, `/resolution`, `/close`), pero **sin exigir comentario obligatorio** (a
diferencia de `/cancel` de Ticket, que sí lo exige) porque SC-006 pide explícitamente que no haya
pasos intermedios de tipo Ticket. Rechaza con 409 si el registro no es de tipo Tarea (un Ticket
sigue usando exclusivamente su propia FSM y endpoints ya existentes).

## Decisión 3 — "Lista" como campo de texto libre (no entidad nueva)

**Decisión** (confirmada con el usuario): columna nueva `tickets.list_name` (`TEXT`, `NULL`able,
sin tabla ni FK). Una Tarea sin `list_name` cae en el grupo "Sin lista" — agrupamiento resuelto
en el frontend (`MyTasksPage.tsx`) agrupando el array ya cargado por ese campo, sin nuevo
endpoint de agregación (volumen esperado por usuario es bajo — no justifica `GROUP BY` en
servidor por ahora). Solo aplica conceptualmente a Tareas, pero no se restringe a nivel de
esquema (un Ticket con `list_name` no se rompe, simplemente no se usa en ninguna pantalla).

**Alternativa descartada**: tabla `task_lists` (Nivel 3 de la jerarquía de 5 niveles descrita en
`constitution.md`) — es la base "correcta" a largo plazo si se necesitan subtareas u orden
explícito de listas, pero el usuario decidió explícitamente diferir esa complejidad hasta que el
uso real la justifique (ver Assumptions del spec).

## Decisión 4 — "Registro relacionado": cerrar el gap de validación por Cliente

**Contexto**: `related_ticket_id` ya existe desde la migración `011` y ya se acepta en
`POST`/`PATCH /api/tickets`, pero **ninguna de las dos rutas valida hoy que el registro
relacionado pertenezca al mismo Cliente** — solo se valida que exista
(`ticket_service.py:70-71` en `validate_create`) o que no sea el propio registro
(`validate_patch:132-135`). Es un gap real de FR-005 (spec `008`), descubierto al planificar,
igual que el gap de permiso de `client_contacts.py` que se corrigió durante la spec `007`.

**Decisión**: agregar la validación de mismo-cliente en `validate_create` y `validate_patch`
(mismo criterio ya usado para `client_contact_id` — 409 `related_ticket_mismatch`). Como
`related_ticket_id` ya es válido para Tickets desde la Fase 1 (aunque nunca se expuso en UI), la
corrección aplica a **ambos** tipos de registro, no solo a Tareas.

**Relación inversa**: el detalle de un Ticket/Tarea debe listar quién lo referencia como
"Registro relacionado" (FR-006). Nuevo método `TicketRepository.list_related_from(ticket_id)`
(consulta simple `WHERE related_ticket_id = :id`, sin migración — el índice implícito de FK ya
cubre esta consulta a la escala esperada) expuesto como campo nuevo `related_from` en
`_ticket_detail()`.

## Decisión 5 — Quién puede crear Tareas: reutilizar `tickets:create`

**Decisión** (confirmada con el usuario): sin permiso nuevo. La creación de una Tarea pasa por el
mismo `POST /api/tickets` ya protegido por `@require_permission("tickets", "create")` — no se
crea `tasks:create` en la matriz de Roles y Permisos. Un Encargado sigue sin poder crear Tareas
porque su flujo de autoservicio (branch `is_encargado`) nunca ofrece "Tarea" como tipo de
registro — mismo mecanismo de bloqueo que ya impide `record_type_id` fuera de "Ticket" hoy
(`resolve_record_type`), solo que ahora el bloqueo se mueve de "todo excepto Ticket" a "todo
excepto Ticket/Tarea, y Tarea nunca se ofrece a un Encargado".

## Decisión 7 — Autoasignación al crear una Tarea (descubierta durante la implementación)

**Contexto**: `TicketRepository.create()` nunca asignaba `assignee_id` por diseño — un Ticket
nace sin asignar y llega a un resolutor recién por Triage Push (`POST /{id}/assign`), deliberado
desde la Fase 1. Al implementar y probar US1 end-to-end contra Docker real, una Tarea recién
creada por un usuario sin asignación explícita **nunca aparecía en su propio "Mis Tareas"**
(que filtra estrictamente por `assignee_id = recurso del usuario actual`) — quedaba huérfana y
el caso de uso central de la Historia 1 ("crear y gestionar tu propio trabajo") no se cumplía.

**Decisión**: al crear una Tarea (no un Ticket), el backend resuelve el `Resource` vinculado al
usuario creador (`ResourceRepository.get_by_user_id`, mismo patrón ya usado en `_actor_context`)
y la autoasigna (`assignee_id`) — sin pasos manuales. Un Ticket normal sigue sin asignación
automática (Triage Push intacto). Si el creador no tiene un `Resource` vinculado, la Tarea nace
sin asignar (mismo comportamiento que hoy, sin romper nada).

**Cambio de código no listado originalmente en plan.md**: `TicketRepository.create()` no incluía
`assignee_id` en la construcción de `TicketModel` pese a que la entidad `Ticket` ya tenía ese
campo desde la Fase 1 — se agregó, con test dedicado
(`test_create_task_auto_assigns_creators_own_resource`).

## Decisión 6 — UI de creación: mismo modal, campos condicionales (no un formulario aparte)

**Decisión**: en `TicketsPage.tsx`, en vez de un modal nuevo, se agrega un control (Segmented o
Radio) "Ticket / Tarea" al inicio del formulario ya existente; según la elección, se
ocultan/muestran los campos de clasificación de incidente (tipo, severidad, herramienta, proceso,
escalamiento) y aparece el campo "Lista" (texto libre, opcional). Cliente, Proyecto, título,
descripción y "Registro relacionado" son comunes a ambos. Evita duplicar el modal completo y la
lógica de carga de Cliente/Proyecto/Encargado ya construida en Fase 2.2.

**Alternativa descartada**: modal separado "Nueva Tarea" — más código duplicado (carga de
clientes/proyectos, validaciones) para un beneficio de UX marginal frente a un control
condicional dentro del mismo formulario.
