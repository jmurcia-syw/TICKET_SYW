# Implementation Plan: Fase 2 — Registro diario de tiempos por recurso

**Branch**: `004-fase2-registro-tiempos` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-fase2-registro-tiempos/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Cada recurso interno (Resolutor, QM, Coordinador) registra manualmente cuánto tiempo dedicó, por
día, a cada ticket en el que participa. La entidad `WorkSession` — ya anticipada en la Capa 1 del
dominio junto a `Ticket`/`Comment`/`User` (Constitución, Principio II) — se implementa por primera
vez en esta fase como el registro atómico de tiempo. Se agrega un nuevo módulo end-to-end (entidad
de dominio → repositorio SQLAlchemy → endpoints Flask-RESTX → pantalla React) siguiendo
exactamente el mismo patrón de tres capas que `Ticket`, reutilizando el stack ya aprobado sin
nuevas dependencias. Incluye: alta/edición/borrado de registros con ventana de edición de 7 días,
validaciones (máx. 24h/día, sin fechas futuras, solo contra tickets propios), historial de
ediciones auditable (mismo patrón que `ticket_assignments`), y un reporte agregado por
recurso/fecha para Coordinador, QM y Admin.

## Technical Context

**Language/Version**: Python 3.12 (backend) + TypeScript 5 strict / React 19 (frontend) — fijado
por la Constitución (Principio V), sin cambios respecto a `002-fase1-tickets`.

**Primary Dependencies**: Flask + Flask-RESTX (contrato Swagger) + Flask-JWT-Extended,
SQLAlchemy + Alembic (persistencia/migraciones). Frontend: React 19 + Ant Design 5 + Zustand +
`date-fns` + Axios. **No se agrega ninguna dependencia nueva** — reutiliza el stack aprobado.

**Storage**: PostgreSQL 16 (on-premise, RLS habilitado), misma instancia que Fase 0/1. Nueva tabla
`work_sessions` + tabla de historial `work_session_edits` (append-only).

**Testing**: `pytest` para dominio/servicio/repositorio y tests de contrato de los nuevos
endpoints (mismo patrón que `002-fase1-tickets`). Sin framework de test de frontend (no aprobado
aún en el stack); validación de UI vía `quickstart.md` manual, igual que en fases anteriores.

**Target Platform**: Servidor Linux on-premise vía Docker Compose (mismo entorno que Fase 0/1).

**Project Type**: Web application (monorepo `backend/` + `frontend/` ya existente).

**Performance Goals**: Alta de un registro de tiempo en <30s percibidos por el usuario (SC-001);
reporte agregado por recurso/rango de fechas en <10s (SC-003). Sin requisitos de throughput
especiales — volumen esperado: decenas de recursos, cientos de registros/día.

**Constraints**: Cero dependencias nuevas (Principio V); FSM y motor SLA existentes no se tocan;
RLS obligatorio en la tabla nueva con datos sensibles (Principio IV); no hay integración con
facturación ni con el motor de SLA en esta fase (ver Assumptions del spec).

**Scale/Scope**: Mismo orden de magnitud que Fase 1 — equipo interno de SyWork, no clientes
externos. 3 historias de usuario (alta, edición/borrado, reporte).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Chequeo | Resultado |
|-----------|---------|-----------|
| I. API-First y Dominio Primero | ¿La lógica de negocio (validación de 24h, ventana de edición, pertenencia al ticket) vive en `backend/domain/`, sin imports de Flask/SQLAlchemy? ¿Existe contrato Swagger antes del código del endpoint? | **PASS** — se diseña `WorkSessionService` puro en dominio; contrato en `contracts/work-sessions-api.md` antes de implementar |
| II. Clean Architecture 3 capas | ¿Se respeta `domain/` → `infra/` → `api/`+`frontend/src/`? | **PASS** — mismo patrón que `Ticket`: `entities/work_session.py`, `infra/models/work_session_model.py` + `infra/repositories/work_session_repo.py`, `api/routes/work_sessions.py` |
| III. Tipado estricto | ¿Type hints en dominio/servicios Python? ¿TS strict sin `any` en frontend? | **PASS** — sin excepciones previstas |
| IV. Seguridad en profundidad | ¿RLS en la tabla nueva? ¿Autorización a nivel de datos para "un recurso solo ve lo suyo"? | **PASS** — `work_sessions`/`work_session_edits` con RLS (mismo patrón app-level que `tickets`); visibilidad por rol enforced en dominio+API (igual que tickets, ver `012_tickets_rls.py`) |
| V. Cero dependencias no aprobadas | ¿Se necesita alguna librería nueva? | **PASS** — ninguna; se reutiliza el stack existente |
| VI. AI-Native | ¿Los endpoints de acción quedan agnósticos al caller? ¿Se preserva historial estructurado? | **PASS** — `work_session_edits` es un historial estructurado (mismo espíritu que el Gold Standard Dataset de `ticket_assignments`), útil a futuro para calcular disponibilidad real (Fase 5) |

Sin violaciones — no aplica la tabla de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-fase2-registro-tiempos/
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
│   │   └── work_session.py          # entidad pura WorkSession (sin SQLAlchemy/Flask)
│   └── services/
│       └── work_session_service.py  # validaciones: 24h/día, sin fechas futuras,
│                                     # pertenencia al ticket, ventana de edición de 7 días
├── infra/
│   ├── models/
│   │   └── work_session_model.py    # WorkSessionModel + WorkSessionEditModel (SQLAlchemy)
│   ├── repositories/
│   │   └── work_session_repo.py     # persistencia + queries de reporte agregado
│   └── migrations/versions/
│       ├── 015_create_work_sessions.py
│       └── 016_work_sessions_rls.py
└── api/
    └── routes/
        └── work_sessions.py         # Namespace Flask-RESTX, path="/api/work-sessions"

frontend/src/
├── components/
│   └── worksessions/                # formulario de carga, listado del día, tabla de reporte
├── pages/
│   └── WorkSessionsPage.tsx / TimeReportPage.tsx
├── services/
│   └── workSessionService.ts        # llamadas Axios a /api/work-sessions
└── types/
    └── workSession.ts

# Nota de implementación: el proyecto no usa un store Zustand por dominio (solo `authStore`
# existe, para sesión/permisos) — todas las páginas de Fase 0/1 manejan su propio estado con
# useState/useEffect locales (ver TicketsPage.tsx). Fase 2 sigue esa misma convención en vez
# de introducir `store/workSessionStore.ts`.

tests/ (backend, pytest — mismo layout que 002-fase1-tickets)
├── contract/   # tests de los endpoints /api/work-sessions*
├── integration/# flujo completo: crear ticket → registrar tiempo → reporte
└── unit/       # WorkSessionService (reglas de negocio en aislamiento)
```

**Structure Decision**: Se reutiliza la estructura de tres capas ya establecida en
`002-fase1-tickets` (Opción "Web application" del template) — no se introduce ningún directorio
ni patrón nuevo. `WorkSession` se suma como quinta entidad de dominio junto a `Ticket`, `Comment`,
`User` (ya anticipada en la Constitución), siguiendo el mismo camino
`domain/entities` → `domain/services` → `infra/models` + `infra/repositories` → `api/routes` →
`frontend/src/services` → `frontend/src/pages` que el resto del sistema.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No aplica — el Constitution Check no registró violaciones.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
