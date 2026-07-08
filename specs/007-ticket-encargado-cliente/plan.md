# Implementation Plan: Selección manual del Encargado solicitante en el Ticket

**Branch**: `develp_Jp` (sin rama dedicada por feature en este repo) | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-ticket-encargado-cliente/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Agregar al Ticket una referencia opcional a un Encargado (`client_contact_id`, FK a
`client_contacts`, acotada al `client_id` del ticket), seleccionable por personal interno al crear
o editar el ticket — sin tocar Cliente ni Proyecto. Reutiliza el motor de "Encargado" ya construido
en Fase 2.1 (`client_contacts`, `_requester()`), extendiéndolo para que el "Encargado solicitante"
pueda venir de dos orígenes: automático (creador con rol Encargado, sin cambios) o manual
(`client_contact_id`, nuevo). Requiere una migración de base de datos (columna nueva, sin tabla
nueva) y tocar la capa de dominio/API de tickets; también corrige un gap de permisos descubierto
durante la planificación: hoy `GET /api/client-contacts` exige `client_contacts:manage`
(Admin/Coordinador), lo que impediría a un Resolutor ver la lista de Encargados de un cliente al
crear/editar un ticket (lo pide explícitamente la Historia 1 del spec).

## Technical Context

**Language/Version**: Python 3.12 + Flask (backend), TypeScript 5 estricto + React 19 (frontend) —
sin cambios de versión.

**Primary Dependencies**: SQLAlchemy + Alembic (migración nueva), Flask-RESTX (swagger ya
existente de `tickets`/`client-contacts`), Ant Design 5 (`Select`) en frontend. Ninguna
dependencia nueva (Principio V).

**Storage**: PostgreSQL 16. Nueva columna `tickets.client_contact_id` (UUID, nullable, FK →
`client_contacts.id`, `ON DELETE SET NULL`) — sin tabla nueva, sin cambios de RLS (mismo alcance
de columnas ya cubierto por la política RLS existente de `tickets`, `012_tickets_rls.py`).

**Testing**: Backend — pytest, con tests nuevos dirigidos exclusivamente a lo que cambia
(`backend/tests/domain/test_ticket_service_client_contact.py`,
`backend/tests/api/test_tickets_client_contact.py`). **Restricción explícita del solicitante para
esta funcionalidad**: no se ejecuta la suite completa de pytest de forma masiva — solo esos dos
archivos dirigidos. Frontend — sin suite automatizada configurada; validación con `npx tsc -b` +
`quickstart.md` manual.

**Target Platform**: Web (misma SPA + API REST ya existentes).

**Project Type**: Web application (`backend/` + `frontend/`) — esta funcionalidad toca ambos
lados, a diferencia de la Feature 006 (solo frontend).

**Performance Goals**: Sin objetivo nuevo; una columna nullable indexada solo si se necesitara
filtrar tickets por Encargado (no lo pide el spec — sin índice nuevo por ahora).

**Constraints**: Debe preservar el comportamiento automático ya existente (Fase 2.1) para tickets
creados por un usuario con rol Encargado — un ticket nunca combina ambos orígenes (FR-009). No se
puede reemplazar `client_contact_id` por reutilizar `created_by`: el creador del ticket (personal
interno) y el Encargado solicitante son personas distintas.

**Scale/Scope**: 1 columna nueva + 1 migración; 4 archivos backend de dominio/infra/API tocados; 1
corrección de permiso en `client_contacts.py`; 2 pantallas frontend tocadas (`TicketsPage.tsx`,
`TicketDetailPage.tsx`) + tipos/servicio ya existentes reutilizados sin cambios de forma.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (API-First / Dominio primero)**: La regla "el Encargado debe pertenecer al
  Cliente del ticket" y "no editable si el creador es Encargado" vive en
  `backend/domain/services/ticket_service.py` (`validate_create`/`validate_patch`), no en rutas ni
  en el frontend. El endpoint `PATCH /api/tickets/{id}` ya existe y se reutiliza sin acoplarse a
  una pantalla concreta. **PASS**.
- **Principio II (Clean Architecture 3 capas)**: Columna nueva en Capa 2
  (`backend/infra/models/ticket_model.py`, `backend/infra/repositories/ticket_repo.py`), campo
  nuevo en la entidad de Capa 1 (`backend/domain/entities/ticket.py`, sin imports externos),
  serialización en Capa 3 (`backend/api/routes/tickets.py`). Frontend: `services/` para las
  llamadas, `pages/` solo orquesta y renderiza. **PASS**.
- **Principio III (Tipado estricto)**: TypeScript strict sin `any`; type hints en los métodos
  Python nuevos/tocados. **PASS**.
- **Principio IV (Seguridad en profundidad)**: La regla FR-009 (no editable si el creador es
  Encargado) se aplica en el backend (`validate_patch`), no solo ocultando el control en el
  frontend — un PATCH directo a la API también debe rechazarse. RLS de `tickets` no cambia (mismo
  alcance de filas, columna nueva no introduce una nueva dimensión de acceso). La corrección de
  permiso en `GET /api/client-contacts` amplía el acceso de **lectura** a roles con
  `tickets:create`/`tickets:edit`, no toca `POST` (sigue exigiendo `client_contacts:manage`) — no
  debilita la seguridad existente, solo corrige un gap que bloquea un flujo legítimo (mismo patrón
  ya aplicado a `notifications.py` en Fase 2.1 cuando se descubrió un gap similar). **PASS**.
- **Principio V (Gobernanza de librerías)**: Sin dependencias nuevas. **PASS**.
- **Principio VI (AI-Native)**: No aplica — cambio de clasificación del ticket, no de sus acciones
  críticas (`/assign`, `/status`). **PASS**.

**Resultado**: Sin violaciones. No se requiere entrada en "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/007-ticket-encargado-cliente/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command) — delta de tickets/client-contacts
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

Proyecto "Web application" ya establecido (`backend/` + `frontend/`). Archivos concretos que toca
esta funcionalidad:

```text
backend/
├── infra/migrations/versions/
│   └── 022_tickets_client_contact.py     # NUEVO: columna tickets.client_contact_id
├── domain/
│   ├── entities/ticket.py                # MODIFICADO: campo client_contact_id; agregarlo a
│   │                                       # FIELD_LOCKS["cerrado"/"cancelado"] (FR-008)
│   └── services/ticket_service.py        # MODIFICADO: validate_create/validate_patch validan
│                                           # pertenencia al cliente (FR-002) y bloquean edición
│                                           # si el creador es Encargado (FR-009); PATCHABLE_FIELDS
├── infra/
│   ├── models/ticket_model.py            # MODIFICADO: columna + to_entity()
│   ├── repositories/ticket_repo.py       # MODIFICADO: create() incluye el campo nuevo
│   │                                       # (update_fields ya es genérico, sin cambios ahí)
│   └── repositories/client_contact_repo.py  # MODIFICADO: agregar get_by_id() (falta hoy)
├── api/routes/
│   ├── tickets.py                        # MODIFICADO: input/output swagger, POST/PATCH, _requester()
│   │                                       # prioriza client_contact_id sobre el auto-derivado
│   └── client_contacts.py                # MODIFICADO: GET admite tickets:create/tickets:edit
│                                           # además de client_contacts:manage (gap de permiso)
└── tests/
    ├── domain/test_ticket_service_client_contact.py   # NUEVO
    └── api/test_tickets_client_contact.py             # NUEVO

frontend/src/
├── types/ticket.ts        # MODIFICADO: client_contact_id en TicketFormData y TicketDetail
├── pages/
│   ├── TicketsPage.tsx     # MODIFICADO: Select "Encargado" en el formulario de creación,
│   │                        # filtrado por client_id, junto a Cliente/Proyecto (sin tocarlos)
│   └── TicketDetailPage.tsx # MODIFICADO: Select "Encargado" editable en "Clasificación"
│                             # (reutiliza el mismo Tag ya existente para mostrarlo; bloqueado si
│                             # el origen es automático, FR-009)
```

**Structure Decision**: Se mantiene la estructura ya vigente (Capa 1/2/3 en backend;
`pages/services/types` en frontend). No se crean carpetas nuevas; todos los cambios caen dentro de
los módulos de dominio `tickets`/`client_contacts` ya existentes.

## Complexity Tracking

*Sin violaciones de la Constitution Check — tabla no aplica.*
