# Tasks: Usuario/cliente por Proyecto, Asignación de Personal y Estructura de Skills

**Input**: Design documents from `specs/010-proyecto-personal-skills/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos y **dirigidos** (FR-020): solo los tests de lo que cambia, nunca la suite
completa de forma masiva durante el desarrollo.

**Organización**: tareas agrupadas por User Story. Orden de ejecución: US1 → US3 → US2 → US4
(US3 antes que US2 porque la UI/endpoints de personal son la forma natural de vincular a un
Usuario/cliente con un Proyecto, prerequisito práctico para probar US2 end-to-end; ambas son
P1 — ver Dependencies).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] renombre Encargado→Usuario/cliente, [US2] solicitante por Proyecto,
  [US3] Personal del Proyecto + Equipos, [US4] estructura de Skills

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): sin cambios en
  `backend/requirements.txt` ni `frontend/package.json` (ver plan.md Technical Context)

**Checkpoint**: sin cambios de dependencias.

---

## Phase 2: Foundational (bloqueante para las 4 historias)

**Nota**: la migración `025` concentra el renombre del rol (US1), las tablas de personal
(US2/US3) y la estructura de skills (US4) — nada es probable sin ella.

- [X] T002 Migración `backend/infra/migrations/versions/025_project_members_skills.py`
  (down_revision `024`), en el orden de data-model.md: (1) `UPDATE roles` Encargado →
  Usuario/cliente (mismo UUID); (2-4) crear `project_members` (UNIQUE project_id+user_id),
  `project_teams` (UNIQUE project_id+name), `project_team_members` (FKs ON DELETE CASCADE a
  ambas), con índices y RLS; (5) backfill de membresías desde tickets con
  `client_contact_id`+`project_id` (ON CONFLICT DO NOTHING); (6-7) `skills` += `skill_type`
  (backfill: JDE_AR/ORACLE_CRM→funcional, resto→tecnico; luego SET NOT NULL + CHECK
  `ck_skills_type`), `tool_id` FK NULL, `process_id` FK NULL; (8) insertar procesos "Compras"
  y "Mantenimiento" en `catalog_processes` si no existen; (9) upsert de las 10 semillas de
  skills por `code` (tabla en research.md Decisión 5, tool/process resueltos por subselect de
  nombre). `downgrade` completo (depende de T001)
- [X] T003 [P] `backend/domain/entities/project_member.py` nuevo: dataclasses `ProjectMember`
  (`id, project_id, user_id, assigned_at`) y `ProjectTeam` (`id, project_id, name,
  created_at`), sin imports de framework (depende de T002)
- [X] T004 [P] `backend/domain/entities/resource.py`: `Skill` += `skill_type: str`,
  `tool_id: Optional[uuid.UUID]`, `process_id: Optional[uuid.UUID]`; `Skill.create()` acepta
  los campos nuevos (depende de T002)
- [X] T005 `backend/infra/models/project_member_model.py` nuevo: `ProjectMemberModel`,
  `ProjectTeamModel`, `ProjectTeamMemberModel` + `to_entity()` (depende de T003)
- [X] T006 [P] Modelo SQLAlchemy de Skill (en `backend/infra/models/`, donde vive hoy el
  modelo de skills): columnas `skill_type`, `tool_id`, `process_id` + `to_entity()` (depende
  de T004)
- [X] T007 `backend/infra/repositories/project_member_repo.py` nuevo:
  `list_by_project(project_id, role_name=None)` (join `users`/`roles` para `role_name`, join
  `resources` para `full_name` con fallback a username), `create()`, `delete(member_id,
  project_id)`, `is_member(project_id, user_id)`, `list_project_ids_by_user(user_id)`;
  y para teams: `list_teams(project_id)` (con members), `create_team()`, `rename_team()`,
  `delete_team()`, `replace_team_members(team_id, member_ids)` (depende de T005)
- [X] T008 `backend/infra/repositories/resource_repo.py`: `SkillRepository.list_all()` y
  `create()` con los campos nuevos (+ join a catálogos para `tool_name`/`process_name`);
  `update()` nuevo para PATCH (depende de T006)
- [X] T009 [P] `backend/infra/repositories/client_contact_repo.py`: `list_paginated()` gana
  filtro opcional `project_id` (join `project_members` por `user_id`) (depende de T002)
- [X] T010 `backend/domain/services/project_member_service.py` nuevo: `validate_assign`
  (usuario existe y activo → 409 `user_inactive`; no duplicado → 409 `already_member`),
  `validate_team_name` (no vacío, único en el proyecto → 409 `duplicate_name`),
  `validate_team_members` (todos los `member_ids` pertenecen al mismo proyecto → 409
  `member_not_in_project`) (depende de T007)
- [X] T011 `backend/domain/services/skill_service.py`: `validate_create`/`validate_update`
  exigen `skill_type in ('funcional','tecnico')` (400 `validation_error`); `tool_id`/
  `process_id` opcionales pero deben existir en su catálogo si vienen (404 `not_found`)
  (depende de T004)
- [X] T012 [P] `frontend/src/types/projectMember.ts` nuevo: interfaces `ProjectMember` (`id,
  project_id, user_id, full_name, email, role_name, assigned_at`) y `ProjectTeam` (`id,
  project_id, name, members, member_count, created_at`); tipo `Skill` existente (en
  `frontend/src/types/`) += `skill_type: 'funcional' | 'tecnico'`, `tool_id`, `tool_name`,
  `process_id`, `process_name` (nullables)
- [X] T013 [P] `frontend/src/services/projectMemberService.ts` nuevo: `listMembers(projectId,
  roleName?)`, `addMember(projectId, userId)`, `removeMember(projectId, memberId)`,
  `listTeams(projectId)`, `createTeam(projectId, name)`, `renameTeam(teamId, name)`,
  `deleteTeam(teamId)`, `setTeamMembers(teamId, memberIds)`;
  `frontend/src/services/clientContactService.ts` += parámetro `project_id` en el listado
  (depende de T012)

**Checkpoint**: migración `025` aplicada, entidades/modelos/repos/servicios base y tipos +
servicios frontend listos — las 4 historias pueden arrancar.

---

## Phase 3: User Story 1 — Renombre "Encargado" → "Usuario/cliente" (Priority: P1) 🎯 MVP

**Goal**: el rol y todas las etiquetas visibles dicen "Usuario/cliente"; permisos, usuarios y
comportamiento intactos (el renombre en BD ya lo hizo T002).
**Independent Test**: Escenarios 0 (parte de rol) y 1 del quickstart.

- [X] T014 [US1] `backend/api/routes/client_contacts.py`: constante módulo
  `USUARIO_CLIENTE_ROLE_NAME = "Usuario/cliente"` reemplaza el literal `"Encargado"` en
  `get_by_name(...)` y en el mensaje `role_not_configured`; docstrings/descripciones Swagger
  del namespace actualizadas (depende de T002)
- [X] T015 [P] [US1] `backend/api/routes/tickets.py`: mensajes de error y descripciones
  Swagger "Encargado" → "Usuario/cliente" (códigos de error sin cambios —
  contracts/tickets.md); ídem cualquier otro texto backend visible (`app.py`,
  `notifications.py`, `ticket_service.py` mensaje de `client_contact_mismatch`) (depende de
  T002)
- [X] T016 [P] [US1] Frontend — reemplazar el texto visible "Encargado" por "Usuario/cliente"
  en las 7 ubicaciones: `frontend/src/pages/ClientContactsPage.tsx`,
  `frontend/src/pages/TicketsPage.tsx`, `frontend/src/pages/TicketDetailPage.tsx`,
  `frontend/src/components/tickets/SubtaskList.tsx`, `frontend/src/config/navigation.tsx`,
  `frontend/src/components/common/ProtectedRoute.tsx`, `frontend/src/types/ticket.ts`
  (comentarios/labels)
- [X] T017 [US1] Tests dirigidos actualizados: `backend/tests/conftest.py` (fixture del rol:
  `get_by_name("Usuario/cliente")`) y expectativas de nombre de rol en
  `backend/tests/api/test_tickets_encargado.py` /
  `backend/tests/api/test_tickets_client_contact.py`; correr SOLO esos archivos:
  `docker exec sywork_backend pytest tests/api/test_tickets_encargado.py
  tests/api/test_tickets_client_contact.py -v` (depende de T014)

**Checkpoint US1**: Escenario 1 del quickstart ejecutable — 0 apariciones de "Encargado" en UI,
login y restricciones del rol intactos.

---

## Phase 4: User Story 3 — Personal del Proyecto con sección "Equipo" (Priority: P1)

**Goal**: asignar cualquier usuario a un Proyecto y agruparlo en subgrupos "Equipo", estilo
Teamwork (pestañas Personas/Equipos).
**Independent Test**: Escenario 2 del quickstart.

- [X] T018 [US3] `backend/api/routes/project_members.py` nuevo, según
  contracts/project-members.md y contracts/project-teams.md: `GET/POST
  /api/projects/{id}/members` (GET con filtro `role_name`), `DELETE
  /api/projects/{id}/members/{member_id}`, `GET/POST /api/projects/{id}/teams`,
  `PATCH/DELETE /api/project-teams/{team_id}`, `PUT /api/project-teams/{team_id}/members`;
  módulo de permisos `projects` (`enforce_module("projects")` — lectura `view`, mutación
  `edit`, research Decisión 7) (depende de T010)
- [X] T019 [US3] Registrar el namespace `project_members` en `backend/app.py`
  (`api.add_namespace`, junto a los demás) (depende de T018)
- [X] T020 [P] [US3] Test API `backend/tests/api/test_project_members.py`: asignar usuario →
  201 con `role_name`; duplicado → 409 `already_member`; usuario inactivo → 409
  `user_inactive`; listar con filtro `role_name`; crear/renombrar/eliminar team (nombre
  duplicado → 409); `PUT members` con member de otro proyecto → 409 `member_not_in_project`;
  eliminar team NO desasigna del proyecto; `DELETE member` lo saca de sus teams (cascade);
  sin permiso `projects:edit` → 403. Correr solo este archivo (depende de T019)
- [X] T021 [US3] Frontend `frontend/src/pages/ProjectPeoplePage.tsx` nueva: `Tabs` con
  **Personas** (Table nombre/correo/tipo-rol como Tag/fecha + botón "Asignar personal" con
  Select de búsqueda de usuarios activos vía `userService` + acción quitar con
  `ConfirmationModal`) y **Equipos** (lista de subgrupos con nombre, avatares y conteo;
  crear/renombrar/eliminar; administrar miembros con Select múltiple acotado al personal del
  proyecto); botones de mutación solo con `hasPermission('projects','edit')` (depende de T013)
- [X] T022 [US3] Wire de la página: ruta `/projects/:id/people` en `frontend/src/App.tsx`,
  acción "Personal" por fila en `frontend/src/pages/ProjectsPage.tsx`, breadcrumb consistente
  con el patrón de `ProjectListsPage` (depende de T021)

**Checkpoint US3**: Escenario 2 del quickstart ejecutable end-to-end.

---

## Phase 5: User Story 2 — Solicitante del ticket filtrado por Proyecto (Priority: P1)

**Goal**: el selector de solicitante se alimenta del personal del Proyecto; el Ticket conserva
su campo (clarificación 2026-07-09); autoservicio acotado a proyectos vinculados.
**Independent Test**: Escenarios 3 y 4 del quickstart.

- [X] T023 [US2] `backend/domain/services/ticket_service.py`: `validate_create`/
  `validate_patch` — si hay `client_contact_id` **y** `project_id`, validar membresía vía
  `project_members_repo.is_member()` → 409 `contact_not_in_project`; check por Cliente
  existente intacto; y si el creador es Usuario/cliente con `project_id`, validar 409
  `project_not_assigned` (FR-007) (depende de T010)
- [X] T024 [US2] `backend/api/routes/tickets.py`: inyectar `ProjectMemberRepository` en las
  llamadas a `validate_create`/`validate_patch`; documentar los dos 409 nuevos en Swagger
  (contracts/tickets.md) (depende de T023)
- [X] T025 [US2] `backend/api/routes/client_contacts.py`: `GET /api/client-contacts` acepta
  `project_id` (repo ya listo en T009); endpoint nuevo `GET /api/client-contacts/me/projects`
  (`@require_authenticated`) que devuelve los proyectos vinculados del Usuario/cliente actual
  (vía `list_project_ids_by_user` + `ProjectRepository`) para el selector del autoservicio;
  actualizar contracts/client-contacts.md con este endpoint (depende de T009, T014 mismo
  archivo)
- [X] T026 [P] [US2] Tests dirigidos: `backend/tests/api/test_tickets_client_contact.py` +=
  crear ticket con solicitante NO vinculado al proyecto → 409 `contact_not_in_project`; con
  vinculado → 201; autoservicio a proyecto ajeno → 409 `project_not_assigned`;
  `backend/tests/domain/test_ticket_service_client_contact.py` += casos de dominio
  equivalentes. Correr solo esos 2 archivos (depende de T024)
- [X] T027 [US2] Frontend `frontend/src/pages/TicketsPage.tsx`: el Select de solicitante pasa
  de filtrar por `client_id` a `project_id` (habilitado solo con proyecto elegido; se limpia
  al cambiar proyecto — regla de spec `007` extendida); en autoservicio, el selector de
  proyecto usa `GET /api/client-contacts/me/projects` (depende de T013, T016 mismo archivo)
- [X] T028 [US2] Frontend `frontend/src/pages/TicketDetailPage.tsx`: mismo cambio de fuente
  del Select de solicitante (por `project_id` del ticket), conservando bloqueos de spec `007`
  (autoservicio/estados finales) (depende de T013, T016 mismo archivo)

**Checkpoint US2**: Escenarios 3 y 4 del quickstart ejecutables end-to-end.

---

## Phase 6: User Story 4 — Estructura de Skills + semillas (Priority: P2)

**Goal**: skills con tipo obligatorio, herramienta/proceso opcionales, semillas visibles y
editables (las semillas y el backfill ya los hizo T002).
**Independent Test**: Escenario 5 del quickstart.

- [X] T029 [US4] `backend/api/routes/resources.py`: `_skill_input`/`_skill_out` += los campos
  nuevos (`skill_type`, `tool_id`, `tool_name`, `process_id`, `process_name`); `POST
  /api/skills` valida vía `skill_service` (400 sin tipo); endpoint nuevo `PATCH
  /api/skills/{id}` según contracts/skills.md (depende de T008, T011)
- [X] T030 [P] [US4] Test API `backend/tests/api/test_skills_structure.py`: semillas presentes
  con tool/process/type correctos (muestra: JDE_GL funcional/JDE/Finanzas, OIC
  tecnico/Oracle Fusion/Integraciones, DBA tecnico sin tool/process); JDE_GL no duplicada;
  POST sin `skill_type` → 400; POST con tipo y sin tool/process → 201; PATCH cambia tipo y
  tool; skills preexistentes (JDE_AR) con tipo backfilled. Correr solo este archivo (depende
  de T029)
- [X] T031 [US4] Frontend `frontend/src/pages/SkillsPage.tsx`: columnas nuevas (Tipo como Tag,
  Herramienta, Proceso) y formulario con `Radio` de tipo (obligatorio) + `Select` de
  herramienta/proceso (opcionales, `allowClear`, poblados con `catalogService`) (depende de
  T012)
- [X] T032 [US4] `frontend/src/services/resourceService.ts` (donde viven las llamadas de
  skills): create/patch con los campos nuevos, tipado con el `Skill` ampliado (depende de
  T012)

**Checkpoint US4**: Escenario 5 del quickstart ejecutable end-to-end.

---

## Phase 7: Polish y validación transversal

- [X] T033 [P] Swagger revisado contra `contracts/`: members/teams, client-contacts
  (`project_id`, `/me/projects`), skills (input/out/PATCH), tickets (409 nuevos), textos sin
  "Encargado"
- [X] T034 Ejecutar `quickstart.md` (Escenarios 0-6) contra Docker real: migración/backfill,
  renombre en UI, personal + equipos, solicitante por proyecto, autoservicio acotado, skills,
  regresión dirigida
- [X] T035 Validación dirigida de cierre (NUNCA la suite completa — FR-020): `docker exec
  sywork_backend pytest tests/api/test_project_members.py tests/api/test_skills_structure.py
  tests/api/test_tickets_client_contact.py tests/api/test_tickets_encargado.py
  tests/domain/test_ticket_service_client_contact.py -v`; `cd frontend && npx tsc -b` → sin
  errores

**Checkpoint Final**: quickstart completo en verde y tests dirigidos en verde.

---

## Dependencies & Execution Order

```
Phase 1 (T001)
→ Phase 2 (T002 → T003/T004∥ → T005/T006∥ → T007,T008,T009∥ → T010,T011; T012∥ → T013)
→ Phase 3/US1 (T014 → T015∥, T016∥ → T017)
→ Phase 4/US3 (T018 → T019 → T020∥; T021 → T022)
→ Phase 5/US2 (T023 → T024 → T026∥; T025 [mismo archivo que T014]; T027, T028 [mismos archivos que T016])
→ Phase 6/US4 (T029 → T030∥; T031; T032)
→ Phase 7 (T033∥, T034, T035)
```

- US1, US2 y US3 son P1. US1 va primero (vocabulario para todo lo demás). **US3 se ejecuta
  antes que US2** aunque la spec las numere al revés: la UI/endpoints de personal (US3) son la
  vía natural para vincular a un Usuario/cliente con un Proyecto, que es el precondición del
  test independiente de US2 (el vínculo también puede hacerse por API/backfill, así que US2
  sigue siendo lógicamente independiente).
- US2 comparte archivos con US1 (`client_contacts.py`, `TicketsPage.tsx`,
  `TicketDetailPage.tsx`) — dependencia de archivo, no de dominio.
- US4 solo depende de Foundational (T002 hizo semillas/backfill; T008/T011 los repos y
  validaciones).

## Parallel Example: Foundational

```bash
# Tras T002 (migración):
Task: "Entidades backend/domain/entities/project_member.py"   # T003
Task: "Entidad Skill ampliada backend/domain/entities/resource.py"  # T004
Task: "Tipos frontend projectMember.ts + Skill"               # T012

# Tras T005/T006:
Task: "Repo project_member_repo.py"                           # T007
Task: "SkillRepository con campos nuevos"                     # T008
Task: "Filtro project_id en client_contact_repo.py"           # T009
```

## Parallel Example: User Story 3

```bash
# Tras T019 (namespace registrado):
Task: "Test API tests/api/test_project_members.py"            # T020
Task: "Página ProjectPeoplePage.tsx"                          # T021 (frontend, archivo distinto)
```

---

## Implementation Strategy

1. **MVP = Phase 1 + Phase 2 + US1** (renombre completo funcionando sobre la migración) —
   valor visible inmediato y sin riesgo.
2. Incremento 1: US3 (personal + equipos) — habilita la gestión visual y el vínculo
   Usuario/cliente↔Proyecto.
3. Incremento 2: US2 (solicitante por proyecto + autoservicio acotado) — usa el vínculo del
   incremento anterior.
4. Incremento 3: US4 (skills) — independiente, puede adelantarse si conviene.
5. Riesgo concentrado en T002 (migración con backfill — validar Escenario 0 del quickstart
   sobre datos reales antes de avanzar historias, mismo criterio que la spec `009`).

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
- **Directriz estricta**: no tocar archivos fuera de los listados (FR-019) y no ejecutar la
  suite completa de tests durante el desarrollo (FR-020)
