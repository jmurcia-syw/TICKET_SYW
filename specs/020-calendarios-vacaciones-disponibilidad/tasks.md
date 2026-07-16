# Tasks: Calendarios Multi-Zona Horaria, Festivos, Vacaciones (RRHH) y Disponibilidad

**Input**: Design documents from `specs/020-calendarios-vacaciones-disponibilidad/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/calendar-disponibilidad.md](contracts/calendar-disponibilidad.md),
[quickstart.md](quickstart.md)

**Tests**: Se incluyen tareas de test unitario ultra-limitadas (≤10 registros de prueba, Principio
VII) solo para los dos servicios de dominio con lógica de negocio no trivial
(`availability_service`, `absence_service`), tal como pidió el usuario explícitamente al iniciar
esta fase. No se generan contract tests ni se corre la suite completa.

**Organization**: Tareas agrupadas por historia de usuario (spec.md) para permitir implementación
y prueba independiente de cada una.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3, US4)
- Cada tarea incluye la ruta de archivo exacta

## Path Conventions

Web app existente: `backend/` (Flask, Clean Architecture 3 capas) + `frontend/` (React 19 +
TypeScript, Ant Design 5). Ver `plan.md` → Project Structure para el árbol completo.

---

## Phase 1: Setup

**Purpose**: Alta de la única dependencia nueva de esta fase (research.md Decisión 1)

- [X] T001 [P] Instalar `@fullcalendar/core`, `@fullcalendar/react`, `@fullcalendar/daygrid`,
      `@fullcalendar/timegrid` (`pnpm add`) en `frontend/package.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Esquema de base de datos, entidades/repositorios compartidos y catálogo/rol RRHH que
las 4 historias necesitan

**⚠️ CRITICAL**: Ninguna historia puede empezar hasta completar esta fase

- [X] T002 [P] Migración `backend/infra/migrations/versions/034_client_resource_timezone.py`:
      agrega `clients.timezone`, `clients.country`, `resources.timezone` (data-model.md)
- [X] T003 [P] Agregar `timezone`/`country` a `ClientModel` en
      `backend/infra/models/client_model.py` y a `Client` en `backend/domain/entities/client.py`
- [X] T004 [P] Agregar `timezone` a `ResourceModel` en `backend/infra/models/resource_model.py` y
      a `Resource` en `backend/domain/entities/resource.py`
- [X] T005 [P] Exponer `timezone`/`country` en body/respuesta de
      `backend/api/routes/clients.py` (`POST`/`PATCH`/`GET /api/clients`) — depende de T003
- [X] T006 [P] Agregar `timezone` a `_PROFILE_TEXT_FIELDS`/`_resource_out` en
      `backend/api/routes/resources.py` (`PATCH /api/resources/{id}`) — depende de T004
- [X] T007 Migración `backend/infra/migrations/versions/035_holidays_work_schedules.py`: crea
      `holidays` y `work_schedules` (data-model.md, sin RLS — Decisión 6)
- [X] T008 Migración `backend/infra/migrations/versions/036_catalog_absence_types.py`: crea
      `catalog_absence_types` (mismo patrón `_CatalogMixin`) + seed Vacaciones/Incapacidad
      médica/Permiso personal/Otro; registra `AbsenceTypeCatalogModel` y
      `CATALOG_MODELS["absence-types"]` en `backend/infra/models/catalog_model.py`
- [X] T009 Migración `backend/infra/migrations/versions/037_absence_requests.py`: crea
      `absence_requests` y `absence_request_attachments` (data-model.md) — depende de T008
- [X] T010 Migración `backend/infra/migrations/versions/038_absence_requests_rls.py`: habilita RLS
      app-level (mismo patrón `031_client_access_rls.py`) en ambas tablas — depende de T009
- [X] T011 Migración `backend/infra/migrations/versions/039_rrhh_role_permissions.py`: seed rol
      `RRHH` + permisos `absence_requests:create/view_all/decide_hr`, `holidays:manage` (mismo
      patrón `021_encargado_role_permissions.py`; `create` a todos los roles internos vinculados a
      Recurso, no a `Encargado`) — depende de T009
- [X] T012 [P] Crear `backend/domain/entities/calendar.py`: `@dataclass Holiday`,
      `WorkScheduleSlot`, `AbsenceRequest`, `AbsenceRequestAttachment`, `Availability`
      (data-model.md → "Actualización de tipos existentes")
- [X] T013 Crear `backend/infra/models/calendar_model.py`: `HolidayModel`, `WorkScheduleModel`,
      `AbsenceRequestModel`, `AbsenceRequestAttachmentModel` con `to_entity()`/`from_entity()` —
      depende de T007, T009, T012
- [X] T014 Crear `backend/infra/repositories/calendar_repo.py`: `HolidayRepository` (list por
      país, create, activate/deactivate), `WorkScheduleRepository` (get/replace por recurso),
      `AbsenceRequestRepository` (create, list por scope, decide, adjuntos) — depende de T013
- [X] T015 [P] Extender `backend/infra/repositories/client_repo.py` para persistir
      `timezone`/`country` en create/update — depende de T003
- [X] T016 [P] Extender `backend/infra/repositories/resource_repo.py` para persistir `timezone`
      en update/perfil — depende de T004
- [X] T017 [P] Crear `frontend/src/types/calendar.ts`: `Holiday`, `WorkScheduleSlot`,
      `AbsenceType`, `AbsenceRequest`, `AbsenceRequestAttachment`, `Availability`
- [X] T018 [P] Agregar `timezone`/`country` a `frontend/src/types/client.ts` y `timezone` a
      `frontend/src/types/resource.ts`
- [X] T019 [P] Crear `frontend/src/services/calendarService.ts` con el cliente Axios base (mismo
      patrón que `frontend/src/services/resourceService.ts`); incluye ya `getAvailability` (T024)
      dado que es la única llamada que el MVP (US1) necesita

**Checkpoint**: Esquema y capas de dominio/infra listas — las 4 historias pueden implementarse.

---

## Phase 3: User Story 1 - Alerta de disponibilidad al asignar un ticket (Priority: P1) 🎯 MVP

**Goal**: El panel de asignación (`AssignModal`) muestra, por resolutor, si está disponible ahora
mismo (ausencia aprobada > festivo > horario laboral) sin bloquear nunca la asignación (FR-013 a
FR-016).

**Independent Test**: Con datos de horario/festivo/ausencia cargados directamente en BD para un
recurso, abrir el selector de resolutor y verificar el indicador de "No disponible" con motivo, o
su ausencia cuando el recurso sí está disponible; confirmar que la asignación se completa en
ambos casos (quickstart.md Escenario 1).

### Tests for User Story 1

- [X] T020 [P] [US1] Test unitario ultra-limitado (≤10 registros) de
      `availability_service.compute_availability` en
      `backend/tests/domain/test_availability_service.py`: cubre orden ausencia > festivo >
      horario, y el caso "sin datos configurados ⇒ disponible" (FR-016). 6 tests, todos PASS
      (`docker exec sywork_backend python -m pytest tests/domain/test_availability_service.py`)

### Implementation for User Story 1

- [X] T021 [US1] Crear `backend/domain/services/availability_service.py`: función pura
      `compute_availability(resource, now_utc, holidays, work_schedule_slots, active_absence) ->
      Availability`, sin imports de Flask/SQLAlchemy (Principio I) — depende de T012
- [X] T022 [US1] Crear `backend/api/routes/calendar.py` con el namespace `calendar` y
      `GET /api/resources/availability` (`resource_ids`, `at` opcionales), permiso
      `tickets:assign` reutilizado (contracts/calendar-disponibilidad.md) — depende de T014, T021
- [X] T023 [US1] Registrar `api.add_namespace(ns_calendar)` en `backend/app.py` (junto a los demás
      `add_namespace`, línea ~109) — depende de T022. Verificado end-to-end contra Docker real:
      migraciones 034-039 aplicadas, festivo/fuera-de-horario/disponible responden correctamente
- [X] T024 [US1] Agregar `getAvailability(resourceIds, at?)` a
      `frontend/src/services/calendarService.ts` — depende de T019, T023
- [X] T025 [US1] Actualizar `frontend/src/components/tickets/AssignModal.tsx`: consultar
      disponibilidad junto a la carga (`useEffect` existente), renderizar `Tag` roja con tooltip
      del motivo sobre cada tarjeta de resolutor no disponible (mismo patrón visual que el `Tag`
      "Menor carga" ya existente, sin ocultar ni deshabilitar el botón de asignar) — depende de
      T024. Verificado en navegador contra Docker real: badge "Fuera de horario" se renderiza y
      la asignación se completa igual (`POST .../assign` → 200 OK). Nota: fue necesario reiniciar
      `sywork_frontend` para que Vite recogiera el archivo nuevo `calendarService.ts` (problema
      conocido de file-watching en Docker/Windows, ver memoria de sesiones previas)
- [X] T026 [US1] Validar manualmente el Escenario 1 de `quickstart.md` (festivo, fuera de horario,
      disponible) contra Docker. Festivo y disponible verificados por API (`curl`, migraciones
      034-039 aplicadas); fuera de horario verificado además en el navegador real (badge visible
      + `POST /api/tickets/{id}/assign` sigue devolviendo 200, confirmando FR-015). Dato de
      prueba (`work_schedules` temporal) eliminado tras la verificación

**Checkpoint**: User Story 1 funcional y probable de forma independiente — MVP entregable.

---

## Phase 4: User Story 2 - Solicitud y aprobación en cadena de ausencias (Priority: P2)

**Goal**: Un miembro del equipo envía una solicitud de ausencia (tipo + fechas + adjunto
opcional); su Jefe directo y un usuario RRHH la aprueban/rechazan de forma independiente; el
estado general se deriva según la Decisión 4 de `research.md` (FR-008 a FR-012a).

**Independent Test**: Crear una solicitud, aprobarla como Jefe directo, aprobarla como RRHH →
`overall_status=approved`; en una segunda solicitud, un rechazo de cualquiera de los dos la deja
`rejected` de inmediato (quickstart.md Escenario 2).

### Tests for User Story 2

- [X] T027 [P] [US2] Test unitario ultra-limitado (≤10 registros) de `absence_service` en
      `backend/tests/domain/test_absence_service.py`: solapamiento de fechas (FR-009),
      `overall_status` con jefe+RRHH, rechazo unilateral (FR-011a), auto-aprobación de
      `manager_status` sin jefe (FR-011b), bloqueo de auto-aprobación (FR-012). 8 tests, todos
      PASS (`docker exec sywork_backend python -m pytest tests/domain/test_absence_service.py`)

### Implementation for User Story 2

- [X] T028 [US2] Crear `backend/domain/services/absence_service.py`: validación de rango de
      fechas y solapamiento, cálculo de `overall_status`, guarda de auto-decisión — depende de
      T012
- [X] T029 [US2] `POST /api/absence-requests` en `backend/api/routes/calendar.py` (acepta
      `multipart/form-data` con `files` opcionales, reutiliza
      `backend/infra/storage/attachments.py::save(..., entity_kind="absence_requests")`) —
      depende de T014, T028
- [X] T030 [US2] `GET /api/absence-requests?scope=own|manager|hr` en
      `backend/api/routes/calendar.py` (filtrado por pertenencia o `absence_requests:view_all`) —
      depende de T014
- [X] T031 [US2] `PATCH /api/absence-requests/{id}/decision` en `backend/api/routes/calendar.py`
      (`role=manager|hr`, verificación de pertenencia/`decide_hr`, bloqueo de auto-decisión) —
      depende de T028
- [X] T032 [US2] `GET/POST/DELETE /api/absence-requests/{id}/attachments` en
      `backend/api/routes/calendar.py`, mismo criterio de permiso que ver/crear la solicitud padre
      — depende de T014
- [X] T033 [US2] Agregar `createAbsenceRequest`, `listAbsenceRequests(scope)`,
      `decideAbsenceRequest`, `uploadAbsenceAttachment` a
      `frontend/src/services/calendarService.ts` — depende de T019, T029-T032
- [X] T034 [US2] Crear `frontend/src/pages/AbsenceRequestsPage.tsx`: sección "Mis solicitudes"
      (formulario tipo+fechas+adjunto y listado propio) + sección "Aprobaciones pendientes"
      (visible condicionalmente: como Jefe si tiene subordinados — pestaña "manager" se oculta
      si el `GET ?scope=manager` responde 403 —, como RRHH si tiene el permiso `view_all`) —
      depende de T033
- [X] T035 [US2] Registrar ruta `/absence-requests` en `frontend/src/App.tsx`
      (`ProtectedRoute` con `{module: 'absence_requests', action: 'create'}`) y entrada de menú
      "Vacaciones y Permisos" en `frontend/src/config/navigation.tsx` (nuevo grupo
      `absenceNavItems`, junto a Tickets/Registro de tiempos en `DashboardPage.tsx`) — depende de
      T034
- [X] T036 [US2] Validar manualmente el Escenario 2 de `quickstart.md` (doble aprobación, rechazo
      unilateral, auto-aprobación bloqueada) contra Docker. Verificado end-to-end vía UI (creación
      con auto-aprobación de `manager_status` sin jefe, FR-011b) y vía API real con jefe/RRHH
      temporales: aprobación doble → `overall_status=approved`; RRHH rechaza antes que el jefe →
      `overall_status=rejected` de inmediato (FR-011a); jefe/RRHH intentando decidir su propia
      solicitud → `403 own_request` (FR-012); segunda decisión del mismo lado → `409
      already_decided`; adjunto subido y listado correctamente (FR-008a). Datos de prueba
      (solicitudes, adjunto, `manager_id`/rol temporales) eliminados tras la verificación

**Checkpoint**: User Stories 1 y 2 funcionan de forma independiente.

---

## Phase 5: User Story 3 - Calendario con festivos por país (Cliente y Equipo) (Priority: P3)

**Goal**: Vista de Calendario con pestañas "Cliente" y "Equipo" (FullCalendar) que resaltan los
festivos del país configurado de cada uno, en su zona horaria (FR-001, FR-004, FR-005, FR-017).

**Independent Test**: Configurar país en un Cliente y en un Recurso, verificar que cada calendario
muestra únicamente sus propios festivos, sin mezclarlos y sin error cuando un país no tiene
festivos cargados (quickstart.md Escenario 3).

### Implementation for User Story 3

- [X] T037 [US3] `GET /api/holidays?country=`, `POST /api/holidays`,
      `PATCH /api/holidays/{id}/activate|deactivate` en `backend/api/routes/calendar.py`
      (permiso `holidays:manage` para altas/bajas, lectura abierta a autenticados) — depende de
      T014
- [X] T038 [P] [US3] Seed de ≤10 festivos de prueba (países con Clientes/Recursos activos hoy) en
      la migración `backend/infra/migrations/versions/035_holidays_work_schedules.py` o una
      migración de datos separada, según research.md Decisión 2. Ya cumplido en Foundational
      (T007): 5 festivos seed (CO×3, MX×2) verificados en BD
- [X] T039 [US3] Agregar `listHolidays(country)`, `createHoliday`,
      `setHolidayActive(id, active)` a `frontend/src/services/calendarService.ts` — depende de
      T019, T037
- [X] T040 [US3] Agregar campos `timezone`/`country` al formulario de
      `frontend/src/pages/ClientsPage.tsx` (Select con catálogo ISO ya existente en
      `frontend/src/data/countries.ts`, reutilizado de `TeamPage.tsx`; `frontend/src/data/timezones.ts`
      nuevo, vía `Intl.supportedValuesOf('timeZone')`) — depende de T005. Verificado end-to-end en
      navegador real: edición guarda `country`/`timezone`, confirmado por el cuerpo real del PATCH
      interceptado (`{"country":"CO","timezone":"America/Bogota",...}`) y por el valor persistido
      en BD
- [X] T041 [US3] Crear `frontend/src/pages/CalendarPage.tsx`: `Tabs` "Cliente" (selector de
      cliente + `FullCalendar` en su país) / "Equipo" (un calendario independiente por miembro
      seleccionado, festivos de su propio país, sin mezclar — variante sin plugin de recursos, ya
      que solo `@fullcalendar/daygrid`/`timegrid` están aprobados esta fase) — depende de T001,
      T039
- [X] T042 [US3] Registrar ruta `/calendar` en `frontend/src/App.tsx` (permiso
      `resources:view`) y entrada de menú "Calendarios" en `frontend/src/config/navigation.tsx`
      (grupo `absenceNavItems`, junto a Tickets/Registro de tiempos) — depende de T041
- [X] T043 [US3] Validar manualmente el Escenario 3 de `quickstart.md` (festivos por país,
      aislamiento entre miembros, país sin festivos) contra Docker. Verificado en navegador real:
      pestaña "Cliente" muestra "Día de la Raza" (12 oct) para un Cliente con `country=CO`;
      pestaña "Equipo" con dos Recursos seleccionados muestra el festivo solo en el que tiene
      `calendar_country=CO`, y "Sin país configurado — no hay festivos que mostrar" (sin error) en
      el que no tiene país configurado — confirma aislamiento y el edge case

**Checkpoint**: User Stories 1, 2 y 3 funcionan de forma independiente.

---

## Phase 6: User Story 4 - Horario laboral semanal por defecto (Priority: P4)

**Goal**: Cada recurso puede tener un horario laboral semanal explícito (o usar el default
documentado) que `availability_service` consulta para decidir "dentro/fuera de horario" (FR-006).

**Independent Test**: Configurar un horario custom para un recurso y verificar que las horas
dentro del rango se consideran laborales y las de fuera no, respetando su zona horaria
(quickstart.md Escenario 4).

### Implementation for User Story 4

- [X] T044 [US4] `GET/PUT /api/resources/{id}/work-schedule` en
      `backend/api/routes/calendar.py` (respuesta incluye `is_default: true` cuando no hay filas
      propias, reutilizando la constante de horario por defecto de
      `availability_service.py`) — depende de T014, T021
- [X] T045 [US4] Agregar `getWorkSchedule(resourceId)`, `setWorkSchedule(resourceId, slots)` a
      `frontend/src/services/calendarService.ts` — depende de T019, T044
- [X] T046 [US4] Crear `frontend/src/components/resources/WorkScheduleDrawer.tsx`: editor de
      franjas por día de semana (0-6) — depende de T045
- [X] T047 [US4] Agregar campo `timezone` y botón "Horario laboral" (abre
      `WorkScheduleDrawer`) al formulario de `frontend/src/pages/TeamPage.tsx` — depende de T006,
      T046
- [X] T048 [US4] Validar manualmente el Escenario 4 de `quickstart.md` (horario default vs.
      custom) contra Docker. Verificado vía API real: `GET` sin config → `is_default:true`,
      lunes-viernes 08:00-17:00; `PUT` con franja custom (06:00-14:00 lun-vie) → `is_default:false`;
      disponibilidad a las 15:00 hora Bogotá (fuera del custom) → `outside_hours`, a las 10:00
      (dentro) → `available:true`. Verificado en navegador real: `WorkScheduleDrawer` carga y
      muestra correctamente el horario custom persistido; el campo "Huso horario" del formulario
      de `TeamPage.tsx` se pre-llena con el valor real (`America/Bogota`)

**Checkpoint**: Las 4 historias de usuario funcionan de forma independiente.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T049 [P] Revisar en Swagger UI (`/swagger.json` o `/api/docs`) que todos los endpoints
      nuevos de `backend/api/routes/calendar.py` quedaron documentados (`@ns.doc`/`@ns.response`)
      antes de darse por completos (Principio I). Verificado descargando `/swagger.json` real y
      confirmando `summary` + `responses` en los 13 endpoints nuevos: `/api/holidays` (GET/POST),
      `/api/holidays/{id}/{action}` (PATCH), `/api/absence-requests` (GET/POST),
      `/api/absence-requests/{id}/decision` (PATCH), `/api/absence-requests/{id}/attachments`
      (GET/POST), `/api/absence-requests/{id}/attachments/{id}` (GET/DELETE),
      `/api/resources/availability` (GET), `/api/resources/{id}/work-schedule` (GET/PUT)
- [X] T050 Ejecutar los 4 escenarios de `quickstart.md` de punta a punta en una sola pasada contra
      Docker, sin atajos entre historias. Escenario 1: festivo de prueba creado para hoy vía API,
      `GET /api/resources/availability` confirma `available:false, reason:holiday`; badge y
      asignación sin bloqueo confirmados por revisión estática de `AssignModal.tsx` (el `onClick`
      de la tarjeta y el botón "Asignar resolutor" solo dependen de `selected`, nunca de
      `avail.available` — FR-015); festivo desactivado y confirmado `outside_hours` a las 22:00
      hora Bogotá y `available:true` sin indicadores a las 10:00. Escenario 2: solicitud con
      adjunto → aprobación Jefe directo → aprobación RRHH → `overall_status=approved`; segunda
      solicitud rechazada por RRHH antes de que el jefe decida → `overall_status=rejected`
      inmediato (FR-011a); autodecisión → `403 own_request` (FR-012). Escenario 3: aislamiento de
      festivos por país confirmado vía `GET /api/holidays?country=CO|MX` y revisión de
      `CalendarPage.tsx` (pestaña Cliente usa el país del cliente elegido; pestaña Equipo renderiza
      un `HolidayCalendar` independiente por recurso, cada uno con su propio `calendar_country`, sin
      mezclar festivos). Escenario 4: `WorkScheduleDrawer` abierto en navegador real sobre el
      recurso `admin` confirma que carga y muestra el horario custom persistido
      (lunes-viernes 06:00-14:00, checkboxes correctos). Nota: la selección interactiva de Cliente
      en los formularios (`Nuevo ticket`, pestañas de `CalendarPage`) no pudo completarse por clic
      automatizado — se instrumentó el DOM con listeners y se confirmó que los eventos de clic no
      llegan al elemento `option` del dropdown (limitación de la herramienta de automatización del
      navegador en este entorno, no un defecto del producto); se compensó con verificación de
      contrato real vía API + revisión estática del código fuente de los componentes involucrados.
      Datos de prueba (recursos `QA Resolutor B`/`QA RRHH`, solicitudes de ausencia, festivo de
      prueba, rol temporal de `qm@sywork.net`) creados vía API real y eliminados/revertidos al
      finalizar (Principio VII)
- [X] T051 Confirmar RLS activo en `absence_requests`/`absence_request_attachments`
      (`SELECT * FROM pg_policies WHERE tablename LIKE 'absence_request%'`) — Principio IV.
      Verificado: `rowsecurity=t` en ambas tablas, con política `_app_access` (`cmd=ALL`) en cada
      una
- [X] T052 Confirmar que `POST /api/tickets/{id}/assign` (`backend/api/routes/tickets.py`) no fue
      modificado por esta fase — FR-015 y Decisión 7 de `research.md`. Verificado: el archivo no
      aparece en el commit de esta fase (`cac9538`); su último cambio es del commit `990c711`
      (feature 019, previo a esta fase). Solo se modificó `AssignModal.tsx` en frontend (consumo
      del nuevo endpoint de disponibilidad), no el endpoint de asignación en sí

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede iniciar de inmediato
- **Foundational (Phase 2)**: depende de Setup — bloquea las 4 historias
- **User Stories (Phase 3-6)**: todas dependen de Foundational; pueden avanzar en paralelo o en
  orden de prioridad P1→P2→P3→P4
- **Polish (Phase 7)**: depende de que las historias que se vayan a entregar estén completas

### User Story Dependencies

- **US1 (P1)**: solo depende de Foundational. No depende de US2/US3/US4 (si no hay ausencias
  aprobadas ni festivos cargados, simplemente no hay nada que mostrar — FR-016).
- **US2 (P2)**: solo depende de Foundational. Sus datos alimentan a US1 pero US1 ya maneja el caso
  sin datos, así que ambas son probables por separado.
- **US3 (P3)**: solo depende de Foundational. Comparte `holidays`/`GET /api/holidays` con US1
  (que los consume desde `availability_service`, no desde el endpoint de US3) — sin dependencia de
  código entre ambas.
- **US4 (P4)**: depende de Foundational y reutiliza la constante de horario por defecto de
  `availability_service.py` (T021, de US1) — única dependencia cruzada real, ya reflejada en T044.

### Parallel Opportunities

- Foundational: T002, T003, T004, T005, T006, T012, T015-T019 marcadas [P] (archivos distintos)
- Una vez completada Foundational: US1, US2, US3 pueden avanzar en paralelo por
  desarrolladores distintos; US4 debe esperar a que T021 (US1) exista
- Dentro de cada historia, los tests marcados [P] corren en paralelo con tareas de otra historia,
  nunca con la implementación de su propia historia (mismo archivo `calendar.py`/
  `calendarService.ts` compartido dentro de la historia)

---

## Parallel Example: Foundational

```bash
Task: "Migración 034 timezone/country en clients/resources"
Task: "ClientModel + Client entity timezone/country"
Task: "ResourceModel + Resource entity timezone"
Task: "frontend/src/types/calendar.ts"
Task: "frontend/src/types/client.ts + resource.ts timezone/country"
```

---

## Implementation Strategy

### MVP First (User Story 1 solamente)

1. Completar Phase 1 (Setup) + Phase 2 (Foundational)
2. Completar Phase 3 (US1) — alerta de disponibilidad
3. **Detenerse y validar**: Escenario 1 de `quickstart.md`
4. Demo: el panel de asignación ya advierte sobre disponibilidad, aunque todavía no haya UI para
   cargar ausencias/festivos/horarios (se pueden insertar directo en BD para la demo, como indica
   el "Independent Test" de la historia)

### Incremental Delivery

1. Setup + Foundational → base lista
2. US1 → validar → demo (MVP)
3. US2 → validar → demo (ahora las ausencias se cargan desde la UI, no solo por BD)
4. US3 → validar → demo (calendarios visuales)
5. US4 → validar → demo (horario laboral configurable, ya no solo el default)

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes
- [Story] mapea cada tarea a su historia de usuario para trazabilidad
- Alcance de esta sesión (directriz del usuario + Principio VII): solo migraciones/modelos de
  calendarios-países-festivos-vacaciones, el controlador de disponibilidad/asignación y las vistas
  correspondientes — nada de refactors fuera de esta lista de tareas
- Tests nuevos: ≤10 registros de prueba por test, solo `availability_service`/`absence_service`
- Confirmar antes de cerrar la fase: `POST /api/tickets/{id}/assign` sigue sin bloquear por
  disponibilidad (FR-015)
