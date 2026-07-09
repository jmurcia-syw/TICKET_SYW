# Tasks: Fase 3 — Manejo de Tareas

**Input**: Design documents from `specs/008-fase3-tareas/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos — el plan.md ya compromete 3 archivos de test nuevos (mismo criterio que
Fases 1/2/2.1/2.2: tests dirigidos a lo que cambia, no toda la suite en cada tarea).

**Organización**: Tareas agrupadas por User Story para implementación y validación independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] crear y gestionar el ciclo de vida básico de una Tarea, [US2] Registro
  relacionado, [US3] agrupar por Lista en Mis Tareas

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): `python-transitions`
  ya aprobado y en uso por `ticket_fsm.py`, Ant Design 5 (`Segmented`/`Select`) ya cubre la UI
  condicional; sin cambios en `backend/requirements.txt` ni `frontend/package.json` (ver
  research.md)

**Checkpoint**: sin cambios de dependencias.

---

## Phase 2: Foundational (bloqueante para las 3 historias)

**Nota**: sin el ajuste de `resolve_record_type`, ninguna Tarea puede crearse — ninguna historia
puede probarse sin este bloque.

- [X] T002 Migración `backend/infra/migrations/versions/023_tasks_status_list.py`: agrega
  `tickets.list_name` (TEXT, nullable) y amplía el CHECK `ck_tickets_status` con `pendiente`,
  `en_progreso`, `hecha` (reutiliza `cancelado` ya existente) (depende de T001)
- [X] T003 [P] `backend/domain/entities/ticket.py`: `STATUS_LABELS` extendido con los 4 estados
  de Tarea; `FIELD_LOCKS["hecha"] = {"title","description","priority","list_name",
  "related_ticket_id"}`; `FIELD_LOCKS["pendiente"]`/`FIELD_LOCKS["en_progreso"]` = `set()` (depende
  de T002)
- [X] T004 [P] `backend/infra/models/ticket_model.py`: columna `list_name` + `to_entity()`
  (depende de T002)
- [X] T005 `backend/infra/repositories/ticket_repo.py`: `create()` incluye `list_name=ticket.
  list_name` (`update_fields()` ya es genérico vía `setattr`, sin cambios ahí) (depende de T004)
- [X] T006 `backend/domain/services/ticket_service.py`: `resolve_record_type` deja de rechazar
  el valor `"Tarea"` del catálogo (elimina el bloqueo `record_type_not_allowed` para ese caso);
  `PATCHABLE_FIELDS` += `"list_name"` (depende de T002)

**Checkpoint**: columna y estados nuevos en base de datos, entidad/modelo/repo listos, "Tarea" ya
es un `record_type_id` creable — las 3 historias pueden arrancar.

---

## Phase 3: User Story 1 — Crear y gestionar el ciclo de vida básico de una Tarea (P1) 🎯 MVP

**Goal**: crear un registro de tipo "Tarea" sin los campos de clasificación de incidente de un
Ticket, verlo distinguido en "Mis Tareas", y moverlo por su ciclo de vida propio (Pendiente → En
progreso → Hecha/Cancelada, con reapertura) sin ningún paso intermedio de tipo Ticket.
**Independent Test**: Escenarios 1 y 3 del quickstart.

- [X] T007 [US1] `backend/domain/fsm/task_fsm.py` nuevo: FSM independiente de `ticket_fsm.py`
  (`python-transitions`) con triggers `start` (pendiente→en_progreso), `complete`
  (en_progreso→hecha), `cancel` (pendiente|en_progreso→cancelado), `reopen`
  (hecha|cancelado→en_progreso) (depende de T003)
- [X] T008 [US1] `backend/api/routes/tickets.py`: `_ticket_input` swagger += `list_name`; en
  `POST`, nuevo branch para cuando `record_type_id` resuelve a "Tarea" — defaultea
  `ticket_type/priority/severity` silenciosamente (`"incident"/"medium"/"s3"`, mismo patrón ya
  usado para el alta de un Encargado) y fuerza `status` inicial `"pendiente"` (depende de T006)
- [X] T009 [US1] `backend/api/routes/tickets.py`: nuevo endpoint `POST /api/tickets/{id}/
  task-transition` — body `{"trigger": ...}`, usa `task_fsm.apply()`, exige `tickets:edit`
  (permiso ya existente), 409 `not_a_task` si el registro no es Tarea (depende de T007, T008)
- [X] T010 [US1] `backend/api/routes/tickets.py`: `_ticket_detail_out`/`_ticket_detail()`
  exponen `list_name` (depende de T008)
- [X] T011 [P] [US1] Test dominio `backend/tests/domain/test_task_fsm.py`: transiciones válidas
  desde cada estado, transición inválida (409), reapertura desde `hecha` y desde `cancelado`
  (depende de T007)
- [X] T012 [P] [US1] Test dominio `backend/tests/domain/test_ticket_service_tasks.py`:
  `resolve_record_type` acepta `"Tarea"`; sigue rechazando valores inactivos/inexistentes
  (depende de T006)
- [X] T013 [P] [US1] Test API `backend/tests/api/test_tickets_tasks.py`: `POST` crea una Tarea
  sin `ticket_type`/`priority`/`severity` en el body y nace en `"pendiente"`; `task-transition`
  mueve el estado según el trigger; `task-transition` sobre un Ticket → 409 `not_a_task`; un
  Encargado no puede crear una Tarea (depende de T008, T009)
- [X] T014 [US1] Frontend `frontend/src/types/ticket.ts`: `TicketStatus` += `'pendiente' |
  'en_progreso' | 'hecha'` (reutiliza `'cancelado'`); `STATUS_LABELS` extendido;
  `TicketFormData`/`TicketDetail` += `list_name?: string | null`
- [X] T015 [US1] Frontend `frontend/src/theme.ts`: `TICKET_STATUS_CHIP` += entradas para los 3
  estados nuevos de Tarea (depende de T014)
- [X] T016 [US1] Frontend `frontend/src/services/ticketService.ts`: `taskTransition(id, trigger)`
  nuevo, `POST /api/tickets/{id}/task-transition` (depende de T014)
- [X] T017 [US1] Frontend `frontend/src/pages/TicketsPage.tsx`: control Ticket/Tarea
  (`Segmented`) al inicio del formulario; oculta Tipo/Severidad/Herramienta/Proceso/Nivel cuando
  es Tarea (sin tocar Cliente/Proyecto/Encargado/título/descripción, ya construidos) (depende de
  T014)
- [X] T018 [US1] Frontend `frontend/src/pages/TicketDetailPage.tsx`: para una Tarea, controles de
  transición (Iniciar/Completar/Cancelar/Reabrir vía `taskTransition`) en vez de los comentarios
  tipificados de Ticket; oculta severidad/herramienta/proceso/escalamiento (depende de T014, T016)
- [X] T019 [US1] Frontend `frontend/src/pages/MyTasksPage.tsx`: distingue visualmente Tarea de
  Ticket en el listado (Tag/columna "Tipo") — el agrupamiento completo por lista llega en US3
  (depende de T014)

**Checkpoint US1**: Escenarios 1 y 3 del quickstart ejecutables end-to-end.

---

## Phase 4: User Story 2 — Registro relacionado (P2)

**Goal**: vincular una Tarea (o un Ticket) a un "Registro relacionado" del mismo Cliente, ver el
vínculo en ambos sentidos desde el detalle, y que el sistema rechace vínculos cruzados de
Cliente — corrige un gap real de la Fase 1 que hoy no valida esto para ningún tipo de registro.
**Independent Test**: Escenario 2 del quickstart.

- [X] T020 [US2] `backend/domain/services/ticket_service.py`: `validate_create`/`validate_patch`
  validan que `related_ticket_id` pertenezca al mismo `client_id` del registro (409
  `related_ticket_mismatch`) — aplica a Ticket y Tarea por igual (depende de T006, mismo archivo)
- [X] T021 [US2] `backend/infra/repositories/ticket_repo.py`: `list_related_from(ticket_id)`
  nuevo — `WHERE related_ticket_id = :id` (depende de T005, mismo archivo)
- [X] T022 [US2] `backend/api/routes/tickets.py`: `_ticket_detail_out`/`_ticket_detail()`
  exponen `related_from` (usa T021) (depende de T010, T021)
- [X] T023 [P] [US2] Test dominio (mismo archivo de T012): `validate_create`/`validate_patch`
  rechazan `related_ticket_id` de otro cliente, tanto para Ticket como para Tarea (depende de
  T020)
- [X] T024 [P] [US2] Test API (mismo archivo de T013): `POST`/`PATCH` rechazan Registro
  relacionado de otro cliente (409 `related_ticket_mismatch`); `GET` detalle expone
  `related_from` con los registros que referencian al actual (depende de T020, T022)
- [X] T025 [US2] Frontend `frontend/src/pages/TicketDetailPage.tsx`: campo "Registro relacionado"
  editable (`Select` acotado al Cliente del registro, mismo patrón ya usado para Encargado por
  Cliente en Fase 2.2) + sección "Referenciado por" (`related_from`) (depende de T014, T018,
  mismo archivo)

**Checkpoint US2**: Escenario 2 del quickstart ejecutable end-to-end.

---

## Phase 5: User Story 3 — Agrupar Tareas por Lista en Mis Tareas (P3)

**Goal**: escribir un nombre de lista en una Tarea y ver "Mis Tareas" agrupado por esas listas,
con "Sin lista" como grupo por defecto para las que no tienen una asignada.
**Independent Test**: Escenario 4 del quickstart.

- [X] T026 [US3] Frontend `frontend/src/pages/TicketsPage.tsx`: campo "Lista" (texto libre,
  opcional) visible solo cuando el control está en "Tarea" (depende de T017, mismo archivo)
- [X] T027 [US3] Frontend `frontend/src/pages/TicketDetailPage.tsx`: campo "Lista" editable en el
  detalle de una Tarea (bloqueado en `hecha`, ver `FIELD_LOCKS`) (depende de T018, T025, mismo
  archivo)
- [X] T028 [US3] Frontend `frontend/src/pages/MyTasksPage.tsx`: agrupa el listado por
  `list_name` ("Sin lista" por defecto para `null`); retira el texto "el agrupamiento por listas
  llega en Fase 3" (depende de T019, mismo archivo)

**Checkpoint US3**: Escenario 4 del quickstart ejecutable end-to-end — las 3 historias funcionan
independientemente.

---

## Phase 6: Polish y validación transversal

- [X] T029 [P] Swagger revisado: `_ticket_input`/`_ticket_detail_out` (`list_name`,
  `related_from`), nuevo endpoint `task-transition` documentado con sus respuestas
  400/403/404/409 según `contracts/tickets-delta.md`
- [X] T030 Ejecutado `quickstart.md` (Escenarios 1-5) contra Docker real: creación de Tarea sin
  clasificación, autoservicio de Encargado sin cambios, ciclo de vida completo (incluida
  reapertura), Registro relacionado cruzado rechazado (Ticket y Tarea), agrupamiento por lista,
  regresión de Ticket sin cambios de comportamiento
- [X] T031 [P] Validación dirigida únicamente (mismo criterio ya usado en las fases anteriores —
  NO correr la suite completa de pytest de forma masiva durante el desarrollo de cada tarea):
  `pytest tests/domain/test_task_fsm.py tests/domain/test_ticket_service_tasks.py
  tests/api/test_tickets_tasks.py -v`; `cd frontend && npx tsc -b` → sin errores

**Checkpoint Final**: quickstart completo en verde, tests dirigidos en verde, sin ejecutar la
suite completa del proyecto durante el desarrollo (sí como parte del Polish si se decide).

---

## Dependencies & Execution Order

```
Phase 1 (T001) → Phase 2 (T002 → T003 → T004 → T005 → T006, T003/T004 en paralelo tras T002)
Phase 2 → Phase 3/US1 (T007 → T008 → T009 → T010; T011∥ → ; T012∥; T013∥;
                        T014 → T015, T016 → T017 → T018 → T019)
Phase 3/US1 (T006, T010) → Phase 4/US2 (T020 → T021 → T022; T023∥; T024∥;
                                          T014,T018 → T025)
Phase 3/US1 (T017) → Phase 5/US3 (T026; T018,T025 → T027; T019 → T028)
Todo → Phase 6 (T029∥, T030, T031∥)
```

- US1 es el MVP: sin poder crear ni gestionar una Tarea, no hay nada que vincular (US2) ni
  agrupar (US3).
- US2 depende de US1 porque reutiliza los mismos archivos backend (`ticket_service.py`,
  `tickets.py`) y el mismo `TicketDetailPage.tsx` — no porque el vínculo dependa lógicamente del
  ciclo de vida (podrían haberse planeado en paralelo con dos desarrolladores coordinando esos
  archivos compartidos).
- US3 depende de US1 (y toca el mismo `TicketDetailPage.tsx` que ya modifica US2) por el mismo
  motivo de archivos compartidos, no por dependencia lógica — el campo `list_name` ya existe
  desde Foundational, US3 solo lo expone en UI y lo usa para agrupar.

## Parallel Example: Foundational

```bash
# Tras T002 (migración):
Task: "Entidad backend/domain/entities/ticket.py — STATUS_LABELS + FIELD_LOCKS"   # T003
Task: "Modelo backend/infra/models/ticket_model.py — columna list_name"           # T004
```

## Parallel Example: User Story 1

```bash
# Tras T009 (endpoint task-transition):
Task: "Test API backend/tests/api/test_tickets_tasks.py"                          # T013

# Tras T007 (task_fsm.py):
Task: "Test dominio backend/tests/domain/test_task_fsm.py"                        # T011

# Tras T006 (resolve_record_type):
Task: "Test dominio backend/tests/domain/test_ticket_service_tasks.py"            # T012
```

---

## Implementation Strategy

1. **MVP = Phase 1 + Phase 2 + US1**: se puede crear una Tarea, distinguirla de un Ticket, y
   moverla por su ciclo de vida completo (Pendiente → En progreso → Hecha/Cancelada, con
   reapertura) — funcionando end-to-end.
2. Incremento 1: US2 (Registro relacionado) — depende de que Foundational y US1 ya estén.
3. Incremento 2: US3 (agrupar por Lista) — depende de que Foundational, US1 y US2 ya estén
   (comparte `TicketDetailPage.tsx` con US2).
4. Cada checkpoint valida su escenario del quickstart antes de avanzar.
5. Alcance acotado a los archivos listados arriba — sin tabla `task_lists` nueva, sin permiso
   `tasks:create` nuevo, sin tocar `ticket_fsm.py` (FSM de Ticket queda intacta).

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- [Story] mapea la tarea a su user story para trazabilidad
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
