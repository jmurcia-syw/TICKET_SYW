# Implementation Plan: Usuario/cliente por Proyecto, Asignación de Personal y Estructura de Skills

**Branch**: `develp_Jp` (rama de desarrollo actual; el directorio de la spec es `010-proyecto-personal-skills`) | **Date**: 2026-07-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-proyecto-personal-skills/spec.md`

## Summary

Tres cambios acotados sobre maestros y tickets: (1) renombrar el rol "Encargado" a
"Usuario/cliente" en la BD (fila de `roles`) y en todas las etiquetas de UI, sin tocar el
comportamiento; (2) crear la relación **Personal del Proyecto** (`project_members`) válida para
cualquier usuario, con subgrupos visuales **"Equipo"** (`project_teams` +
`project_team_members`), y mover la fuente del selector de solicitante del ticket del filtro
por Cliente al personal del Proyecto (el campo `tickets.client_contact_id` **se conserva** —
decisión de clarificación 2026-07-09); (3) ampliar `skills` con `tool_id` (opcional, FK
`catalog_tools`), `process_id` (opcional, FK `catalog_processes`) y `skill_type` (obligatorio,
`funcional|tecnico`), con backfill y semillas de 10 skills de referencia.

**Directriz estricta del solicitante**: tocar solo migraciones, modelos/entidades, servicios y
componentes UI directamente afectados; sin refactors colaterales; validación con tests
dirigidos, nunca la suite completa durante el desarrollo.

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript strict / React 19 (frontend)

**Primary Dependencies**: Flask 3.x + Flask-RESTX, SQLAlchemy 2.x + Alembic, Ant Design 5,
Zustand 5, Axios — **sin dependencias nuevas** (Principio V)

**Storage**: PostgreSQL 16 (Docker `sywork_db`), migraciones Alembic `025`+ (última actual: `024`)

**Testing**: pytest contra Postgres real en Docker (`docker exec sywork_backend pytest <tests
dirigidos>`), `npx tsc -b` para typecheck frontend. **Solo tests dirigidos** (FR-020)

**Target Platform**: Docker Compose on-premise (`sywork_db`/`sywork_backend`/`sywork_frontend`)

**Project Type**: Web application (backend Flask 3 capas + frontend React SPA)

**Performance Goals**: sin cambios sobre los existentes; el listado de personal de un proyecto
debe responder como cualquier maestro (<1 s con cientos de usuarios)

**Constraints**: alcance mínimo (FR-019); compatibilidad total con specs `005`/`007` (flujo
Usuario/cliente de autoservicio y solicitante del ticket); migración sin pérdida de datos
(SC-003: 0 tickets pierden solicitante)

**Scale/Scope**: ~1 migración con 3 bloques, 2 entidades nuevas + 1 ampliada, ~6 endpoints
nuevos + 2 modificados, 1 página frontend nueva + 4 modificadas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|-----------|------------|--------|
| I. API-First y Dominio Primero | Validaciones nuevas (`membership del proyecto`, `skill_type` obligatorio) viven en servicios de dominio (`project_member_service`, `skill_service`, `ticket_service`); contratos documentados en `contracts/` antes de implementar | ✅ |
| II. Clean Architecture 3 capas | Entidades puras (`ProjectMember`, `ProjectTeam`, `Skill` ampliada) sin imports de framework; repos en `infra/`; rutas solo orquestan | ✅ |
| III. Tipado estricto | Tipos TS nuevos (`ProjectMember`, `ProjectTeam`, `Skill` ampliado) sin `any`; type hints en servicios Python | ✅ |
| IV. Seguridad en profundidad | Endpoints nuevos bajo JWT + `@require_permission`/`enforce_module`; RLS habilitado en las tablas nuevas (consistente con maestros); sin secretos en frontend | ✅ |
| V. Zero dependencias no aprobadas | Ninguna dependencia nueva en `requirements.txt` ni `package.json` | ✅ |
| VI. AI-Native | Skills quedan **mejor** parametrizados (tipo/herramienta/proceso) — refuerza el Gold Standard del futuro Triage Agent; endpoints agnósticos al caller | ✅ |

Sin violaciones — la tabla Complexity Tracking queda vacía.

**Re-check post-diseño (Phase 1)**: sin cambios — el diseño no introduce dependencias nuevas ni
mueve lógica fuera del dominio. ✅

## Project Structure

### Documentation (this feature)

```text
specs/010-proyecto-personal-skills/
├── plan.md              # Este archivo
├── research.md          # Phase 0 — decisiones y alternativas
├── data-model.md        # Phase 1 — entidades, tablas, migración 025
├── quickstart.md        # Phase 1 — guía de validación end-to-end
├── contracts/           # Phase 1 — contratos de API
│   ├── project-members.md
│   ├── project-teams.md
│   ├── client-contacts.md
│   ├── skills.md
│   └── tickets.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 — /speckit-tasks (no lo crea /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   ├── entities/
│   │   ├── project_member.py        # NUEVO: ProjectMember, ProjectTeam
│   │   └── resource.py              # MODIFICADO: Skill += skill_type, tool_id, process_id
│   └── services/
│       ├── project_member_service.py # NUEVO: validaciones de asignación y subgrupos
│       ├── skill_service.py          # MODIFICADO: skill_type obligatorio, FK opcionales
│       └── ticket_service.py         # MODIFICADO: solicitante validado contra personal del proyecto
├── infra/
│   ├── migrations/versions/
│   │   └── 025_project_members_skills.py  # NUEVA: renombre rol + project_members/teams + skills
│   ├── models/
│   │   ├── project_member_model.py   # NUEVO
│   │   └── resource_model.py         # MODIFICADO (columnas de skill)
│   └── repositories/
│       ├── project_member_repo.py    # NUEVO
│       ├── client_contact_repo.py    # MODIFICADO: filtro por project_id
│       └── resource_repo.py          # MODIFICADO: SkillRepository con campos nuevos
├── api/routes/
│   ├── project_members.py            # NUEVO: members + teams de un proyecto
│   ├── client_contacts.py            # MODIFICADO: rol renombrado, filtro project_id
│   ├── resources.py                  # MODIFICADO: skills con tool/process/type
│   └── tickets.py                    # MODIFICADO: validación de solicitante por proyecto
└── tests/
    ├── api/test_project_members.py   # NUEVO (dirigido)
    ├── api/test_skills_structure.py  # NUEVO (dirigido)
    └── api/test_tickets_client_contact.py  # MODIFICADO (fuente por proyecto)

frontend/src/
├── types/
│   ├── projectMember.ts              # NUEVO: ProjectMember, ProjectTeam
│   └── (resource/skill types)        # MODIFICADO: Skill += type/tool/process
├── services/
│   ├── projectMemberService.ts       # NUEVO
│   └── clientContactService.ts       # MODIFICADO: listByProject
├── pages/
│   ├── ProjectPeoplePage.tsx         # NUEVA: pestañas Personas / Equipos (estilo Teamwork)
│   ├── ProjectsPage.tsx              # MODIFICADO: acceso a "Personal" por proyecto
│   ├── SkillsPage.tsx                # MODIFICADO: columnas/formulario tipo-herramienta-proceso
│   ├── TicketsPage.tsx               # MODIFICADO: selector solicitante por Proyecto + textos
│   ├── TicketDetailPage.tsx          # MODIFICADO: selector + textos
│   └── ClientContactsPage.tsx        # MODIFICADO: textos "Usuario/cliente"
└── config/navigation.tsx             # MODIFICADO: textos
```

**Structure Decision**: web application existente (backend 3 capas + SPA React). Se respeta la
estructura actual; solo se agregan los archivos listados y se modifican los directamente
afectados (FR-019).

## Complexity Tracking

Sin violaciones a la Constitución — no aplica.
