# Tasks: Encargado (Usuario/cliente) en múltiples Proyectos

**Input**: Design documents from `specs/015-encargado-multiples-proyectos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos y **dirigidos** (Principio VII): un solo archivo de test nuevo, ≤10
registros por caso; nunca correr la suite completa durante el desarrollo.

**Restricción de alcance en pruebas/fixtures** (directriz del solicitante 2026-07-14): los tests
de T008/T012 (y cualquier prueba manual de quickstart.md) DEBEN limitarse a los maestros que
participan del flujo de esta feature — Clientes y Proyectos ya existentes (o creados mínimamente
si el entorno no los tiene). Prohibido:
- Crear usuarios Resolutor adicionales como fixture — no es un actor de esta feature.
- Disparar el flujo de correo de reseteo/reenvío de contraseña (`backend/infra/email/mailer.py`,
  endpoints de `backend/api/routes/auth.py`) — el alta de Usuario/cliente ya devuelve la
  contraseña provisional en la respuesta (sin email), y así debe seguir probándose.

**Organización**: tareas agrupadas por User Story. Orden de ejecución: US1 (P1, alta con varios
Proyectos) → US2 (P2, gestión posterior). Sin migraciones (data-model.md: `project_members` ya
existe desde spec 010).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] alta con varios Proyectos, [US2] agregar/quitar Proyectos de un Usuario/
  cliente existente

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): sin cambios en
  `backend/requirements.txt` ni `frontend/package.json` — `Select mode="multiple"` ya es parte
  de Ant Design 5 (ver plan.md Technical Context)

**Checkpoint**: sin cambios de dependencias.

---

## Phase 2: Foundational (bloqueante para US1 y US2)

**Nota**: sin migración — ambas historias comparten la misma validación de dominio ("mismo
Cliente") y el mismo método de repositorio para resolver una membresía por Proyecto+usuario.

- [X] T002 `backend/domain/services/client_contact_service.py` += método
  `resolve_common_client(project_ids: list[uuid.UUID], projects_repo) -> uuid.UUID`: resuelve
  cada Proyecto, levanta `ClientContactBusinessError` 404 si no existe, 409 `project_inactive`
  si está inactivo, 400 `validation_error` si los Proyectos resueltos no comparten `client_id`;
  devuelve el `client_id` común (ver data-model.md)
- [X] T003 [P] `backend/infra/repositories/project_member_repo.py` += método
  `get_by_project_and_user(project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ProjectMember]`
  (lectura simple sobre `project_members`, usada para resolver el `member_id` antes de borrar)

**Checkpoint**: validación de "mismo Cliente" y lookup de membresía listos — US1 y US2 pueden
arrancar.

---

## Phase 3: User Story 1 — Alta de Usuario/cliente con varios Proyectos (Priority: P1) 🎯 MVP

**Goal**: el alta de Usuario/cliente acepta uno o varios Proyectos del mismo Cliente en un solo
flujo, en vez de exactamente uno.

**Independent Test**: Escenarios 1, 2 y 4 del quickstart.

### Implementation for User Story 1

- [X] T004 [US1] `backend/api/routes/client_contacts.py`: `POST /api/client-contacts` cambia el
  body de `project_id: string` a `project_ids: string[]` (dedupe antes de procesar); usa
  `resolve_common_client` (T002) para derivar `client_id`; crea un `ProjectMember` por cada
  `project_id` de la lista; `client_id` directo (forma legada) sin cambios; actualizar
  `_client_contact_input`/docs de Swagger (depende de T002)
- [X] T005 [P] [US1] `frontend/src/types/clientContact.ts`:
  `ClientContactCreateRequest.project_id?` → `project_ids?: string[]`
- [X] T006 [US1] `frontend/src/services/clientContactService.ts`: `create()` sin cambios de
  firma (ya reenvía el body tal cual; el tipo actualizado en T005 basta)
- [X] T007 [US1] `frontend/src/pages/ClientContactsPage.tsx`: el `<Select>` de Proyecto en el
  modal "Nuevo Usuario/cliente" pasa a `mode="multiple"`, campo `project_ids`; validación
  "selecciona al menos un Proyecto" (depende de T005)
- [X] T008 [US1] `backend/tests/api/test_client_contacts_projects.py` nuevo (dirigido, ≤10
  registros, **solo Clientes y Proyectos como fixtures — sin usuarios Resolutor ni disparo de
  correo de contraseña**): alta con 2 `project_ids` del mismo Cliente → 201 con 2 membresías
  creadas (la contraseña provisional se verifica en la respuesta JSON, nunca por email); alta
  con Proyectos de Clientes distintos → 400 `validation_error`, sin cuenta ni membresías
  parciales creadas; alta con un `project_id` inactivo → 409 `project_inactive`; alta legada con
  `client_id` directo sigue funcionando (0 Proyectos). Correr solo este archivo: `docker exec
  sywork_backend pytest tests/api/test_client_contacts_projects.py -v` (depende de T004)

**Checkpoint US1**: Escenarios 1, 2 y 4 del quickstart ejecutables end-to-end.

---

## Phase 4: User Story 2 — Agregar/quitar Proyectos de un Usuario/cliente existente (Priority: P2)

**Goal**: un Admin puede agregar o quitar Proyectos de un Usuario/cliente ya creado, sin
recrear la cuenta ni afectar tickets históricos.

**Independent Test**: Escenario 3 del quickstart.

### Implementation for User Story 2

- [X] T009 [US2] `backend/api/routes/client_contacts.py` +=
  `POST /api/client-contacts/{contact_id}/projects` (body `{project_id}`; valida contacto
  existente, Proyecto activo y del mismo Cliente vía `resolve_common_client`, no duplicado vía
  `ProjectMemberRepository.is_member`; 201 con `{id, project_id, name}`) y
  `DELETE /api/client-contacts/{contact_id}/projects/{project_id}` (resuelve el `member_id` con
  `get_by_project_and_user` (T003), 404 si no es miembro, luego `ProjectMemberRepository.delete`;
  204); mismo permiso `client_contacts:manage`; actualizar
  `contracts/client-contacts-delta.md` si cambia algún detalle (depende de T002, T003)
- [X] T010 [P] [US2] `frontend/src/services/clientContactService.ts` +=
  `addProject(contactId, projectId)` (`POST .../projects`) y
  `removeProject(contactId, projectId)` (`DELETE .../projects/{projectId}`)
- [X] T011 [US2] `frontend/src/pages/ClientContactsPage.tsx`: acción "Gestionar proyectos" por
  fila → modal con `<Select>` para agregar (Proyectos del mismo Cliente, excluyendo los ya
  asignados) y botón "Quitar" por cada `Tag` de Proyecto ya vinculado; refresca la lista tras
  cada cambio (depende de T007, T010)
- [X] T012 [US2] `backend/tests/api/test_client_contacts_projects.py` += (mismos fixtures que
  T008, sin usuarios Resolutor nuevos ni correo de contraseña): agregar Proyecto del mismo
  Cliente a un contacto existente → 201, aparece en `GET /api/client-contacts`; agregar Proyecto
  de otro Cliente → 400; agregar Proyecto ya asignado → 409; quitar Proyecto → 204, desaparece
  del listado y un ticket ya creado con ese `client_contact_id` conserva el campo sin cambios;
  quitar de un Proyecto donde no es miembro → 404. Mismo archivo que T008 — correr solo ese
  archivo (depende de T009)

**Checkpoint US2**: Escenario 3 del quickstart ejecutable end-to-end.

---

## Phase 5: Polish y validación transversal

- [X] T013 [P] Swagger revisado contra `contracts/client-contacts-delta.md`: `project_ids[]` en
  el alta, los dos endpoints nuevos, códigos de error (400/404/409)
- [X] T014 Ejecutar `quickstart.md` (Escenarios 1-4) contra Docker real
- [X] T015 Validación dirigida de cierre (NUNCA la suite completa — Principio VII): `docker exec
  sywork_backend pytest tests/api/test_client_contacts_projects.py -v`; `cd frontend && npx tsc
  -b` → sin errores

**Checkpoint Final**: quickstart completo en verde y tests dirigidos en verde.

---

## Dependencies & Execution Order

```
Phase 1 (T001)
→ Phase 2 (T002 → T003[P] pueden correr en paralelo, archivos distintos)
→ Phase 3/US1 (T004 → T008; T005[P] → T007; T006 no-op)
→ Phase 4/US2 (T009 → T012 [mismo archivo que T008]; T010[P] → T011 [mismo archivo que T007])
→ Phase 5 (T013[P], T014, T015)
```

- US1 y US2 comparten `backend/api/routes/client_contacts.py` y
  `frontend/src/pages/ClientContactsPage.tsx` — dependencia de archivo (T009 después de T004;
  T011 después de T007), no de dominio: US2 es independientemente testeable una vez creado un
  contacto por cualquier vía (incluida la forma legada).
- T008 y T012 son el mismo archivo de test — T012 se agrega después de T008, no en paralelo.

## Parallel Example: Foundational

```bash
# En paralelo tras Phase 1:
Task: "resolve_common_client en client_contact_service.py"   # T002
Task: "get_by_project_and_user en project_member_repo.py"    # T003
```

## Parallel Example: User Story 1

```bash
# Tras T004 (endpoint listo):
Task: "Tipo ClientContactCreateRequest.project_ids"           # T005 (frontend, archivo distinto)
Task: "Test API test_client_contacts_projects.py"             # T008 (backend, tras T004)
```

---

## Implementation Strategy

1. **MVP = Phase 1 + Phase 2 + US1** (alta con varios Proyectos funcionando) — resuelve
   directamente el pedido original sin tocar la gestión posterior.
2. Incremento 1: US2 (agregar/quitar Proyectos de un contacto existente) — paridad de gestión,
   reutiliza la misma validación de dominio de US1.
3. Sin riesgo de migración: toda la Foundational es código de aplicación sobre una tabla ya
   existente y probada (spec 010).

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
- **Directriz estricta**: no tocar archivos fuera de los listados y no ejecutar la suite
  completa de tests durante el desarrollo (Principio VII)
