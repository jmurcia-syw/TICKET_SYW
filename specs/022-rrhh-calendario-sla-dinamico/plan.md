# Implementation Plan: RRHH — Franjas Horarias, Calendario Superpuesto y Motor de SLA Dinámico

**Branch**: `022-rrhh-calendario-sla-dinamico` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/022-rrhh-calendario-sla-dinamico/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Extiende la Fase 5 (specs `020`/`021`, ya completas) con: (1) Franjas Horarias globales por país
que el equipo hereda, con modo "Personalizado" cuando un recurso edita su propio horario; (2) un
calendario de equipo con vistas Mes/Semana/Día y superposición de varios miembros, más ausencias
parciales por horas; (3) un motor de SLA que solo consume tiempo dentro de la disponibilidad real
del técnico (horario + festivos + ausencias), pausando/reanudando automáticamente; (4) una vista
diaria que prioriza tickets por Prioridad/Severidad. El enfoque técnico reutiliza al máximo lo ya
construido en spec 020/021 (`availability_service`, `sla_service`, `absence_service`, el patrón de
cálculo perezoso sin persistir estado derivado) para minimizar superficie de cambio, sin añadir
dependencias nuevas (Principio V) — el calendario superpuesto se resuelve con los plugins de
FullCalendar **ya instalados** (`daygrid`, `timegrid`), no con el paquete de recursos/swimlanes.

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript 5 strict (frontend) — sin cambios, reusa
el stack ya aprobado.

**Primary Dependencies**: Flask-RESTX, SQLAlchemy + Alembic, `python-transitions` (FSM, no se
toca), Celery + Redis (se reutiliza el worker de `sla_tasks.py`, ya existente desde spec 014),
React 19 + Ant Design 5 + Zustand + `date-fns` + `@fullcalendar/react` con los plugins
`@fullcalendar/daygrid` y `@fullcalendar/timegrid` (ambos **ya instalados** en
`frontend/package.json` desde spec 020 — `timegrid` no se usa aún en `CalendarPage.tsx`, pero no
requiere instalación nueva). **Cero dependencias nuevas** (Principio V).

**Storage**: PostgreSQL 16 — nuevas tablas `work_hour_templates` /
`work_hour_template_slots` (Franja Horaria global) y columnas nuevas en `resources`
(`schedule_mode`, `work_hour_template_id`) y en `absence_requests` (`start_time`, `end_time`
nullable). No se toca el esquema de `tickets` (solo lectura de `priority`/`severity`/asignación).

**Testing**: pytest, acotado por directriz explícita del usuario y Principio VII de la
constitución — solo el/los test(s) del cálculo de disponibilidad-SLA nuevo, con 5-10 registros
dummy, sin correr la suite global. Frontend: `tsc -b` (typecheck estricto), sin suite nueva de
componentes.

**Target Platform**: Docker Compose on-premise ya existente (`sywork_backend`, `sywork_frontend`,
`sywork_worker`, `sywork_redis`, `sywork_db`) — sin contenedores nuevos.

**Project Type**: Web app (monorepo `backend/` Flask + `frontend/` React), estructura ya
establecida.

**Performance Goals**: el cómputo de disponibilidad y SLA dinámico se resuelve en el mismo patrón
de "cálculo perezoso" ya usado por `sla_service`/`availability_service` (sin persistir estado
derivado, recalculado en cada lectura) — mismo orden de magnitud de latencia que el SLA actual
(spec 014: listado 52 ms, panel 64 ms con 500+ tickets).

**Constraints**: Alcance de código limitado estrictamente a tablas de usuario/perfil (`resources`,
horario/Franja), lógica de cálculo de SLA (`sla_service`, `availability_service`), y vistas de
calendario/RRHH (`CalendarPage.tsx`, navegación); **no se modifican** controladores/rutas de
Ticket fuera de la lectura de prioridad/severidad/asignación (Principio VII + directriz explícita
del usuario). El SLA dinámico aplica **hacia adelante únicamente** — ver Assumptions de spec.md.

**Scale/Scope**: mismo orden de equipo/tickets que las fases anteriores (decenas de recursos,
cientos de tickets activos); el overlay de calendario cubre selección de equipo típica (no
miles de recursos simultáneos).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación |
|-----------|------------|
| I. API-First y Dominio Primero | PASS — la lógica de Franja Horaria, disponibilidad y SLA dinámico vive en `backend/domain/` (funciones puras, sin Flask/SQLAlchemy); los contratos Swagger de los endpoints nuevos se definen en Fase 1 (`contracts/`) antes de codificar. No se toca `POST /api/tickets/{id}/assign`. |
| II. Clean Architecture 3 capas | PASS — nuevas entidades (`WorkHourTemplate`, `WorkHourTemplateSlot`) y extensiones (`Resource.schedule_mode`, `AbsenceRequest.start_time/end_time`) en Capa 1; modelos SQLAlchemy en Capa 2; rutas Flask solo orquestan en Capa 3 (`backend/api/routes/calendar.py`, ya existente, se extiende). |
| III. Tipado estricto | PASS — type hints en las nuevas funciones de dominio; tipos TS nuevos en `frontend/src/types/calendar.ts` (ya existente); prohibido `any`. |
| IV. Seguridad en profundidad | PASS — nuevos endpoints de Franja Horaria protegidos con `@require_permission` (permiso nuevo, ver data-model.md); RLS ya habilitado en `absence_requests` (migración 038) se mantiene; `work_hour_templates` no contiene datos sensibles por recurso (es una plantilla por país), no requiere RLS propio. |
| V. Gobernanza de librerías | PASS — cero dependencias nuevas. Decisión documentada en research.md: el overlay de calendario se resuelve fusionando eventos de varios recursos en una sola instancia de FullCalendar (plugins ya instalados), rechazando `@fullcalendar/resource-timegrid` (requeriría licencia Premium/Scheduler, fuera de alcance sin aprobación explícita de costo). |
| VI. AI-Native | PASS (no aplica cambio) — no se altera el Gold Standard Dataset ni los endpoints de asignación; la disponibilidad calculada queda expuesta como dato de solo lectura, consumible a futuro por el AI Dispatcher sin cambios adicionales. |
| VII. Alcance de sesión y testing ultra-limitado | PASS — ver Constraints arriba; tests nuevos limitados al cálculo de SLA dinámico con 5-10 registros dummy; no se ejecuta la suite global. |

Sin violaciones — no se requiere tabla de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/022-rrhh-calendario-sla-dinamico/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   ├── entities/
│   │   └── calendar.py            # + WorkHourTemplate, WorkHourTemplateSlot; AbsenceRequest
│   │                               #   gana start_time/end_time opcionales
│   └── services/
│       ├── availability_service.py  # active_absence reconoce ausencias parciales por horas;
│       │                            # sin cambios en la firma de compute_availability — la
│       │                            # resolución heredado/personalizado ocurre en la ruta
│       │                            # (Capa 3), no aquí (Principio I: dominio sin DB)
│       ├── absence_service.py       # + validación de rango horario parcial + solape por horas
│       ├── sla_service.py           # + compute_available_seconds; compute_consumed_seconds/
│       │                            # compute_state ganan parámetros opcionales de contexto de
│       │                            # calendario (research.md Decisión 10)
│       └── work_hour_template_service.py  # NUEVO — solo VALIDACIÓN de dominio (timezone IANA,
│                                           # end_time > start_time por slot); nunca toca DB,
│                                           # mismo patrón que absence_service.py (Decisión 12)
├── infra/
│   ├── models/calendar_model.py    # + WorkHourTemplateModel, WorkHourTemplateSlotModel;
│   │                               #   ResourceModel + schedule_mode/work_hour_template_id;
│   │                               #   AbsenceRequestModel + start_time/end_time
│   ├── repositories/
│   │   ├── calendar_repo.py        # + WorkHourTemplateRepository (nuevo, CRUD + slots);
│   │   │                           #   AbsenceRequestRepository.list_approved_between (nuevo,
│   │   │                           #   ranged — research.md Decisión 11)
│   │   └── resource_repo.py        # + ResourceRepository.list_by_schedule_mode (nuevo)
│   └── migrations/versions/        # 041..044 (ver data-model.md)
└── api/routes/
    ├── calendar.py                  # + endpoints de Franja Horaria, ausencias parciales
    │                                 #   (mismo archivo ya existente de spec 020/021)
    ├── resources.py                 # + endpoint GET /api/resources/{id}/workload
    └── tickets.py                   # cambio de solo lectura: resuelve resource/holidays/
                                      #   schedule_slots/absences y los pasa a sla_service antes
                                      #   de serializar el bloque `sla` (research.md Decisión 10)

frontend/src/
├── config/navigation.tsx           # + RRHH_GROUP_KEY / rrhhNavItems (mismo patrón que
│                                   #   MAESTROS_GROUP_KEY), agrupa /calendar y /absence-requests
├── pages/
│   ├── DashboardPage.tsx           # + submenú "RRHH" (idéntico patrón visual a "Maestros")
│   ├── CalendarPage.tsx            # + vistas Semana/Día (timegrid), overlay real (eventos
│   │                               #   fusionados de varios recursos), workload, agenda diaria
│   │                               #   priorizada
│   ├── MyProfilePage.tsx           # + edición de horario propio → dispara "Personalizado"
│   └── WorkHourTemplatesPage.tsx   # NUEVO — RRHH administra Franjas Horarias + ve Personalizados
├── services/calendarService.ts     # + llamadas a los endpoints nuevos
└── types/calendar.ts               # + tipos WorkHourTemplate, workload, ausencia parcial
```

**Structure Decision**: Se extienden los archivos ya existentes de la Fase 5
(`calendar.py`/`calendar_model.py`/`calendar_repo.py`/`resource_repo.py`/`calendar.py`
routes/`CalendarPage.tsx`/`calendarService.ts`) en vez de crear un módulo paralelo, siguiendo el
patrón ya usado por spec 021 sobre spec 020. Solo dos **archivos** nuevos:
`work_hour_template_service.py` (Capa 1, solo validación) y `WorkHourTemplatesPage.tsx` (Capa 3)
— la persistencia de la Franja Horaria vive en una clase nueva (`WorkHourTemplateRepository`)
dentro del `calendar_repo.py` ya existente, no en un archivo aparte (research.md Decisión 12). No
se toca ningún controlador de Ticket **excepto** una lectura de solo lectura en
`tickets.py` para resolver el contexto de disponibilidad que necesita el SLA dinámico (research.md
Decisión 10) — no se altera el FSM ni ninguna transición.

## Complexity Tracking

*Sin violaciones de la Constitution Check — tabla no requerida.*
