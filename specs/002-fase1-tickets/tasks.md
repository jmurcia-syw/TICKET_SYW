# Tasks: Fase 1 — Tickets

**Input**: Design documents from `specs/002-fase1-tickets/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tareas agrupadas por User Story para implementación y validación
independiente. Tests incluidos (la Constitución exige verificación y el quickstart define
negativos críticos de seguridad/FSM).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] registro/consulta, [US2] Triage Push, [US3] ciclo de vida, [US4] panel

---

## Phase 1: Setup

- [x] T001 Agregar `transitions` a `backend/requirements.txt` (única dependencia nueva,
  aprobada en Constitución) y rebuild de la imagen backend (`docker compose build backend`)
- [x] T002 [P] Crear volumen/directorio de adjuntos: carpeta `uploads/` en la raíz (montada
  ya vía `.:/repo`), agregar `uploads/` a `.gitignore`, y `backend/infra/storage/__init__.py`
- [x] T003 [P] Crear `backend/domain/fsm/__init__.py` y estructura de carpetas nuevas del
  plan (`backend/api/routes/{assignment_panel,notifications,catalogs}.py` vacíos no —
  se crean en sus tareas; solo los paquetes `fsm/` y `storage/`)

**Checkpoint**: imagen backend con `transitions`; estructura lista.

---

## Phase 2: Foundational (bloqueante para todas las stories)

### Migración y modelos base

- [x] T004 Migración `backend/infra/migrations/versions/011_create_tickets.py` según
  data-model.md: secuencia `ticket_number_seq`; tablas `tickets` (+CHECKs e índices),
  `ticket_comments`, `comment_attachments`, `ticket_status_transitions`,
  `ticket_assignments` (context JSONB), `notifications`, `catalog_tools`,
  `catalog_processes`, `catalog_resolution_types` (+seed de valores iniciales); seed de
  permisos `tickets` (view/create/edit/assign/transition/cancel), `assignment_panel:view`,
  `catalogs` (view/create/deactivate) con la matriz por rol del data-model.md
- [x] T005 [P] Entidades de dominio: `backend/domain/entities/ticket.py` (Ticket + enums
  estado/tipo/prioridad/severidad/nivel + FIELD_LOCKS), `comment.py` (Comment +
  CommentType + visibilidad), `notification.py`
- [x] T006 [P] FSM `backend/domain/fsm/ticket_fsm.py` con `python-transitions`: las 16
  transiciones de la matriz (data-model.md), estados finales cerrado/cancelado, API
  `can_transition(from, trigger)` y `apply(ticket, trigger)` — sin imports de Flask/SQLAlchemy
- [x] T007 Modelos SQLAlchemy: `backend/infra/models/ticket_model.py` (TicketModel,
  StatusTransitionModel, AssignmentModel), `comment_model.py` (CommentModel,
  AttachmentModel), `notification_model.py`, `catalog_model.py` (3 catálogos)
- [x] T008 Repositorios: `backend/infra/repositories/ticket_repo.py` (list con filtros
  combinables + next_ticket_number por secuencia), `comment_repo.py`,
  `notification_repo.py`, `catalog_repo.py`
- [x] T009 [P] Storage de adjuntos `backend/infra/storage/attachments.py`: guardar
  (valida tamaño/tipo, ruta `uploads/tickets/{ticket_id}/{uuid}-{filename}`), abrir stream,
  borrar huérfanos

### Enforcement de seguridad (FR-022 — cierra deuda Fase 0)

- [x] T010 Reescribir `backend/api/middleware/rbac.py`: decorador
  `@require_permission(module, action)` que reutiliza `jwt_required_active`, carga permisos
  del rol una vez por request (cache en `g`), 403 genérico sin detalle; manejar la
  excepción JWT→401 explícito (patrón ya aplicado en compensación)
- [x] T011 Aplicar `@require_permission` a TODAS las rutas de maestros existentes:
  `clients.py` (módulo clients), `projects.py`, `resources.py` (resources/skills;
  compensación ya protegida — migrarla al decorador común), `users.py`, `roles.py`,
  `permissions.py` (módulo roles). Mantener la excepción "propio perfil" del Resolutor en
  el servicio. Rutas públicas intactas: login, google, health
- [x] T012 [P] Actualizar `frontend/src/services/apiClient.ts` si hace falta (interceptor
  401 → redirigir a login limpiando sesión) y verificar que todas las pantallas de
  maestros siguen operando con enforcement activo
- [x] T013 [P] Tests de enforcement en `backend/tests/api/test_enforcement.py`: sin token →
  401 en maestros y tickets; token de rol sin permiso → 403 genérico; con permiso → 200
  (Escenario 1 del quickstart)
- [x] T014 [P] Tests de dominio FSM en `backend/tests/domain/test_ticket_fsm.py`: las 16
  transiciones válidas pasan; una muestra representativa de inválidas (nuevo→resuelto,
  cerrado→cualquiera, etc.) es rechazada

**Checkpoint**: migración 011 aplicada, FSM verificada, API completa protegida —
`docker exec sywork_backend python -m pytest tests/ -q` en verde.

---

## Phase 3: User Story 1 — Registro y consulta de tickets (P1) 🎯 MVP

**Goal**: crear tickets (nacen en NUEVO con consecutivo), listarlos con filtros y ver el
detalle con historial. **Independent Test**: Escenario 2 del quickstart.

- [x] T015 [US1] `backend/domain/services/ticket_service.py`: validaciones de creación
  (cliente activo, proyecto activo y del cliente, catálogos activos, related <> self),
  formato `TK-{n:06d}`, y validación de PATCH contra FIELD_LOCKS (409 field_locked)
- [x] T016 [US1] Rutas `backend/api/routes/catalogs.py`: GET/POST/activate/deactivate por
  catálogo con bloqueo por uso (contracts/notifications-catalogs.md), Swagger completo,
  registradas en `app.py`
- [x] T017 [US1] Rutas `backend/api/routes/tickets.py` (parte 1): GET lista con filtros,
  POST crear, GET /{id} detalle (con `locked_fields`, `close_eligible`, comments,
  transitions, assignments embebidos), PATCH edición — según contracts/tickets.md;
  registrar namespace en `app.py`
- [x] T018 [P] [US1] Tests API `backend/tests/api/test_tickets_crud.py`: creación ok (nace
  NUEVO, consecutivo), proyecto de otro cliente → 400/409, filtros combinados, PATCH campo
  bloqueado → 409, PATCH status → 400
- [x] T019 [P] [US1] Tipos TS `frontend/src/types/ticket.ts` y `catalog.ts` (según
  contratos: TicketListItem, TicketDetail, TicketFormData, enums de estado/prioridad/
  severidad con labels en español, Catalog)
- [x] T020 [P] [US1] Servicios `frontend/src/services/ticketService.ts` y
  `catalogService.ts`
- [x] T021 [US1] `frontend/src/components/tickets/TicketStatusTag.tsx` (badge por estado) y
  `frontend/src/pages/TicketsPage.tsx`: tabla con filtros combinables (estado multi,
  cliente, proyecto, prioridad, asignado, búsqueda), paginación, botón "Nuevo ticket" con
  modal de creación (selectores de cliente/proyecto activos y catálogos)
- [x] T022 [US1] `frontend/src/pages/TicketDetailPage.tsx` (versión US1): cabecera con
  clasificación, campos editables según `locked_fields`, historial de transiciones;
  ruta `/tickets/:id`
- [x] T023 [US1] `frontend/src/pages/CatalogsPage.tsx` (administración simple de los 3
  catálogos) + rutas `/tickets`, `/catalogs` y entradas de menú por permiso `tickets:view`
  / `catalogs:view` en `navigation.tsx` y `App.tsx`

**Checkpoint US1**: Escenario 2 del quickstart ejecutable end-to-end.

---

## Phase 4: User Story 2 — Triage Push y Gold Standard Dataset (P1)

**Goal**: asignar desde NUEVO/PRE-ANÁLISIS con comentario automático, notificación y
registro de contexto. **Independent Test**: Escenario 3 del quickstart.

- [x] T024 [US2] `backend/domain/services/assignment_service.py`: valida recurso activo y
  transición FSM (modes resolver/pre_analysis), construye snapshot de contexto (skills,
  tickets abiertos del asignado, prioridad, severidad), genera comentario automático
  tipo asignado/pre_analisis
- [x] T025 [P] [US2] `backend/domain/services/notification_service.py`: creación de
  notificaciones por evento (assigned, user_replied, resolution_rejected, closed,
  close_eligible) con mensajes en español
- [x] T026 [US2] Endpoint `POST /api/tickets/{id}/assign` en `tickets.py` (permiso
  `tickets:assign`): operación atómica assign+comment+assignment+notification según
  contrato; y rutas `backend/api/routes/notifications.py` (GET propias con unread_count,
  PATCH /read)
- [x] T027 [P] [US2] Tests API `backend/tests/api/test_assign.py`: asignación resolver →
  CONTACTO + comentario + fila assignment con context JSONB completo; pre_analysis →
  PRE-ANÁLISIS; reasignación conserva histórico; recurso inactivo → 400; desde estado
  inválido → 409; vía curl/API directa idéntico a UI
- [x] T028 [P] [US2] `frontend/src/types/notification.ts` +
  `frontend/src/services/notificationService.ts`
- [x] T029 [US2] `frontend/src/components/tickets/AssignModal.tsx`: selector de resolutor
  activo mostrando skills y conteo de tickets abiertos; botones "Asignar" y "Pre-Análisis
  (QM)"; visible con permiso `tickets:assign` desde TicketDetailPage y TicketsPage
- [x] T030 [US2] `frontend/src/components/common/NotificationBell.tsx` en el header del
  Dashboard: badge de no-leídas, dropdown con lista, marcar leídas, polling 60 s +
  refresco al navegar

**Checkpoint US2**: Escenario 3 completo, incluido el SELECT del Gold Standard Dataset.

---

## Phase 5: User Story 3 — Ciclo de vida por comentarios tipificados (P2)

**Goal**: camino feliz NUEVO→CERRADO solo con comentarios/botones de la matriz, con
adjuntos, bloqueos y negativos. **Independent Test**: Escenario 4 del quickstart.

- [x] T031 [US3] `backend/domain/services/comment_service.py`: mapa tipo→trigger FSM,
  validación de tipo permitido por estado y de autoría (Resolutor solo sus asignados,
  FR-028; Coordinador/QM/Admin cualquiera), efectos colaterales (resolved_at en
  solicitud_cierre, notificaciones user_replied)
- [x] T032 [US3] Endpoints en `tickets.py` (parte 2): `POST /{id}/comments`
  (multipart+JSON, adjuntos vía storage), `POST /{id}/testing` (toggle EN PRUEBAS),
  `POST /{id}/resolution` (accepted true/false), `POST /{id}/close` (valida
  resolution_type + descripcion_solucion + elegibilidad; notifica Coordinador y QM),
  `POST /{id}/cancel` (permiso tickets:cancel), `GET /{id}/attachments/{aid}` (descarga
  autenticada) — todo según contrato
- [x] T033 [P] [US3] Tests API `backend/tests/api/test_lifecycle.py`: camino feliz completo
  del Escenario 4; negativos: comentario inválido para el estado → 409 con acciones
  válidas, cierre sin tipo de resolución → bloqueado, resolutor ajeno → 403, adjunto
  >10 MB → 400, rechazo de resolución → EN EJECUCIÓN + notificación
- [x] T034 [P] [US3] `frontend/src/components/tickets/CommentThread.tsx`: hilo cronológico
  con tipo (tag), visibilidad interno/externo, autor, adjuntos descargables
- [x] T035 [US3] `frontend/src/components/tickets/CommentComposer.tsx`: selector de tipo
  válido según estado actual (la API informa las acciones válidas), cuerpo, subida de
  adjuntos (límite visible), y botones de acción de estado (EN PRUEBAS toggle,
  aceptar/rechazar resolución, cerrar con tipo de resolución, cancelar con motivo por
  permiso)
- [x] T036 [US3] Integrar CommentThread + CommentComposer en `TicketDetailPage.tsx`;
  refrescar `status`/`locked_fields` tras cada acción; deshabilitar campos bloqueados

**Checkpoint US3**: Escenario 4 completo (feliz + negativos).

---

## Phase 6: User Story 4 — Panel de Asignación (P2)

**Goal**: matriz resolutor × estado + NUEVOs asignables inline.
**Independent Test**: Escenario 5 del quickstart.

- [x] T037 [US4] Endpoint `GET /api/assignment-panel` en
  `backend/api/routes/assignment_panel.py` (permiso `assignment_panel:view`): matriz de
  conteos por resolutor y estado (query agregada sobre índice assignee+status), lista de
  NUEVOs sin asignar, filtro `statuses`; registrar en `app.py`
- [x] T038 [P] [US4] Test API `backend/tests/api/test_assignment_panel.py`: conteos
  correctos con datos sembrados, filtro de estados, permiso (Resolutor → 403)
- [x] T039 [US4] `frontend/src/pages/AssignmentPanelPage.tsx`: tabla matriz con conteos
  clicables (→ listado filtrado), sección de NUEVOs con AssignModal inline (T029), filtro
  multi-estado; ruta `/assignment-panel` + menú por permiso `assignment_panel:view`

**Checkpoint US4**: Escenario 5 completo.

---

## Phase 7: Polish y validación transversal

- [x] T040 [P] Política RLS sobre `tickets` en migración complementaria
  `012_tickets_rls.py` según Decisión 9 de research.md (lectura autenticada; doble
  protección Principio IV)
- [x] T041 [P] Seed de ~500 tickets de prueba (script `backend/scripts/seed_tickets.py`)
  y verificación de SC-005 (panel < 2 s) y SC-008 (listado < 1 s)
- [x] T042 [P] Swagger revisado: todos los endpoints nuevos documentados con modelos y
  códigos de error; descripción general actualizada (ya sin la nota de "maestros sin JWT")
- [x] T043 Ejecutar quickstart.md completo (Escenarios 1-6 + checklist) contra el stack
  Docker; typecheck frontend (`npx tsc -b`) y suite completa backend en contenedor
- [x] T044 [P] Actualizar `docs/MER.md` con las 9 tablas nuevas (diagrama delta del
  data-model.md)

---

## Dependencies & Execution Order

```
Phase 1 (T001-T003) → Phase 2 (T004 → {T005,T006} → T007 → T008; T009∥; T010 → T011 → {T012,T013}; T014∥)
Phase 2 → US1 (T015 → {T016,T017} → T018; {T019,T020} → T021 → T022 → T023)
US1 → US2 (T024 → T026; T025∥ → T026; T027∥; T028 → T029 → T030)
US1+US2 → US3 (T031 → T032 → T033; T034∥ → T035 → T036)
US2 → US4 (T037 → {T038,T039})
Todo → Phase 7 (T040-T044)
```

- US1 es el MVP; US2 depende de US1 (tickets existentes); US3 depende de US2 (tickets
  asignados); US4 depende de US2 (asignación inline reutiliza AssignModal).

## Parallel Example: Phase 2

```
T005 (entidades) ∥ T006 (FSM)          — tras T004
T009 (storage) ∥ T013 (tests enf.) ∥ T014 (tests FSM) — archivos independientes
```

## Implementation Strategy

1. **MVP = Phase 1 + 2 + US1**: seguridad activada + tickets creables/consultables.
2. Incrementos independientes: US2 (triage) → US3 (ciclo de vida) → US4 (panel).
3. Cada checkpoint valida su escenario del quickstart antes de avanzar.
4. El enforcement (T010-T013) va en Foundational a propósito: si rompe algo de Fase 0,
   se detecta antes de construir encima.
