# Tasks: Cronómetro Manual de Tiempo en el Ticket

**Input**: Design documents from `specs/012-cronometro-manual-ticket/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/timer.md, quickstart.md

**Tests**: incluidos y **dirigidos**, siguiendo la convención ya establecida en el proyecto
(specs `007`-`010`): tests específicos de lo que cambia, sin exigir la suite completa durante el
desarrollo salvo en la validación de cierre (Fase 6).

**Organización**: tareas agrupadas por User Story. Orden de ejecución: US1 → US2 → US3 (mismo
orden de prioridad que en spec.md; US1 es el MVP).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] ciclo iniciar/pausar/reanudar/terminar, [US2] persistencia entre
  recargas/sesiones, [US3] visibilidad personal por recurso

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): sin cambios en
  `backend/requirements.txt` ni `frontend/package.json` (ver plan.md Technical Context — sin
  Celery/Redis/WebSockets)

**Checkpoint**: sin cambios de dependencias.

---

## Phase 2: Foundational (bloqueante para las 3 historias)

**Nota**: la migración `026` crea la única tabla nueva de esta feature; nada es probable sin
ella.

- [X] T002 Migración `backend/infra/migrations/versions/026_ticket_timers.py` (down_revision
  `025`): crear tabla `ticket_timers` (PK `resource_id` FK `resources.id` ON DELETE CASCADE,
  `ticket_id` FK `tickets.id` nullable ON DELETE SET NULL, `status` texto CHECK
  `inactive|running|paused` default `inactive`, `accumulated_seconds` entero default `0`,
  `started_at` TIMESTAMPTZ nullable, `created_at`/`updated_at`), CHECK de consistencia de
  estado (data-model.md), RLS app-level (mismo patrón que `025_project_members_skills.py` —
  el aislamiento real por `resource_id` se aplica en la capa API, no en Postgres).
  `downgrade` completo (depende de T001)
- [X] T003 [P] `backend/domain/entities/ticket_timer.py` nuevo: dataclass `TicketTimer`
  (`resource_id, ticket_id, status, accumulated_seconds, started_at, created_at, updated_at`) +
  método puro `total_seconds(now: datetime) -> int` (accumulated_seconds + now-started_at si
  running, si no accumulated_seconds), sin imports de framework (depende de T002)
- [X] T004 `backend/infra/models/ticket_timer_model.py` nuevo: `TicketTimerModel` SQLAlchemy +
  `to_entity()`/`from_entity()` (depende de T003)
- [X] T005 `backend/infra/repositories/ticket_timer_repo.py` nuevo: `get_by_resource(resource_id)`
  (si no existe fila, devuelve un `TicketTimer` transitorio en memoria con `status=inactive` sin
  persistir hasta el primer `start`), `save(timer)` (upsert por `resource_id`) (depende de T004)
- [X] T006 [P] `frontend/src/types/timer.ts` nuevo: `type TimerStatus = 'inactive' | 'running' |
  'paused'`; interfaz `Timer` (`status: TimerStatus, ticket_id: string | null, ticket_number:
  string | null, total_seconds: number, running_seconds: number, stale: boolean`)
- [X] T007 [P] `frontend/src/services/timerService.ts` nuevo: `getCurrent()`,
  `start(ticketId: string)`, `pause()`, `resume()`, `finish(note?: string)` — llamadas Axios a
  `/api/timer*` (depende de T006)

**Checkpoint**: migración `026` aplicada, entidad/modelo/repo base y tipos/servicio frontend
listos — las 3 historias pueden arrancar.

---

## Phase 3: User Story 1 — Iniciar, pausar, reanudar y terminar el cronómetro (Priority: P1) 🎯 MVP

**Goal**: ciclo completo de control del cronómetro por el recurso, con generación de un Registro
de tiempo real al terminar, reutilizando las validaciones ya existentes de `work_sessions`
(spec `004`).
**Independent Test**: Escenarios 1, 4, 5 y 6 del quickstart (ciclo completo, un solo cronómetro
activo por recurso, bloqueo en ticket cerrado, duración mínima).

- [X] T008 [US1] `backend/domain/services/ticket_timer_service.py` nuevo:
  `start(resource_id, ticket_id, timer_repo, tickets_repo, resources_repo, is_task)` (valida
  ticket existe → 404; reutiliza `WorkSessionService.assert_ticket_ownership()` para 403
  `not_assigned`; si ya hay timer `running`/`paused` en **otro** ticket → 409
  `timer_already_active` con el `ticket_id` en curso; si no, crea/reemplaza fila con
  `status=running, accumulated_seconds=0, started_at=now`); `pause(resource_id, timer_repo)`
  (409 `no_active_timer` si no `running`); `resume(resource_id, timer_repo)` (409
  `no_paused_timer` si no `paused`); `finish(resource_id, note, timer_repo, work_session_service,
  work_sessions_repo, tickets_repo, resources_repo, is_task)` (calcula total; si < 60s → 409
  `duration_too_short` **sin resetear** el timer; si no, delega en
  `WorkSessionService.create()` ya existente — mismas validaciones de ticket cerrado/límite
  diario, que se propagan tal cual como 409 `ticket_closed`/`daily_limit_exceeded` **sin
  resetear** el timer si fallan; si `create()` tiene éxito, resetea el timer a `inactive`)
  (depende de T005; reutiliza `backend/domain/services/work_session_service.py` sin
  modificarlo)
- [X] T009 [US1] `backend/api/routes/timer.py` nuevo, según `contracts/timer.md`: namespace
  `timer`, path `/api/timer`; `GET /api/timer` (calcula `total_seconds`/`running_seconds`/
  `stale` al vuelo con `TicketTimer.total_seconds(now)`, umbral `stale` = 12h de referencia);
  `POST /api/timer/start` (body `ticket_id`), `/pause`, `/resume`, `/finish` (body opcional
  `note`); todos con `@require_permission("work_sessions", "manage")`; el `resource_id` se
  resuelve **siempre** de `ResourceRepository(db).get_by_user_id(g.current_user.id)`, ningún
  endpoint acepta `resource_id` en query/body (a diferencia de `work_sessions`, sin variante
  "para otro recurso" — FR-005); reutiliza el helper `_is_task` de
  `backend/api/routes/work_sessions.py` (o una copia local de 3 líneas) para pasar `is_task` a
  `assert_ticket_ownership` (depende de T008)
- [X] T010 [US1] Registrar el namespace `timer` en `backend/app.py` (`api.add_namespace`, junto
  a los demás) (depende de T009)
- [X] T011 [P] [US1] Test API `backend/tests/api/test_timer.py`: `POST /start` → 201 `running`;
  segundo `start` con otro `ticket_id` → 409 `timer_already_active`; `pause` → `paused`;
  `pause` estando ya `paused` → 409; `resume` → `running`; `finish` crea `WorkSession` con
  `duration_minutes` correcto (±1) y el timer vuelve a `inactive`; `finish` con < 1 minuto
  acumulado → 409 `duration_too_short` y el timer sigue activo; `finish` con el ticket
  `cerrado` → 409 `ticket_closed` y el timer sigue activo (no se resetea); `start` sobre un
  ticket donde el recurso no participa → 403 `not_assigned`; sin permiso
  `work_sessions:manage` → 403. Correr solo este archivo (depende de T010)
- [X] T012 [US1] Frontend `frontend/src/components/worksessions/TicketTimerWidget.tsx` nuevo:
  botones Iniciar/Pausar/Reanudar/Terminar (Ant Design), estado inicial vía
  `timerService.getCurrent()`, tick visual local (`setInterval` 1s) calculado desde
  `total_seconds` + timestamp de la última respuesta del servidor (nunca un contador propio
  independiente del backend); modal simple de confirmación para "Terminar" con campo `note`
  opcional (depende de T007)
- [X] T013 [US1] Wire: montar `<TicketTimerWidget>` en
  `frontend/src/pages/TicketDetailPage.tsx` junto a `TicketWorkSessions`, visible solo con
  `hasPermission('work_sessions', 'manage')` (depende de T012)

**Checkpoint US1**: Escenarios 1, 4, 5 y 6 del quickstart ejecutables end-to-end — MVP
funcional.

---

## Phase 4: User Story 2 — Persistencia entre recargas y sesiones (Priority: P1)

**Goal**: el estado del cronómetro sobrevive a recargas de página, navegación y cierres de
sesión porque se deriva siempre de timestamps guardados en el servidor, nunca de estado del
navegador.
**Independent Test**: Escenario 2 del quickstart.

- [X] T014 [US2] Endurecer `GET /api/timer` (`backend/api/routes/timer.py`) para garantizar que
  el cálculo de `total_seconds`/`running_seconds` sea puramente derivado de
  `started_at`/`accumulated_seconds` guardados en BD (sin ningún estado en memoria del proceso
  Flask), de forma que sobreviva también a un reinicio del backend, no solo a un reload del
  navegador (depende de T009)
- [X] T015 [US2] Frontend `TicketTimerWidget.tsx`: al montar el componente (carga inicial de la
  página del ticket, incluida una recarga completa), llamar `timerService.getCurrent()` y
  resincronizar el tick visual desde el valor servidor-side antes de mostrar cualquier número
  (evitar parpadeo en 0 mientras carga) (depende de T012)
- [X] T016 [P] [US2] Test API `backend/tests/api/test_timer.py` += casos de persistencia:
  iniciar un timer, simular el paso del tiempo manipulando `started_at` en el pasado vía
  fixture/BD directa, y confirmar que una llamada `GET /api/timer` **nueva** (sesión/request
  distinta) refleja el `total_seconds` correcto; pausar y confirmar que llamadas `GET`
  sucesivas separadas en el tiempo devuelven el mismo `total_seconds` (no avanza en pausa).
  Correr solo este archivo (depende de T014)

**Checkpoint US2**: Escenario 2 del quickstart ejecutable end-to-end.

---

## Phase 5: User Story 3 — Cronómetro personal por recurso (Priority: P2)

**Goal**: ningún usuario distinto de quien inició el cronómetro puede verlo ni controlarlo.
**Independent Test**: Escenario 3 del quickstart.

- [X] T017 [US3] Confirmar en `backend/api/routes/timer.py` (Swagger incluido) que ningún
  endpoint acepta `resource_id` como parámetro — a diferencia de `work_sessions`, el cronómetro
  no tiene variante `manage_all`/"para otro recurso"; documentar explícitamente esa ausencia en
  las descripciones Swagger de cada ruta (depende de T009)
- [X] T018 [P] [US3] Test API `backend/tests/api/test_timer.py` += con dos recursos distintos
  (fixtures A y B): A inicia su cronómetro en el Ticket X; `GET /api/timer` autenticado como B
  devuelve `status: inactive` (no ve el de A); B inicia su propio cronómetro en su propio
  Ticket Y (un mismo ticket solo admite un resolutor asignado a la vez vía Triage — ver
  quickstart.md Escenario 3); ambos avanzan de forma independiente (`pause` de uno no afecta al
  otro); cada `finish` genera su propio `WorkSession` distinto. Correr solo este archivo
  (depende de T017)

**Checkpoint US3**: Escenario 3 del quickstart ejecutable end-to-end.

---

## Phase 6: Polish y validación transversal

- [X] T019 [P] Swagger revisado contra `contracts/timer.md`: `GET/POST /api/timer{,/start,
  /pause,/resume,/finish}`, códigos 400/403/404/409 documentados con sus `error` codes exactos
- [X] T020 Ejecutar `quickstart.md` (Escenarios 0-6) contra Docker real: migración, ciclo
  completo, persistencia, visibilidad personal, un solo timer activo, ticket cerrado, duración
  mínima
- [X] T021 Validación dirigida de cierre: `docker exec sywork_backend pytest
  tests/api/test_timer.py tests/api/test_work_sessions_create.py
  tests/api/test_work_sessions_start_end.py -v` (el cronómetro reutiliza `WorkSessionService`,
  se corre junto a sus tests para detectar regresiones cruzadas); `cd frontend && npx tsc -b` →
  sin errores

**Checkpoint Final**: quickstart completo en verde y tests dirigidos en verde.

---

## Dependencies & Execution Order

```
Phase 1 (T001)
→ Phase 2 (T002 → T003 → T004 → T005; T006 → T007, en paralelo con la rama backend)
→ Phase 3/US1 (T008 → T009 → T010 → T011∥; T012 → T013)
→ Phase 4/US2 (T014 → T016∥; T015 [mismo archivo que T012])
→ Phase 5/US3 (T017 → T018∥)
→ Phase 6 (T019∥, T020, T021)
```

- US1, US2 son P1; US3 es P2. US1 va primero por ser el MVP — sin el ciclo completo de control
  no hay nada que persista (US2) ni nada que aislar por recurso (US3).
- US2 y US3 comparten archivos con US1 (`timer.py`, `TicketTimerWidget.tsx`) — dependencia de
  archivo, no de dominio; cada historia sigue siendo probable de forma independiente contra el
  comportamiento ya desplegado por US1.
- Ninguna historia depende de `specs/011-ticket-skills-requeridas` ni de otra spec en curso.

## Parallel Example: Foundational

```bash
# Tras T005 (repo backend listo):
Task: "Tipos frontend frontend/src/types/timer.ts"          # T006
Task: "Servicio frontend frontend/src/services/timerService.ts"  # T007 (depende de T006)
```

## Parallel Example: User Story 1

```bash
# Tras T010 (namespace registrado):
Task: "Test API tests/api/test_timer.py"                    # T011
Task: "Componente TicketTimerWidget.tsx"                    # T012 (frontend, archivo distinto)
```

---

## Implementation Strategy

1. **MVP = Phase 1 + Phase 2 + US1** (ciclo completo iniciar/pausar/reanudar/terminar,
   generando Registros de tiempo reales) — valor visible inmediato.
2. Incremento 1: US2 (persistencia) — endurece lo ya construido, bajo riesgo, mayormente
   verificación + un efecto de re-fetch en el frontend.
3. Incremento 2: US3 (aislamiento por recurso) — ya viene garantizado por el diseño de T009
   (resource_id siempre del JWT); esta fase formaliza la prueba dirigida.
4. Riesgo concentrado en T008 (servicio de dominio, especialmente la reutilización correcta de
   `WorkSessionService.create()` sin duplicar ni romper sus validaciones existentes) — validar
   el Escenario 1 y 5 del quickstart sobre datos reales antes de dar la feature por cerrada.

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
- No se toca `backend/domain/services/work_session_service.py` ni ningún archivo de la spec
  `004` — el cronómetro solo lo **llama**, nunca lo modifica (research.md Decisión 4)
