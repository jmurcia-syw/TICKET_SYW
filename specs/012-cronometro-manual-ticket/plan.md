# Implementation Plan: Cronómetro Manual de Tiempo en el Ticket

**Branch**: `develp_Jp` (rama de desarrollo actual; el directorio de la spec es
`012-cronometro-manual-ticket`) | **Date**: 2026-07-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-cronometro-manual-ticket/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See
`.specify/templates/plan-template.md` for the execution workflow.

## Summary

Cronómetro manual y provisional por recurso, iniciable desde el detalle del ticket: un solo
control personal (Iniciar/Pausar/Reanudar/Terminar) por recurso a la vez, cuyo estado persiste
en el servidor (sobrevive a recargas y cierres de sesión) y que, al "Terminar", genera un
Registro de tiempo formal reutilizando el `WorkSessionService` ya existente (spec `004`) —
mismas reglas de negocio (ticket cerrado, participación del recurso, límite diario de 24h), sin
duplicarlas. Es visible y controlable únicamente por quien lo inició. No introduce dependencias
nuevas ni infraestructura de fondo (sin Celery/Redis/WebSockets): el tiempo transcurrido se
deriva de timestamps del servidor (`GET /api/timer`), y el frontend solo hace un tick visual
local entre lecturas.

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript strict / React 19 (frontend)

**Primary Dependencies**: Flask 3.x + Flask-RESTX, SQLAlchemy 2.x + Alembic, Ant Design 5,
Zustand 5, Axios — **sin dependencias nuevas** (Principio V); no se usa Celery/Redis ni
WebSockets para esta feature.

**Storage**: PostgreSQL 16 (Docker `sywork_db`), migración Alembic nueva `ticket_timers`
(`down_revision` = `025`, última actual).

**Testing**: pytest contra Postgres real en Docker (`docker exec sywork_backend pytest <tests
dirigidos>`), `npx tsc -b` para typecheck frontend. Tests dirigidos al cronómetro (no se exige
correr la suite completa, pero a diferencia de la spec `010` esta spec no impone esa restricción
explícitamente — se recomienda correr al menos los tests de `work_sessions` + `timer` juntos por
la dependencia funcional entre ambos).

**Target Platform**: Docker Compose on-premise (`sywork_db`/`sywork_backend`/`sywork_frontend`),
sin cambios de infraestructura.

**Project Type**: Web application (backend Flask 3 capas + frontend React SPA).

**Performance Goals**: cada acción del cronómetro (iniciar/pausar/reanudar/terminar) responde en
menos de 300ms; el refresco visual en pantalla es local (tick de 1s) sin llamadas de red
adicionales entre acciones.

**Constraints**: cero dependencias nuevas (Principio V); el cálculo del tiempo transcurrido debe
ser determinista a partir de timestamps del servidor, no del reloj del navegador; el `finish`
debe reutilizar `WorkSessionService.create()` en vez de reimplementar sus validaciones.

**Scale/Scope**: una fila en `ticket_timers` por recurso (decenas), sin impacto de escala.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|-----------|------------|--------|
| I — API-First y Dominio Primero | Entidad `TicketTimer` y `TicketTimerService` viven en `backend/domain/` sin imports de Flask/SQLAlchemy; contrato Swagger (`contracts/timer.md`) definido antes de implementar las rutas. | ✅ PASS |
| II — Clean Architecture 3 capas | Entidad en `domain/entities/`, modelo + repositorio en `infra/`, rutas Flask en `api/routes/timer.py`; componente React "tonto" que solo llama a `frontend/src/services/timerService.ts`. | ✅ PASS |
| III — Tipado estricto | `TicketTimer` con type hints en Python; interfaz `Timer`/`TimerState` en TypeScript strict, sin `any`. | ✅ PASS |
| IV — Seguridad en profundidad | Todas las rutas exigen JWT + `@require_permission("work_sessions","manage")`; RLS habilitado en `ticket_timers` restringido al propio `resource_id`, sin variante "ver todos" (más estricto que `work_sessions`, por FR-005). | ✅ PASS |
| V — Zero dependencias no aprobadas | No se agrega ninguna librería a `requirements.txt` ni `package.json`; no se usa Celery/Redis/WebSockets. | ✅ PASS |
| VI — AI-Native | No introduce riesgo: el cronómetro es informativo/operativo, no reemplaza ni contamina el Gold Standard Dataset ni los skills parametrizados. | ✅ PASS (N/A directo) |

Sin violaciones — no aplica la tabla de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/012-cronometro-manual-ticket/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── timer.md          # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   ├── entities/
│   │   └── ticket_timer.py         # nuevo — TicketTimer (dataclass, sin imports de framework)
│   └── services/
│       └── ticket_timer_service.py # nuevo — start/pause/resume/finish; finish delega en
│                                    # WorkSessionService.create() (spec 004), sin duplicar reglas
├── infra/
│   ├── models/
│   │   └── ticket_timer_model.py   # nuevo — SQLAlchemy, PK resource_id, to_entity()/from_entity()
│   ├── repositories/
│   │   └── ticket_timer_repo.py    # nuevo — get_by_resource(), upsert de estado
│   └── migrations/versions/
│       └── 026_ticket_timers.py    # nueva — tabla + CHECKs de consistencia + RLS
└── api/routes/
    └── timer.py                     # nuevo — namespace `timer`, path /api/timer
                                      # (registrar en backend/app.py junto a los demás)

frontend/src/
├── components/worksessions/
│   └── TicketTimerWidget.tsx        # nuevo — control Iniciar/Pausar/Reanudar/Terminar, tick
│                                    # visual local; se monta en TicketDetailPage junto a
│                                    # TicketWorkSessions (frontend/src/pages/TicketDetailPage.tsx)
├── services/
│   └── timerService.ts              # nuevo — getCurrent(), start(), pause(), resume(), finish()
└── types/
    └── timer.ts                     # nuevo — TimerState ('inactive'|'running'|'paused'), Timer
```

**Structure Decision**: se sigue la misma estructura de 3 capas ya usada por `work_sessions`
(spec `004`) y `project_members` (spec `010`): entidad + servicio de dominio puro, modelo +
repositorio de infraestructura, ruta Flask-RESTX registrada como namespace nuevo, y un
componente React "tonto" adicional junto a `TicketWorkSessions` en el detalle del ticket. No se
crean carpetas nuevas de primer nivel.

## Complexity Tracking

> No aplica — el Constitution Check no registró violaciones.
