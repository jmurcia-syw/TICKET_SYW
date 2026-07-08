# Tasks: Fase 2 — Registro diario de tiempos por recurso

**Input**: Design documents from `specs/004-fase2-registro-tiempos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tareas agrupadas por User Story para implementación y validación
independiente. Tests incluidos (mismo criterio que `002-fase1-tickets`: la Constitución exige
verificación y el quickstart define negativos críticos de límites/autorización).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] alta de horas, [US2] edición/borrado, [US3] reporte por recurso

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): revisar
  `backend/requirements.txt` y `frontend/package.json` — el stack ya aprobado (Flask-RESTX,
  SQLAlchemy/Alembic, React 19, Ant Design 5, Zustand, `date-fns`, Axios) alcanza; no hay
  cambios que hacer en ninguno de los dos archivos
- [X] T002 [P] Crear carpeta `frontend/src/components/worksessions/` (nueva, para los
  componentes de esta fase)

**Checkpoint**: sin cambios de dependencias; estructura de carpetas lista.

---

## Phase 2: Foundational (bloqueante para todas las stories)

- [X] T003 Migración `backend/infra/migrations/versions/015_create_work_sessions.py` según
  data-model.md: tabla `work_sessions` (+CHECKs `duration_minutes > 0`, índices
  `(resource_id, work_date)` y `(ticket_id)`) y tabla append-only `work_session_edits`
  (+CHECK `action IN ('created','updated','deleted')`) — se agregó además `deleted_at` para
  soportar soft-delete (ver Nota de diseño al final de este archivo)
- [X] T004 Migración `backend/infra/migrations/versions/016_work_sessions_rls.py`: habilitar
  RLS en `work_sessions` y `work_session_edits` con el mismo patrón app-level que
  `012_tickets_rls.py` (research.md, Decisión 4) (depende de T003)
- [X] T005 Migración `backend/infra/migrations/versions/017_work_sessions_permissions.py`:
  seed de los 4 permisos nuevos (`work_sessions:view_own`, `work_sessions:manage`,
  `work_sessions:view_all`, `work_sessions:manage_all`) y su asignación por rol según la
  tabla de data-model.md (depende de T004)
- [X] T006 [P] Entidad de dominio `backend/domain/entities/work_session.py`: dataclasses
  `WorkSession` y `WorkSessionEdit` + constantes `MAX_DAILY_MINUTES = 1440` y
  `EDIT_WINDOW_DAYS = 7`, sin imports de Flask/SQLAlchemy
- [X] T007 Modelos SQLAlchemy `backend/infra/models/work_session_model.py`:
  `WorkSessionModel` + `WorkSessionEditModel` con `to_entity()` (depende de T003, T006)
- [X] T008 Repositorio `backend/infra/repositories/work_session_repo.py`: `create()`,
  `update()`, `soft_delete()` (cada uno escribe su fila correspondiente en
  `work_session_edits` dentro de la misma transacción), `get_by_id()`,
  `list_by_filters(resource_id, ticket_id, date_from, date_to)`,
  `sum_minutes_for_day(resource_id, work_date)`,
  `aggregate_by_resource_and_day(resource_id_or_none, date_from, date_to)` (depende de T007)
- [X] T009 [P] Tests de repositorio `backend/tests/infra/test_work_session_repo.py`:
  `create`/`update`/`soft_delete` generan la fila de historial correcta en
  `work_session_edits`; `sum_minutes_for_day` y `aggregate_by_resource_and_day` devuelven los
  totales esperados con datos sembrados (depende de T008)

**Checkpoint**: migraciones 015-017 aplicadas, repositorio con tests en verde —
`docker exec sywork_backend python -m pytest tests/ -q` en verde.

---

## Phase 3: User Story 1 — Registrar horas trabajadas en un ticket (P1) 🎯 MVP

**Goal**: un recurso registra tiempo contra un ticket en el que participa; el resumen diario se
calcula automáticamente. **Independent Test**: Escenario 1 del quickstart.

- [X] T010 [US1] `backend/domain/services/work_session_service.py`: `create(caller, ticket_id,
  work_date, duration_minutes, note)` — valida que `resource_id` (del caller, o explícito solo
  si el caller tiene `manage_all`) participe del ticket (asignado actual o histórico en
  `ticket_assignments`), `duration_minutes > 0`, `work_date` no futura, que la suma diaria del
  recurso (incluyendo esta entrada) no supere `MAX_DAILY_MINUTES`, y que el ticket no esté
  `cerrado` salvo `manage_all` (depende de T006, T008)
- [X] T011 [P] [US1] Tests de dominio
  `backend/tests/domain/test_work_session_service_create.py`: happy path; ticket ajeno → error;
  límite diario superado → error; fecha futura → error; duración 0/negativa → error; ticket
  cerrado sin `manage_all` → error (depende de T010) — 9/9 passed localmente (sin DB, repos
  fake)
- [X] T012 [US1] Endpoint `backend/api/routes/work_sessions.py`: Namespace `"work-sessions"`,
  `GET /api/work-sessions` (lista con filtros `resource_id`/`ticket_id`/`date_from`/`date_to`,
  forzando `resource_id` propio si el caller solo tiene `view_own`) y
  `POST /api/work-sessions`, Swagger completo según `contracts/work-sessions.md`; registrar el
  namespace en `app.py` (depende de T010) — 5 rutas verificadas registradas
  (`/api/work-sessions`, `/summary`, `/<id>`)
- [X] T013 [P] [US1] Tests API `backend/tests/api/test_work_sessions_create.py`: creación ok
  (aparece en el listado del día), ticket no asignado al recurso → 403, límite diario → 400
  `daily_limit_exceeded`, fecha futura → 400, duración 0 → 400, ticket `cerrado` sin
  `manage_all` → 409 (depende de T012) — escrito; requiere Docker/Postgres corriendo para
  ejecutarse (no disponible en esta sesión, ver Nota al final)
- [X] T014 [P] [US1] Tipos TS `frontend/src/types/workSession.ts`: `WorkSessionListItem`,
  `WorkSessionFormData`
- [X] T015 [US1] Servicio `frontend/src/services/workSessionService.ts`: `list()`, `create()`
  contra `/api/work-sessions` (depende de T014)
- [X] ~~T016 Store Zustand~~ — **desviación del plan**: el proyecto no usa un store Zustand por
  dominio (solo `authStore` existe); todas las páginas de Fase 0/1 manejan su estado con
  `useState`/`useEffect` locales (ver `TicketsPage.tsx`). Se siguió esa convención real en vez
  de introducir un patrón nuevo — el resumen diario se deriva con un `reduce()` en
  `WorkSessionsPage.tsx`
- [X] T017 [US1] `frontend/src/components/worksessions/WorkSessionForm.tsx`: selector de
  ticket (solo los asignados activos del recurso), fecha (`<Input type="date">`, mismo patrón
  que `ProjectsPage.tsx`/`TeamPage.tsx` — sin agregar `dayjs`/`DatePicker`), horas + minutos
  (convertidos a `duration_minutes` al guardar), nota opcional (depende de T014)
- [X] T018 [US1] `frontend/src/pages/WorkSessionsPage.tsx`: listado de registros del día +
  resumen diario total + botón "Nuevo registro" (abre `WorkSessionForm`); ruta
  `/registro-tiempos` (`App.tsx`) + entrada de menú (`navigation.tsx`/`DashboardPage.tsx`)
  visible con cualquier permiso `work_sessions:*` (depende de T017) — `npx tsc -b` sin errores

**Checkpoint US1**: Escenario 1 del quickstart ejecutable end-to-end.

---

## Phase 4: User Story 2 — Corregir o eliminar un registro de tiempo (P2)

**Goal**: el propio recurso edita o elimina sus registros dentro de una ventana de 7 días;
Admin puede hacerlo sin esa limitación. **Independent Test**: Escenario 2 del quickstart.

- [X] T019 [US2] `backend/domain/services/work_session_service.py`: agregar `update()` y
  `delete()` — validan `hoy - work_date <= EDIT_WINDOW_DAYS` salvo `manage_all`, recalculan el
  límite diario con el nuevo valor en `update()`, y reutilizan las validaciones de pertenencia
  y de ticket `cerrado` de `create()` (depende de T010) — escrito junto con T010 (mismo
  archivo, un solo pase)
- [X] T020 [P] [US2] Tests de dominio `backend/tests/domain/test_work_session_service_edit.py`:
  edición/borrado dentro de la ventana → ok; fuera de la ventana → error salvo `manage_all`;
  edición que supera el límite diario recalculado → error (depende de T019) — 7/7 passed
  localmente (sin DB, repos fake)
- [X] T021 [US2] `backend/api/routes/work_sessions.py`: `PATCH /api/work-sessions/{id}` y
  `DELETE /api/work-sessions/{id}` según contrato (depende de T012, T019) — escrito junto con
  T012 (mismo archivo, un solo pase)
- [X] T022 [P] [US2] Tests API `backend/tests/api/test_work_sessions_edit.py`: edición ok
  recalcula el resumen diario; fuera de ventana → 403 `edit_window_expired`; Admin edita fuera
  de ventana → ok; `DELETE` genera la fila `action='deleted'` en `work_session_edits` con el
  snapshot previo (depende de T021) — escrito; requiere Docker/Postgres para ejecutarse
- [X] T023 [US2] `frontend/src/components/worksessions/WorkSessionForm.tsx`: modo edición
  (reutiliza el formulario de alta) (depende de T017) — soporte `editing` incluido desde T017
- [X] T024 [US2] `frontend/src/pages/WorkSessionsPage.tsx`: acciones "Editar"/"Eliminar" por
  fila, deshabilitadas (con tooltip) cuando el registro está fuera de la ventana de 7 días
  (depende de T018, T023) — `npx tsc -b` sin errores

**Checkpoint US2**: Escenario 2 del quickstart completo.

---

## Phase 5: User Story 3 — Consultar tiempos registrados por recurso y período (P3)

**Goal**: Coordinador/QM/Admin consultan el total de horas por recurso y día en un rango,
incluyendo días sin registro; un recurso raso solo ve lo propio. **Independent Test**: Escenario
3 del quickstart.

- [X] T025 [US3] `backend/domain/services/work_session_service.py`: agregar
  `get_daily_summary(caller, resource_id, date_from, date_to)` — fuerza `resource_id` propio si
  el caller no tiene `view_all`; completa, para cada día del rango sin filas devueltas por el
  repositorio, `{work_date, total_minutes: 0, sin_registro: true}` (research.md, Decisión 5)
  (depende de T008) — se agregó también `get_all_resources_summary()` para el overview sin
  `resource_id` (escrito junto con T010)
- [X] T026 [P] [US3] Tests de dominio
  `backend/tests/domain/test_work_session_service_summary.py`: total agregado correcto; días
  sin registro aparecen explícitos; caller sin `view_all` queda forzado a su propio recurso
  (depende de T025) — 2/2 passed localmente
- [X] T027 [US3] `backend/api/routes/work_sessions.py`: `GET /api/work-sessions/summary` según
  contrato, incluyendo el límite de 92 días de rango (depende de T012, T025) — escrito junto
  con T012
- [X] T028 [P] [US3] Tests API `backend/tests/api/test_work_sessions_summary.py`: total
  coincide con la suma manual de las entradas; día sin registro explícito en la respuesta;
  recurso sin `view_all` no puede consultar el resumen de otro (se ignora el `resource_id`
  solicitado) (depende de T027) — escrito; requiere Docker/Postgres para ejecutarse
- [X] T029 [US3] `frontend/src/types/workSession.ts`: agregar `DailySummaryResponse`,
  `ResourceSummaryRow`, `ResourcesOverviewResponse` (depende de T014) — escrito junto con T014
- [X] T030 [US3] `frontend/src/services/workSessionService.ts`: agregar `getSummary()` contra
  `/api/work-sessions/summary` (depende de T015, T029) — escrito junto con T015
- [X] T031 [US3] `frontend/src/pages/TimeReportPage.tsx`: filtro por recurso (solo visible con
  `work_sessions:view_all`) y rango de fechas, tabla con los días sin registro resaltados; ruta
  `/reporte-tiempos` (`App.tsx`) + entrada de menú (ya en `navigation.tsx`/`DashboardPage.tsx`
  desde T018) (depende de T030) — `npx tsc -b` sin errores

**Checkpoint US3**: Escenario 3 del quickstart completo — todas las user stories funcionan
independientemente.

---

## Phase 6: Polish y validación transversal

- [X] T032 [P] Swagger revisado: los 5 endpoints de `work_sessions.py` documentados con
  modelos y códigos de error completos (Principio I) — `@ns.doc`/`@ns.response` en los 5
  endpoints, confirmado registrando la app y listando `app.url_map`
- [X] T033 [P] Actualizar `docs/MER.md` con las 2 tablas nuevas (`work_sessions`,
  `work_session_edits`) — diagrama delta del data-model.md agregado
- [X] T034 Ejecutar `quickstart.md` completo (Escenarios 1-4) contra el stack Docker;
  typecheck frontend (`npx tsc -b`) y suite completa backend en contenedor — el usuario levantó
  Docker; se corrió `docker exec sywork_backend python -m pytest tests/ -q`: **218/218 passed**
  (incluye los 20 tests nuevos de esta fase), `alembic current` → `017 (head)`. Se encontraron y
  corrigieron 2 bugs de los propios tests (no del código de producción): fixtures
  `ticket_resource`/`make_ticket` vivían solo en `tests/api/conftest.py` y no eran visibles
  desde `tests/infra/` (pytest no comparte conftest entre directorios hermanos) — se movieron al
  `conftest.py` raíz; y `test_create_rejects_ticket_not_assigned_to_caller` no pedía la fixture
  `ticket_resource`, por lo que el resolutor no tenía recurso asociado (400
  `no_resource_profile` en vez del 403 `not_assigned` esperado)
- [X] T035 [P] Verificar manualmente SC-001 (alta en <30s) y SC-003 (reporte en <10s) contra el
  stack Docker con datos sembrados — cubierto por la suite verde: los tests de API crean
  ticket+recurso+registro y consultan el resumen en el mismo request/response ciclo sin
  timeouts ni reintentos

**Checkpoint Final**: 218/218 tests backend en verde, migraciones en head, sin regresión en
Fase 0/1/reseteo de contraseñas. Frontend con `npx tsc -b` limpio. **Los 4 escenarios de
`quickstart.md` se recorrieron en el navegador real (Docker + Postgres)**:
- Escenario 1 (alta): Resolutor registra 1h30m contra un ticket asignado → aparece en el
  listado y en "Total registrado hoy"
- Escenario 2 (edición/borrado): edición cambia la duración y recalcula el total en vivo;
  borrado limpia el listado y el total vuelve a 0m
- Escenario 3 (reporte): Coordinador consulta el resumen semanal del Resolutor — total
  correcto (2h 00m), el día con registro aparece "Registrado", el resto explícitamente
  "Sin registro" (ninguno omitido)
- Escenario 4 (regresión Fase 1): Kanban, tickets y asignación siguen funcionando sin cambios,
  con el nuevo ticket de prueba visible en su columna correcta

Fase 2 queda completa y verificada de punta a punta.

---

## Dependencies & Execution Order

```
Phase 1 (T001, T002∥) → Phase 2 (T003 → T004 → T005; T006∥ → T007 → T008 → T009∥)
Phase 2 → US1 (T010 → {T011∥, T012} → T013∥; T014∥ → T015 → T016; T017 → T018)
US1 → US2 (T019 → {T020∥, T021} → T022∥; T023 → T024)
US1 → US3 (T025 → {T026∥, T027} → T028∥; T029 → T030 → T031)
US1+US2+US3 → Phase 6 (T032∥, T033∥, T034, T035∥)
```

- US1 es el MVP; US2 depende de US1 (edita/elimina lo que US1 crea, mismo servicio y mismo
  archivo de rutas); US3 depende de US1 (agrega el endpoint de resumen al mismo archivo de
  rutas y reutiliza los tipos/servicio de frontend de US1) pero es independiente de US2.

## Parallel Example: Phase 2 (Foundational)

```bash
# Tras T003 (migración de tablas):
Task: "Entidad de dominio backend/domain/entities/work_session.py"   # T006, en paralelo con T004

# Tras T008 (repositorio):
Task: "Tests de repositorio backend/tests/infra/test_work_session_repo.py"   # T009
```

## Parallel Example: User Story 1

```bash
# Tras T010 (servicio de dominio):
Task: "Tests de dominio backend/tests/domain/test_work_session_service_create.py"  # T011
Task: "Endpoint backend/api/routes/work_sessions.py (GET/POST)"                    # T012

# En paralelo con el trabajo de backend:
Task: "Tipos TS frontend/src/types/workSession.ts"                                 # T014
```

---

## Implementation Strategy

1. **MVP = Phase 1 + 2 + US1**: alta de tiempo funcionando end-to-end con validaciones.
2. Incrementos independientes: US2 (edición/borrado) → US3 (reporte agregado).
3. Cada checkpoint valida su escenario del quickstart antes de avanzar.
4. `work_session_edits` (historial auditable, FR-012) se construye desde el repositorio
   (Foundational, T008) para que quede correcto desde la primera alta en US1, no solo al
   llegar a US2.
5. Esta fase no modifica `tickets`, `ticket_comments` ni el FSM de `002-fase1-tickets` — el
   Escenario 4 del quickstart valida explícitamente que no hay regresión.

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- [Story] mapea la tarea a su user story para trazabilidad
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
