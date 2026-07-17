---

description: "Task list template for feature implementation"
---

# Tasks: RRHH — Franjas Horarias, Calendario Superpuesto y Motor de SLA Dinámico

**Input**: Design documents from `/specs/022-rrhh-calendario-sla-dinamico/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/rrhh-calendario-sla-dinamico.md),
[quickstart.md](quickstart.md)

**Revisión**: esta versión incorpora las correcciones de `/speckit-analyze` — hallazgo **C1**
(crítico: faltaba el cableado real del motor de SLA dinámico hacia `tickets.py`/`sla_tasks.py`,
y una consulta ranged de ausencias aprobadas) y **I1** (la vista diaria no filtra tickets por
fecha, porque `Ticket` no tiene ese campo). Ver research.md Decisiones 10-12 y data-model.md
"Repositorios (Capa 2)".

**Tests**: Limitados por directriz explícita del usuario y Principio VII de la constitución —
**un solo** archivo de test (T038), dirigido al cálculo de SLA dinámico, con 5-10 registros
dummy. No se generan tests para el resto de historias; no se ejecuta la suite global.

**Organization**: Tareas agrupadas por historia de usuario para permitir implementación y
prueba independiente de cada una.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivo distinto, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3, US4)
- Todas las rutas de archivo son relativas a la raíz del repo

## Path Conventions

Web app ya existente: `backend/` (Flask, Capas 1-2-3) + `frontend/src/` (React). No se crean
directorios nuevos de alto nivel — todo se ubica en la estructura ya existente descrita en
`plan.md`.

---

## Phase 1: Setup

**Purpose**: Scaffolding de los dos archivos nuevos que introduce esta feature (todo lo demás
extiende archivos ya existentes de spec 020/021).

- [X] T001 [P] Crear scaffold vacío de `backend/domain/services/work_hour_template_service.py`
      (docstring de módulo, sin imports de Flask/SQLAlchemy — Principio I; este archivo será
      **solo validación**, la persistencia vive en un repositorio, ver Foundational)
- [X] T002 [P] Crear scaffold vacío de `frontend/src/pages/WorkHourTemplatesPage.tsx`
      (componente funcional vacío exportado por default)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Entidades, modelos, repositorios, migraciones y navegación base que consumen 2 o
más historias.

**⚠️ CRITICAL**: Ninguna historia de usuario puede empezar hasta completar esta fase.

- [X] T003 Agregar dataclasses `WorkHourTemplate` y `WorkHourTemplateSlot` en
      `backend/domain/entities/calendar.py` (mismo shape que `WorkScheduleSlot` — ver
      data-model.md)
- [X] T004 Extender la dataclass `AbsenceRequest` en `backend/domain/entities/calendar.py` con
      `start_time`/`end_time` opcionales (depende de T003, mismo archivo)
- [X] T005 [P] Agregar `schedule_mode` (`"heredado"` \| `"personalizado"`) y
      `work_hour_template_id` a la dataclass `Resource` en
      `backend/domain/entities/resource.py`
- [X] T006 Agregar `WorkHourTemplateModel`/`WorkHourTemplateSlotModel` (SQLAlchemy) en
      `backend/infra/models/calendar_model.py` (depende de T003)
- [X] T007 Extender `AbsenceRequestModel` en `backend/infra/models/calendar_model.py` con
      columnas `start_time`/`end_time` (depende de T004; mismo archivo que T006, tras T006)
- [X] T008 [P] Agregar columnas `schedule_mode`/`work_hour_template_id` a `ResourceModel` en
      `backend/infra/models/resource_model.py` (depende de T005)
- [X] T009 Migración `backend/infra/migrations/versions/041_work_hour_templates.py`: crear
      tablas `work_hour_templates` y `work_hour_template_slots` (depende de T006)
- [X] T010 Migración `backend/infra/migrations/versions/042_resource_schedule_mode.py`: agregar
      columnas a `resources` + migración de datos (`UPDATE resources SET schedule_mode =
      'personalizado' WHERE id IN (SELECT DISTINCT resource_id FROM work_schedules)` — decisión
      ya confirmada con el usuario, ver research.md Decisión 3) (depende de T008, T009)
- [X] T011 [P] Migración
      `backend/infra/migrations/versions/043_absence_requests_partial_hours.py`: agregar
      `start_time`/`end_time` nullable a `absence_requests` (depende de T007)
- [X] T012 [P] Migración
      `backend/infra/migrations/versions/044_rrhh_work_hour_templates_permission.py`: agregar
      permiso `work_hour_templates:manage` a los roles RRHH y Admin (mismo patrón que
      `039_rrhh_role_permissions.py`)
- [X] T013 [P] Agregar `RRHH_GROUP_KEY`/`rrhhNavItems` (Calendario, Permisos) en
      `frontend/src/config/navigation.tsx`, agrupando lo que hoy son `absenceNavItems` planos
      (mismo patrón que `MAESTROS_GROUP_KEY`/`maestrosNavItems`)
- [X] T014 Renderizar el submenú "RRHH" en `frontend/src/pages/DashboardPage.tsx` con el mismo
      patrón visual de `Menu` con `children` ya usado por "Maestros" (depende de T013)
- [X] T015 [P] Agregar tipos `WorkHourTemplate`/`WorkHourTemplateSlot` en
      `frontend/src/types/calendar.ts`
- [X] T016 Agregar clase `WorkHourTemplateRepository` (`list_by_country`, `get_by_id`, `create`,
      `update`, `replace_slots`, `list_slots`) en `backend/infra/repositories/calendar_repo.py`
      — Capa 2, la persistencia de la Franja Horaria vive aquí, **no** en
      `work_hour_template_service.py` (research.md Decisión 12) (depende de T006, T009)
- [X] T017 [P] Agregar método `list_by_schedule_mode(mode)` a `ResourceRepository` en
      `backend/infra/repositories/resource_repo.py` (depende de T008, T010)

**Checkpoint**: fundación lista — las historias de usuario pueden empezar.

---

## Phase 3: User Story 1 - RRHH administra Franjas Horarias y modo Personalizado (Priority: P1) 🎯 MVP

**Goal**: RRHH crea/edita Franjas Horarias globales por país que el equipo hereda
automáticamente, y puede ver quién está en modo Personalizado.

**Independent Test**: Crear una Franja Horaria para un país, verificar que el equipo la refleja;
editar el horario propio desde el Perfil y verificar que pasa a "Personalizado" y queda excluido
de una actualización masiva posterior.

- [X] T018 [US1] Implementar validación de dominio (timezone IANA válida, `end_time > start_time`
      por slot) en `backend/domain/services/work_hour_template_service.py` — **solo validación,
      sin DB** (depende de T003, T001)
- [X] T019 [US1] Agregar función reutilizable `resolve_effective_schedule_slots(db, resource)` en
      `backend/infra/repositories/calendar_repo.py` (heredado → slots de
      `WorkHourTemplateRepository`; personalizado → `WorkScheduleRepository.list_by_resource`,
      ya existente) — un único punto de resolución reusado por US1, US2 y por el endpoint de
      disponibilidad ya existente (depende de T016)
- [X] T020 [US1] Refactorizar el endpoint de disponibilidad ya existente
      (`backend/api/routes/calendar.py`, ~línea 103, spec 020) para usar
      `resolve_effective_schedule_slots` en vez de siempre `WorkScheduleRepository` — sin cambio
      de contrato HTTP (depende de T019)
- [X] T021 [US1] Endpoints `GET/POST/PATCH /api/work-hour-templates` y
      `GET /api/work-hour-templates/personalized` en `backend/api/routes/calendar.py`
      (usa `work_hour_template_service` + `WorkHourTemplateRepository` +
      `ResourceRepository.list_by_schedule_mode`), protegidos con
      `require_permission("work_hour_templates", "manage")` (depende de T018, T016, T017, T012;
      mismo archivo que T020, tras T020)
- [X] T022 [US1] Endpoint `PATCH /api/resources/{id}/work-hour-template` (asignar/reasignar
      Franja a un recurso) en `backend/api/routes/calendar.py` (mismo archivo, tras T021)
- [X] T023 [US1] Extender `PUT /api/resources/{id}/work-schedule` en
      `backend/api/routes/calendar.py` para marcar automáticamente `schedule_mode="personalizado"`
      y `work_hour_template_id=NULL` al guardar (mismo archivo, tras T022)
- [X] T024 [P] [US1] Agregar llamadas a los endpoints de Franja Horaria (listar/crear/editar/
      personalizados/asignar) en `frontend/src/services/calendarService.ts`
- [X] T025 [US1] Implementar `frontend/src/pages/WorkHourTemplatesPage.tsx`: gestión de Franjas
      Horarias por país + listado de recursos Personalizados (depende de T024, T002)
- [X] T026 [US1] Agregar edición de horario propio en `frontend/src/pages/MyProfilePage.tsx`
      (usa el endpoint ya extendido en T023) (depende de T024)
- [X] T027 [US1] Registrar la ruta `/rrhh/franjas-horarias` → `WorkHourTemplatesPage` protegida
      por el permiso `work_hour_templates:manage` en `frontend/src/App.tsx` (depende de T025,
      T014)

**Checkpoint**: US1 funcional y probable de forma independiente (FR-001 a FR-005).

---

## Phase 4: User Story 2 - Motor de SLA Dinámico basado en disponibilidad real (Priority: P1)

**Goal**: el reloj de SLA de Diagnóstico/Análisis/Ejecución solo avanza cuando el recurso
asignado está disponible; pausa y reanuda automáticamente sin intervención manual.

**Independent Test**: verificable por API (sin necesidad del calendario ni de la vista diaria)
reproduciendo el escenario estricto del enunciado — jornada 8-18h, ticket entra a las 17h con 1h
disponible, consume esa hora, pausa a las 18h, reanuda a las 8h del día siguiente.

- [X] T028 [US2] Nueva función `compute_available_seconds(resource, from_dt, to_dt, holidays,
      schedule_slots, absences)` en `backend/domain/services/sla_service.py` (suma solo los
      intervalos en los que `availability_service` habría devuelto `available=True`) (depende de
      T004)
- [X] T029 [US2] `compute_consumed_seconds` en `backend/domain/services/sla_service.py` gana
      parámetros opcionales (`resource`, `holidays`, `schedule_slots`, `absences`, default
      `None`) y usa `compute_available_seconds` para el delta cuando vienen informados, dejando
      `sla_consumed_seconds` (la base ya persistida) intacto — de aquí sale el comportamiento
      "hacia adelante únicamente" (research.md Decisión 4) (mismo archivo, tras T028)
- [X] T030 [US2] `compute_state()` en `backend/domain/services/sla_service.py` gana los mismos
      parámetros opcionales y agrega el campo de lectura `pause_reason` (`None` \|
      `"outside_hours"` \| `"holiday"` \| `"absence"` \| `"ticket_status"`) sin cambiar los
      valores posibles de `sla_status` (mismo archivo, tras T029)
- [X] T031 [US2] `active_absence` en `backend/domain/services/availability_service.py` reconoce
      ausencias parciales por horas (compara `start_time`/`end_time` cuando están presentes)
      (depende de T004)
- [X] T032 [US2] Agregar método `list_approved_between(resource_id, start_date, end_date)` a
      `AbsenceRequestRepository` en `backend/infra/repositories/calendar_repo.py` — ranged, solo
      solicitudes con ambos lados `approved` (research.md Decisión 11; `get_active_absence` es de
      un solo día y `list_overlapping` incluye `pending`, ninguno alcanza para sumar
      disponibilidad en un rango multi-día) (depende de T011; mismo archivo que T016/T019, tras
      T019)
- [X] T033 [US2] **(Cierra el hallazgo C1 de `/speckit-analyze`)** En
      `backend/api/routes/tickets.py` (~línea 358, lectura de ticket), resolver
      `ResourceRepository.get_by_id(ticket.assignee_id)` →
      `resolve_effective_schedule_slots(db, resource)` (T019) →
      `HolidayRepository.list_by_country(resource.calendar_country)` (ya existente) →
      `AbsenceRequestRepository.list_approved_between(...)` (T032), y pasar ese contexto a
      `sla_service.compute_state(...)` en vez de `compute_state(ticket, now)` a secas (depende de
      T030, T019, T032)
- [X] T034 [US2] Mismo cableado que T033 en el segundo punto de lectura de
      `backend/api/routes/tickets.py` (~línea 454) (mismo archivo, tras T033)
- [X] T035 [US2] **(Cierra el hallazgo C1 de `/speckit-analyze`)** En
      `backend/workers/sla_tasks.py: check_sla_breaches`, resolver el mismo contexto
      (resource/schedule_slots/holidays/absences) por cada ticket con SLA corriendo antes de
      invocar `sla_service.is_breach`/`compute_state` — hoy esa tarea no importa nada de
      calendario/festivos/horario/ausencias (depende de T030, T019, T032)
- [X] T036 [P] [US2] Endpoint `GET /api/resources/{id}/workload` en
      `backend/api/routes/resources.py`, permiso `resources:view` (mismo `enforce_module
      ("resources")` ya aplicado a `ResourceList`/`ResourceDetail` para GET) (depende de T028,
      T019)
- [X] T037 [US2] Incluir `pause_reason` en la serialización del bloque `sla` de
      `GET /api/tickets/{id}` y `GET /api/tickets` en `backend/api/routes/tickets.py` — mismo
      archivo que T033/T034, cambio de solo lectura, no se tocan transiciones FSM ni otros
      endpoints de Ticket (Principio VII / alcance confirmado) (mismo archivo, tras T034)
- [X] T038 [P] [US2] Test dirigido en `backend/tests/domain/test_sla_dynamic_availability.py`
      con 5-10 registros dummy (festivos, slots de Franja, ausencia parcial), cubriendo el
      escenario estricto del enunciado (depende de T028, T029). **Único test automatizado de
      esta feature** — directriz explícita del usuario / Principio VII: no ejecutar la suite
      global.
- [X] T039 [US2] Agregar tipo `Workload` y el campo `pause_reason` al tipo de SLA del ticket en
      `frontend/src/types/calendar.ts` (depende de T015, mismo archivo)

**Checkpoint**: US1 + US2 funcionales de forma independiente (FR-006 a FR-010).

---

## Phase 5: User Story 3 - Calendario de Equipo Superpuesto (Priority: P2)

**Goal**: overlay real de varios miembros del equipo en una sola vista (Mes/Semana/Día) y
solicitudes de ausencia/permiso parciales por horas, con visualización de carga de trabajo.

**Independent Test**: seleccionar varios miembros (o "Seleccionar todo"), alternar vistas,
registrar una ausencia parcial de 2 horas y verificar que aparece superpuesta junto con
festivos/cumpleaños y que reduce la disponibilidad del ticket asignado.

- [X] T040 [US3] `validate_partial_hours()` + extender `assert_no_overlap` para comparar también
      el rango horario (FR-017) en `backend/domain/services/absence_service.py` (depende de T004)
- [X] T041 [US3] Extender `POST`/`GET /api/absence-requests` en `backend/api/routes/calendar.py`
      para aceptar/devolver `start_time`/`end_time` (depende de T040, T011; mismo archivo que
      T020-T023, tras T023)
- [X] T042 [US3] Agregar `start_time`/`end_time` al tipo `AbsenceRequest` en
      `frontend/src/types/calendar.ts` (depende de T039, mismo archivo)
- [X] T043 [US3] Actualizar creación/listado de ausencias con horas + agregar `getWorkload()` en
      `frontend/src/services/calendarService.ts` (depende de T024, mismo archivo)
- [X] T044 [US3] Fusionar los eventos de los recursos seleccionados en una sola instancia de
      `<FullCalendar>` (overlay real, no una grilla de calendarios separados) + opción
      "Seleccionar todo" en `frontend/src/pages/CalendarPage.tsx` (depende de T043)
- [X] T045 [US3] Agregar vistas conmutables Semana/Día con el plugin `@fullcalendar/timegrid`
      (ya instalado, sin dependencia nueva) en `frontend/src/pages/CalendarPage.tsx` (mismo
      archivo, tras T044)
- [X] T046 [US3] Agregar formulario de solicitud de ausencia/permiso parcial por horas (mismo
      flujo de doble aprobación ya existente) en `frontend/src/pages/CalendarPage.tsx` (mismo
      archivo, tras T045)
- [X] T047 [US3] Agregar visualización de carga de trabajo por recurso (indicador con
      `getWorkload()`) en `frontend/src/pages/CalendarPage.tsx` (mismo archivo, tras T046)

**Checkpoint**: US1 + US2 + US3 funcionales (FR-011 a FR-014, FR-017).

---

## Phase 6: User Story 4 - Vista Diaria priorizada por criticidad (Priority: P3)

**Goal**: la vista de Día ordena y resalta los tickets según Prioridad/Severidad.

**Independent Test**: asignar al mismo recurso tickets de distinta criticidad el mismo día y
verificar que el orden y el resaltado corresponden estrictamente al nivel de criticidad.

> **Nota (corrección tras `/speckit-analyze`, hallazgo I1)**: `Ticket` no tiene un campo de fecha
> propio. La vista de Día **no** filtra tickets por fecha — usa `GET /api/tickets?assignee_id=
> {id}` (filtro ya existente) trayendo los tickets abiertos actualmente asignados al recurso;
> "Día" identifica de quién se ve la agenda, no una fecha del ticket (ver spec.md, Assumptions, y
> contracts/rrhh-calendario-sla-dinamico.md).

- [X] T048 [US4] En la vista de Día, ordenar los tickets asignados (obtenidos vía
      `assignee_id`, sin filtro de fecha) por Prioridad → Severidad
      (`critical`/`high`/`medium`/`low` × `s1`-`s4`) en `frontend/src/pages/CalendarPage.tsx`
      (mismo archivo, tras T047)
- [X] T049 [US4] Resaltar visualmente los tickets de criticidad alta (prioridad
      `critical`/`high`, severidad `s1`/`s2`) en `frontend/src/pages/CalendarPage.tsx` (mismo
      archivo, tras T048)

**Checkpoint**: las 4 historias de usuario funcionales.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T050 [P] Ejecutar manualmente los Escenarios 1-4 de
      [quickstart.md](quickstart.md) contra Docker real — validado: 4 migraciones (041-044)
      aplicadas contra la BD real con migración de datos correcta (2 recursos ya
      "personalizado", 2 "heredado"); permiso `work_hour_templates:manage` sembrado para
      Admin/RRHH; en el navegador contra `sywork_frontend`/`sywork_backend` reales: menú RRHH
      con Calendario/Permisos/Franjas Horarias, creación de Franja Horaria (POST 201),
      listado de Personalizados, superposición de calendario de equipo con "Seleccionar todo"
      (13 recursos fusionados en una sola vista sin errores de consola) + panel de carga de
      trabajo con valores reales de `GET /.../workload`; permiso parcial por horas creado vía
      API (`start_time`/`end_time` persistidos) y solape parcial correctamente rechazado
      (`error: overlap`) vs. horario disjunto correctamente aceptado
- [X] T051 Confirmado: `backend/tests/domain/test_sla_dynamic_availability.py` (T038) es el
      único archivo de test nuevo (7 tests). Validación adicional ejecutada, acotada a los
      módulos directamente tocados (no la suite global): `test_availability_service.py`,
      `test_sla_service.py`, `test_absence_service.py` (dominio), y
      `test_tickets_sla.py`/`test_tickets_sla_filters.py`/`test_sla_rules.py`/
      `test_resources_and_skills_api.py`/`test_holiday_api_client.py` (API/infra, ya
      existentes) — 38 + 51 = 89 tests pasando, cero regresiones. `npx tsc -b` del frontend
      sin errores. No se ejecutó `pytest` sin acotar ni la suite global de integración
      (Principio VII / directriz explícita del usuario).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede empezar de inmediato
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las historias
- **US1 (Phase 3)**: depende de Foundational (en particular T016/T017, los repositorios nuevos)
- **US2 (Phase 4)**: depende de Foundational + T019 (US1, `resolve_effective_schedule_slots`) —
  el resto de US2 (funciones de dominio, cableado en `tickets.py`/`sla_tasks.py`, workload) es
  funcionalmente independiente de que exista ya la UI de US1
- **US3 (Phase 5)**: depende de Foundational + T020-T023 (US1, mismo archivo `calendar.py`) y
  T039 (US2, mismo archivo `calendar.ts`) por edición secuencial de archivo compartido, no por
  acoplamiento funcional
- **US4 (Phase 6)**: depende de Foundational + T047 (US3, mismo archivo `CalendarPage.tsx`)
- **Polish (Phase 7)**: depende de todas las historias que se vayan a entregar

### Notas de dependencia por archivo compartido

Varias tareas de historias distintas comparten archivo (`backend/api/routes/calendar.py`,
`backend/api/routes/tickets.py`, `backend/infra/repositories/calendar_repo.py`,
`frontend/src/pages/CalendarPage.tsx`, `frontend/src/types/calendar.ts`,
`frontend/src/services/calendarService.ts`) y por eso se numeran secuencialmente aunque
pertenezcan a historias diferentes — esto es una restricción de edición de archivo, no una
dependencia funcional real entre historias (cada historia sigue siendo independientemente
verificable vía su "Independent Test").

### Parallel Opportunities

- T001, T002 (Setup) en paralelo
- T003→T004 secuencial; T005 en paralelo con ambos (archivo distinto)
- T006→T007 secuencial; T008 en paralelo (archivo distinto)
- T009→T010 secuencial; T011, T012 en paralelo entre sí y con T009/T010 (migraciones distintas)
- T013 en paralelo con el bloque de migraciones; T014 depende de T013
- T015 en paralelo con todo lo anterior (archivo distinto)
- T017 en paralelo con T016 (archivos distintos: `resource_repo.py` vs `calendar_repo.py`)
- Dentro de US2: T036 y T038 en paralelo entre sí (archivos distintos, ambos dependen de T028)

---

## Parallel Example: Foundational

```bash
# En paralelo (archivos distintos, sin dependencias entre sí):
Task: "Agregar schedule_mode/work_hour_template_id a la dataclass Resource en backend/domain/entities/resource.py"
Task: "Agregar RRHH_GROUP_KEY/rrhhNavItems en frontend/src/config/navigation.tsx"
Task: "Agregar tipos WorkHourTemplate/WorkHourTemplateSlot en frontend/src/types/calendar.ts"
Task: "Agregar list_by_schedule_mode a ResourceRepository en backend/infra/repositories/resource_repo.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 únicamente)

1. Completar Fase 1 (Setup) y Fase 2 (Foundational)
2. Completar Fase 3 (US1 — Franjas Horarias + Personalizado)
3. **Detener y validar**: Escenario 1 de quickstart.md
4. US1 por sí solo ya es útil para RRHH aunque el motor de SLA aún use el horario por defecto

### Entrega incremental

1. Setup + Foundational → base lista
2. US1 (Franjas Horarias) → validar → demo
3. US2 (SLA Dinámico) → validar con el escenario estricto del enunciado, **incluyendo el
   cableado real hacia `tickets.py`/`sla_tasks.py` (T033-T035)** → demo — **valor de negocio
   central**, se puede entregar sin esperar a US3/US4
4. US3 (Calendario superpuesto + ausencias parciales) → validar → demo
5. US4 (Vista diaria priorizada) → validar → cierre de la fase

---

## Notes

- Tests limitados a T038 por directriz explícita del usuario y Principio VII de la constitución
  — no agregar tests de integración ni de otras historias sin pedido explícito.
- No se modifica ningún controlador de Ticket más allá de la lectura de solo-lectura en
  T033/T034/T037 (Principio VII / alcance confirmado en plan.md).
- Cero dependencias nuevas (Principio V) — `@fullcalendar/timegrid` ya está instalado desde
  spec 020.
- **No saltarse T033-T035**: son las tareas que realmente conectan las funciones de dominio de
  US2 con datos reales — sin ellas, `compute_available_seconds` existiría pero nunca se
  invocaría (hallazgo C1 de `/speckit-analyze`).
- Commitear tras cada tarea o grupo lógico; detenerse en cada checkpoint para validar la
  historia de forma independiente antes de continuar.
