# Implementation Plan: Corregir el Cliente de un Usuario/cliente y desambiguar Proyectos homónimos

**Branch**: `develp_Jp` (rama de desarrollo actual; el directorio de la spec es
`016-corregir-cliente-encargado`) | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/016-corregir-cliente-encargado/spec.md`

## Summary

Bug fix sobre spec 015: hoy `client_contacts.client_id` se fija en el alta y el endpoint
`POST /api/client-contacts/{id}/projects` siempre exige que el Proyecto agregado sea del mismo
Cliente ya guardado, **incluso si el contacto quedó en 0 Proyectos** tras quitar los mal
asignados — dejando un error de Cliente sin forma de corrección. Este plan relaja esa regla
**solo** cuando el contacto tiene 0 `project_members`: en ese caso el Proyecto agregado puede ser
de cualquier Cliente activo, y el Cliente del contacto se actualiza para coincidir (nuevo método
`ClientContactRepository.update_client_id`). Además, el selector de "agregar Proyecto" en
`ClientContactsPage.tsx` pasa a mostrar "Cliente — Proyecto" (como ya hace el selector de alta),
para distinguir Proyectos homónimos entre Clientes distintos, y se corrige un bug de refetch que
impedía ver el Cliente actualizado tras la corrección. Sin migraciones ni endpoints nuevos.

**Directriz estricta**: tocar solo `client_contacts.py`, `client_contact_repo.py` y
`ClientContactsPage.tsx` (los mismos archivos de spec 015 afectados por este bug); extender el
test dirigido existente (`test_client_contacts_projects.py`), sin crear archivos de test nuevos
ni tocar módulos ajenos al flujo de Usuario/cliente.

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript strict / React 19 (frontend)

**Primary Dependencies**: Flask 3.x + Flask-RESTX, SQLAlchemy 2.x, Ant Design 5 — **sin
dependencias nuevas** (Principio V)

**Storage**: PostgreSQL 16 (Docker `sywork_db`) — **sin migración nueva**, reutiliza
`client_contacts`/`project_members` (spec 010/015)

**Testing**: pytest contra Postgres real en Docker (`docker exec sywork_backend pytest <tests
dirigidos>`), `npx tsc -b` para typecheck frontend. Solo tests dirigidos (Principio VII); casos
nuevos se agregan al archivo ya existente `test_client_contacts_projects.py`, sin fixtures de
Resolutor ni disparo de correo (misma restricción de spec 015)

**Target Platform**: Docker Compose on-premise (`sywork_db`/`sywork_backend`/`sywork_frontend`)

**Project Type**: Web application (backend Flask 3 capas + frontend React SPA)

**Performance Goals**: sin cambios — una consulta adicional (`list_project_ids_by_user`, ya
existente) por llamada al endpoint de agregar Proyecto

**Constraints**: alcance mínimo (solo el endpoint de agregar Proyecto y el selector
correspondiente); compatibilidad total con spec 015 (regla de "mismo Cliente" con 1+ Proyectos
sin cambios); 0 tickets históricos afectados (SC-003)

**Scale/Scope**: 0 migraciones, 1 método nuevo de repositorio, 1 endpoint modificado (lógica,
sin cambio de firma), 1 archivo frontend modificado (selector + refetch), tests agregados al
archivo existente

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|-----------|------------|--------|
| I. API-First y Dominio Primero | La decisión de "0 Proyectos ⇒ Cliente corregible" vive en la ruta orquestando repos ya existentes (`resolve_common_client` de dominio + `list_project_ids_by_user`); contrato documentado en `contracts/client-contacts-delta.md` antes de tocar el endpoint | ✅ |
| II. Clean Architecture 3 capas | Sin entidades nuevas; `ClientContactRepository` (Capa 2) gana un método de escritura simple; la ruta (Capa 3) solo orquesta la decisión | ✅ |
| III. Tipado estricto | Sin `any` nuevo; el método de repo tipado con `uuid.UUID` | ✅ |
| IV. Seguridad en profundidad | Mismo permiso `client_contacts:manage`; sin cambios de RLS (tablas ya existentes) | ✅ |
| V. Zero dependencias no aprobadas | Ninguna dependencia nueva | ✅ |
| VI. AI-Native | Sin impacto — no toca skills, asignación ni FSM | ✅ |
| VII. Alcance de sesión / testing ultra-limitado | Alcance acotado a los 3 archivos de spec 015 afectados por el bug; casos nuevos se agregan al test dirigido ya existente, no un archivo nuevo | ✅ |

Sin violaciones — la tabla Complexity Tracking queda vacía.

**Re-check post-diseño (Phase 1)**: sin cambios — el diseño (research.md, data-model.md,
contracts/) no introduce dependencias, tablas, ni endpoints nuevos; solo relaja una validación
existente bajo una condición precisa (0 Proyectos). ✅

## Project Structure

### Documentation (this feature)

```text
specs/016-corregir-cliente-encargado/
├── plan.md              # Este archivo
├── research.md          # Phase 0 — decisiones y alternativas
├── data-model.md        # Phase 1 — sin migración, regla de negocio actualizada
├── quickstart.md        # Phase 1 — guía de validación end-to-end
├── contracts/
│   └── client-contacts-delta.md  # Phase 1 — contrato de API (delta sobre spec 015)
├── checklists/requirements.md
└── tasks.md              # Phase 2 — /speckit-tasks (no lo crea /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── infra/
│   └── repositories/
│       └── client_contact_repo.py        # MODIFICADO: += update_client_id(contact_id, client_id)
├── api/routes/
│   └── client_contacts.py                # MODIFICADO: POST .../projects — permite Cliente
│                                          #   distinto y corrige client_id cuando 0 Proyectos
└── tests/
    └── api/test_client_contacts_projects.py  # MODIFICADO (spec 015): += casos de corrección

frontend/src/
└── pages/
    └── ClientContactsPage.tsx            # MODIFICADO: selector "agregar Proyecto" muestra
                                           #   Cliente — Proyecto y ya no se acota al Cliente
                                           #   actual cuando el contacto tiene 0 Proyectos;
                                           #   refetch tras agregar usa email en vez de client_id
```

**Structure Decision**: mismos 3 archivos que tocó spec 015 para este flujo — no se agregan
páginas, endpoints nuevos ni migraciones. Cambio acotado a una condición de negocio y a un
selector de UI.

## Complexity Tracking

Sin violaciones a la Constitución — no aplica.
