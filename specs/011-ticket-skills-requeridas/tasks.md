---

description: "Task list for Skills Requeridas en el Ticket (spec 011)"
---

# Tasks: Skills Requeridas en el Ticket

**Input**: Design documents from `/specs/011-ticket-skills-requeridas/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/ticket-skills.md](contracts/ticket-skills.md),
[quickstart.md](quickstart.md)

**Tests**: Se incluyen tareas de test dirigidas (pytest contra Postgres real en Docker), mismo
criterio que la spec `012` — no es TDD estricto pero cada historia deja cobertura verificada.

**Organization**: Tareas agrupadas por historia de usuario (US1/US2/US3, spec.md) para permitir
implementación y validación independiente de cada una.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)

## Path Conventions

Web app existente: `backend/` (Flask, Clean Architecture 3 capas) + `frontend/src/` (React 19).

---

## Phase 1: Setup

**Purpose**: Preparar el esquema de base de datos para la nueva relación.

- [X] T001 [P] Confirmar que no se requiere ninguna dependencia nueva (Flask-RESTX, SQLAlchemy,
      React, Ant Design ya cubren la feature — research.md, Technical Context)
- [X] T002 Crear migración `backend/infra/migrations/versions/027_ticket_skills.py`
      (`down_revision = "026"`): tabla `ticket_skills(ticket_id, skill_id, assigned_at)` con PK
      compuesta, FK `ticket_id` con `ON DELETE CASCADE` y FK `skill_id` **sin** cascade (a
      propósito, ver FR-007/data-model.md) a `tickets`/`skills`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Capa de dominio/infra compartida que las 3 historias necesitan antes de poder
implementarse.

**⚠️ CRITICAL**: Ninguna historia puede empezar hasta completar esta fase.

- [X] T003 Agregar campo `skills: list[Skill] = field(default_factory=list)` a la entidad
      `Ticket` en `backend/domain/entities/ticket.py` (mismo patrón que `Resource.skills`)
- [X] T004 [P] Agregar tabla asociativa `ticket_skills_table` y relación
      `skills = relationship("SkillModel", secondary=ticket_skills_table, lazy="joined")` a
      `TicketModel` en `backend/infra/models/ticket_model.py`; incluir `skills=[...]` en
      `to_entity()` (mismo patrón que `ResourceModel`)
- [X] T005 Agregar `TicketRepository.update_skills(ticket_id, skill_ids)` (reemplazo total, mismo
      patrón que `ResourceRepository.update_skills`) en
      `backend/infra/repositories/ticket_repo.py` (depende de T004)
- [X] T006 Agregar `"skills": [{"id", "code", "label"}, ...]` a `_ticket_detail()` en
      `backend/api/routes/tickets.py` (depende de T004)

**Checkpoint**: Modelo, repositorio y serialización listos — las historias pueden implementarse.

---

## Phase 3: User Story 1 - Asignar Skills requeridas al ticket (Priority: P1) 🎯 MVP

**Goal**: Un Coordinador/Resolutor agrega o quita Skills opcionales de un ticket desde su
detalle, quedando reflejadas de inmediato.

**Independent Test**: crear un ticket sin Skills (se guarda vacío), editarlo agregando dos
Skills del catálogo, verificar que ambas quedan listadas en el ticket.

### Implementation for User Story 1

- [X] T007 [US1] Implementar `TicketSkills` — `PATCH /api/tickets/{id}/skills` (reemplazo total
      vía `TicketRepository.update_skills`, `@require_permission("tickets", "edit")`, sin pasar
      por `validate_patch`/`locked_fields_for`) en `backend/api/routes/tickets.py`
      (contracts/ticket-skills.md; depende de T005, T006)
- [X] T008 [P] [US1] Agregar modelos Swagger `SkillRef` y `TicketSkillsUpdate` en
      `backend/api/routes/tickets.py`
- [X] T009 [P] [US1] Agregar `ticketService.updateTicketSkills(ticketId, skillIds)` en
      `frontend/src/services/ticketService.ts`
- [X] T010 [P] [US1] Agregar `skills?: { id, code, label }[]` al tipo `Ticket` en
      `frontend/src/types/ticket.ts`
- [X] T011 [US1] Crear `TicketSkillsSelector.tsx` (multi-select Ant Design sobre `GET
      /api/skills` activos, dispara `updateTicketSkills` al cambiar) en
      `frontend/src/components/tickets/TicketSkillsSelector.tsx` (depende de T009, T010)
- [X] T012 [US1] Montar `TicketSkillsSelector` en la sección de clasificación del detalle de
      ticket, visible solo con `hasPermission('tickets','edit')`, en
      `frontend/src/pages/TicketDetailPage.tsx` (depende de T011)
- [X] T013 [US1] Test API dirigido `backend/tests/api/test_ticket_skills.py`: asignar Skills a
      ticket sin ninguna, reemplazo total, `403` para Resolutor (no tiene `tickets:edit` en este
      sistema — research.md Decisión 4)

**Checkpoint**: User Story 1 funcional y testeable de forma independiente (MVP).

---

## Phase 4: User Story 2 - Cambiar Skills requeridas en cualquier fase del ticket (Priority: P1)

**Goal**: El conjunto de Skills requeridas se puede modificar sin importar el estado del ticket
(incluidos Cerrado/Cancelado), sin transición de estado ni comentario.

**Independent Test**: llevar un ticket a estado "Cerrado" y verificar que igual se pueden
agregar o quitar Skills requeridas, sin reabrir el ticket ni registrar comentario.

### Implementation for User Story 2

- [X] T014 [US2] Test API dirigido: `PATCH /api/tickets/{id}/skills` sobre ticket en estado
      Cerrado y Cancelado devuelve `200` sin cambiar `status` ni crear comentario/notificación,
      en `backend/tests/api/test_ticket_skills.py` (verifica la Decisión 2 de research.md — el
      endpoint ya no pasa por `locked_fields_for`, no requiere código nuevo)
- [X] T015 [US2] Confirmar que `TicketSkillsSelector` no deshabilita su edición según
      `ticket.status` (a diferencia de otros campos de clasificación bloqueados) en
      `frontend/src/components/tickets/TicketSkillsSelector.tsx`

**Checkpoint**: User Stories 1 y 2 funcionan de forma independiente.

---

## Phase 5: User Story 3 - Visualizar las Skills requeridas del ticket (Priority: P2)

**Goal**: Cualquier usuario con acceso al ticket ve, en su detalle, las Skills requeridas
asociadas.

**Independent Test**: abrir el detalle de un ticket con dos Skills requeridas asignadas y
confirmar que ambas se muestran con su nombre/etiqueta; un ticket sin Skills muestra la sección
vacía sin errores.

### Implementation for User Story 3

- [X] T016 [US3] Renderizar las Skills requeridas como `Tag`s de solo lectura (sin selector) en
      `TicketDetailPage.tsx` para usuarios sin `tickets:edit` (p. ej. rol `Coordinador` en modo
      lectura, u otro Resolutor) en `frontend/src/pages/TicketDetailPage.tsx`
- [X] T017 [P] [US3] Test API dirigido: `GET /api/tickets/{id}` incluye `skills: []` por defecto
      y la lista completa tras asignar, verificado con Resolutor (`tickets:view` sin
      `tickets:edit`), en `backend/tests/api/test_ticket_skills.py`
- [X] T018 [US3] Test API dirigido del edge case FR-007: `DELETE /api/skills/{id}` sobre una
      Skill ya asignada a un ticket devuelve `409 skill_in_use` (el catálogo de Skills no tiene
      "desactivar", solo eliminar — se extendió `SkillService.validate_delete()` +
      `TicketRepository.count_tickets_with_skill()` para bloquearlo, mismo criterio que el
      chequeo ya existente para Skills asignadas a Recursos), en
      `backend/tests/api/test_ticket_skills.py`

**Checkpoint**: Las 3 historias de usuario funcionan de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validación final transversal a las 3 historias.

- [X] T019 [P] Revisar Swagger generado contra `contracts/ticket-skills.md` (request/response,
      códigos de error)
- [X] T020 Correr los 7 escenarios de `quickstart.md` contra Docker real
- [X] T021 Suite de tests dirigida (`test_ticket_skills.py` + regresión de `test_tickets_*.py`) +
      `tsc -b` sin errores

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede iniciar de inmediato.
- **Foundational (Phase 2)**: depende de Setup (T002, la migración) — bloquea las 3 historias.
- **User Stories (Phase 3-5)**: todas dependen de Foundational. US1 y US2 comparten el mismo
  endpoint (T007) — US2 es mayormente verificación de que el diseño de US1 ya cumple el
  requisito de "cualquier estado". US3 depende de la serialización de T006 pero es
  independiente en frontend (solo lectura).
- **Polish (Phase 6)**: depende de que US1-US3 estén completas.

### User Story Dependencies

- **US1 (P1)**: depende de Foundational. Sin dependencia de otras historias.
- **US2 (P1)**: depende de Foundational y reutiliza el endpoint de US1 (T007) — recomendable
  implementar después de US1 aunque no haya código exclusivo nuevo más allá de tests.
- **US3 (P2)**: depende de Foundational (T006). Puede desarrollarse en paralelo a US1/US2 una
  vez completada la Fase 2, ya que solo lee `skills` del detalle ya serializado.

### Parallel Opportunities

- T001 y T002 (Setup) en paralelo.
- T004 puede iniciar en paralelo a T003 (archivos distintos); T005-T006 dependen de T004.
- T008, T009, T010 (US1) en paralelo entre sí.
- T017 (US3, test) en paralelo a T014-T015 (US2) una vez completado Foundational.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Setup + Foundational (T001-T006).
2. Completar User Story 1 (T007-T013) — endpoint + selector + wiring.
3. Validar de forma independiente (Escenario 1 de quickstart.md).
4. Continuar con US2 (mayormente verificación) y US3 (visualización de solo lectura).

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → Coordinador/Resolutor puede asignar Skills (MVP).
3. US2 → confirma que funciona en cualquier estado (Cerrado/Cancelado incluidos).
4. US3 → cualquier usuario con acceso ve las Skills asignadas.
5. Polish → Swagger, quickstart end-to-end, suite completa + `tsc -b`.
