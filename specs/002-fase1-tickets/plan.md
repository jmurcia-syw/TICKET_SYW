# Implementation Plan: Fase 1 — Tickets

**Branch**: `002-fase1-tickets` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-fase1-tickets/spec.md`

## Summary

Implementar el núcleo operativo de la aplicación: registro y gestión de tickets con ciclo de
vida de 9 estados + CANCELADO (matriz `docs/Regla de actividad de estados.xlsx`), comentarios
tipificados con adjuntos que ejecutan las transiciones, asignación Triage Push con registro
inmutable de contexto (Gold Standard Dataset), Panel de Asignación resolutor × estado,
notificaciones internas, y **activación del enforcement JWT + permisos en toda la API**
(cierra la deuda diferida de Fase 0). La validación de transiciones vive en el dominio como
máquina de estados con `python-transitions` (disparada manualmente en esta fase; la
automatización llega en Fase 6 sin cambio de arquitectura).

## Technical Context

**Language/Version**: Python 3.12 (backend) + TypeScript 5.6 strict (frontend)

**Primary Dependencies**:
- Backend: Flask 3.1, Flask-RESTX, SQLAlchemy 2.x + Alembic, Flask-JWT-Extended,
  `python-transitions` (nueva — aprobada en la Constitución para FSM)
- Frontend: React 19, Ant Design 5, Zustand, Axios, date-fns, pnpm

**Storage**: PostgreSQL 16 (tablas nuevas: tickets, ticket_comments, comment_attachments,
ticket_status_transitions, ticket_assignments, notifications, 3 catálogos). Adjuntos en
filesystem del contenedor bajo volumen Docker (`/repo/uploads`), metadatos en DB.

**Testing**: pytest + pytest-flask (dominio sin DB + API contra Postgres real vía Docker) —
Vitest/typecheck en frontend

**Target Platform**: Web app — Docker Compose on-premise (misma infraestructura de Fase 0)

**Project Type**: Web application (SPA + REST API), extensión del monolito existente

**Performance Goals**:
- Listados de tickets con filtros < 1 s hasta 5.000 tickets (SC-008)
- Panel de Asignación < 2 s con 500 tickets (SC-005)
- Transición por comentario tipificado: una sola operación atómica (comentario + transición
  + notificación en la misma transacción)

**Constraints**:
- Transiciones válidas SOLO las de la matriz (FR-008) — enforcement en dominio, no en UI
- Enforcement JWT + permiso módulo+acción en TODAS las rutas API (FR-022); públicos solo
  login, callback Google y health
- Histórico de transiciones y asignaciones append-only (nunca update/delete)
- Adjuntos: máx 10 MB/archivo por defecto, tipos configurables (FR-015)
- Estados manuales en esta fase: sin jobs automáticos (el cierre por 3 días es elegibilidad
  calculada, no un cron)

**Scale/Scope**: cientos de tickets/mes, 10-30 usuarios internos, 6 pantallas/vistas nuevas
(listado, detalle+comentarios, formulario, panel de asignación, catálogos, notificaciones)

## Constitution Check

*GATE: constitución v1.1.0.*

| Principio | Estado | Verificación |
|-----------|--------|--------------|
| I. API-First; contrato antes de código | PASS | `contracts/tickets.md` + `contracts/notifications-catalogs.md` definidos en Phase 1 |
| I. `POST /api/tickets/{id}/assign` independiente de UI | PASS | Endpoint dedicado; panel y detalle lo consumen igual (FR-018) |
| II. Clean Architecture 3 capas | PASS | FSM y reglas en `domain/`; repos en `infra/`; rutas orquestan |
| III. TS strict sin `any`; type hints Python | PASS | Igual que Fase 0 |
| IV. JWT + RLS doble protección | PASS | Enforcement JWT+permisos en toda la API (FR-022); RLS en `tickets` (asignado/rol) |
| V. Gobernanza de librerías | PASS | Única dependencia nueva: `python-transitions` — ya aprobada explícitamente en la Constitución (stack FSM) |
| VI. AI-Native: Gold Standard Dataset | PASS | `ticket_assignments` append-only con contexto JSONB (FR-019); tipos de comentario estructurados (FR-013) |
| FSM: solo transiciones definidas | PASS | Matriz del Excel codificada en `domain/fsm/ticket_fsm.py` |

**Resultado**: PASS sin violaciones. Complexity Tracking vacío.

## Project Structure

### Documentation (this feature)

```text
specs/002-fase1-tickets/
├── plan.md              este archivo
├── research.md          decisiones técnicas Phase 0
├── data-model.md        entidades y relaciones Phase 1
├── quickstart.md        guía de validación
├── contracts/
│   ├── tickets.md       CRUD + assign + comments + transiciones + panel
│   └── notifications-catalogs.md
└── tasks.md             generado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── domain/
│   ├── entities/
│   │   ├── ticket.py            Ticket + enums (TicketType, Priority, Severity, Level)
│   │   ├── comment.py           Comment + CommentType (catálogo estructurado)
│   │   └── notification.py      Notification
│   ├── fsm/
│   │   └── ticket_fsm.py        máquina de estados python-transitions (matriz FR-008)
│   └── services/
│       ├── ticket_service.py    creación, validaciones, número consecutivo
│       ├── comment_service.py   tipo comentario → transición + bloqueos de campos (FR-010/014)
│       ├── assignment_service.py Triage Push + snapshot de contexto (FR-019)
│       └── notification_service.py eventos → notificaciones (FR-023/024)
├── infra/
│   ├── models/
│   │   ├── ticket_model.py      TicketModel + StatusTransitionModel + AssignmentModel
│   │   ├── comment_model.py     CommentModel + AttachmentModel
│   │   ├── notification_model.py
│   │   └── catalog_model.py     ToolCatalog, ProcessCatalog, ResolutionTypeCatalog
│   ├── repositories/
│   │   ├── ticket_repo.py
│   │   ├── comment_repo.py
│   │   ├── notification_repo.py
│   │   └── catalog_repo.py
│   ├── storage/
│   │   └── attachments.py       guardado/lectura de archivos en /repo/uploads
│   └── migrations/versions/
│       └── 011_create_tickets.py  tablas + catálogos seed + permisos tickets/assignment_panel
├── api/
│   ├── middleware/
│   │   └── rbac.py              @require_permission(module, action) — reemplaza require_role
│   └── routes/
│       ├── tickets.py           /api/tickets (+/assign,/comments,/cancel,/close,/relate)
│       ├── assignment_panel.py  /api/assignment-panel
│       ├── notifications.py     /api/notifications
│       └── catalogs.py          /api/catalogs/{tools|processes|resolution-types}
└── tests/
    ├── domain/                  FSM (todas las transiciones válidas e inválidas), servicios
    └── api/                     tickets, assign, comments+transición, panel, enforcement 401/403

frontend/src/
├── components/tickets/
│   ├── TicketStatusTag.tsx      badge por estado (colores del tema)
│   ├── CommentThread.tsx        hilo de comentarios con tipos y adjuntos
│   ├── CommentComposer.tsx      selector de tipo válido según estado + adjuntos
│   └── AssignModal.tsx          selector de resolutor con skills y carga visible
├── pages/
│   ├── TicketsPage.tsx          listado con filtros combinables
│   ├── TicketDetailPage.tsx     detalle + historial + composer
│   ├── AssignmentPanelPage.tsx  matriz resolutor × estado + NUEVOs
│   └── CatalogsPage.tsx         administración de catálogos
├── services/
│   ├── ticketService.ts
│   ├── notificationService.ts
│   └── catalogService.ts
├── types/ticket.ts, notification.ts, catalog.ts
└── components/common/NotificationBell.tsx  campana en el header del Dashboard
```

**Structure Decision**: extensión del monolito web existente (backend Flask 3 capas +
SPA React). Sin proyectos nuevos. Las únicas piezas estructurales nuevas son
`backend/domain/fsm/` (máquina de estados pura) y `backend/infra/storage/` (adjuntos).

## Complexity Tracking

> Sin violaciones a la Constitución — tabla vacía.

---

## Amendment 2026-07-06 — Catálogo dinámico de tipo de registro

**Input**: Cambio de spec (FR-029/FR-030, spec.md sesión 2026-07-06) — el campo
`record_type` (Ticket/Tarea) pasa de CHECK constraint fijo a catálogo administrable
`catalog_record_types`, siguiendo el mismo patrón que `catalog_tools`/`catalog_processes`/
`catalog_resolution_types`. El dominio sigue bloqueando la creación de tickets con "Tarea"
(reservado Fase 3) — solo el catálogo se vuelve dinámico.

### Technical Context (delta)

- Nueva migración `013_dynamic_record_type.py`: crea `catalog_record_types` (misma forma que
  los otros 3 catálogos: `id`, `name` UNIQUE, `active`, `created_at`), la siembra con
  `Ticket`/`Tarea`, agrega columna `tickets.record_type_id UUID NOT NULL FK
  catalog_record_types(id)`, hace backfill de las filas existentes (`record_type='ticket'` →
  id de "Ticket"; no deberían existir filas `'task'` porque el dominio nunca las permitió) y
  elimina la columna vieja `record_type` junto con su CHECK constraint en la misma migración.
- Sin dependencias nuevas: reutiliza el mecanismo genérico de catálogos ya existente
  (`CATALOG_MODELS` / `CATALOG_TICKET_COLUMN` en `backend/infra/models/catalog_model.py`,
  ruta genérica `backend/api/routes/catalogs.py`).
- Cambios de código acotados: `TicketModel` (columna), `Ticket` entity + `TicketService`
  (validación FR-030: rechazar `record_type_id` que no resuelva a "Ticket"), serialización en
  `backend/api/routes/tickets.py::_ticket_summary` (`record_type` string → `record_type_id`
  uuid), frontend (`types/ticket.ts`, `services/ticketService.ts`, formulario de nuevo
  ticket, `CatalogsPage.tsx` agrega pestaña "Tipo de registro" con el mismo componente
  genérico de catálogos).

### Constitution Check (re-evaluación)

| Principio | Estado | Verificación |
|-----------|--------|--------------|
| I. API-First; contrato antes de código | PASS | `contracts/tickets.md` y `contracts/notifications-catalogs.md` ya actualizados (`record_type_id`, slug `record-types`) antes de tocar código |
| II. Clean Architecture 3 capas | PASS | Regla FR-030 vive en `TicketService` (dominio), no en la ruta ni en el frontend |
| III. TS strict / type hints Python | PASS | Sin cambio de patrón — mismo tipado que `tool_id`/`process_id` |
| IV. JWT + RLS doble protección | PASS | El catálogo nuevo cae bajo el permiso genérico `catalogs:*` ya protegido; sin superficie nueva de auth |
| V. Gobernanza de librerías | PASS | Cero dependencias nuevas |
| VI. AI-Native | N/A | No aplica a este cambio |
| FSM: solo transiciones definidas | N/A | `record_type_id` no participa en la FSM de estados |

**Resultado**: PASS sin violaciones. Complexity Tracking vacío.

### Project Structure (delta)

```text
backend/
├── infra/
│   ├── models/catalog_model.py     + RecordTypeCatalogModel; CATALOG_MODELS["record-types"]
│   ├── models/ticket_model.py      record_type (TEXT) → record_type_id (UUID FK)
│   └── migrations/versions/
│       └── 013_dynamic_record_type.py   catálogo + seed + backfill + drop columna vieja
├── domain/
│   ├── entities/ticket.py          record_type → record_type_id
│   └── services/ticket_service.py  valida record_type_id resuelve a "Ticket" (FR-030)
└── api/routes/tickets.py           _ticket_summary: "record_type" → "record_type_id"

frontend/src/
├── types/ticket.ts                 record_type → record_type_id
├── services/ticketService.ts       payload de creación incluye record_type_id (default)
└── pages/CatalogsPage.tsx          pestaña "Tipo de registro" (mismo componente genérico)
```

**Structure Decision**: sin piezas estructurales nuevas — extensión directa del patrón de
catálogos ya existente; no se crean carpetas ni módulos nuevos.

### Complexity Tracking (amendment)

> Sin violaciones — tabla vacía.
