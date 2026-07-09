# Implementation Plan: Listas de Tareas, Subtareas, ciclo de vida unificado y fix de Registro de tiempo

**Branch**: `009-tareas-listas-subtareas` | **Date**: 2026-07-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-tareas-listas-subtareas/spec.md`

## Summary

Fase 3 (spec `008`) entregó la Tarea como el mismo registro `tickets` con una FSM propia de 4
estados y campos de clasificación ocultos. Esta spec revierte ambas decisiones — Tarea comparte
el catálogo de 10 estados y todos los campos de clasificación del Ticket, con transición **libre**
(cualquier estado a cualquier estado) y **comentario obligatorio** por cambio — y agrega dos
niveles nuevos a la jerarquía ya prevista en la constitución: **Lista de tareas** (Nivel 3, entidad
real dentro de un Proyecto) y **Subtarea** (Nivel 5, autorreferencial vía `parent_task_id`, mismo
registro `tickets`). También corrige el defecto de Registro de tiempo rechazando a un creador/
encargado legítimo. El enfoque técnico reutiliza al máximo: mismo `ticket_fsm.py` (sin bifurcar
por tipo), un nuevo servicio delgado de "transición libre + comentario" para Tarea, una tabla
`task_lists` nueva y una columna `parent_task_id` autorreferencial en `tickets` — sin tabla
`subtasks` separada, ya que Subtarea es conceptualmente el mismo registro con un padre.

## Technical Context

**Language/Version**: Python 3.12 (backend) + TypeScript 5 strict (frontend, React 19)

**Primary Dependencies**: Flask + Flask-RESTX (Swagger), SQLAlchemy + Alembic, `python-transitions`
(FSM, reutilizada sin cambios — Tarea deja de tener FSM propia), Ant Design 5, `@hello-pangea/dnd`
(Kanban ya existente)

**Storage**: PostgreSQL 16 — reutiliza la tabla `tickets` (Nivel 4/5: Tarea/Subtarea) y `projects`
(Nivel 2); agrega tabla nueva `task_lists` (Nivel 3) y columna autorreferencial
`tickets.parent_task_id` (Nivel 5)

**Testing**: `pytest` (backend, dominio + API), `tsc -b` (frontend, sin suite de tests dedicada
todavía — validación manual E2E vía Docker real, mismo patrón que specs `007`/`008`)

**Target Platform**: Web app servida por Docker Compose (`sywork_backend` Flask dev server,
`sywork_frontend` Vite, `sywork_db` Postgres 16)

**Project Type**: Web application (backend + frontend, Clean Architecture 3 capas por
`.specify/memory/constitution.md`)

**Performance Goals**: sin metas nuevas — el volumen esperado (decenas de Listas/Tareas/Subtareas
por Proyecto) no justifica paginación ni agregación en servidor más allá de lo ya existente en
`GET /api/tickets`

**Constraints**: no romper ninguna transición ni endpoint ya validado de Ticket (FR-002, SC-… de
specs previas); la migración de datos de la spec `008` (estados de 4 valores, `list_name` texto
libre) debe preservar el estado y la agrupación visible hoy en "Mis Tareas" (FR-012, FR-013)

**Scale/Scope**: 1 backend Flask + 1 frontend React, cambios acotados a los módulos de Ticket/Tarea
ya existentes (`backend/domain/{entities,services,fsm}`, `backend/infra/{models,repositories,
migrations}`, `backend/api/routes/tickets.py`, más rutas nuevas para `task_lists`) y a las páginas
de Ticket/Tarea/Kanban/Mis Tareas del frontend, más una pantalla nueva "Lista" (sidebar de
Proyecto, según `docs/mockup.html`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (API-First y Dominio Primero)**: PASS. La transición libre de Tarea vive en
  `backend/domain/services/` (nuevo método, sin Flask/SQLAlchemy); el contrato Swagger de
  `POST /api/tickets/{id}/status` (endpoint nuevo, reemplaza `task-transition`) y de
  `task_lists` se define antes de implementar la ruta.
- **Principio II (Clean Architecture 3 capas)**: PASS. `task_fsm.py` se **retira** (no se
  bifurca `ticket_fsm.py` por tipo — Decisión pendiente de research.md sobre cómo modelar la
  transición libre sin duplicar la FSM de 16 transiciones). `TaskList` es una entidad de dominio
  nueva con su propio repositorio en `backend/infra/repositories/`.
- **Principio III (Tipado estricto)**: PASS. Sin `any` nuevo; `parent_task_id` tipado
  `Optional[uuid.UUID]` en la entidad `Ticket`.
- **Principio IV (Seguridad en profundidad)**: PASS. `task_lists` hereda el mismo alcance de RLS
  por Cliente que `projects`/`tickets` (vía `project_id` → `client_id`), sin tabla nueva fuera del
  perímetro ya protegido.
- **Principio V (Zero dependencias no aprobadas)**: PASS. Ninguna librería nueva — se reutiliza
  `python-transitions` (ya aprobada) y el resto del stack sin cambios.
- **Principio VI (AI-Native)**: **Atención**. El comentario obligatorio de un cambio de estado de
  Tarea (FR-005) es texto libre, no un tipo estructurado como los del Ticket (Principio VI: "El
  sistema de comentarios DEBE exponer tipos de comentario como datos estructurados"). Se
  documenta como excepción justificada en Complexity Tracking: forzar un catálogo de tipos
  estructurados para una transición sin restricciones de secuencia no aporta valor de análisis
  (el "tipo" ya lo da el estado destino elegido) y contradice la petición explícita del usuario
  de "sin restricciones".

## Project Structure

### Documentation (this feature)

```text
specs/009-tareas-listas-subtareas/
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
│   │   ├── ticket.py                 # + parent_task_id, list_id; retira TASK_STATUSES/FIELD_LOCKS de 4 estados
│   │   └── task_list.py              # NUEVO: entidad TaskList (id, project_id, name, position)
│   ├── fsm/
│   │   └── task_fsm.py               # RETIRADO (reemplazado por transición libre en ticket_service)
│   ├── services/
│   │   ├── ticket_service.py         # + free_transition_task() (estado libre + comentario obligatorio)
│   │   ├── task_list_service.py      # NUEVO: crear/listar Listas, validar pertenencia a Proyecto
│   │   └── work_session_service.py   # assert_ticket_ownership(): + chequeo por creador (FR-001)
│   └── errors.py
├── infra/
│   ├── models/
│   │   ├── ticket_model.py           # + parent_task_id, list_id (FK task_lists.id)
│   │   └── task_list_model.py        # NUEVO
│   ├── repositories/
│   │   ├── ticket_repo.py            # + list_subtasks(parent_task_id), filtro por list_id
│   │   └── task_list_repo.py         # NUEVO
│   └── migrations/versions/
│       └── 024_task_lists_and_subtasks.py   # NUEVO: tabla task_lists, parent_task_id, migración
│                                              # de datos (list_name→task_lists, estados 4→10)
└── api/routes/
    ├── tickets.py                    # retira /task-transition; + PATCH /{id}/status (libre+comentario)
    └── task_lists.py                 # NUEVO: CRUD de Listas dentro de un Proyecto

frontend/src/
├── types/
│   ├── ticket.ts                     # retira TaskTrigger/TASK_TRIGGER_LABELS; + parent_task_id, list_id
│   └── taskList.ts                   # NUEVO
├── services/
│   ├── ticketService.ts              # retira taskTransition(); + changeStatus(id, status, comment)
│   └── taskListService.ts            # NUEVO
├── components/tickets/
│   ├── TaskActions.tsx               # RETIRADO (reemplazado por selector de estado + comentario)
│   ├── TaskStatusChanger.tsx         # NUEVO: dropdown de 10 estados + modal de comentario obligatorio
│   └── SubtaskList.tsx               # NUEVO: lista de Subtareas anidadas bajo una Tarea
├── pages/
│   ├── TicketDetailPage.tsx          # des-oculta clasificación para isTask; usa TaskStatusChanger + SubtaskList
│   ├── KanbanPage.tsx                # tarjetas con tag Ticket/Tarea; drag de Tarea usa transición libre
│   ├── MyTasksPage.tsx               # agrupa por Lista real (list_id) en vez de list_name texto libre
│   └── ProjectListsPage.tsx          # NUEVO: sidebar de Listas de un Proyecto (docs/mockup.html, id="s-lista")
└── config/
    └── kanbanTransitions.ts          # sin cambios para Ticket; Tarea no pasa por esta tabla (libre)
```

**Structure Decision**: Web application ya existente (`backend/` Flask + `frontend/` React) —
esta spec no introduce proyectos nuevos, solo extiende los módulos de dominio/infra/api de
Ticket ya presentes desde la Fase 1 y agrega el módulo paralelo `task_lists` (mismo patrón que
`client_contacts` de la spec `007`: entidad + modelo + repo + rutas propias, acoplado a
`projects` en vez de a `clients`).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| Comentario de cambio de estado de Tarea sin tipo estructurado (excepción al Principio VI) | El usuario pidió explícitamente transición libre "sin restricciones"; forzar un tipo por transición reintroduciría la secuencia que se quiere evitar | Reutilizar los 10 tipos de comentario del Ticket: descartado — esos tipos están atados 1:1 a transiciones fijas de la FSM del Ticket (`confirmacion_atencion`, `solicitud_cierre`, etc.), que no tienen sentido para "cualquier estado a cualquier estado" |
