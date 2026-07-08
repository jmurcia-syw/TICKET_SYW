# Tasks: Selección manual del Encargado solicitante en el Ticket

**Input**: Design documents from `specs/007-ticket-encargado-cliente/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos — el plan.md ya compromete 2 archivos de test nuevos (mismo criterio que
Fases 1/2/2.1: tests dirigidos a lo que cambia, no toda la suite en cada tarea).

**Organización**: Tareas agrupadas por User Story para implementación y validación independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] asignar Encargado al crear, [US2] corregir/asignar después de creado

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): SQLAlchemy/Alembic,
  Flask-RESTX y Ant Design 5 (`Select`) ya cubren toda la funcionalidad; sin cambios en
  `backend/requirements.txt` ni `frontend/package.json` (ver research.md)

**Checkpoint**: sin cambios de dependencias.

---

## Phase 2: Foundational (bloqueante para ambas historias)

**Nota**: la columna nueva y el gap de permiso son prerequisito compartido — ninguna historia
puede probarse sin ellos.

- [X] T002 Migración `backend/infra/migrations/versions/022_tickets_client_contact.py`: agrega
  `client_contact_id` (UUID, nullable, FK `client_contacts.id`, `ON DELETE SET NULL`) a `tickets`
  (depende de T001)
- [X] T003 [P] `backend/domain/entities/ticket.py`: agregar campo `client_contact_id:
  Optional[uuid.UUID] = None` al dataclass `Ticket`; agregarlo a `FIELD_LOCKS["cerrado"]` y
  `FIELD_LOCKS["cancelado"]` (FR-008) (depende de T002)
- [X] T004 `backend/infra/models/ticket_model.py`: columna `client_contact_id` +
  `to_entity()` (depende de T002, T003)
- [X] T005 `backend/infra/repositories/ticket_repo.py`: `create()` incluye
  `client_contact_id=ticket.client_contact_id` (`update_fields()` ya es genérico vía `setattr`,
  sin cambios ahí) (depende de T004)
- [X] T006 [P] `backend/infra/repositories/client_contact_repo.py`: agregar `get_by_id(id)`
  (falta hoy — lo necesita `_requester()` en tickets.py)
- [X] T007 [P] `backend/api/routes/client_contacts.py`: el método `GET` pasa de
  `@require_permission("client_contacts","manage")` a `@require_authenticated()` + chequeo manual
  `current_user_has("client_contacts","manage") or current_user_has("tickets","create") or
  current_user_has("tickets","edit")` (mismo patrón que el fix de `notifications.py` en Fase 2.1);
  `POST` no cambia (research.md Decisión 4)

**Checkpoint**: columna en base de datos, entidad/modelo/repos listos, permiso de lectura
corregido — ambas historias pueden arrancar.

---

## Phase 3: User Story 1 — Asignar Encargado al crear el ticket (P1) 🎯 MVP

**Goal**: al crear un ticket, poder elegir un Encargado de la lista del Cliente seleccionado; el
detalle del ticket lo muestra como "Encargado solicitante". **Independent Test**: Escenarios 1 y
2 del quickstart.

- [X] T008 [US1] `backend/domain/services/ticket_service.py`: `validate_create` valida que, si
  viene `client_contact_id`, pertenezca al `client_id` del ticket (404 si no existe, 409
  `client_contact_mismatch` si es de otro cliente) — nuevo parámetro `client_contacts_repo`
  (depende de T006)
- [X] T009 [US1] `backend/api/routes/tickets.py`: `_ticket_input` swagger + `POST` parsea y valida
  `client_contact_id` en la rama de personal interno (se ignora en la rama `is_encargado`, que no
  lo lee) (depende de T008)
- [X] T010 [US1] `backend/api/routes/tickets.py`: `_requester()` prioriza `client_contact_id`
  (resuelve `client_contact` → su `user`) antes de caer al comportamiento ya existente por
  `created_by`; `_ticket_detail_out`/`_ticket_detail()` exponen `client_contact_id` crudo (depende
  de T006, T009)
- [X] T011 [P] [US1] Test dominio `backend/tests/domain/test_ticket_service_client_contact.py`:
  `validate_create` acepta Encargado del cliente correcto, rechaza de otro cliente (409), rechaza
  inexistente (404), acepta `None` (depende de T008)
- [X] T012 [P] [US1] Test API `backend/tests/api/test_tickets_client_contact.py`: creación con
  `client_contact_id` válido → `requester` lo refleja; cliente sin encargados no bloquea la
  creación; Encargado autoservicio no se ve afectado (su `requester` sigue igual que antes,
  escenario 4 del spec) (depende de T009, T010)
- [X] T013 [US1] Frontend `frontend/src/types/ticket.ts`: `client_contact_id?: string | null` en
  `TicketFormData` y en `TicketDetail`
- [X] T014 [US1] Frontend `frontend/src/pages/TicketsPage.tsx`: `Select` "Encargado" junto a
  Cliente/Proyecto (sin tocarlos), poblado con `clientContactService.list({ client_id })`,
  filtrado al Cliente elegido; vacío/deshabilitado con aviso claro si el cliente no tiene
  encargados, sin bloquear la creación (depende de T007, T013)

**Checkpoint US1**: Escenarios 1 y 2 del quickstart ejecutables end-to-end.

---

## Phase 4: User Story 2 — Corregir o asignar el Encargado después de creado (P2)

**Goal**: desde el detalle del ticket, asignar o cambiar el Encargado solicitante en cualquier
momento salvo Cerrado/Cancelado, y nunca si el ticket fue creado por un Encargado (autoservicio).
**Independent Test**: Escenarios 3 y 4 del quickstart.

- [X] T015 [US2] `backend/domain/services/ticket_service.py`: agregar `client_contact_id` a
  `PATCHABLE_FIELDS`; `validate_patch` valida pertenencia al cliente (mismo criterio que T008) y
  rechaza con 409 `requester_immutable` si `ticket.created_by` tiene rol Encargado (FR-009) —
  nuevo parámetro `client_contacts_repo`/`users_repo` (depende de T008, mismo archivo)
- [X] T016 [US2] `backend/api/routes/tickets.py`: `patch()` pasa los repos nuevos a
  `validate_patch` (depende de T015)
- [X] T017 [P] [US2] Test dominio (mismo archivo de T011): `validate_patch` acepta reasignar a
  otro Encargado del mismo cliente, rechaza de otro cliente, rechaza si el creador es Encargado,
  respeta `FIELD_LOCKS` en Cerrado/Cancelado (depende de T015, T011)
- [X] T018 [P] [US2] Test API (mismo archivo de T012): `PATCH` asigna/corrige el Encargado; 409
  `requester_immutable` sobre ticket creado por Encargado; 409 `field_locked` en Cerrado/Cancelado
  (depende de T016, T012)
- [X] T019 [US2] Frontend `frontend/src/pages/TicketDetailPage.tsx`: `Select` editable "Encargado"
  en "Clasificación" (mismo patrón ya usado para Prioridad/Severidad/Tiempo estimado): editable
  solo si `canEdit`, no bloqueado por `locked_fields`, y el origen no es automático (no mostrar
  editable cuando `client_contact_id` es `null` y `requester.is_encargado` es `true` — FR-009);
  reutiliza el mismo Tag ya existente de Fase 2.1 para mostrarlo en modo lectura (depende de T013,
  T014, T016)

**Checkpoint US2**: Escenarios 3 y 4 del quickstart completos — ambas historias funcionan
independientemente.

---

## Phase 5: Polish y validación transversal

- [X] T020 [P] Swagger revisado: `_ticket_input`/`_ticket_detail_out` (`client_contact_id`),
  nuevas respuestas 404/409 documentadas en `POST`/`PATCH /api/tickets` y `GET
  /api/client-contacts` según `contracts/tickets-delta.md`
- [ ] T021 Ejecutado `quickstart.md` (Escenarios 1-6) contra Docker real: creación con/sin
  Encargado, autoservicio sin cambios, edición/corrección posterior, bloqueo por origen automático
  y por estado, limpieza al cambiar Cliente, Resolutor puede listar Encargados sin 403
- [X] T022 [P] Validación dirigida únicamente (directriz explícita del solicitante — NO correr la
  suite completa de pytest de forma masiva): `pytest tests/domain/test_ticket_service_client_contact.py
  tests/api/test_tickets_client_contact.py -v` → 20/20 passed; `cd frontend && npx tsc -b` → sin
  errores

**Checkpoint Final**: quickstart completo en verde, tests dirigidos en verde, sin ejecutar la
suite completa del proyecto.

---

## Dependencies & Execution Order

```
Phase 1 (T001) → Phase 2 (T002 → T003 → T004 → T005; T006∥; T007∥)
Phase 2 → Phase 3/US1 (T008 → T009 → T010; T011∥ → ; T012∥; T013 → T014)
Phase 3/US1 (T008, T011) → Phase 4/US2 (T015 → T016; T017∥; T018∥;
                             T013,T014,T016 → T019)
Todo → Phase 5 (T020∥, T021, T022∥)
```

- US1 es el MVP: sin Encargado seleccionable no hay nada que corregir después.
- US2 depende de US1 porque reutiliza el mismo archivo de servicio (`ticket_service.py`) y los
  mismos archivos de test — no porque la funcionalidad en sí dependa lógicamente (podrían haberse
  planeado en paralelo con dos desarrolladores coordinando esos archivos compartidos).
- El fix de permiso (T007) es prerequisito de **ambas** pantallas frontend (T014, T019), por eso
  vive en Foundational y no dentro de una historia puntual.

## Parallel Example: Foundational

```bash
# Tras T002 (migración):
Task: "Entidad backend/domain/entities/ticket.py"           # T003

# En paralelo con la cadena de T003→T004→T005:
Task: "Repo backend/infra/repositories/client_contact_repo.py — get_by_id"   # T006
Task: "Permiso backend/api/routes/client_contacts.py — GET"                  # T007
```

## Parallel Example: User Story 1

```bash
# Tras T009/T010 (endpoint + _requester):
Task: "Test API backend/tests/api/test_tickets_client_contact.py"     # T012

# Tras T008 (validate_create):
Task: "Test dominio backend/tests/domain/test_ticket_service_client_contact.py"  # T011

# En paralelo con el trabajo de backend:
Task: "Tipos TS frontend/src/types/ticket.ts"                          # T013
```

---

## Implementation Strategy

1. **MVP = Phase 1 + Phase 2 + US1**: Encargado seleccionable al crear el ticket, visible en el
   detalle, funcionando end-to-end.
2. Incremento: US2 (corregir/asignar después) — depende de que Foundational y US1 ya estén.
3. Cada checkpoint valida su escenario del quickstart antes de avanzar.
4. Alcance acotado a los archivos listados arriba — sin tocar Cliente ni Proyecto, sin crear
   tablas nuevas, sin nuevas dependencias.

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- [Story] mapea la tarea a su user story para trazabilidad
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
