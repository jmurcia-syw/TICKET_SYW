# Tasks: Festivos sincronizados por API, categorización visual y cumpleaños en el Calendario

**Input**: Design documents from `specs/021-festivos-api-cumpleanos/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/festivos-api-cumpleanos.md](contracts/festivos-api-cumpleanos.md),
[quickstart.md](quickstart.md)

**Tests**: Se incluyen tareas de test unitario ultra-limitadas (≤10 registros de prueba, Principio
VII), consistente con el criterio ya usado en spec 020 para servicios de dominio con lógica no
trivial: el filtro de disponibilidad por categoría (`availability_service.py`) y el cliente HTTP
externo mockeado (`holiday_api_client.py`). No se generan contract tests ni se corre la suite
completa.

**Organization**: Tareas agrupadas por historia de usuario (spec.md) para permitir implementación
y prueba independiente de cada una.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)
- Cada tarea incluye la ruta de archivo exacta

## Path Conventions

Web app existente: `backend/` (Flask, Clean Architecture 3 capas) + `frontend/` (React 19 +
TypeScript, Ant Design 5). Ver `plan.md` → Project Structure para el árbol completo.

---

## Phase 1: Setup

**Purpose**: Confirmar que la integración externa es viable antes de construir sobre ella (sin
dependencias nuevas que instalar — `requests` ya está en `requirements.txt`, research.md
Decisión 1)

- [X] T001 [P] Verificar conectividad saliente real desde `sywork_backend` hacia
      `https://date.nager.at/api/v3/PublicHolidays/2026/CO` (`docker exec sywork_backend python -c
      "import requests; print(requests.get(...).status_code)"`) — confirma que el entorno permite
      la llamada antes de escribir el cliente HTTP. Verificado: `200`, 19 festivos oficiales de
      Colombia para 2026 recibidos, incluyendo el 20 de julio ("Declaracion de la Independencia de
      Colombia") que faltaba en el seed manual de spec 020. Confirmado además que la API no
      distingue festivos oficiales de religiosos/regionales (ambos con `types:["Public"]`), por lo
      que esa categorización sigue siendo, correctamente, una decisión humana (research.md
      Decisión 1)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Esquema de base de datos, entidad/modelo/repositorio de `holidays` extendidos y el
cliente HTTP externo que US1 y US2 necesitan

**⚠️ CRITICAL**: Ninguna historia backend puede empezar hasta completar esta fase (US3 es 100%
frontend y no depende de esta fase — ver "User Story Dependencies" más abajo)

- [X] T002 [P] Migración `backend/infra/migrations/versions/040_holidays_categoria_sync.py`:
      agrega `holidays.category` (`text`, default `'oficial'`, CHECK
      `IN ('oficial','regional_religioso')`) y `holidays.source` (`text`, default `'manual'`,
      CHECK `IN ('api','manual')`); crea tabla `holiday_sync_status` (`country`, `year`,
      `last_synced_at`, `success`, `error_message`, `UNIQUE (country, year)`), sin RLS
      (data-model.md). Aplicada con `alembic upgrade head` sin errores; verificado con `\d
      holidays`/`\d holiday_sync_status` que las columnas, CHECK constraints y el UNIQUE quedaron
      correctos, y que los 5 festivos ya sembrados en spec 020 quedaron con los defaults
      (`oficial`/`manual`)
- [X] T003 [P] Agregar `category: str = "oficial"` y `source: str = "manual"` a `Holiday` en
      `backend/domain/entities/calendar.py`
- [X] T004 Extender `HolidayModel` en `backend/infra/models/calendar_model.py` (`category`,
      `source`, `to_entity()`); crear `HolidaySyncStatusModel` — depende de T002, T003
- [X] T005 [P] Crear `backend/infra/external/holiday_api_client.py`:
      `fetch_public_holidays(country: str, year: int) -> list[dict]`, llama
      `GET https://date.nager.at/api/v3/PublicHolidays/{year}/{country}` con `requests`, timeout
      corto (~3s), captura `RequestException`/HTTP no-200 y los relanza como una excepción propia
      (`HolidayApiError`) para que el llamador decida cómo degradar (FR-003). 3 tests unitarios
      (T008) pasan mockeando `requests.get`
- [X] T006 Extender `HolidayRepository` en `backend/infra/repositories/calendar_repo.py`:
      `list_by_country(country, category=None)` con filtro opcional por categoría; `create`,
      `activate`/`deactivate` y el nuevo `update` (T016) fuerzan `source='manual'`;
      `upsert_api_holiday(country, holiday_date, name)` que **omite** la fecha si ya existe
      cualquier festivo manual ese mismo día para ese país (evita duplicados nombre-distinto de un
      mismo feriado, ver research.md Decisión 6); nuevo `HolidaySyncStatusRepository`
      (`get(country, year)`, `record_attempt(country, year, success, error_message=None)`) —
      depende de T004
- [X] T007 [P] Agregar `category: 'oficial' | 'regional_religioso'` y `source: 'api' | 'manual'`
      a `Holiday` en `frontend/src/types/calendar.ts` — `tsc --noEmit` limpio

**Checkpoint**: Modelo de datos y cliente HTTP listos — US1 y US2 pueden avanzar en paralelo. US3
no depende de nada de esta fase.

---

## Phase 3: User Story 1 - Festivos oficiales siempre completos y actualizados (Priority: P1) 🎯 MVP

**Goal**: `GET /api/holidays` siempre devuelve el calendario oficial completo de un país,
sincronizado automáticamente desde Nager.Date, sin bloquear el sistema si la fuente externa falla.

**Independent Test**: seleccionar un país sin festivos `source='api'` aún, consultar
`GET /api/holidays?country=CO` y verificar que aparece el calendario oficial completo, incluyendo
el 20 de julio ("Día de la Independencia") que faltaba en la carga manual de spec 020.

### Tests for User Story 1

- [X] T008 [P] [US1] Test unitario `backend/tests/infra/test_holiday_api_client.py`: caso de
      respuesta válida (mock de `requests.get`) y caso de timeout/error HTTP → `HolidayApiError`
      (≤10 registros de prueba). 3/3 tests pasan (`pytest tests/infra/test_holiday_api_client.py`)

### Implementation for User Story 1

- [X] T009 [US1] Crear `backend/infra/external/holiday_sync_service.py::sync_country(db, country,
      year) -> bool`: llama `holiday_api_client.fetch_public_holidays`, mapea cada festivo
      recibido a `HolidayRepository.upsert_api_holiday(...)` (`category='oficial'`,
      `source='api'`), registra el resultado vía `HolidaySyncStatusRepository.record_attempt` —
      depende de T005, T006
- [X] T010 [US1] Crear `backend/workers/holiday_sync_tasks.py`: tarea Celery
      `sync_holidays` (mismo patrón que `sla_tasks.py::check_sla_breaches`) — recorre países
      distintos de `clients.country`/`resources.calendar_country` (no nulos), sincroniza año
      actual + siguiente vía `sync_country`; registrar en `celery_app.conf.beat_schedule`
      (`crontab(hour=3, minute=0)`, diaria) — depende de T009. Verificado registrado vía `celery
      inspect registered`
- [X] T011 [US1] Extender `GET /api/holidays` en `backend/api/routes/calendar.py`: si
      `HolidaySyncStatusRepository.get(country, año_actual)` no existe, invocar `sync_country`
      inline (año actual y siguiente) antes de responder, con manejo de excepción que nunca
      propaga error HTTP (FR-003); exponer `category`/`source` en el modelo Swagger `_holiday_out`
      y en la serialización — depende de T009
- [X] T012 [US1] Verificar en Docker que `GET /api/holidays?country=CO` ya incluye el 20 de julio
      y el resto del calendario oficial colombiano (FR-015) — se autocompleta por el mecanismo de
      T011, sin necesidad de migración de datos adicional (Colombia ya tiene festivos `manual` de
      spec 020, pero ninguno `source='api'`, así que el disparador de sincronización sigue
      cumpliéndose). Verificado vía curl real: 19 festivos 2026 + 19 2027 recibidos, incluye "20
      de julio — Declaracion de la Independencia de Colombia" (`source=api`); los 5 festivos
      manuales previos (Año Nuevo, Día de la Raza, Navidad en CO/MX) se preservaron sin duplicados
      (dedup por fecha-manual funcionó correctamente); `holiday_sync_status` quedó con una fila
      `success=true` por país/año
- [X] T013 [US1] Validar Escenario 1 de `quickstart.md` contra Docker

**Checkpoint**: US1 funciona de forma independiente — el calendario de festivos oficiales se
autocompleta y mantiene al día sin intervención manual.

---

## Phase 4: User Story 2 - Distinguir festivos oficiales de celebraciones regionales/religiosas (Priority: P2)

**Goal**: cada festivo se categoriza como Oficial o Regional/Religioso, se distingue visualmente
en el calendario, y solo lo Oficial afecta el cálculo de disponibilidad.

**Independent Test**: crear un festivo oficial (sincronizado) y uno regional/religioso manual
(ej. "Virgen del Rosario de Chiquinquirá") para el mismo país; verificar colores distintos en el
calendario y que solo el oficial produce `reason: "holiday"` en
`GET /api/resources/availability`.

### Tests for User Story 2

- [X] T014 [P] [US2] Test unitario en `backend/tests/domain/test_availability_service.py`: caso
      "festivo `category='regional_religioso'` activo hoy → `available: true`" y caso "festivo
      `category='oficial'` activo hoy → `available: false, reason: holiday`" (≤10 registros) —
      depende de T003. 8/8 tests del archivo pasan (6 previos de spec 020 + 2 nuevos)

### Implementation for User Story 2

- [X] T015 [US2] Extender `POST /api/holidays` (`backend/api/routes/calendar.py`): acepta
      `category` opcional (default `"oficial"`), valida los dos valores permitidos, `source`
      siempre `"manual"` en creación manual — depende de T006
- [X] T016 [US2] Crear `PATCH /api/holidays/{id}` (endpoint nuevo, `backend/api/routes/calendar.py`,
      permiso `holidays:manage`): edita `name`/`holiday_date`/`category` de un festivo existente,
      fuerza `source='manual'` sin importar su valor previo (FR-009) — depende de T006. Verificado
      vía curl: PATCH reclasificando "Día de la Virgen de Chiquinquirá" (sincronizada como
      `oficial`/`api`) a `category=regional_religioso` → `source` pasó a `manual` correctamente
- [X] T017 [US2] Extender `PATCH /api/holidays/{id}/activate|deactivate` existentes para forzar
      `source='manual'` al ejecutarse — depende de T006 (implementado directamente en
      `HolidayRepository.set_active`, sin cambios adicionales en la ruta)
- [X] T018 [US2] Filtrar por `category == "oficial"` antes de evaluar disponibilidad: el
      repositorio que alimenta `compute_availability` (`backend/domain/services/
      availability_service.py`) solo debe pasarle festivos oficiales — depende de T003, T006
      (filtro aplicado dentro de `_has_holiday_today`, dominio puro, per research.md Decisión 5).
      Verificado end-to-end vía `GET /api/resources/availability` con un recurso de prueba
      (`calendar_country=CO` ISO correcto): 13 de julio (Chiquinquirá, regional) →
      `available:true`; 20 de julio (Independencia, oficial) → `available:false,
      reason:holiday`
- [X] T019 [P] [US2] Agregar `updateHoliday(id, data)` a
      `frontend/src/services/calendarService.ts` — depende de T007
- [X] T020 [US2] Colorear festivos por `category` (naranja = oficial, púrpura = regional/religioso)
      + leyenda simple en `frontend/src/pages/CalendarPage.tsx` (`HolidayCalendar`) — depende de
      T019. `tsc --noEmit` limpio; verificado replicando la lógica exacta contra datos reales del
      backend (ver T023) que el color asignado es correcto por categoría
- [X] T021 [US2] Validar Escenario 2 de `quickstart.md` contra Docker

**Checkpoint**: US1 y US2 funcionan juntas — festivos completos, categorizados y con el efecto
correcto (o nulo) sobre disponibilidad.

---

## Phase 5: User Story 3 - Cumpleaños del equipo visibles en el calendario (Priority: P3)

**Goal**: la pestaña Equipo del calendario muestra un evento anual recurrente en la fecha de
cumpleaños de cada Recurso seleccionado con `birth_date` configurado.

**Independent Test**: configurar `birth_date` en un Recurso, seleccionarlo en la pestaña Equipo y
verificar que aparece un evento anual distinguible de los festivos; un recurso sin `birth_date` no
genera ningún evento.

### Implementation for User Story 3

- [X] T022 [US3] En `frontend/src/pages/CalendarPage.tsx` (pestaña Equipo): generar, por cada
      recurso seleccionado con `birth_date` no nulo (campo ya expuesto por `GET /api/resources` —
      sin cambios de backend, research.md Decisión 7), eventos de FullCalendar para una ventana de
      año actual ± 2 en el día/mes de su cumpleaños, con color/ícono (🎂) distinto de los festivos,
      fusionados con los eventos de `HolidayCalendar` del mismo recurso
- [X] T023 [US3] Validar Escenario 3 de `quickstart.md` contra Docker. Nota: la selección
      interactiva del Select multi-valor "Equipo" no pudo completarse por clic/teclado
      automatizado en ninguna de dos pestañas de navegador distintas (una de ellas totalmente
      reiniciada) — instrumentado con listeners de eventos, se confirmó que ni clics ni teclas
      llegan al elemento `option`/input real pese a que `elementFromPoint` ubica el elemento
      correcto (mismo tipo de limitación de la herramienta de automatización ya documentada en
      spec 020, no un defecto del producto). Se compensó ejecutando en la consola del navegador,
      con el token de sesión real, un `fetch` a `/api/holidays?country=CO` y
      `/api/resources?active=true` y reproduciendo la lógica EXACTA de `_birthdayEvents`/color de
      `CalendarPage.tsx` contra esos datos reales: para el recurso `admin` con `birth_date`
      temporal `1990-07-20` (revertido a `null` al finalizar), se generaron correctamente 5
      eventos anuales "🎂 admin" (2024-2028) en color verde, distintos del festivo oficial del 20
      de julio (naranja) que cae el mismo día — confirma el edge case "festivo y cumpleaños el
      mismo día se muestran como eventos independientes". Confirmado además que un `birth_date`
      nulo hace que `_birthdayEvents` retorne `[]` (guard clause trivial, sin necesidad de prueba
      adicional en vivo)

**Checkpoint**: Las 3 historias de usuario funcionan de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T024 [P] Revisar en Swagger UI que `PATCH /api/holidays/{id}` quedó documentado
      (`@ns.doc`/`@ns.response`) antes de darse por completo (Principio I). Verificado
      descargando `/swagger.json` real: los 4 endpoints de festivos (`GET`/`POST /api/holidays`,
      `PATCH /api/holidays/{holiday_id}`, `PATCH /api/holidays/{holiday_id}/{action}`) tienen
      `summary` y códigos de respuesta documentados
- [X] T025 Ejecutar los 3 escenarios de `quickstart.md` de punta a punta en una sola pasada contra
      Docker, sin atajos entre historias. Escenario 1: sincronización automática verificada (19
      festivos CO 2026 incl. 20 de julio, sin duplicar los 3 manuales previos). Escenario 2:
      categorización + efecto en disponibilidad verificados end-to-end (Chiquinquirá→regional→no
      bloquea; Independencia→oficial→sí bloquea). Escenario 3: cumpleaños verificados
      reproduciendo la lógica real de `CalendarPage.tsx` contra datos reales del backend (ver nota
      de T023 sobre la limitación de automatización del Select)
- [X] T026 Confirmar que `holiday_sync_status` permanece sin RLS (mismo criterio que
      `holidays`/`work_schedules`, Decisión 8 de `research.md`) y que
      `POST /api/tickets/{id}/assign` no fue modificado por esta fase. Verificado:
      `rowsecurity=f` en las 3 tablas; `tickets.py` sin cambios en el árbol de trabajo, último
      commit `990c711` (previo a esta fase)
- [X] T027 Confirmar que la tarea Celery `sync_holidays` está registrada
      (`docker exec sywork_worker celery -A backend.workers.celery_app inspect registered`) y que
      no interfiere con `check_sla_breaches` ni otras tareas ya existentes. Verificado: ambas
      tareas (`sync_holidays`, `check_sla_breaches`) listadas como registradas, worker `OK`, sin
      errores en logs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede iniciar de inmediato
- **Foundational (Phase 2)**: depende de Setup — bloquea US1 y US2 (no a US3)
- **US1/US2 (Phase 3-4)**: dependen de Foundational; pueden avanzar en paralelo o en orden de
  prioridad P1→P2
- **US3 (Phase 5)**: sin dependencia de Foundational ni de US1/US2 — puede desarrollarse en
  cualquier momento, en paralelo con todo lo demás
- **Polish (Phase 6)**: depende de que las historias que se vayan a entregar estén completas

### User Story Dependencies

- **US1 (P1)**: depende de Foundational (T002-T007). No depende de US2/US3.
- **US2 (P2)**: depende de Foundational. Reutiliza el mecanismo de sincronización de US1
  (los festivos oficiales que categoriza pueden venir de T009-T011), pero es independientemente
  probable — un festivo `category='regional_religioso'` se puede crear manualmente sin que la
  sincronización automática haya corrido nunca.
- **US3 (P3)**: sin dependencias — usa datos (`Resource.birth_date`) y componentes
  (`CalendarPage.tsx`) que ya existían desde spec 020, no toca nada de esta fase.

### Parallel Opportunities

- Foundational: T002, T003, T005, T007 marcadas `[P]` (archivos distintos)
- Una vez completada Foundational: US1 y US2 pueden avanzar en paralelo por desarrolladores
  distintos; US3 puede avanzar en paralelo desde el inicio, sin esperar a Foundational
- Dentro de cada historia, los tests marcados `[P]` corren en paralelo con tareas de otra
  historia, nunca con la implementación de su propia historia (mismo archivo `calendar.py`
  compartido dentro de la historia)

---

## Parallel Example: Foundational

```bash
Task: "Migración 040 category/source + holiday_sync_status"
Task: "Holiday entity: category/source en calendar.py"
Task: "holiday_api_client.py (cliente HTTP Nager.Date)"
Task: "frontend/src/types/calendar.ts: category/source"
```

---

## Implementation Strategy

### MVP First (User Story 1 solamente)

1. Completar Phase 1 (Setup) + Phase 2 (Foundational)
2. Completar Phase 3 (US1) — festivos oficiales sincronizados automáticamente
3. **Detenerse y validar**: Escenario 1 de `quickstart.md` — confirmar que Colombia ya incluye el
   20 de julio
4. Demo: el calendario de cualquier país nuevo se autocompleta solo, sin cargar festivos a mano

### Incremental Delivery

1. Setup + Foundational → base lista
2. US1 → validar → demo (MVP: festivos siempre completos y actualizados)
3. US2 → validar → demo (categorización visual + efecto correcto en disponibilidad)
4. US3 → validar → demo (cumpleaños del equipo, puede entregarse en cualquier punto — es
   independiente del resto)
5. Polish → cierre de fase

### Parallel Team Strategy

Con más de un desarrollador: Foundational se completa en equipo; luego una persona toma US1
(sincronización/backend), otra toma US2 (categorización, depende de que Foundational esté listo
pero no de que US1 termine), y una tercera puede tomar US3 desde el primer día (sin esperar nada).
