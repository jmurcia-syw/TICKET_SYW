# Implementation Plan: Registro de tiempo en el detalle del ticket, rol Encargado y navegación

**Branch**: `005-ticket-tiempo-encargado-nav` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-ticket-tiempo-encargado-nav/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Cuatro mejoras independientes sobre lo ya construido en Fase 1/2: (1) embeber el registro de
tiempo (`work_sessions`) directamente en `TicketDetailPage`, extendiendo la entidad con hora de
inicio/fin opcionales; (2) mostrar el tiempo estimado (`estimated_resolution_minutes`, ya
existente) en horas, junto al tiempo real; (3) un nuevo rol "Encargado" — usuario externo
vinculado a un Cliente fijo, que solo crea y ve sus propios tickets — implementado con una nueva
tabla ligera `client_contacts` (análoga a `resources` pero para contactos externos) y un nuevo
permiso `tickets:view_own` que se suma al esquema de permisos ya existente; (4) corregir
"Volver" en el detalle del ticket para que respete la pantalla de origen (Kanban, Tickets con
filtros, o Panel de Asignación) usando el `state` de navegación de React Router en vez de un
destino fijo.

## Technical Context

**Language/Version**: Python 3.12 (backend) + TypeScript 5 strict / React 19 (frontend) — sin
cambios, mismo stack de Fase 0-2.

**Primary Dependencies**: Flask + Flask-RESTX + Flask-JWT-Extended, SQLAlchemy + Alembic.
Frontend: React 19 + Ant Design 5 + `date-fns` + Axios + `react-router-dom` 6.28 (ya instalado —
se usa su soporte nativo de `state` en `navigate()`/`useLocation()`, sin librería nueva). **Cero
dependencias nuevas.**

**Storage**: PostgreSQL 16 (misma instancia). Se extiende `work_sessions` (columnas nuevas) y se
agrega una tabla nueva `client_contacts`; no se toca el resto del esquema.

**Testing**: `pytest` (dominio/servicio/repositorio/API), mismo patrón que Fases 1-2. Verificación
de UI vía `quickstart.md` manual (sin framework de test de frontend, igual que antes).

**Target Platform**: Servidor Linux on-premise vía Docker Compose (sin cambios).

**Project Type**: Web application (monorepo `backend/` + `frontend/` ya existente).

**Performance Goals**: Sin requisitos nuevos de throughput; mismo orden de magnitud que Fases 1-2.

**Constraints**: Cero dependencias nuevas (Principio V); no se modifican las reglas de negocio ya
vigentes de `work_sessions` (límite 24h/día, ventana de edición 7 días) ni el FSM de tickets; el
campo `estimated_resolution_minutes` conserva su almacenamiento en minutos y sus bloqueos por
estado ya definidos (`FIELD_LOCKS` en `backend/domain/entities/ticket.py`).

**Scale/Scope**: 4 historias de usuario independientes entre sí; alcance acotado a
`TicketDetailPage`, el motor de `work_sessions`, el esquema de roles/permisos, y el router del
frontend.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Chequeo | Resultado |
|-----------|---------|-----------|
| I. API-First y Dominio Primero | ¿La lógica (cálculo de duración desde horas, filtrado "solo propios" para Encargado, resolución de Cliente fijo) vive en `backend/domain/`? ¿Hay contrato Swagger antes del código? | **PASS** — se extiende `WorkSessionService` y se agrega lógica en `TicketService`/nuevo `ClientContactService`; contratos actualizados en `contracts/` antes de tocar rutas |
| II. Clean Architecture 3 capas | ¿Se respeta `domain/`→`infra/`→`api/`+`frontend/src/`? | **PASS** — mismo patrón que Fases 1-2: entidad `ClientContact` en `domain/entities/`, modelo+repo en `infra/`, endpoints en `api/routes/` |
| III. Tipado estricto | ¿Type hints Python? ¿TS strict sin `any`? | **PASS** — sin excepciones previstas |
| IV. Seguridad en profundidad | ¿RLS en `client_contacts`? ¿El Encargado realmente no puede ver tickets/pantallas ajenas aunque la API sea atacada directamente? | **PASS** — RLS en `client_contacts` (mismo patrón app-level); filtrado por `created_by` a nivel de dominio+API para `tickets:view_own` (igual patrón que `work_sessions:view_own`), no solo a nivel de UI |
| V. Cero dependencias no aprobadas | ¿Alguna librería nueva? | **PASS** — ninguna; se reutiliza `react-router-dom` ya instalado y el stack existente |
| VI. AI-Native | ¿Los nuevos datos (hora inicio/fin, Encargado solicitante) quedan como datos estructurados reutilizables a futuro? | **PASS** — hora de inicio/fin en `work_sessions` y el vínculo Encargado→Cliente quedan como columnas estructuradas, no texto libre |

Sin violaciones — no aplica la tabla de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-ticket-tiempo-encargado-nav/
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
│   │   ├── work_session.py       # + started_at/ended_at opcionales
│   │   └── client_contact.py     # NUEVO: ClientContact (Encargado↔Cliente)
│   └── services/
│       ├── work_session_service.py   # + cálculo de duración desde inicio/fin
│       ├── ticket_service.py         # + creación simplificada para Encargado
│       └── client_contact_service.py # NUEVO: alta/consulta de Encargados
├── infra/
│   ├── models/
│   │   ├── work_session_model.py     # + columnas started_at/ended_at
│   │   └── client_contact_model.py   # NUEVO
│   ├── repositories/
│   │   ├── work_session_repo.py      # sin cambios de interfaz
│   │   └── client_contact_repo.py    # NUEVO
│   └── migrations/versions/
│       ├── 018_work_sessions_start_end.py
│       ├── 019_create_client_contacts.py
│       ├── 020_client_contacts_rls.py
│       └── 021_encargado_role_permissions.py
└── api/
    └── routes/
        ├── work_sessions.py      # + GET /api/work-sessions?ticket_id= (ya soportado)
        ├── tickets.py            # + filtro "solo propios" en list/detail;
        │                         #   creación simplificada si caller es Encargado
        └── client_contacts.py    # NUEVO: alta de Encargados (Admin/Coordinador)

frontend/src/
├── components/
│   ├── tickets/
│   │   └── TicketBreadcrumb.tsx      # NUEVO: migas de pan / "Volver" con origen
│   └── worksessions/
│       ├── WorkSessionForm.tsx       # + campos hora inicio/fin
│       └── TicketWorkSessions.tsx    # NUEVO: sección embebida en el detalle
├── pages/
│   ├── TicketDetailPage.tsx          # + sección "Registros de tiempo" + breadcrumb
│   ├── TicketsPage.tsx               # navega pasando `state` de origen
│   ├── KanbanPage.tsx                # navega pasando `state` de origen
│   └── AssignmentPanelPage.tsx       # navega pasando `state` de origen
├── types/
│   └── workSession.ts                # + started_at/ended_at
└── services/
    └── workSessionService.ts         # sin cambios de firma (ya soporta ticket_id)

tests/ (backend, pytest)
├── domain/   test_work_session_service_start_end.py, test_client_contact_service.py
├── infra/    test_client_contact_repo.py
└── api/      test_tickets_encargado.py, test_client_contacts_api.py
```

**Structure Decision**: Se reutiliza la estructura de tres capas ya establecida (Fases 1-2) sin
introducir patrones nuevos. `ClientContact` se suma como sexta entidad de dominio, siguiendo el
mismo camino `domain/entities` → `domain/services` → `infra/models`+`infra/repositories` →
`api/routes` que el resto del sistema. El fix de navegación es puramente frontend (React Router
`state`), sin tocar el backend.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No aplica — el Constitution Check no registró violaciones.
