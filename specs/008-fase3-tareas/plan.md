# Implementation Plan: Fase 3 — Manejo de Tareas

**Branch**: `develp_Jp` (sin rama dedicada por feature en este repo) | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/008-fase3-tareas/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Habilitar la creación y gestión de "Tareas" reutilizando la tabla `tickets` ya existente,
distinguidas por `record_type_id = 'Tarea'` (catálogo sembrado desde la Fase 1, hoy bloqueado en
`TicketService.resolve_record_type`). Una Tarea usa un formulario reducido (sin clasificación de
incidente), sigue una FSM propia y simple (`task_fsm.py`: Pendiente → En progreso → Hecha /
Cancelada, con reapertura), se agrupa por "lista" (campo de texto libre) en "Mis Tareas", y puede
vincularse a un "Registro relacionado" (`related_ticket_id`, ya existente desde la Fase 1 pero
nunca expuesto en la UI). De paso, corrige un gap real descubierto al planificar: ni `POST` ni
`PATCH /api/tickets` validaban hoy que `related_ticket_id` perteneciera al mismo Cliente — el fix
aplica tanto a Tickets como a Tareas.

## Technical Context

**Language/Version**: Python 3.12 + Flask (backend), TypeScript 5 estricto + React 19 (frontend) —
sin cambios de versión.

**Primary Dependencies**: `python-transitions` (FSM nueva `task_fsm.py`, misma librería que
`ticket_fsm.py` — sin dependencia nueva), SQLAlchemy + Alembic (1 migración), Ant Design 5
(`Segmented`/`Select` en frontend). Ninguna dependencia nueva (Principio V).

**Storage**: PostgreSQL 16. 1 columna nueva `tickets.list_name` (TEXT, nullable) + ampliación del
CHECK `ck_tickets_status` con 3 valores nuevos (`pendiente`, `en_progreso`, `hecha`) — reutiliza
`cancelado` ya existente. Sin tabla nueva, sin cambios de RLS (mismo alcance de columnas ya
cubierto por `012_tickets_rls.py`).

**Testing**: Backend — pytest, tests nuevos dirigidos exclusivamente a lo que cambia
(`test_task_fsm.py`, `test_ticket_service_tasks.py`, `test_tickets_tasks.py`); mismo criterio ya
aplicado en la spec `007` de no correr la suite completa durante el desarrollo de cada tarea.
Frontend — sin suite automatizada configurada; validación con `npx tsc -b` + `quickstart.md`
manual contra Docker real.

**Target Platform**: Web (misma SPA + API REST ya existentes).

**Project Type**: Web application (`backend/` + `frontend/`) — toca ambos lados.

**Performance Goals**: Sin objetivo nuevo. El agrupamiento por "lista" en "Mis Tareas" se resuelve
en memoria sobre el array ya paginado (volumen esperado por usuario bajo) — sin `GROUP BY` nuevo
en servidor.

**Constraints**: Una Tarea NO DEBE pasar por ningún paso del ciclo de vida de Ticket (comentarios
tipificados, tipo de resolución) — su transición de estado es una acción directa sin comentario
obligatorio (SC-006). El rol Encargado permanece sin poder crear Tareas en ningún punto del flujo
(FR-008).

**Scale/Scope**: 1 migración nueva; 1 FSM nueva e independiente; 6 archivos backend
tocados/nuevos (dominio + infra + API); 3 archivos de test nuevos; 4-5 pantallas/componentes
frontend tocados (`TicketsPage`, `TicketDetailPage`, `MyTasksPage`, `TicketStatusTag`, `theme.ts`,
tipos y servicio de tickets).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (API-First / Dominio primero)**: Las reglas de la Tarea (qué campos son
  obligatorios, qué transiciones son válidas, mismo-cliente del "Registro relacionado") viven en
  `backend/domain/services/ticket_service.py` y `backend/domain/fsm/task_fsm.py`, no en rutas ni
  en el frontend. El nuevo endpoint `POST /api/tickets/{id}/task-transition` es un endpoint de
  backend independiente, análogo a `/cancel`/`/close` ya existentes — no acoplado a una pantalla
  concreta. **PASS**.
- **Principio II (Clean Architecture 3 capas)**: `task_fsm.py` y la extensión de `ticket.py`
  (Capa 1, sin imports externos); columna nueva + repositorio en Capa 2
  (`ticket_model.py`, `ticket_repo.py`); serialización y endpoint nuevo en Capa 3
  (`api/routes/tickets.py`). Frontend: `services/ticketService.ts` para la llamada nueva,
  `pages/` solo orquesta y renderiza. **PASS**.
- **Principio III (Tipado estricto)**: TypeScript strict sin `any` (unión `TicketStatus` extendida
  con los 4 estados de Tarea); type hints en las funciones Python nuevas/tocadas. **PASS**.
- **Principio IV (Seguridad en profundidad)**: La regla "una Tarea no puede crearse desde el
  autoservicio de un Encargado" se aplica en el backend (el branch `is_encargado` de
  `POST /api/tickets` nunca lee `record_type_id`), no solo ocultando el control en el frontend.
  El nuevo endpoint de transición exige el mismo permiso `tickets:edit` ya vigente — no se
  introduce una superficie de permisos nueva. RLS de `tickets` no cambia (columna nueva no amplía
  ni reduce qué filas ve cada rol). **PASS**.
- **Principio V (Gobernanza de librerías)**: Sin dependencias nuevas — `task_fsm.py` reutiliza
  `python-transitions`, ya aprobado y en uso por `ticket_fsm.py`. **PASS**.
- **Principio VI (AI-Native)**: No aplica de forma directa — la transición de una Tarea no es una
  acción de Triage/asignación (no genera Gold Standard Dataset); es equivalente en naturaleza a
  otras acciones de ciclo de vida ya existentes (`/cancel`, `/testing`) que tampoco lo generan.
  **PASS**.

**Resultado**: Sin violaciones. No se requiere entrada en "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/008-fase3-tareas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command) — delta de tickets
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

Proyecto "Web application" ya establecido (`backend/` + `frontend/`). Archivos concretos que toca
esta funcionalidad:

```text
backend/
├── infra/migrations/versions/
│   └── 023_tasks_status_list.py          # NUEVO: columna list_name + CHECK de status ampliado
├── domain/
│   ├── entities/ticket.py                # MODIFICADO: STATUS_LABELS + FIELD_LOCKS para los 4
│   │                                       # estados de Tarea
│   ├── fsm/
│   │   └── task_fsm.py                   # NUEVO: FSM independiente (start/complete/cancel/reopen)
│   └── services/ticket_service.py        # MODIFICADO: resolve_record_type ya no rechaza "Tarea";
│                                           # validate_create/validate_patch validan mismo-cliente
│                                           # del related_ticket_id (FR-005, cierra gap Fase 1);
│                                           # PATCHABLE_FIELDS += list_name
├── infra/
│   ├── models/ticket_model.py            # MODIFICADO: columna list_name + to_entity()
│   └── repositories/ticket_repo.py       # MODIFICADO: create() incluye list_name;
│                                           # list_related_from() nuevo (relación inversa FR-006)
├── api/routes/
│   └── tickets.py                        # MODIFICADO: swagger + branch de creación de Tarea
│                                           # (defaults silenciosos de clasificación); nuevo
│                                           # endpoint POST /{id}/task-transition;
│                                           # _ticket_detail() agrega list_name + related_from
└── tests/
    ├── domain/
    │   ├── test_task_fsm.py                      # NUEVO
    │   └── test_ticket_service_tasks.py          # NUEVO
    └── api/test_tickets_tasks.py                 # NUEVO

frontend/src/
├── theme.ts                 # MODIFICADO: TICKET_STATUS_CHIP += 4 estados de Tarea
├── types/ticket.ts           # MODIFICADO: TicketStatus += 4 literales; STATUS_LABELS extendido;
│                              # TicketDetail += list_name/related_from; TicketFormData += list_name
├── services/ticketService.ts # MODIFICADO: taskTransition(id, trigger) nuevo
├── components/tickets/
│   └── TicketStatusTag.tsx   # Sin cambios de lógica — hereda los 4 estados nuevos vía el mapa ya
│                              # existente (theme.ts + STATUS_LABELS)
└── pages/
    ├── TicketsPage.tsx        # MODIFICADO: control Ticket/Tarea; oculta clasificación de
    │                          # incidente y muestra "Lista" cuando es Tarea (sin tocar el resto
    │                          # del formulario ya construido en Fases 1/2.2)
    ├── TicketDetailPage.tsx   # MODIFICADO: para una Tarea, controles de transición (Iniciar/
    │                          # Completar/Cancelar/Reabrir) en vez de comentarios tipificados;
    │                          # campo "Lista" editable; sección "Registro relacionado" +
    │                          # "Referenciado por" (related_from)
    └── MyTasksPage.tsx        # MODIFICADO: agrupa por list_name ("Sin lista" por defecto),
                               # retira el texto "el agrupamiento por listas llega en Fase 3"
```

**Structure Decision**: Se mantiene la estructura ya vigente (Capa 1/2/3 en backend;
`pages/services/types` en frontend). Única carpeta nueva: `backend/domain/fsm/` ya existe
(contiene `ticket_fsm.py`) — solo se agrega un archivo (`task_fsm.py`), no una carpeta. Sin
namespace de rutas nuevo (`task-transition` cuelga de `/api/tickets/{id}`, mismo namespace
`tickets` ya existente).

## Complexity Tracking

*Sin violaciones de la Constitution Check — tabla no aplica.*
