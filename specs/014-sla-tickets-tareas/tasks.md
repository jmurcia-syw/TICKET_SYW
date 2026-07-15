# Tasks: SLAs por Proyecto y Prioridad

**Input**: Design documents from `/specs/014-sla-tickets-tareas/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/sla-contract.md, quickstart.md

**Tests**: Incluidos — el plan.md nombra explícitamente los archivos de test (`test_sla_rules.py`,
`test_sla_service.py`, `test_sla_notifications.py`) y la Constitución (Principio VII) exige tests
ultra-limitados (≤ 5-10 registros) del código nuevo, no la suite completa.

**Organization**: Tareas agrupadas por historia de usuario (spec.md) para permitir implementación
y prueba independiente de cada una.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar el worker Celery/Redis (aprobado en la Constitución pero sin código previo
en el repo) y el permiso administrativo nuevo.

- [X] T001 Agregar servicios `redis` y `worker` (Celery) a `docker-compose.yml`, reutilizando la
  imagen del backend para el worker (`command: celery -A backend.workers.sla_tasks worker`)
  (implementado con `celery -A backend.workers.celery_app worker --beat`, ver T002)
- [X] T002 [P] Crear `backend/workers/__init__.py` y configuración mínima de la app Celery
  (`backend/workers/celery_app.py`) apuntando al Redis del compose (incluye `beat_schedule` cada
  5 min para `check_sla_breaches`, T026)

**Checkpoint**: Worker Celery arrancable con `docker compose up -d worker redis` (sin tareas
todavía).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelo de datos y motor de dominio compartidos por las 3 historias de usuario.

**⚠️ CRITICAL**: Ninguna historia de usuario puede implementarse hasta completar esta fase.

- [X] T003 Migración `backend/infra/migrations/versions/028_sla_rules.py`: crear tabla
  `sla_rules` (columnas y constraint de unicidad `(project_id, priority)` de `data-model.md`) +
  columnas `sla_rule_id`, `sla_phase`, `sla_phase_limit_minutes`, `sla_consumed_seconds`,
  `sla_last_resume_at`, `sla_status`, `sla_contact_result`, `sla_contact_consumed_seconds` en
  `tickets` (default `sla_status='sin_sla'`, `sla_consumed_seconds=0`)
- [X] T004 [P] Agregar permiso `sla_rules:manage` al catálogo de permisos y asignarlo a los roles
  Admin y Coordinador en la misma migración T003 (seguir el patrón de
  `backend/infra/migrations/versions/017_work_sessions_permissions.py`)
- [X] T005 [P] Crear entidad de dominio `SlaRule` (dataclass pura, sin imports de SQLAlchemy) en
  `backend/domain/entities/sla_rule.py` — implementado con tuplas de solo-lectura
  (`SLA_STATUSES`, `SLA_PHASES`, `SLA_CONTACT_RESULTS`) en vez de `enum.Enum`, consistente con el
  patrón ya usado por `PRIORITIES`/`SEVERITIES` en `backend/domain/entities/ticket.py`
- [X] T006 [P] Agregar diccionarios `SLA_PHASE_FOR_STATE` y `STATE_COUNTS_FOR_SLA` (solo lectura,
  sin nuevas transiciones) a `backend/domain/fsm/ticket_fsm.py` según la tabla de `data-model.md`
  (2 fases: Contacto = `nuevo`/`pre_analisis`; Ejecución = `contacto`/`en_analisis`/
  `en_ejecucion`/`en_pruebas`). Agregado el comentario inline advirtiendo que el estado FSM
  `contacto` mapea a la fase de SLA `ejecucion` (F3 del `/speckit-analyze`)
- [X] T007 Crear `backend/infra/models/sla_rule_model.py` (modelo SQLAlchemy `SlaRuleModel`,
  `project_id` NOT NULL) y agregar las columnas `sla_*` al `TicketModel` existente en
  `backend/infra/models/ticket_model.py` (+ campos correspondientes en el dataclass `Ticket` de
  `backend/domain/entities/ticket.py`, necesarios para que `to_entity()` no rompa)
- [X] T008 Crear `backend/infra/repositories/sla_rule_repo.py` con CRUD básico
  (`create`, `get_by_id`, `list_paginated(project_id=None)`, `find_by_project_priority(project_id,
  priority)` — búsqueda exacta sin fallback, `research.md` Decisión 3, `update`, `exists_active`
  para la validación de duplicados de T010)

**Checkpoint**: Migración aplicable (`alembic upgrade head`), entidad y repositorio listos —
puede comenzar la implementación de las historias de usuario.

---

## Phase 3: User Story 1 - Configurar tiempos límite de SLA por Proyecto (Priority: P1) 🎯 MVP

**Goal**: Admin/Coordinador puede crear, editar y desactivar reglas de SLA por
Proyecto × Prioridad (sin reglas de respaldo — cada combinación es independiente).

**Independent Test**: `POST /api/sla-rules` + `GET /api/sla-rules` desde Postman/curl con un
token de Admin, sin que exista todavía ningún contador corriendo en un ticket.

### Tests for User Story 1

- [X] T009 [P] [US1] Test dirigido `backend/tests/api/test_sla_rules.py`: crear regla, listar
  (con filtro `project_id`), editar tiempos, rechazar duplicado (409), rechazar creación sin
  `project_id` (400), rechazar rol sin `sla_rules:manage` (403) — 8 tests, todos pasando contra
  Docker real (`docker exec sywork_backend pytest tests/api/test_sla_rules.py -v`)

### Implementation for User Story 1

- [X] T010 [US1] Endpoint `backend/api/routes/sla_rules.py`: `GET/POST /api/sla-rules`,
  `PATCH /api/sla-rules/{id}` según `contracts/sla-contract.md`, protegido con
  `require_permission("sla_rules", "manage")`, registrado el namespace en `backend/app.py`
- [X] T011 [P] [US1] Tipos TS `frontend/src/types/sla.ts` (`SlaRule`, payloads de request:
  `project_id`, `priority`, `contact_minutes`, `execution_minutes`; además `TicketSlaState` ya
  tipado para cuando lo consuma la Historia 2)
- [X] T012 [P] [US1] Servicio `frontend/src/services/slaService.ts` con `list/create/update` sobre
  `/api/sla-rules`
- [X] T013 [US1] Formulario `frontend/src/components/sla/SlaRuleForm.tsx` (selección de Proyecto
  obligatoria + Prioridad + 2 tiempos en horas y minutos: contacto y diagnóstico-análisis-
  ejecución), con tooltip junto al tiempo de ejecución aclarando la conversión de "días hábiles"
  a horas corridas (F2 del `/speckit-analyze`)
- [X] T014 [US1] Página `frontend/src/pages/SlaRulesPage.tsx` (listado filtrable por Proyecto +
  alta/edición/activar-desactivar, reutilizando `PageToolbar`/`StatusTag`), ruta
  `/sla-rules` protegida por `sla_rules:manage` en `frontend/src/App.tsx`, entrada de menú "SLA"
  bajo "Maestros" en `frontend/src/config/navigation.tsx`. Verificado en navegador real (Docker):
  login Admin → crear regla (Proyecto A Verif013 / Baja / 15 / 7200) → aparece en tabla → editar
  → Proyecto/Prioridad deshabilitados correctamente en modo edición.

**Checkpoint**: Historia 1 completamente funcional y probable de forma independiente.

---

## Phase 4: User Story 2 - Ver el contador de SLA en el ticket, 2 fases (Priority: P1)

**Goal**: El detalle del ticket muestra fase vigente/tiempo consumido/límite/estado real, con
pausa, reanudación y transición Contacto→Ejecución correctas según el estado del ticket.

**Independent Test**: Con una regla de SLA ya configurada (Historia 1), crear un ticket, moverlo
por transiciones de estado y verificar que el bloque `sla` del detalle refleja el cambio de fase,
la pausa y la reanudación sin abrir el listado ni el dashboard.

### Tests for User Story 2

- [X] T015 [P] [US2] Test dirigido `backend/tests/domain/test_sla_service.py`: resolución de
  regla exacta por `(project_id, priority)` (con regla, sin regla → `sin_sla`), transición
  Contacto→Ejecución (congela `contact_result`, reinicia `sla_consumed_seconds`), cómputo de
  consumo con pausa/reanudación, transición a estado final detiene el contador, reapertura desde
  `resuelto` (reject_resolution), recalcular regla al cambiar Proyecto o Prioridad conservando el
  consumo de la fase vigente (FR-011) — 15 tests, todos pasando, sin DB (dominio puro)
- [X] T016 [P] [US2] Test dirigido `backend/tests/api/test_tickets_sla.py`: crear ticket con regla
  aplicable, verificar bloque `sla` en `GET /api/tickets/{id}` (`phase=contacto`), ejecutar
  `assign_resolver` y verificar `phase=ejecucion` + `contact_result` congelado, mover a
  `pendiente_usuario` y verificar `status=pausado`, volver a `en_ejecucion` y verificar que el
  consumo no se reinició, cancelar detiene el SLA, Tareas no tienen SLA (FR-012) — 6 tests, todos
  pasando contra Docker real

### Implementation for User Story 2

- [X] T017 [US2] Motor de dominio `backend/domain/services/sla_service.py`: `resolve_rule`,
  `initial_state`, `compute_state`, `apply_transition`, `recalc_rule_for_project_or_priority_change`
  — puro, recibe `SLA_PHASE_FOR_STATE`/`STATE_COUNTS_FOR_SLA` (T006) y datos ya cargados, sin
  SQLAlchemy (depende de T005, T006, T008)
- [X] T018 [US2] Invocado `sla_service.apply_transition` desde los endpoints de transición ya
  existentes en `backend/api/routes/tickets.py` (`/assign`, `/comments` con trigger, `/testing`
  vía el helper compartido `_apply_transition`, `/resolution` rama de rechazo, `/close`,
  `/cancel`) y desde la creación (`POST /api/tickets`, `sla_service.initial_state` solo si
  `record_type == "Ticket"`, FR-012) — sin alterar la lógica FSM existente. Nuevo helper
  `_sla_updates_for_transition` centraliza el efecto lateral con try/except propio (FR-014).
  **Nota de alcance**: `/status` (PATCH) es exclusivo de Tareas/Subtareas (spec 009, rechaza
  Tickets con 409 `not_a_task`) — no se le agregó SLA porque nunca aplicaría (FR-012).
  **Bug encontrado y corregido**: `TicketRepository.create()` construía el `TicketModel` sin las
  columnas `sla_*`, así que el `sla_fields` inicial se habría descartado silenciosamente en la
  creación — se agregaron las 7 columnas a ese `INSERT`.
- [X] T019 [US2] Recalcular y congelar `sla_rule_id`/`sla_phase_limit_minutes` en el PATCH de
  edición de ticket (`backend/api/routes/tickets.py`) cuando cambia `priority`, conservando
  `sla_consumed_seconds` acumulado de la fase vigente. **Hallazgo de alcance**: `project_id` NO
  está en `PATCHABLE_FIELDS` de `ticket_service.py` — no existe ningún endpoint hoy para cambiar
  el Proyecto de un ticket ya creado, así que la mitad de FR-011 ("cambia de Proyecto") es
  actualmente inalcanzable; `recalc_rule_for_project_or_priority_change` soporta ambos parámetros
  para cuando esa capacidad exista, pero solo el cambio de Prioridad es ejercitable hoy.
- [X] T020 [US2] Extendido `_ticket_detail_out` y `_ticket_detail()` en
  `backend/api/routes/tickets.py` con el bloque `sla` (`phase`, `status`, `phase_limit_minutes`,
  `consumed_seconds`, `rule_id`, `contact_result`, `contact_consumed_seconds`) calculado en el
  momento de la lectura vía `sla_service.compute_state` (cálculo perezoso, sin persistir)
- [X] T021 [P] [US2] Componente `frontend/src/components/tickets/SlaCounter.tsx` (reemplaza el
  placeholder `—:—:—` / "Próximamente · Fase 4"): muestra fase vigente, tiempo consumido/restante,
  estado (corriendo/pausado/vencido/sin SLA) con estilo visual distinto para vencido, y el
  resultado congelado de la fase Contacto una vez superada
- [X] T022 [US2] Integrado `<SlaCounter>` en `frontend/src/pages/TicketDetailPage.tsx`
  (reemplazó el placeholder existente) y agregado el campo `sla: TicketSlaState` en
  `frontend/src/types/ticket.ts`. Verificado en navegador real (Docker) con un ticket creado vía
  API: detalle muestra "0m / 15m · Corriendo · Fase: Contacto"; tras `POST /assign`
  (mode=resolver) pasa a "0m / 8h 00m · Corriendo · Fase: Diagnóstico, Análisis y Ejecución ·
  Contacto: Cumplido (10m)" — coincide exactamente con el bloque `sla` devuelto por la API.

**Checkpoint**: Historias 1 y 2 funcionan de forma independiente y en conjunto.

---

## Phase 5: User Story 3 - Alertas e indicadores en listados y dashboard (Priority: P2)

**Goal**: El listado de Tickets y el dashboard reflejan el estado agregado de SLA, y se generan
notificaciones internas al vencer.

**Independent Test**: Con varios tickets en distintos niveles de consumo de SLA (Historia 2 ya
funcionando), verificar que el listado los distingue visualmente, que "Vencen hoy" cuenta
correctamente, y que al forzar la tarea Celery se genera la notificación esperada.

### Tests for User Story 3

- [X] T023 [P] [US3] Test dirigido `backend/tests/api/test_tickets_sla_filters.py`: filtros
  `sla_status` y `sla_expiring_within_hours` en `GET /api/tickets`, y bloque `sla` resumido en el
  listado — 5 tests, todos pasando contra Docker real
- [X] T024 [P] [US3] Test dirigido `backend/tests/domain/test_sla_notifications.py`: predicado
  puro `sla_service.is_breach` (sin DB) — vencido y aún no marcado, dentro del límite, ya marcado
  vencido (no re-notifica), pausado, sin SLA — 5 tests, todos pasando

### Implementation for User Story 3

- [X] T025 [US3] Agregados filtros `sla_status` y `sla_expiring_within_hours` a
  `TicketRepository.list_paginated` (`backend/infra/repositories/ticket_repo.py`, con cálculo de
  tiempo restante en tiempo real vía SQL `func.extract('epoch', ...)`) y a la ruta
  `GET /api/tickets` en `backend/api/routes/tickets.py`, con el bloque `sla` resumido
  (`phase`/`status`, vía `sla_service.compute_state`) en cada item del listado
- [X] T026 [US3] Tarea periódica `backend/workers/sla_tasks.py::check_sla_breaches` (beat cada
  5 min, ver `celery_app.py`): usa el nuevo predicado puro `sla_service.is_breach` sobre
  `TicketRepository.list_active_sla_running()`, marca `sla_status='vencido'` y notifica al
  Resolutor/encargado asignado y a los `ProjectMember` con rol Coordinador del proyecto
  (`ProjectMemberRepository.list_by_project(project_id, role_name="Coordinador")`). Nuevo
  event_type `sla_breached` en `notification_service.py`. Verificado manualmente contra Docker
  real (backdateando `sla_last_resume_at` y llamando `check_sla_breaches.run()` directo): marcó
  el ticket vencido y creó la notificación correcta para el Coordinador del proyecto.
- [X] T027 [P] [US3] Indicador de SLA por fila en `frontend/src/pages/TicketsPage.tsx` — nuevo
  componente `frontend/src/components/tickets/SlaStatusTag.tsx` (mismo patrón que
  `TicketStatusTag.tsx`), columna filtrable server-side (`serverColumnFilter`). Verificado en
  navegador real: la columna "SLA" muestra "Vencido" en el ticket de prueba y "Sin SLA" en el
  resto.
- [X] T028 [US3] Reemplazado el `StatCard` "Vencen hoy" por
  `ticketService.list({sla_expiring_within_hours: 24, page_size: 1}).then(r => r.total)` agregada
  al `Promise.all` existente en `loadStats`. Verificado en navegador real: muestra el conteo real
  (16 en los datos de prueba acumulados), ya no el placeholder "—".

**Checkpoint**: Las 3 historias funcionan de manera independiente y en conjunto.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T029 [P] Actualizado `README.md`: banner de fase activa, fila de la Fase 4 en el roadmap
  (✅ Completa), sección "Estado actual" con el resumen funcional de SLAs, filas de las specs
  `013` y `014` en la tabla de especificaciones y "Pendientes conocidos" actualizado (limitación
  real de FR-011 documentada, ya no listaba Fase 4 como pendiente)
- [X] T030 Ejecutado `quickstart.md` (Validaciones 1-3) contra Docker real con usuarios semilla
  (`docs/credenciales_dev.txt`, sin ejercitar flujos fuera de alcance como reseteo de
  contraseña):
  - Tests dirigidos (Principio VII): `test_sla_service.py` + `test_sla_rules.py` → 23 passed
  - V1 (reglas): login Admin → crear regla Proyecto+Prioridad → listado filtrado por
    `project_id` → duplicado rechazado con 409 `DUPLICATE_RULE` — OK
  - V2 (contador): ticket creado en esa Proyecto/Prioridad nace con `phase=contacto`,
    `status=corriendo`, límite de 15 min; `POST /assign` (mode=resolver) pasa a
    `phase=ejecucion`, congela `contact_result=cumplido` y reinicia `consumed_seconds=0` con el
    límite de ejecución — OK (pausa/reanudación ya cubierta por `test_tickets_sla.py`)
  - V3 (agregados): filtros `sla_status`/`sla_expiring_within_hours` en `GET /api/tickets` — OK
  - V3.3 (Celery real): **bug encontrado y corregido** — al disparar
    `celery -A backend.workers.celery_app call ...check_sla_breaches` a través del worker real
    (no llamando la función Python directamente como en la verificación de la Historia 3),
    fallaba con `NoReferencedTableError` en `tickets.process_id → catalog_processes`. Causa
    raíz: `backend/infra/models/__init__.py` solo registraba 6 de los 15 módulos de modelos; la
    app Flask arma el registro completo por la cascada de imports de sus namespaces (`app.py`),
    pero el proceso worker de Celery solo importa `backend.workers.sla_tasks` y nunca disparaba
    esa cascada, dejando el mapper de SQLAlchemy incompleto. Corregido agregando los 9 módulos
    de modelo faltantes a `backend/infra/models/__init__.py` e importando ese paquete completo
    en `backend/workers/celery_app.py`. Reconstruido y reiniciado `sywork_worker`: la tarea real
    corrió, marcó 14 tickets `vencido` (datos reales acumulados en la sesión) y no re-notificó
    en una segunda corrida (idempotente). Suite completa re-corrida tras el cambio (archivo
    compartido): 437 passed, sin regresiones.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede iniciar de inmediato
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA las 3 historias
- **US1 (Phase 3)**: depende solo de Foundational
- **US2 (Phase 4)**: depende de Foundational; funcionalmente necesita que existan reglas (US1)
  para mostrar datos reales, pero el código de US2 no depende de los archivos de US1 (puede
  implementarse en paralelo usando datos de prueba insertados directamente)
- **US3 (Phase 5)**: depende de Foundational y de que el bloque `sla` de US2 exista en el detalle
  del ticket (T020) para poder replicarlo en el listado (T025)
- **Polish (Phase 6)**: depende de que las historias que se vayan a entregar estén completas

### Parallel Opportunities

- T001/T002 (Setup) en paralelo
- T004, T005, T006 (Foundational) en paralelo tras T003
- T009, T011, T012 (US1) en paralelo
- T015, T016 (US2, tests) en paralelo; T021 en paralelo con T017-T020 (archivo distinto)
- T023, T024 (US3, tests) en paralelo; T027 en paralelo con T025-T026

---

## Parallel Example: User Story 2

```bash
Task: "Test dirigido backend/tests/domain/test_sla_service.py"
Task: "Componente frontend/src/components/tickets/SlaCounter.tsx"
```

---

## Implementation Strategy

1. **MVP = US1** (Setup + Foundational + Phase 3): permite configurar reglas de SLA de punta a
   punta, aunque todavía no se vea ningún contador en el ticket.
2. **Incremento 2 = US2**: el valor perceptible por Resolutor/Coordinador aparece — el placeholder
   `—:—:—` se reemplaza por datos reales con pausa/reanudación correcta.
3. **Incremento 3 = US3**: vista agregada (listado + dashboard) y notificaciones proactivas vía
   Celery — cierra el alcance de la Fase 4 del roadmap.

**Restricciones transversales (Constitución v1.2.0, Principio VII)**: no refactorizar la FSM ni
los endpoints de transición más allá del efecto lateral de SLA descrito en T018; no ejecutar la
suite de tests masivamente (solo los archivos listados en cada historia); tests con ≤ 5-10 mocks/
registros; sin trabajo fuera del alcance de esta feature.
