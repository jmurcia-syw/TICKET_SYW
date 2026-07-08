# Tasks: Registro de tiempo en el detalle del ticket, rol Encargado y navegación

**Input**: Design documents from `specs/005-ticket-tiempo-encargado-nav/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tareas agrupadas por User Story para implementación y validación
independiente. Tests incluidos (mismo criterio que Fases 1-2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] registro de tiempo embebido, [US2] tiempo estimado, [US3] rol Encargado,
  [US4] navegación/breadcrumb

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): `react-router-dom`
  6.28 (ya instalado) alcanza para pasar `state` en la navegación; sin cambios en
  `backend/requirements.txt` ni `frontend/package.json`
- [X] T002 [P] Confirmar `docker exec sywork_backend alembic current` → `017 (head)` antes de
  agregar las migraciones 018-021 de esta fase — confirmado, Docker corriendo

**Checkpoint**: sin cambios de dependencias; migraciones previas confirmadas en head.

---

## Phase 2: Foundational

**Nota**: las 4 historias de esta fase son independientes entre sí (US1 toca `work_sessions`,
US3 toca `client_contacts`/`tickets`, US2 y US4 son solo frontend) — no hay una base de datos o
entidad compartida que bloquee a todas. No se listan tareas foundational forzadas; cada historia
arranca directamente en su propia fase.

---

## Phase 3: User Story 1 — Registro de tiempo embebido en el detalle del ticket (P1) 🎯 MVP

**Goal**: cargar/ver/editar/eliminar registros de tiempo (con hora de inicio/fin opcionales)
directamente desde el detalle del ticket. **Independent Test**: Escenario 1 del quickstart.

- [X] T003 [US1] Migración `backend/infra/migrations/versions/018_work_sessions_start_end.py`:
  agrega `started_at`/`ended_at` (TIMESTAMPTZ, nullable) a `work_sessions` (depende de T002) —
  aplicada en Docker, `alembic current` → 018
- [X] T004 [US1] `backend/domain/entities/work_session.py`: agregar `started_at`/`ended_at`
  opcionales a `WorkSession` (depende de T003)
- [X] T005 [US1] `backend/domain/services/work_session_service.py`: nueva validación que calcula
  `duration_minutes` a partir de `started_at`/`ended_at` cuando ambos vienen presentes (exige que
  vengan juntos y que `ended_at > started_at`); si el caller envía `duration_minutes` explícito
  junto con el rango, se ignora y se usa el calculado (research.md Decisión 1) (depende de T004)
- [X] T006 [P] [US1] Tests de dominio
  `backend/tests/domain/test_work_session_service_start_end.py`: cálculo correcto de duración;
  error si falta uno de los dos extremos; error si `ended_at <= started_at`; `duration_minutes`
  explícito se ignora cuando hay rango (depende de T005) — 9/9 passed (100/100 tests de dominio
  sin regresión)
- [X] T007 [US1] `backend/infra/models/work_session_model.py`: agregar columnas
  `started_at`/`ended_at`; actualizar `to_entity()`/`from_entity()` (depende de T003, T004)
- [X] T008 [US1] `backend/api/routes/work_sessions.py`: aceptar y devolver `started_at`/
  `ended_at` en `POST`/`PATCH`/listado/detalle, según `contracts/work-sessions-delta.md`
  (depende de T005, T007)
- [X] T009 [P] [US1] Tests API `backend/tests/api/test_work_sessions_start_end.py`: creación con
  horas calcula la duración; duración manual sin horas sigue funcionando (compatibilidad con
  Fase 2); falta un extremo → 400; `ended_at<=started_at` → 400 (depende de T008) — 6/6 passed
  contra Docker/Postgres real (26/26 en total, sin regresión de Fase 2)
- [X] T010 [P] [US1] `frontend/src/types/workSession.ts`: agregar `started_at`/`ended_at`
  opcionales a `WorkSessionListItem`/`WorkSessionFormData`
- [X] T011 [US1] `frontend/src/components/worksessions/WorkSessionForm.tsx`: agregar campos hora
  de inicio/hora de fin (`Segmented` para elegir modo "Hora de inicio/fin" vs "Duración manual"),
  con opción de fijar la duración manualmente en vez de horas exactas (depende de T010)
- [X] T012 [US1] Nuevo `frontend/src/components/worksessions/TicketWorkSessions.tsx`: historial +
  alta/edición/borrado de registros de tiempo filtrados por `ticket_id` (reutiliza
  `WorkSessionForm` vía T011 y `workSessionService.list({ticket_id})` ya soportado), con el total
  acumulado del ticket (depende de T011)
- [X] T013 [US1] `frontend/src/pages/TicketDetailPage.tsx`: agregar sección "Registros de tiempo"
  usando `TicketWorkSessions`, visible para cualquier recurso que participe del ticket (depende
  de T012) — `npx tsc -b` sin errores

**Checkpoint US1**: Escenario 1 del quickstart ejecutable end-to-end.

---

## Phase 4: User Story 2 — Tiempo estimado de solución visible (P2)

**Goal**: mostrar el tiempo estimado (ya existente) en horas, junto al tiempo real acumulado.
**Independent Test**: Escenario 2 del quickstart.

- [X] T014 [US2] `frontend/src/pages/TicketDetailPage.tsx`: mostrar "Tiempo estimado de
  solución" convertido a horas (o "Sin estimar" si es `null`) junto al total de tiempo real de
  la sección T013 (depende de T013) — agregado como segundo `Statistic` dentro de
  `TicketWorkSessions`
- [X] T015 [P] [US2] Formulario de edición de tickets (`frontend/src/pages/TicketDetailPage.tsx`):
  el campo de estimado ahora se edita en horas (`InputNumber` con `addonAfter="h"`, paso 0.5) y
  se convierte a minutos al enviar (`estimated_resolution_minutes` sin cambios de contrato ni de
  `FIELD_LOCKS`) — **nota**: no se tocó el formulario de creación en `TicketsPage.tsx` porque hoy
  no incluye ese campo al crear (solo se carga después, en el detalle, igual que antes de esta
  fase); fuera del alcance pedido

**Checkpoint US2**: Escenario 2 del quickstart completo.

---

## Phase 5: User Story 3 — Rol "Encargado" (P2)

**Goal**: usuarios externos vinculados a un Cliente fijo que solo crean/ven sus propios tickets,
visibles como solicitante distinto del Cliente. **Independent Test**: Escenario 3 del quickstart.

- [X] T016 [US3] Migración `backend/infra/migrations/versions/019_create_client_contacts.py`:
  tabla `client_contacts` (`user_id` FK `users.id` UNIQUE, `client_id` FK `clients.id`) (depende
  de T003, mismo orden de revisión Alembic) — aplicada en Docker
- [X] T017 [US3] Migración `backend/infra/migrations/versions/020_client_contacts_rls.py`: RLS en
  `client_contacts`, mismo patrón app-level que `012_tickets_rls.py`/`016_work_sessions_rls.py`
  (depende de T016) — aplicada en Docker
- [X] T018 [US3] Migración
  `backend/infra/migrations/versions/021_encargado_role_permissions.py`: seed del rol
  "Encargado"; permiso nuevo `tickets:view_own` (solo Encargado); agregar Encargado como rol
  adicional del permiso `tickets:create` ya existente; permiso nuevo `client_contacts:manage`
  (Admin, Coordinador) (depende de T017) — aplicada en Docker, `alembic current` → 021. Incluye
  además el `DROP` de `ck_users_email_domain` (decisión confirmada con el usuario): el Encargado
  usa su email externo real, no `@sywork.net`; el resto de roles internos sigue exigiéndolo a
  nivel de aplicación en `backend/api/routes/users.py` (sin cambios ahí)
- [X] T019 [P] [US3] `backend/domain/entities/client_contact.py`: entidad `ClientContact` pura
  (id, user_id, client_id, created_at)
- [X] T020 [US3] `backend/infra/models/client_contact_model.py` +
  `backend/infra/repositories/client_contact_repo.py`: `create()`, `get_by_user_id()`,
  `list_paginated(client_id=None)` (depende de T016, T019)
- [X] T021 [US3] `backend/domain/services/client_contact_service.py`: valida cliente
  existente/activo y email no duplicado antes de crear el `User` (rol Encargado) + su fila en
  `client_contacts` (depende de T019)
- [X] T022 [P] [US3] Tests de dominio/repo
  `backend/tests/domain/test_client_contact_service.py` (4 tests) +
  `backend/tests/infra/test_client_contact_repo.py` (3 tests) — 7/7 passed (depende de T020,
  T021)
- [X] T023 [US3] Endpoint `backend/api/routes/client_contacts.py`: `POST`/`GET
  /api/client-contacts` (permiso `client_contacts:manage`), según `contracts/tickets-delta.md`;
  registrado el namespace en `backend/app.py` (depende de T021)
- [X] T024 [US3] `backend/api/routes/tickets.py` (list + detail): reemplazado
  `@require_permission("tickets","view")` por el nuevo decorador `require_authenticated()`
  (agregado en `backend/api/middleware/rbac.py`, mismo patrón try/except de `require_permission`
  para mapear JWT ausente a 401) + chequeo manual `current_user_has("tickets","view") or
  current_user_has("tickets","view_own")`, filtrando por `created_by = caller` cuando solo hay
  `view_own` (ignora el resto de filtros); detalle devuelve 404 (no 403) si el ticket ajeno no es
  visible (depende de T018)
- [X] T025 [US3] `backend/api/routes/tickets.py` (creación): si el caller tiene rol Encargado,
  completa `ticket_type/priority/severity` con defaults (`incident`/`medium`/`s3`) y resuelve
  `client_id` desde `client_contacts.get_by_user_id`; 409 `no_client_contact` si no tiene fila
  (depende de T020, T024)
- [X] T026 [US3] `backend/api/routes/tickets.py` (detalle): expone `requester` (`created_by`
  resuelto a `{id, name, is_encargado}`) en la respuesta, según `contracts/tickets-delta.md`
  (depende de T024)
- [X] T027 [P] [US3] Tests API `backend/tests/api/test_tickets_encargado.py` (8 tests): creación
  simplificada + Cliente auto-asignado; ignora campos extra enviados; requiere title/description;
  Encargado solo ve sus propios tickets (list filtra, detail ajeno → 404); Admin sigue viendo
  todos; `requester.is_encargado` correcto; 409 `no_client_contact` sin fila — 8/8 passed (depende
  de T025, T026)
- [X] T028 [P] [US3] Tests API `backend/tests/api/test_client_contacts_api.py` (6 tests): alta
  ok, email duplicado → 409, cliente inexistente → 404, cliente inactivo → 404 (client_not_found,
  según contrato), listado filtrado por cliente, 403 para Resolutor — 6/6 passed (depende de
  T023)
- [X] **Fix descubierto en verificación manual** — `backend/api/routes/notifications.py`
  dependía únicamente de `tickets:view` (comentario original: "lo tienen los 4 roles seed"), sin
  contemplar que Encargado solo tiene `tickets:view_own` — rompía la campana de notificaciones
  con 403 al loguearse como Encargado real en el navegador. Reemplazado por
  `require_authenticated()` + chequeo manual `tickets:view OR tickets:view_own` (mismo patrón que
  T024). Test de regresión agregado:
  `test_encargado_can_list_own_notifications` en `test_tickets_encargado.py`. Suite completa
  backend: 254/254 passed, sin regresión.
- [X] T029 [US3] Frontend `frontend/src/types/clientContact.ts` +
  `frontend/src/services/clientContactService.ts`: tipos y llamadas a `/api/client-contacts`
  (depende de T023)
- [X] T030 [US3] Frontend: nuevo `frontend/src/pages/ClientContactsPage.tsx` (alta de Encargados
  para Admin/Coordinador, patrón simplificado tipo `TeamPage.tsx`), ruta `/client-contacts` en
  `App.tsx` y entrada de menú "Encargados" en Maestros con permiso `client_contacts:manage`
  (depende de T029)
- [X] T031 [US3] Frontend `frontend/src/pages/TicketsPage.tsx`: formulario de creación
  simplificado (solo título/descripción) cuando `useAuthStore().role?.name === 'Encargado'`;
  oculta filtros/campos que dependen de catálogos internos (cliente/tipo/prioridad/severidad/
  herramienta/proceso) y evita las llamadas a esos endpoints (403 innecesarios) (depende de T029)
- [X] T032 [US3] Frontend `frontend/src/config/navigation.tsx` (nuevo campo `action` en
  `NavLeaf`, acepta lista de acciones alternativas — Tickets ahora usa `['view','view_own']`) +
  `App.tsx` + `ProtectedRoute.tsx` (mismo soporte de lista de acciones): el rol Encargado ve/
  accede solo a Tickets (creación/listado propio); sin entradas de menú ni rutas accesibles a
  Kanban, Panel de Asignación, Maestros, Registro/Reporte de Tiempos (depende de T031)
- [X] T033 [US3] Frontend `frontend/src/pages/TicketDetailPage.tsx`: nuevo
  `Descriptions.Item label="Encargado solicitante"` (Tag distintivo) usando
  `ticket.requester.is_encargado` de T026, mostrado junto a Cliente y diferenciado visualmente
  (depende de T026, T013). `npx tsc -b` sin errores

**Checkpoint US3**: Escenario 3 del quickstart completo.

---

## Phase 6: User Story 4 — Navegación con origen correcto (P3)

**Goal**: "Volver" desde el detalle del ticket regresa exactamente a la pantalla de origen
(Kanban, Tickets con filtros, o Panel de Asignación). **Independent Test**: Escenario 4 del
quickstart.

- [X] T034 [US4] `frontend/src/pages/KanbanPage.tsx`: al navegar al detalle, pasa
  `state: { from: { pathname: '/kanban', label: 'Kanban' } }`
- [X] T035 [P] [US4] `frontend/src/pages/TicketsPage.tsx`: al navegar al detalle (botón "Ver
  detalle"), pasa `state: { from: { pathname: '/tickets', label: 'Tickets' } }` — los filtros de
  esta pantalla viven en estado local (no en la URL, ver research.md Decisión 5/Assumptions), así
  que no hay `search` que preservar; queda fuera de alcance mover los filtros a query params
- [X] T036 [P] [US4] `frontend/src/pages/AssignmentPanelPage.tsx`: al navegar al detalle (columna
  "Número" de Pendientes de triage), pasa
  `state: { from: { pathname: '/assignment-panel', label: 'Panel de Asignación' } }`
- [X] T037 [US4] Nuevo `frontend/src/components/tickets/TicketBreadcrumb.tsx`: lee
  `useLocation().state?.from`; si existe, "Volver a {label}" navega a `pathname`; si no existe,
  "Volver" navega a `/tickets` por defecto (FR-013) (depende de T034, T035, T036)
- [X] T038 [US4] `frontend/src/pages/TicketDetailPage.tsx`: reemplazado el botón "Volver" fijo
  (`navigate('/tickets')`) por `<TicketBreadcrumb />`; removidos `useNavigate`/`ArrowLeftOutlined`
  que quedaron sin uso (depende de T037). Verificado en navegador con Docker real: Kanban → detalle
  → "Volver a Kanban" → `/kanban` ✓; Panel de Asignación → detalle → "Volver a Panel de
  Asignación" → `/assignment-panel` ✓; Tickets → detalle → "Volver a Tickets" → `/tickets` ✓;
  acceso directo por URL → "Volver" (sin sufijo) → `/tickets` ✓. `npx tsc -b` sin errores

**Checkpoint US4**: Escenario 4 del quickstart completo — todas las historias funcionan
independientemente.

---

## Phase 7: Polish y validación transversal

- [X] T039 [P] Swagger revisado: `work_sessions` delta (`started_at`/`ended_at` en input/patch/
  output), `client_contacts` (namespace completo, `_client_contact_input/out/list/create_out`),
  y `requester` en `TicketDetail` (`_requester_out`) documentados con modelos y códigos de error
  (400/401/403/404/409/500) en cada endpoint nuevo o modificado
- [X] T040 [P] Actualizado `docs/MER.md`: nueva sección "Ampliación Fase 2.1" con diagrama
  `client_contacts`, extensión de `work_sessions` (started_at/ended_at), reglas del rol
  Encargado/permisos, y la nota sobre el CHECK de dominio de email relajado
- [X] T041 Ejecutado `quickstart.md` (Escenarios 1-5) contra Docker real:
  - Escenario 1 (US1): verificado en la sesión previa — POST con started_at/ended_at → 201,
    duración calculada (90 min), visible en la tabla embebida con "09:00 – 10:30" / "1h 30m"
  - Escenario 2 (US2): verificado — "Tiempo estimado: Sin estimar" junto al total real
  - Escenario 3 (US3): verificado en navegador real (no solo tests) — Admin crea Encargado
    (`juan.perez@arismining.com`) vía `/client-contacts`; login como Encargado → sidebar reducido
    a solo "Tickets"; crea ticket con solo título/descripción → Cliente auto-resuelto a "Aris
    Mining", P3/S3, `requester.is_encargado: true`; listado propio muestra únicamente ese ticket;
    Admin ve el ticket con "Encargado solicitante: juan.perez" junto a "Cliente: Aris Mining"
  - Escenario 4 (US4): verificado en navegador — Kanban/Panel de Asignación/Tickets → detalle →
    "Volver a {origen}" regresa exactamente ahí; acceso directo por URL → "Volver" (sin sufijo) →
    `/tickets`. **Nota de alcance** (ya documentada en research.md Decisión 5/Assumptions): los
    filtros de `TicketsPage` viven en estado local, no en la URL, por lo que no se preservan al
    volver — el escenario 4.2 del quickstart ("con ese mismo filtro aplicado") no aplica hasta
    que los filtros se muevan a query params, explícitamente fuera de alcance de esta fase
  - Escenario 5 (regresión): 254/254 tests backend passed (`docker exec sywork_backend pytest -q`,
    sin regresión de Fases 0-2); `npx tsc -b` frontend sin errores
  - Bug real encontrado y corregido durante la verificación manual: ver nota en T028
    (`notifications.py` rechazaba a Encargado con 403)
- [X] T042 [P] Verificado manualmente: SC-004 (Encargado nunca ve tickets ajenos) — confirmado
  con 1 Encargado real en navegador (solo ve su propio ticket entre 300+ tickets sembrados) +
  test automatizado con 2 Encargados (`test_encargado_only_sees_own_tickets_in_list`). SC-005
  ("Volver" al origen correcto) — confirmado con los 3 orígenes (Kanban, Tickets, Panel de
  Asignación) + el caso de acceso directo, ver T038/T041

**Checkpoint Final**: quickstart completo en verde, suite de tests en verde, sin regresión en
Fases 0-2.

---

## Dependencies & Execution Order

```
Phase 1 (T001, T002∥) → Phase 3/US1 (T003 → T004 → T005 → T006∥; T007 → T008 → T009∥;
                          T010∥ → T011 → T012 → T013)
US1 (T013) → Phase 4/US2 (T014 → T015∥)
Phase 1 (T002) → Phase 5/US3 (T016 → T017 → T018; T019∥ → T020 → T021 → T022∥; T023;
                  T018 → T024 → T025 → T026 → T027∥; T023 → T028∥;
                  T023 → T029 → {T030, T031} → T032; {T026,T013} → T033)
Phase 6/US4 (T034∥, T035∥, T036∥ → T037 → T038) — independiente del resto, requiere solo T013
  para tener un detalle de ticket real donde probar
Todo → Phase 7 (T039∥, T040∥, T041, T042∥)
```

- US1 es el MVP; US2 depende de US1 (agrega el estimado a la misma sección de la pantalla que
  US1 crea); US3 es independiente de US1/US2 (solo comparte la migración de work_sessions en la
  cadena de revisiones de Alembic, no en lógica); US4 es independiente de las tres, solo necesita
  que exista un detalle de ticket navegable.
- T033 (mostrar "Encargado" en el detalle) depende tanto de US3 (T026, el campo `requester`)
  como de que la sección de US1 (T013) ya esté en la pantalla — por eso se etiqueta [US3] y no
  abre una historia nueva.

## Parallel Example: User Story 1

```bash
# Tras T005 (servicio de dominio):
Task: "Tests de dominio backend/tests/domain/test_work_session_service_start_end.py"  # T006

# Tras T008 (endpoint):
Task: "Tests API backend/tests/api/test_work_sessions_start_end.py"                   # T009

# En paralelo con el trabajo de backend:
Task: "Tipos TS frontend/src/types/workSession.ts"                                    # T010
```

## Parallel Example: User Story 3

```bash
# Tras T018 (migraciones):
Task: "Entidad backend/domain/entities/client_contact.py"          # T019

# Tras T023 (endpoint client-contacts):
Task: "Tests API backend/tests/api/test_client_contacts_api.py"    # T028
Task: "Frontend types/services clientContactService.ts"            # T029
```

---

## Implementation Strategy

1. **MVP = Phase 1 + US1**: registro de tiempo embebido en el ticket, funcionando end-to-end.
2. Incrementos independientes: US2 (estimado) → US3 (rol Encargado) → US4 (navegación) — en
   cualquier orden entre sí, ya que no dependen unas de otras.
3. Cada checkpoint valida su escenario del quickstart antes de avanzar.
4. US3 es la historia más grande (18 tareas) porque introduce una entidad nueva
   (`client_contacts`), un permiso nuevo (`tickets:view_own`) y una superficie de UI restringida
   completa (menú/rutas) — puede tratarse como su propio sprint si hace falta partir el trabajo.
5. US4 puede implementarse en paralelo con cualquiera de las otras tres por un segundo
   desarrollador, ya que solo toca páginas de navegación existentes sin dependencias de backend.

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- [Story] mapea la tarea a su user story para trazabilidad
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
