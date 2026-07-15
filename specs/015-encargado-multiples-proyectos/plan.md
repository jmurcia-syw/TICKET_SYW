# Implementation Plan: Encargado (Usuario/cliente) en múltiples Proyectos

**Branch**: `develp_Jp` (rama de desarrollo actual; el directorio de la spec es
`015-encargado-multiples-proyectos`) | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/015-encargado-multiples-proyectos/spec.md`

## Summary

Un Usuario/cliente (Encargado) hoy solo puede quedar vinculado a **un** Proyecto porque el
límite vive en la API de alta (`POST /api/client-contacts` acepta un único `project_id`) y en el
modal de creación del frontend (`<Select>` simple) — el modelo de datos (`project_members`,
spec 010) ya soporta muchos-a-muchos y la lógica de tickets ya filtra correctamente por
Proyecto. Este plan (a) cambia el alta para aceptar varios Proyectos (`project_ids[]`),
validando que todos pertenezcan al mismo Cliente, y (b) agrega un sub-recurso
(`POST`/`DELETE /api/client-contacts/{id}/projects[/{project_id}]`) más una acción en la UI para
agregar/quitar Proyectos de un Usuario/cliente ya existente. Sin migraciones ni cambios de
esquema.

**Directriz estricta del solicitante**: tocar solo los archivos de `client_contacts` (rutas,
servicio de dominio, repos de `project_members`, página y servicio frontend) directamente
afectados; sin refactors colaterales; validación con tests dirigidos, nunca la suite completa.

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript strict / React 19 (frontend)

**Primary Dependencies**: Flask 3.x + Flask-RESTX, SQLAlchemy 2.x, Ant Design 5 (`Select
mode="multiple"`, ya aprobado) — **sin dependencias nuevas** (Principio V)

**Storage**: PostgreSQL 16 (Docker `sywork_db`) — **sin migración nueva**, reutiliza
`project_members` (migración `025`, spec 010)

**Testing**: pytest contra Postgres real en Docker (`docker exec sywork_backend pytest <tests
dirigidos>`), `npx tsc -b` para typecheck frontend. Solo tests dirigidos (Principio VII)

**Target Platform**: Docker Compose on-premise (`sywork_db`/`sywork_backend`/`sywork_frontend`)

**Project Type**: Web application (backend Flask 3 capas + frontend React SPA)

**Performance Goals**: sin cambios — mismo volumen de datos que el listado de Usuarios/cliente
actual

**Constraints**: alcance mínimo (solo `client_contacts` + repo `project_members` ya existente);
compatibilidad total con specs `007`/`010` (autoservicio, solicitante del ticket); sin pérdida ni
modificación de tickets históricos (SC-004)

**Scale/Scope**: 0 migraciones, 1 método nuevo de dominio, 1 método nuevo de repositorio, 2
endpoints nuevos + 1 modificado, 1 página frontend modificada (sin páginas nuevas)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|-----------|------------|--------|
| I. API-First y Dominio Primero | Validación "mismo Cliente" nueva vive en `ClientContactService.resolve_common_client` (Capa 1); contrato documentado en `contracts/client-contacts-delta.md` antes de tocar rutas | ✅ |
| II. Clean Architecture 3 capas | Sin entidades nuevas; `ProjectMemberRepository` (Capa 2, ya existente) gana un método de lectura; rutas (Capa 3) solo orquestan | ✅ |
| III. Tipado estricto | `ClientContactCreateRequest.project_ids: string[]` sin `any`; type hints en el método nuevo de servicio Python | ✅ |
| IV. Seguridad en profundidad | Endpoints nuevos bajo el mismo `@require_permission("client_contacts", "manage")`; RLS de `project_members` ya vigente (spec 010), sin tablas nuevas que habilitar | ✅ |
| V. Zero dependencias no aprobadas | Ninguna dependencia nueva; `Select mode="multiple"` es parte de Ant Design 5 ya aprobado | ✅ |
| VI. AI-Native | Sin impacto — no toca skills, asignación ni FSM | ✅ |
| VII. Alcance de sesión / testing ultra-limitado | Alcance acotado a `client_contacts` + `project_members` (repo); un solo archivo de test nuevo, dirigido, ≤ 10 registros por caso | ✅ |

Sin violaciones — la tabla Complexity Tracking queda vacía.

**Re-check post-diseño (Phase 1)**: sin cambios — el diseño (research.md, data-model.md,
contracts/) no introduce dependencias nuevas, tablas nuevas, ni lógica fuera del dominio. ✅

## Project Structure

### Documentation (this feature)

```text
specs/015-encargado-multiples-proyectos/
├── plan.md              # Este archivo
├── research.md          # Phase 0 — decisiones y alternativas
├── data-model.md         # Phase 1 — sin migración, comportamiento de servicio
├── quickstart.md         # Phase 1 — guía de validación end-to-end
├── contracts/
│   └── client-contacts-delta.md  # Phase 1 — contrato de API (delta sobre spec 007/010)
├── checklists/requirements.md
└── tasks.md              # Phase 2 — /speckit-tasks (no lo crea /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   └── services/
│       └── client_contact_service.py     # MODIFICADO: += resolve_common_client(project_ids, projects_repo)
├── infra/
│   └── repositories/
│       └── project_member_repo.py        # MODIFICADO: += get_by_project_and_user(project_id, user_id)
├── api/routes/
│   └── client_contacts.py                # MODIFICADO: POST acepta project_ids[]; += POST/DELETE .../projects[/{project_id}]
└── tests/
    └── api/test_client_contacts_projects.py  # NUEVO (dirigido, ≤10 registros/test)

frontend/src/
├── types/
│   └── clientContact.ts                  # MODIFICADO: ClientContactCreateRequest.project_ids: string[]
├── services/
│   └── clientContactService.ts           # MODIFICADO: create() con project_ids; += addProject/removeProject
└── pages/
    └── ClientContactsPage.tsx            # MODIFICADO: Select multi-select en alta + acción "Gestionar proyectos"
```

**Structure Decision**: web application existente (backend 3 capas + SPA React). No se agregan
páginas ni módulos nuevos; solo se modifican los archivos de `client_contacts` directamente
afectados, reutilizando `ProjectMemberRepository` ya existente (spec 010).

## Complexity Tracking

Sin violaciones a la Constitución — no aplica.
