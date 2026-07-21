# Tasks: Historial de Estados con SLA Visual y Reasignación de Resolutores

**Input**: Design documents from `specs/023-historial-sla-reasignacion/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/reassign.md](contracts/reassign.md), [quickstart.md](quickstart.md)

**Tests**: Incluidos y acotados — la directriz de la sesión (Constitución, Principio VII) pide
tests puntuales para el cálculo visual del SLA y para la reasignación, con **máximo 5-10
registros de prueba por test**. No se ejecuta la suite completa.

**Organización**: Sin fases de Setup/Foundational — US1 (SLA visual) y US2 (reasignación) no
comparten esquema ni servicio nuevo; cada una parte directo de la infraestructura ya existente
(`sla_service.py`, `ticket_repo.py`, `tickets.py`, `TicketDetailPage.tsx`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1 o US2
- Todas las descripciones incluyen la ruta de archivo exacta

---

## Phase 1: User Story 1 - SLA visual en Historial de Estados (Priority: P1) 🎯 MVP

**Goal**: Cada fila del Historial de Estados de un ticket muestra tiempo transcurrido en el
estado anterior y un ícono ✅/⚠️/❌ de cumplimiento de SLA cuando esa transición cierra una fase
de SLA (research.md Decisión 1).

**Independent Test**: Abrir un ticket con ≥2 transiciones y verificar en `GET
/api/tickets/{id}` y en la UI que las filas traen `elapsed_seconds`/`sla_met` correctos
(quickstart.md Escenario 1), sin que exista todavía la reasignación.

### Tests for User Story 1

- [X] T001 [P] [US1] Test unitario de `compute_transition_compliance` en `backend/tests/domain/test_sla_service.py` — casos: transición que cierra fase Contacto cumplida, cierra fase Contacto vencida, cierra fase Ejecución, transición interna de una fase (sin ícono), primera transición del ticket (sin tiempo ni ícono), ticket sin `sla_rule_id` (≤8 registros de prueba)

### Implementation for User Story 1

- [X] T002 [P] [US1] Implementar `compute_transition_compliance(ticket, transitions, resource=None, holidays=None, schedule_slots=None, absences=None)` en `backend/domain/services/sla_service.py` (función pura, Capa 1) — reutiliza `compute_available_seconds`, `SLA_PHASE_FOR_STATE` y `ticket.sla_contact_result` para devolver, por cada transición, `elapsed_seconds`, `sla_phase_closed` (`"contacto"`/`"ejecucion"`/`null`) y `sla_met` (`true`/`false`/`null`) según research.md Decisión 1/2
- [X] T003 [US1] En `backend/api/routes/tickets.py:473` (bloque `"transitions"` de `_ticket_detail`), pasar `TicketRepository(db).list_transitions(ticket.id)` por `compute_transition_compliance`, reutilizando el mismo contexto que ya arma `_resolve_sla_context(db, ticket)` (usado en la línea 476 para `ticket.sla`) — depende de T002
- [X] T004 [US1] Extender el modelo Swagger `_transition_out` en `backend/api/routes/tickets.py:192` con `elapsed_seconds` (Integer, `allow_null=True`), `sla_phase_closed` (String, `allow_null=True`), `sla_met` (Boolean, `allow_null=True`) — depende de T003
- [X] T005 [P] [US1] Extender `TicketTransition` en `frontend/src/types/ticket.ts:104-111` con `elapsed_seconds: number | null`, `sla_phase_closed: 'contacto' | 'ejecucion' | null`, `sla_met: boolean | null`
- [X] T006 [US1] En la Card "Historial de estados" de `frontend/src/pages/TicketDetailPage.tsx:260-271`, mostrar por fila el tiempo transcurrido formateado (`date-fns`, ya aprobado — Constitución Principio V) y un ícono ✅ (`sla_met === true`), ⚠️/❌ (`sla_met === false`) o ningún ícono (`sla_met === null`) — depende de T005

**Checkpoint**: US1 completa y verificable de forma independiente (quickstart.md Escenario 1).

---

## Phase 2: User Story 2 - Reasignación de resolutor (Priority: P2)

**Goal**: Un usuario con permiso `tickets:assign` puede reasignar un Ticket/Tarea a otro
resolutor sin alterar el FSM, quedando la reasignación visible como "Resolutor anterior ➡️ nuevo
resolutor" en el ticket (research.md Decisión 3/4).

**Independent Test**: Sobre un ticket ya asignado, ejecutar `POST
/api/tickets/{id}/reassign` hacia otro recurso activo y verificar que `assignee_id` cambia, el
`status` no cambia, y aparece la entrada en `reassignments[]` (quickstart.md Escenario 2) — sin
depender de los íconos de SLA de US1.

### Tests for User Story 2

- [X] T007 [P] [US2] Test unitario de `ReassignmentService` en `backend/tests/domain/test_reassignment_service.py` — casos: reasignación válida, mismo resolutor (rechazo FR-010), ticket en estado terminal (rechazo FR-007), recurso inactivo (rechazo), recurso sin skills requeridas (permite + `missing_skills` no vacío, FR-011) (≤6 registros de prueba)
- [X] T008 [P] [US2] Test de integración del endpoint en `backend/tests/api/test_reassign.py` — casos: 200 éxito con entrada nueva en `reassignments`, 400 mismo resolutor, 409 ticket cerrado, 403 sin permiso `tickets:assign` (≤8 registros de prueba)

### Implementation for User Story 2

- [X] T009 [US2] Migración Alembic `backend/infra/migrations/versions/045_ticket_reassignments.py` — crea tabla `ticket_reassignments` (`id`, `ticket_id` FK, `actor_id` FK `users`, `previous_assignee_id` FK `resources` nullable, `new_assignee_id` FK `resources`, `reason` Text nullable, `created_at`) según data-model.md
- [X] T010 [P] [US2] Agregar `ReassignmentModel` en `backend/infra/models/ticket_model.py` (junto a `AssignmentModel` en la línea 118), con su `to_dict`/mapeo análogo al de `AssignmentModel` — depende de T009
- [X] T011 [US2] Crear `backend/domain/services/reassignment_service.py` con `ReassignmentService.validate(ticket, new_assignee, skills_required)` (Capa 1, sin imports de Flask/SQLAlchemy) — aplica las reglas de data-model.md (mismo resolutor, estado terminal, recurso inactivo, `missing_skills`)
- [X] T012 [P] [US2] Agregar `add_reassignment(ticket_id, actor_id, previous_assignee_id, new_assignee_id, reason, commit=True)` y `list_reassignments(ticket_id)` en `backend/infra/repositories/ticket_repo.py` (junto a `add_assignment` en la línea 229) — depende de T010
- [X] T013 [US2] Implementar `POST /api/tickets/<ticket_id>/reassign` en `backend/api/routes/tickets.py` (nueva clase `TicketReassign`, junto a `TicketAssign` en la línea 933) — `require_permission("tickets", "assign")`, invoca `ReassignmentService.validate`, `ticket_repo.update_fields(assignee_id=...)` y `ticket_repo.add_reassignment(...)`, sin invocar `ticket_fsm` (research.md Decisión 3) — depende de T011, T012
- [X] T014 [P] [US2] Agregar modelos Swagger `_reassign_input`/`_reassign_result_out` en `backend/api/routes/tickets.py` (junto a `_assign_input` en la línea 89), documentados según contracts/reassign.md — depende de T013
- [X] T015 [US2] Exponer el bloque `"reassignments": TicketRepository(db).list_reassignments(ticket.id)` en `_ticket_detail` (`backend/api/routes/tickets.py:474`, junto a `"assignments"`) — depende de T012
- [X] T016 [P] [US2] Agregar `TicketReassignment` en `frontend/src/types/ticket.ts` (junto a `TicketAssignment` en la línea 113) y el campo `reassignments: TicketReassignment[]` en `TicketDetail`
- [X] T017 [P] [US2] Agregar `reassign: (id: string, assignee_id: string, reason?: string) => ...` en `frontend/src/services/ticketService.ts:49` (junto a `assign`), llamando `POST /api/tickets/{id}/reassign`
- [X] T018 [US2] Crear `frontend/src/components/tickets/ReassignModal.tsx` (mismo patrón que `AssignModal.tsx`: selector de recurso activo con skills/carga, advertencia no bloqueante si faltan skills requeridas, campo de motivo opcional) — depende de T016, T017
- [X] T019 [US2] Agregar botón "Reasignar" en `frontend/src/pages/TicketDetailPage.tsx` junto al `Descriptions.Item label="Asignado"` (línea 373), visible cuando `ticket.assignee` existe y `ticket.status` no es terminal, que abre `ReassignModal` — depende de T018
- [X] T020 [US2] Mostrar `ticket.reassignments[]` en el bloque de actividad/historial de `TicketDetailPage.tsx` (junto a la Card "Historial de estados") como "Resolutor anterior ➡️ nuevo resolutor" con autor y fecha — depende de T015, T016

**Checkpoint**: US1 y US2 funcionan de forma independiente y en conjunto.

---

## Final Phase: Polish & Validación

- [X] T021 [P] Ejecutar `quickstart.md` (Escenarios 1 y 2) contra el stack Docker Compose real
- [X] T022 Confirmar que `POST /api/tickets/{id}/reassign` queda documentado en Swagger/OpenAPI antes de integrar (Constitución Principio I)

---

## Dependencies & Execution Order

### Phase Dependencies

- **User Story 1 (Phase 1)**: Sin dependencias de otras historias — puede iniciar de inmediato.
- **User Story 2 (Phase 2)**: Sin dependencias de US1 — puede iniciar de inmediato en paralelo.
- **Polish (Final Phase)**: Depende de que US1 y/o US2 estén completas.

### Dentro de cada historia

- US1: T001 (test) antes de T002; T002 → T003 → T004; T005 en paralelo; T006 depende de T004+T005.
- US2: T007/T008 (tests) en paralelo antes de T009 en adelante; T009 → T010 → T011/T012 (paralelo) → T013 → T014/T015 (paralelo) → T016/T017 (paralelo) → T018 → T019 → T020.

### Parallel Opportunities

- US1 y US2 se pueden trabajar en paralelo por completo (sin archivos compartidos salvo
  `tickets.py`/`TicketDetailPage.tsx`, en secciones distintas).
- Dentro de US1: T001 y T005 en paralelo con el resto.
- Dentro de US2: T007+T008, luego T010, luego T012+T014+T015 (una vez sus dependencias
  individuales estén listas), y T016+T017 en paralelo.

---

## Parallel Example: User Story 1

```bash
Task: "Test unitario de compute_transition_compliance en backend/tests/domain/test_sla_service.py"
Task: "Extender TicketTransition en frontend/src/types/ticket.ts"
```

## Parallel Example: User Story 2

```bash
Task: "Test unitario de ReassignmentService en backend/tests/domain/test_reassignment_service.py"
Task: "Test de integración del endpoint en backend/tests/api/test_reassign.py"
Task: "Agregar TicketReassignment en frontend/src/types/ticket.ts"
Task: "Agregar reassign(...) en frontend/src/services/ticketService.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1 (US1) → validar quickstart.md Escenario 1 → demo.

### Incremental Delivery

1. US1 (SLA visual) → demo — ya entrega valor por sí sola.
2. US2 (reasignación) → demo — no rompe nada de US1.

### Alcance explícitamente fuera de esta feature (directrices de la sesión)

- No se toca el endpoint `/assign` ni el FSM (`ticket_fsm.py`).
- No se refactoriza la entidad `Ticket` más allá de exponer los campos derivados/nuevos descritos.
- No se ejecuta la suite completa de tests; solo los archivos listados arriba.
