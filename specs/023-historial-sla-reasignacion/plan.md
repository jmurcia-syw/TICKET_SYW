# Implementation Plan: Historial de Estados con SLA Visual y Reasignación de Resolutores

**Branch**: `023-historial-sla-reasignacion` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/023-historial-sla-reasignacion/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Enriquecer `GET /api/tickets/{id}` (bloque `transitions`) con tiempo transcurrido y cumplimiento
de SLA por transición para pintar ✅/⚠️/❌ en "Historial de estados" del detalle del ticket
(`TicketDetailPage.tsx`), y agregar una acción explícita de reasignación de resolutor
(`POST /api/tickets/{id}/reassign`, nuevo endpoint independiente de `/assign` por gobernanza de
la constitución) que cambia solo el `assignee_id` sin tocar el FSM, dejando un registro de
actividad "Resolutor anterior ➡️ nuevo resolutor" visible junto a las transiciones.

## Technical Context

**Language/Version**: Python 3.12 (backend) + TypeScript strict / React 19 (frontend), ya en uso.

**Primary Dependencies**: Flask-RESTX, SQLAlchemy (repos existentes `ticket_repo.py`,
`ticket_model.py`), `sla_service.py` (dominio, Capa 1); frontend Ant Design 5 (`Card`, `Table`/`List`,
`Modal`, `Select`) — sin dependencias nuevas (Principio V).

**Storage**: PostgreSQL — tabla `ticket_status_transitions` (existente, sin cambios de esquema:
el tiempo/SLA se derivan en lectura) + nueva tabla append-only `ticket_reassignments`
(análoga a `ticket_assignments`, migración Alembic).

**Testing**: `pytest` (backend, test puntual del cálculo de cumplimiento SLA por transición y del
endpoint `/reassign`, máx. 5-10 registros por test — Principio VII); sin pruebas frontend nuevas
(cambio visual + wiring de acción existente, se valida manualmente).

**Target Platform**: Web app (Docker Compose on-premise), sin cambios de plataforma.

**Project Type**: web-service (backend Flask) + frontend React — estructura ya existente.

**Performance Goals**: Sin requisitos nuevos; el cálculo de tiempo/SLA por transición se hace en
la misma respuesta ya paginada de detalle de ticket (N transiciones por ticket, típicamente < 15).

**Constraints**: NO modificar el endpoint `/assign` existente (gobernanza constitucional: los
endpoints de acción crítica `/assign`/`/status` no se refactorizan sin aprobación de arquitectura).
NO tocar la entidad `Ticket` ni el FSM (`ticket_fsm.py`) — la reasignación es un cambio de
`assignee_id` puro, fuera del ciclo de vida de estados.

**Scale/Scope**: Cambio acotado a: 1 endpoint nuevo (`/reassign`), 1 tabla nueva, enriquecimiento
de `list_transitions`/`_ticket_detail`, 1 componente/acción en `TicketDetailPage.tsx` y el bloque
"Historial de estados". Sin refactor global de Ticket (spec, directriz de alcance).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. API-First**: ✅ Nuevo endpoint `POST /api/tickets/{id}/reassign` documentado en Swagger
  antes de implementar, independiente de la UI (igual criterio que `/assign`).
- **II. Clean Architecture**: ✅ Cálculo de tiempo/SLA por transición vive en `sla_service.py`
  (Capa 1, puro); la reasignación usa un método nuevo de dominio/servicio + repo (Capa 2) sin
  lógica de negocio en la ruta Flask (Capa 3) ni en componentes React.
- **III. Tipado estricto**: ✅ `TicketTransition`/`TicketReassignment` tipados en TS; type hints en
  las funciones nuevas de `sla_service.py`/`ticket_repo.py`.
- **IV. Seguridad en profundidad**: ✅ El nuevo endpoint reusa `require_permission("tickets",
  "assign")` (mismo permiso que `/assign`, sin permiso nuevo) + RLS ya vigente sobre `tickets`.
- **V. Gobernanza de librerías**: ✅ Cero dependencias nuevas.
- **VI. AI-Native**: ✅ La reasignación queda como endpoint de acción agnóstico al caller (humano
  o futuro AI Dispatcher), igual criterio que `/assign`.
- **VII. Alcance y tokens**: ✅ Cambios acotados a los archivos de esta feature; tests nuevos con
  ≤10 registros; sin ejecutar la suite completa.
- **Gate de gobernanza explícito**: NO se modifica `/assign` (endpoint de acción crítica) — se
  crea `/reassign` como endpoint nuevo e independiente, evitando el refactor prohibido sin
  aprobación de arquitectura.

Sin violaciones. No aplica tabla de Complexity Tracking.

**Re-chequeo post-diseño (Fase 1)**: `data-model.md`/`contracts/reassign.md` confirman que no se
tocó el esquema de `tickets` ni el FSM, no se agregó ningún permiso ni dependencia nueva, y
`ticket_reassignments` es una tabla append-only aislada del Gold Standard Dataset de
`ticket_assignments`. Gates siguen en verde, sin cambios respecto al chequeo inicial.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
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
│   └── services/
│       └── sla_service.py            # + compute_transition_compliance(...) (nueva función pura)
├── infra/
│   ├── models/
│   │   └── ticket_model.py           # + ReassignmentModel (nueva tabla ticket_reassignments)
│   ├── migrations/versions/
│   │   └── 0XX_ticket_reassignments.py   # nueva migración Alembic
│   └── repositories/
│       └── ticket_repo.py            # + add_reassignment / list_reassignments,
│                                      #   list_transitions enriquecido con elapsed/sla_met
├── api/routes/
│   └── tickets.py                    # + POST /<id>/reassign, _ticket_detail enriquecido
└── tests/
    ├── domain/test_sla_service.py    # + test puntual de compute_transition_compliance
    └── api/test_reassign.py          # + test puntual del endpoint /reassign (≤10 registros)

frontend/src/
├── types/ticket.ts                   # + elapsed_seconds/sla_met en TicketTransition,
│                                      #   + TicketReassignment
├── services/                         # + reassignTicket(...) (llamada API)
├── components/
│   └── (nuevo) ReassignModal.tsx     # modal "tonto": selección de nuevo resolutor
└── pages/
    └── TicketDetailPage.tsx          # Card "Historial de estados" (línea ~260) + botón
                                       # "Reasignar" junto a la ficha de asignación actual
```

**Structure Decision**: Web application (backend Flask + frontend React) ya establecida en el
repo. Esta feature NO agrega proyectos ni capas nuevas: solo extiende los tres archivos backend
de la Capa 1/2/3 ya responsables del ciclo de vida del ticket, y agrega un componente de UI
"tonto" + un service de API en el frontend, siguiendo la convención de directorios vigente.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
