# Implementation Plan: Skills Requeridas en el Ticket

**Branch**: `011-ticket-skills-requeridas` | **Date**: 2026-07-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-ticket-skills-requeridas/spec.md`

## Summary

Permitir asociar, de forma opcional y editable en cualquier estado del Ticket/Tarea/Subtarea, una
o varias Skills del catálogo ya existente (spec `010`) como "Skills requeridas para resolverlo".
Se modela como una relación N:M (`ticket_skills`) idéntica en forma a `resource_skills` ya
existente, expuesta por un endpoint dedicado de reemplazo total
(`PATCH /api/tickets/{id}/skills`) que no pasa por el bloqueo de campos por estado
(`locked_fields_for`) del PATCH genérico de ticket, y visible en el detalle del ticket ya
existente (`GET /api/tickets/{id}`).

## Technical Context

**Language/Version**: Python 3.12 (backend) + TypeScript strict (frontend) — sin cambios.

**Primary Dependencies**: Flask-RESTX, SQLAlchemy 2.x + Alembic, React 19 + Ant Design 5 — todas
ya aprobadas; **sin dependencias nuevas**.

**Storage**: PostgreSQL 16 — nueva tabla puente `ticket_skills` (migración `027`).

**Testing**: pytest (API dirigida contra Postgres real en Docker) + `tsc -b` (frontend estricto).

**Target Platform**: Web (Docker Compose: `sywork_db` + `sywork_backend` + `sywork_frontend`).

**Project Type**: Web application (backend + frontend).

**Performance Goals**: sin metas nuevas — operación de escritura simple sobre tabla puente
pequeña; cumple SC-001 (<15s) por diseño.

**Constraints**: el endpoint de Skills requeridas NO debe pasar por
`TicketService.validate_patch()` / `locked_fields_for(status)` — debe funcionar en cualquier
estado, incluidos Cerrado y Cancelado (FR-002).

**Scale/Scope**: reutiliza el catálogo de Skills existente (~10-20 activos); aplica por igual a
Ticket, Tarea y Subtarea porque comparten la misma tabla `tickets` (spec `008`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Resultado |
|-----------|-----------|-----------|
| I. API-First y Dominio Primero | Contrato (`contracts/ticket-skills.md`) definido antes de tocar código; endpoint `PATCH /api/tickets/{id}/skills` independiente, agnóstico al caller. | ✅ PASS |
| II. Clean Architecture (3 capas) | Sin lógica de negocio nueva más allá de "set sin duplicados desde catálogo existente" (garantizado por PK compuesta + FK) — se resuelve en Capa 2 (`TicketRepository.update_skills`), mismo criterio ya aceptado para `ResourceRepository.update_skills`. No se fuerza un servicio de dominio vacío. | ✅ PASS |
| III. Tipado Estricto | Tipos TS (`Skill`, extensión de `Ticket`) + type hints Python en el nuevo método de repositorio. | ✅ PASS |
| IV. Seguridad en Profundidad | Reutiliza JWT + permiso `tickets:edit` ya existente; sin RLS propio en `ticket_skills` (mismo criterio que `resource_skills`, hereda control de acceso de la API). | ✅ PASS |
| V. Gobernanza de Librerías | Cero dependencias nuevas. | ✅ PASS |
| VI. AI-Native | Las Skills requeridas quedan disponibles como dato base para el futuro Triage Agent (Fase 7), igual que las Skills de Resolutor ya alimentan el Gold Standard Dataset. | ✅ PASS |

**Resultado**: 6/6 PASS. Sin violaciones — Complexity Tracking no aplica.

## Project Structure

### Documentation (this feature)

```text
specs/011-ticket-skills-requeridas/
├── plan.md                       # Este archivo
├── research.md                   # Fase 0
├── data-model.md                 # Fase 1
├── quickstart.md                 # Fase 1
├── contracts/
│   └── ticket-skills.md          # Fase 1
├── checklists/requirements.md    # /speckit-specify
└── tasks.md                      # Fase 2 (/speckit-tasks, no creado aún)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   └── entities/
│       └── ticket.py                 # + campo skills: list[Skill]
├── infra/
│   ├── models/
│   │   └── ticket_model.py           # + ticket_skills_table, relationship skills
│   ├── repositories/
│   │   └── ticket_repo.py            # + update_skills(ticket_id, skill_ids)
│   └── migrations/versions/
│       └── 027_ticket_skills.py      # nueva
├── api/routes/
│   └── tickets.py                    # + TicketSkills (PATCH /skills), + "skills" en _ticket_detail
└── tests/api/
    └── test_ticket_skills.py         # nuevo

frontend/src/
├── types/
│   └── ticket.ts                     # + skills?: SkillRef[] en el tipo Ticket
├── services/
│   └── ticketService.ts              # + updateTicketSkills(ticketId, skillIds)
├── components/tickets/
│   └── TicketSkillsSelector.tsx      # nuevo — multi-select sobre catálogo de Skills
└── pages/
    └── TicketDetailPage.tsx          # monta TicketSkillsSelector en la clasificación del ticket
```

**Structure Decision**: Web application (backend Flask + frontend React) ya establecida por el
proyecto. No se agrega ningún proyecto ni capa nueva — la feature es una extensión acotada de
`Ticket`/`TicketModel`/`TicketRepository` (Capas 1-2) y un endpoint + componente nuevos
(Capa 3), reutilizando el catálogo de Skills y el patrón `resource_skills` ya existentes.

## Complexity Tracking

*No aplica — Constitution Check sin violaciones (6/6 PASS).*
