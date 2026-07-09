# Tasks: Listas de Tareas, Subtareas, ciclo de vida unificado y fix de Registro de tiempo

**Input**: Design documents from `specs/009-tareas-listas-subtareas/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos — mismo criterio que specs `007`/`008`: tests dirigidos a lo que cambia, no
toda la suite en cada tarea.

**Organización**: Tareas agrupadas por User Story para implementación y validación independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] fix de Registro de tiempo, [US2] ciclo de vida unificado + Kanban + campos de
  clasificación, [US3] Listas de tareas administrables, [US4] Subtareas, [US5] Comentarios simples

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): `python-transitions`
  se **deja de usar** para Tarea (se retira `task_fsm.py`, sin reemplazo por librería) — sin
  cambios en `backend/requirements.txt` ni `frontend/package.json` (ver research.md)

**Checkpoint**: sin cambios de dependencias.

---

## Phase 2: Foundational (bloqueante para las 5 historias)

**Nota**: sin la migración de esquema/datos y sin retirar `task_fsm.py`, ninguna historia puede
probarse de forma consistente — todas dependen del catálogo de 10 estados y de `task_lists`.

- [X] T002 Migración `backend/infra/migrations/versions/024_task_lists_and_subtasks.py`: crea
  tabla `task_lists` (`id, project_id FK, name, position, created_at, updated_at`), agrega
  `tickets.list_id` (FK `task_lists.id`) y `tickets.parent_task_id` (FK `tickets.id`,
  autorreferencial); backfill de Listas desde `list_name` distintos por `(project_id, list_name)`;
  backfill de `list_id` por join; migra `status` de Tarea (`pendiente→nuevo`,
  `en_progreso→en_ejecucion`, `hecha→cerrado`); recrea `ck_tickets_status` con los 10 valores
  originales de `011_create_tickets.py` (depende de T001)
- [X] T003 [P] `backend/domain/entities/task_list.py` nuevo: entidad `TaskList` (`id, project_id,
  name, position, created_at, updated_at`), sin FSM ni bloqueos de campo (depende de T002)
- [X] T004 [P] `backend/domain/entities/ticket.py`: `Ticket` += `list_id: Optional[uuid.UUID]`,
  `parent_task_id: Optional[uuid.UUID]`; retira `TASK_STATUSES`/`TASK_FINAL_STATUSES` y las
  entradas `FIELD_LOCKS["pendiente"]`/`["en_progreso"]`/`["hecha"]` propias de la spec `008` (Tarea
  vuelve a usar los `FIELD_LOCKS` por estado ya compartidos con Ticket) (depende de T002)
- [X] T005 [P] `backend/infra/models/task_list_model.py` nuevo: `TaskListModel` + `to_entity()`
  (depende de T003)
- [X] T006 [P] `backend/infra/models/ticket_model.py`: columnas `list_id`, `parent_task_id` +
  `to_entity()` (depende de T004)
- [X] T007 `backend/infra/repositories/task_list_repo.py` nuevo: `create()`, `list_by_project(
  project_id)` (con `task_count` vía subquery), `update()` (depende de T005)
- [X] T008 `backend/infra/repositories/ticket_repo.py`: `create()` incluye `list_id=ticket.list_id,
  parent_task_id=ticket.parent_task_id`; `list_subtasks(parent_task_id)` nuevo (`WHERE
  parent_task_id = :id`) (depende de T006)
- [X] T009 Retirar `backend/domain/fsm/task_fsm.py` (eliminar archivo) y el endpoint
  `POST /api/tickets/{id}/task-transition` de `backend/api/routes/tickets.py` (depende de T004)
- [X] T010 `backend/domain/services/ticket_service.py`: `free_transition_task(ticket, new_status,
  comment_body, actor_id, tickets_repo, comments_repo)` nuevo (valida `new_status in STATUSES`,
  exige `comment_body`, crea `Comment` tipo `comentario_interno`, inserta fila en
  `ticket_status_transitions`, actualiza `status`); `PATCHABLE_FIELDS` retira `list_name`, agrega
  `list_id`; `validate_create`/`validate_patch` validan que `list_id` pertenezca al mismo
  `project_id` (409 `list_mismatch`) (depende de T004, T008, T009)
- [X] T011 `backend/domain/services/task_list_service.py` nuevo: `validate_create` (`name` no
  vacío), `resolve_position` (siguiente posición libre del Proyecto) (depende de T007)
- [X] T012 [P] `frontend/src/types/ticket.ts`: retira `TaskTrigger`/`TASK_TRIGGER_LABELS`;
  `TicketListItem` += `list_id`, `record_type`, `parent_task_id`; `TicketDetail` += `list_id`,
  `list: {id, name} | null`, `parent_task_id`, `subtasks: TicketListItem[]`
- [X] T013 [P] `frontend/src/types/taskList.ts` nuevo: interfaz `TaskList`
  (`id, project_id, name, position, task_count`)
- [X] T014 `frontend/src/services/ticketService.ts`: retira `taskTransition()`; agrega
  `changeStatus(id, status, comment)` → `PATCH /api/tickets/{id}/status` (depende de T012)
- [X] T015 `frontend/src/services/taskListService.ts` nuevo: `listByProject(projectId)`,
  `create(projectId, name)`, `update(id, data)` (depende de T013)

**Checkpoint**: migración `024` aplicada, `task_fsm.py` retirado, `task_lists` operativa a nivel
de dominio/infra, tipos y servicios base del frontend listos — las 5 historias pueden arrancar.

---

## Phase 3: User Story 1 — Fix de Registro de tiempo (Priority: P1) 🎯 MVP

**Goal**: un recurso puede registrar tiempo sobre una Tarea/Subtarea que creó o que tiene
asignada, sin exigir el historial formal de asignaciones de Triage (que solo aplica a Ticket).
**Independent Test**: Escenario 1 del quickstart.

- [X] T016 [US1] `backend/domain/services/work_session_service.py`:
  `assert_ticket_ownership()` gana un chequeo adicional — cuando `ticket.record_type` es
  Tarea/Subtarea, además de `assignee_id`/historial de asignaciones, permite si `resource_id`
  corresponde al `Resource` vinculado a `ticket.created_by` (vía `ResourceRepository
  .get_by_user_id`); sin cambio de comportamiento para Ticket (depende de Foundational T004)
- [X] T017 [P] [US1] Test dominio `backend/tests/domain/test_work_session_service.py`: creador de
  una Tarea/Subtarea (con `assignee_id` distinto) puede registrar tiempo; recurso sin relación
  sigue rechazado (403 `not_assigned`); Ticket sin cambio de comportamiento (depende de T016)
- [X] T018 [P] [US1] Test API `backend/tests/api/test_work_sessions_tasks.py`: `POST
  /api/work-sessions` sobre una Tarea propia (creador, no asignado formal) → `201`; sobre una
  Subtarea de otro asignado creada por el propio usuario → `201`; sobre un registro ajeno → `403`
  (depende de T016)

**Checkpoint US1**: Escenario 1 del quickstart ejecutable end-to-end.

---

## Phase 4: User Story 2 — Ciclo de vida unificado con Ticket (Priority: P1)

**Goal**: la Tarea usa el mismo catálogo de 10 estados que el Ticket, transición libre (cualquier
estado a cualquier estado) con comentario obligatorio, visible en el Kanban, con Tipo/Severidad/
Herramienta/Proceso/Nivel de escalamiento visibles y editables igual que en un Ticket.
**Independent Test**: Escenario 2 del quickstart.

- [X] T019 [US2] `backend/api/routes/tickets.py`: endpoint nuevo `PATCH /api/tickets/{id}/status`
  — body `{"status", "comment"}`, usa `ticket_service.free_transition_task()`, exige
  `tickets:transition` (mismo permiso ya usado por `/comments`/`/testing`/`/cancel` — corregido
  desde `tickets:edit` tras validación E2E: un Resolutor no tiene `edit` y es quien más usa este
  endpoint), 409 `not_a_task` si el registro es un Ticket puro (depende de Foundational T010)
- [X] T020 [US2] `backend/api/routes/tickets.py`: `_ticket_detail()`/`_ticket_detail_out` —
  `valid_actions` para Tarea/Subtarea pasa a ser los 10 estados menos el actual (en vez de los
  triggers de `task_fsm`); `ticket_type`/`severity`/`escalation_level` dejan de ocultarse/
  defaultearse silenciosamente y quedan expuestos y editables igual que en Ticket (depende de
  T019)
- [X] T021 [P] [US2] Test dominio `backend/tests/domain/test_ticket_service_free_transition.py`:
  transición válida desde cualquier estado a cualquier otro (incluye retroceso); rechazo sin
  `comment`; rechazo sobre un Ticket puro (depende de Foundational T010)
- [X] T022 [P] [US2] Test API `backend/tests/api/test_tickets_status_transition.py`: `PATCH
  /{id}/status` end-to-end (200, 400 sin comment, 403 sin permiso, 404, 409 `not_a_task`) (depende
  de T019)
- [X] T023 [US2] Frontend `frontend/src/components/tickets/TaskStatusChanger.tsx` nuevo: `Select`
  de los 10 estados + modal de comentario obligatorio, llama `ticketService.changeStatus` (depende
  de Foundational T014)
- [X] T024 [US2] Frontend `frontend/src/pages/TicketDetailPage.tsx`: reemplaza `<TaskActions/>`
  por `<TaskStatusChanger/>`; retira el filtrado `isTask` que ocultaba Tipo/Severidad/Nivel de
  escalamiento — quedan siempre visibles y editables (depende de T023)
- [X] T025 [US2] Eliminar `frontend/src/components/tickets/TaskActions.tsx` (retirado, spec `008`)
  (depende de T024)
- [X] T026 [US2] Frontend `frontend/src/pages/KanbanPage.tsx`: tarjeta agrega `Tag` con
  `record_type` ("Ticket"/"Tarea"); `handleDragEnd` detecta Tarea/Subtarea y, en vez de
  `getKanbanTransition`, abre directamente el modal de comentario obligatorio y llama
  `ticketService.changeStatus(id, to, comment)` sin validar transición — cualquier columna
  destino es válida (depende de Foundational T012, T014)

**Checkpoint US2**: Escenario 2 del quickstart ejecutable end-to-end.

---

## Phase 5: User Story 3 — Listas de tareas administrables (Priority: P1)

**Goal**: crear y administrar Listas dentro de un Proyecto (sidebar tipo `docs/mockup.html`,
`s-lista`) y asociar una Tarea a una Lista del mismo Proyecto.
**Independent Test**: Escenario 3 del quickstart.

- [X] T027 [US3] `backend/api/routes/task_lists.py` nuevo: `GET /api/projects/{id}/task-lists`,
  `POST /api/projects/{id}/task-lists`, `PATCH /api/task-lists/{id}` — protegidos por
  `tickets:create` (sin permiso nuevo — corregido desde `tickets:edit` tras validación E2E: un
  Resolutor puede crear Tareas pero no tiene `edit`, y necesita organizarlas en Listas) (depende
  de Foundational T011)
- [X] T028 [US3] Registrar el namespace `task_lists` en la app Flask (`backend/api/__init__.py` o
  equivalente donde se registran los demás namespaces) (depende de T027)
- [X] T029 [P] [US3] Test API `backend/tests/api/test_task_lists.py`: crear/listar (con
  `task_count` correcto)/renombrar una Lista; `POST` a un Proyecto inexistente → 404 (depende de
  T027)
- [X] T030 [US3] Frontend `frontend/src/pages/ProjectListsPage.tsx` nuevo: sidebar de Listas de un
  Proyecto con conteo, crear Lista nueva — según `docs/mockup.html` pantalla `s-lista` (depende de
  Foundational T015)
- [X] T031 [US3] Wire de ruta/navegación para `ProjectListsPage` en `frontend/src/App.tsx` +
  `frontend/src/config/navigation.tsx` (depende de T030)
- [X] T032 [US3] Frontend `frontend/src/pages/TicketsPage.tsx`: campo "Lista" pasa de `Input` de
  texto libre a `Select` poblado con `taskListService.listByProject(project_id)` (depende de
  Foundational T015)
- [X] T033 [US3] Frontend `frontend/src/pages/TicketDetailPage.tsx`: campo "Lista" en la
  Descriptions pasa de `Input` a `Select` acotado al Proyecto del registro (depende de Foundational
  T015, T024 mismo archivo)
- [X] T034 [US3] Frontend `frontend/src/pages/MyTasksPage.tsx`: agrupa por el nombre de Lista
  resuelto (`item.list_id` → nombre vía `task_lists`, ya vine resuelto en `TicketListItem.
  list_name` — sin round-trip adicional) en vez de agrupar por el `list_name` de texto libre
  (depende de Foundational T015)

**Checkpoint US3**: Escenario 3 del quickstart ejecutable end-to-end.

---

## Phase 6: User Story 4 — Subtareas con Encargado y Estado propios (Priority: P2)

**Goal**: agregar Subtareas dentro de una Tarea, cada una con su propio Encargado, estado
(catálogo unificado) y comentarios, sin heredar el estado de la Tarea padre.
**Independent Test**: Escenario 4 del quickstart.

- [X] T035 [US4] `backend/domain/services/ticket_service.py`: `validate_create` valida
  `parent_task_id` — DEBE referenciar una Tarea (no un Ticket, no otra Subtarea) del mismo
  `client_id`/`project_id`; rechaza con 409 `nested_subtask_not_allowed` si el padre ya tiene su
  propio `parent_task_id` (depende de Foundational T010)
- [X] T036 [US4] `backend/api/routes/tickets.py`: `POST /api/tickets` acepta `parent_task_id`;
  `_ticket_detail()` expone `subtasks` (vía `TicketRepository.list_subtasks`, solo para Tarea
  Nivel 4, vacío para Ticket y Subtarea) (depende de T035, Foundational T008)
- [X] T037 [P] [US4] Test API `backend/tests/api/test_tickets_subtasks.py`: crear Subtarea con
  Encargado distinto del padre; Subtarea visible en `subtasks[]` del padre; Subtarea anidada
  dentro de otra Subtarea → 409 `nested_subtask_not_allowed`; cambiar estado de una Subtarea no
  afecta el estado del padre (depende de T036)
- [X] T038 [US4] Frontend `frontend/src/components/tickets/SubtaskList.tsx` nuevo: filas anidadas
  bajo una Tarea (título, avatar del Encargado, badge de estado, contador de comentarios) según
  `docs/mockup.html` (depende de Foundational T012)
- [X] T039 [US4] Frontend `frontend/src/pages/TicketDetailPage.tsx`: reemplaza la tarjeta
  "Subtareas — Próximamente" por `<SubtaskList/>` + acción "Agregar subtarea" (depende de T038,
  T033 mismo archivo)

**Checkpoint US4**: Escenario 4 del quickstart ejecutable end-to-end.

---

## Phase 7: User Story 5 — Comentarios en Tarea y Subtarea (Priority: P2)

**Goal**: agregar comentarios simples (sin cambio de estado) a una Tarea o Subtarea, visibles en
su propio historial.
**Independent Test**: Escenario 5 del quickstart.

- [X] T040 [US5] Frontend `frontend/src/pages/TicketDetailPage.tsx`: agrega `<CommentThread/>` +
  `<CommentComposer/>` debajo de `<TaskStatusChanger/>` para Tarea/Subtarea (antes reemplazado
  por completo, spec `008`) (depende de T039 mismo archivo)
- [X] T041 [US5] Frontend `frontend/src/components/tickets/CommentComposer.tsx`: cuando
  `isTask`, restringe el selector de tipo de comentario a `comentario_interno` únicamente (oculta
  los tipos tipificados de Ticket que no aplican) (depende de T040)
- [X] T042 [P] [US5] Test API `backend/tests/api/test_tickets_subtasks.py` (extiende T037):
  comentario simple en una Tarea no genera fila en `ticket_status_transitions`; comentario en una
  Subtarea aparece solo en su propio historial, no en el de la Tarea padre (depende de T036)

**Checkpoint US5**: las 5 historias funcionan de forma independiente.

---

## Phase 8: Polish y validación transversal

- [X] T043 [P] Swagger revisado: `_ticket_input`/`_ticket_detail_out` (`list_id`, `parent_task_id`,
  `subtasks`), `PATCH /{id}/status` y `task_lists` documentados con sus respuestas según
  `contracts/`
- [X] T044 Ejecutar `quickstart.md` (Escenarios 0-6) contra Docker real: migración de datos,
  registro de tiempo por creador, transición libre + Kanban, Listas administrables, Subtareas con
  Encargado propio, comentarios simples, regresión de Ticket sin cambios
- [X] T045 [P] Validación dirigida (no la suite completa durante desarrollo) — WORKDIR del
  contenedor ya es `/repo/backend`: `docker exec sywork_backend pytest
  tests/domain/test_work_session_service_tasks.py tests/domain/test_ticket_service_free_transition.py
  tests/api/test_tickets_status_transition.py tests/api/test_task_lists.py
  tests/api/test_tickets_subtasks.py tests/api/test_work_sessions_tasks.py -v`;
  `cd frontend && npx tsc -b` → sin errores; suite completa `docker exec sywork_backend pytest -q`
  (332 passed) como cierre del Polish

**Checkpoint Final**: quickstart completo en verde, tests dirigidos en verde, suite completa sin
regresión (332/332 tests, `tsc -b` sin errores).

**Bugs encontrados y corregidos durante la validación E2E** (no estaban en el diseño original,
descubiertos recién al probar como Resolutor real en el navegador — mismo patrón que la
Decisión 7 de la spec `008`):
1. `PATCH /api/tickets/{id}/status` exigía `tickets:edit`; un Resolutor (quien más lo usa, sobre
   sus propias Tareas) solo tiene `tickets:transition` → 403 permanente. Corregido a
   `tickets:transition`, mismo criterio que `/comments`, `/testing`, `/cancel`.
2. `task_lists.py` y la ruta `/projects/:id/lists` exigían `tickets:edit`; un Resolutor que crea
   Tareas no podía siquiera ver la pantalla de Listas para organizarlas. Corregido a
   `tickets:create`.
3. Fix real en `TicketService.free_transition_task()`: capturaba `ticket.status` como
   `from_status` DESPUÉS de llamar `tickets_repo.update_fields()` — inofensivo con el repositorio
   real (que no muta el objeto en memoria) pero frágil; se captura ahora en una variable local
   antes de la actualización.
4. Test `test_record_type_catalog.py::test_create_ticket_rejects_tarea_record_type` (Fase 1)
   había quedado obsoleto desde la spec `008` (afirmaba que "Tarea" se rechazaba) sin que nadie
   lo actualizara — corregido a `test_create_ticket_with_tarea_record_type_is_allowed`.

---

## Dependencies & Execution Order

```
Phase 1 (T001)
→ Phase 2 (T002 → T003/T004∥ → T005/T006∥ → T007,T008 → T009 → T010,T011; T012/T013∥ → T014,T015)
→ Phase 3/US1 (T016 → T017∥, T018∥)
→ Phase 4/US2 (T019 → T020; T021∥; T022∥; T023 → T024 → T025; T026)
→ Phase 5/US3 (T027 → T028 → T029∥; T030 → T031; T032; T033 [mismo archivo que T024]; T034)
→ Phase 6/US4 (T035 → T036 → T037∥; T038 → T039 [mismo archivo que T033])
→ Phase 7/US5 (T040 [mismo archivo que T039] → T041; T042∥)
→ Phase 8 (T043∥, T044, T045∥)
```

- US1, US2 y US3 son P1 — las tres deben cerrar antes de considerar el MVP de esta spec completo,
  pero son lógicamente independientes entre sí (US1 no toca `TicketDetailPage.tsx`; US2 y US3
  comparten ese archivo por conveniencia de UI, no por dependencia de dominio).
- US4 depende de que `parent_task_id` exista desde Foundational, pero solo se vuelve útil una vez
  que US2 (estado compartido) y US3 (Lista heredada del padre) ya están, por eso se secuencia
  después.
- US5 depende de que `TicketDetailPage.tsx` ya tenga el layout de US4 (Subtareas) para no
  pisarse — no hay dependencia lógica real entre "comentarios" y "subtareas", solo de archivo
  compartido.

## Parallel Example: Foundational

```bash
# Tras T002 (migración):
Task: "Entidad backend/domain/entities/task_list.py"     # T003
Task: "Entidad backend/domain/entities/ticket.py"         # T004

# Tras T003/T004:
Task: "Modelo backend/infra/models/task_list_model.py"    # T005
Task: "Modelo backend/infra/models/ticket_model.py"       # T006
```

## Parallel Example: User Story 2

```bash
# Tras Foundational T010 (free_transition_task):
Task: "Test dominio backend/tests/domain/test_ticket_service_free_transition.py"  # T021

# Tras T019 (endpoint PATCH /status):
Task: "Test API backend/tests/api/test_tickets_status_transition.py"              # T022
```

---

## Implementation Strategy

1. **MVP = Phase 1 + Phase 2 + US1 + US2 + US3** (las tres P1): fix de registro de tiempo, ciclo
   de vida unificado visible en Kanban, y Listas reales administrables — cubre la reversión
   completa de las Decisiones 1 y 2 de la spec `008` más el defecto reportado.
2. Incremento 1: US4 (Subtareas) — depende de que Foundational y US2/US3 ya estén (mismo estado
   compartido, mismo campo de Lista heredado).
3. Incremento 2: US5 (Comentarios) — depende de que el layout de US4 ya esté en
   `TicketDetailPage.tsx`.
4. Cada checkpoint valida su escenario del quickstart antes de avanzar.
5. Riesgo concentrado en T002 (migración de datos irreversible de forma trivial — ver research.md
   Decisión 4): validar el backfill en un entorno con datos reales de la spec `008` antes de
   avanzar a cualquier historia.

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- [Story] mapea la tarea a su user story para trazabilidad
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
