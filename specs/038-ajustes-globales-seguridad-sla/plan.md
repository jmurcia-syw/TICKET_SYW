# Implementation Plan: Ajustes Globales — Seguridad/Permisos, Notificaciones, Motor de SLA, Bugs de UI y Rendimiento

**Branch**: `038-ajustes-globales-seguridad-sla` | **Date**: 2026-08-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/038-ajustes-globales-seguridad-sla/spec.md`

## Summary

Paquete de 6 frentes independientes sobre el sistema ya existente (sin dependencias nuevas):
(1) acotar por rol lo que un Resolutor ve por defecto (Kanban/Listas/Mis Tareas filtrados a
"asignado a mí", vista global de Tickets solo Coordinador/Admin, Calendario propio, catálogos
maestros no precargados) + menú lateral colapsable; (2) corregir el motor de SLA (Contacto corre
hasta "En Análisis", Resolución corre hasta "Cerrado" en vez de congelarse en "Resuelto") y
generar una entrada de auditoría inicial al crear Ticket/Tarea; (3) cascada Cliente→Proyecto y
3 campos obligatorios/opcionales en formularios; (4) reparar "Copiar Contraseña" y agregar un
correo de bienvenida HTML reutilizando el mecanismo SMTP + token de reseteo ya existente (spec
`003`); (5) diagnosticar y corregir el parpadeo generalizado de UI y el bug de credenciales
cruzadas entre pestañas de Accesos del Cliente; (6) reducir peticiones/renders redundantes en
"Ver detalle de cliente". Todo el trabajo respeta las 3 capas existentes (Capa 1 dominio para
SLA/permisos de negocio, Capa 2 repositorios para el filtrado por rol, Capa 3 rutas/componentes) y
no agrega tablas nuevas salvo un permiso RBAC nuevo (`tickets:view_assigned`).

## Technical Context

**Language/Version**: Python 3.12 (backend) + TypeScript 5 strict (frontend, React 19) — stack existente, sin cambios

**Primary Dependencies**: Flask-RESTX, `python-transitions`, SQLAlchemy 2.x + Alembic, Flask-JWT-Extended, Jinja2 (ya viene con Flask, se reutiliza para la plantilla HTML del correo de bienvenida — sin dependencia nueva), Ant Design 5 (`Layout.Sider` ya soporta modo `collapsible`), Zustand, `date-fns`, Axios — todo ya aprobado en la Constitución (Principio V), **cero dependencias nuevas**

**Storage**: PostgreSQL 16 existente. Un permiso RBAC nuevo (`tickets:view_assigned`) vía migración Alembic; la entrada de auditoría inicial reutiliza la tabla `ticket_status_transitions` ya existente (sin tabla ni columna nueva) con un valor sentinel en `from_status`

**Testing**: `pytest` (backend, acotado a los archivos tocados por Principio VII — máx. 5-10 registros mock por test nuevo) + `tsc -b` (frontend, typecheck estricto). Sin ejecutar la suite completa

**Target Platform**: Docker Compose on-premise ya existente (`sywork_backend`, `sywork_frontend`, `sywork_db`, `sywork_redis`, `sywork_worker`)

**Project Type**: Web application (backend Flask + frontend React, estructura ya establecida)

**Performance Goals**: Reducción perceptible del tiempo de carga de "Ver detalle de cliente" (SC-010); eliminación de parpadeo visible durante 10s de scroll/interacción continua (SC-009) — ambos son metas cualitativas de UX, no hay SLA de latencia numérico definido por el usuario

**Constraints**: Cero dependencias nuevas (Principio V); SLA y RBAC permanecen en Capa 1/Capa 2 sin imports de Flask/SQLAlchemy en el dominio (Principio I/II); ningún test nuevo debe insertar más de 5-10 registros (Principio VII); prohibido ejecutar la suite completa de pytest (Principio VII)

**Scale/Scope**: 6 user stories independientes (spec.md), ~30 requisitos funcionales, sin cambio de escala de datos (mismo volumen de tickets/usuarios/clientes ya operando)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Chequeo | Estado |
|-----------|---------|--------|
| I. API-First y Dominio Primero | El único campo de API nuevo (`notify` en `POST /api/users`) se documenta en `contracts/` antes de tocar código; la lógica de SLA/permisos vive en `backend/domain/`, no en rutas Flask ni componentes React | ✅ PASS |
| II. Clean Architecture 3 capas | `SLA_PHASE_FOR_STATE`/`STATE_COUNTS_FOR_SLA` (Capa 1) cambian sin imports externos; el filtrado "asignado a mí" se resuelve en el repositorio (Capa 2) a partir de un permiso resuelto en la ruta (Capa 3), mismo patrón ya usado para `tickets:view_own`; el envío de correo vive en `backend/infra/email/` (Capa 2), nunca en el dominio | ✅ PASS |
| III. Tipado estricto | Sin `any` nuevo en frontend; tipos de `ticket.ts`/`user.ts` se amplían de forma aditiva (campo `notify` opcional, campo `parent`/`subtasks` ya existentes no cambian) | ✅ PASS |
| IV. Seguridad en profundidad | El filtrado "solo asignado a mí" para Resolutor se implementa a nivel de aplicación (repositorio + permiso RBAC), **no** a nivel de RLS — ver research.md Decisión 1 para la justificación de por qué no se toca la política RLS de `tickets` (migración `012`, deliberadamente permisiva para que los resolutores usen el historial como base de conocimiento). El correo de bienvenida reutiliza el mismo token/expiración de 30 min ya usado en el reseteo de contraseña (spec `003`), sin nuevo mecanismo de secretos | ✅ PASS (con nota documentada, no es una violación — ver research.md) |
| V. Gobernanza de librerías | Cero dependencias nuevas — confirmado arriba en Technical Context | ✅ PASS |
| VI. AI-Native | La entrada de auditoría inicial refuerza el Gold Standard Dataset (más contexto de línea de tiempo completa por ticket, desde su creación); no se altera el contrato de `/assign` ni de comentarios estructurados | ✅ PASS |
| VII. Alcance de sesión / tokens | Cambios acotados a los archivos de cada user story (ver Project Structure); tests nuevos ≤ 5-10 registros; no se corre la suite completa | ✅ PASS |

No hay violaciones que requieran la tabla de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/038-ajustes-globales-seguridad-sla/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── api-changes.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   ├── fsm/ticket_fsm.py                 # US2: SLA_PHASE_FOR_STATE / STATE_COUNTS_FOR_SLA
│   └── services/
│       ├── sla_service.py                # US2: congelamiento Contacto/Resolución
│       ├── ticket_service.py             # US2: entrada de auditoría inicial al crear
│       └── work_session_service.py       # US4: `note` obligatorio
├── infra/
│   ├── email/mailer.py                   # US5: plantilla HTML de bienvenida (nueva función)
│   ├── models/ticket_model.py            # US2: sin cambio de esquema (sentinel en from_status)
│   ├── repositories/ticket_repo.py       # US1: filtro "asignado a mí" (tickets:view_assigned)
│   └── migrations/versions/052_*.py      # US1: permiso `tickets:view_assigned` para Resolutor
└── api/routes/
    ├── tickets.py                        # US1: enforcement de view_assigned; US2: 404 patrón existente
    ├── users.py                          # US5: campo `notify` en creación de usuario
    └── calendar.py                       # US1: acotar a "propio" para Resolutor

frontend/src/
├── components/common/
│   ├── AuthLayout.tsx / Layout principal # US1: Sider colapsable
│   └── ...                               # US3: diagnóstico del parpadeo generalizado
├── pages/
│   ├── KanbanPage.tsx, MyTasksPage.tsx   # US1: filtro "Asignado a mí" por defecto (Resolutor)
│   ├── TicketsPage.tsx                   # US1/US4: ruta restringida; cascada Cliente→Proyecto
│   ├── ClientsPage.tsx                   # US3: fix credenciales cruzadas; US6: lazy load pestañas
│   ├── TeamPage.tsx                      # US5: fix "Copiar Contraseña" + checkbox "Notificar"
│   ├── SlaRulesPage.tsx / ReportsPage.tsx # US4: cascada Cliente→Proyecto en filtros
│   └── CalendarPage.tsx                  # US1: vista acotada a "propio" para Resolutor
├── components/worksessions/WorkSessionForm.tsx  # US4: campo `note` obligatorio
└── services/                             # userService (notify), ticketService (sin contrato nuevo)
```

**Structure Decision**: Se reutiliza la estructura de 3 capas ya establecida (`backend/domain` →
`backend/infra` → `backend/api` + `frontend/src`). No se crean módulos ni directorios nuevos; el
único archivo nuevo de infraestructura es la migración Alembic `052_*` y la función de envío de
correo de bienvenida dentro de `backend/infra/email/mailer.py` (mismo archivo ya usado para el
reseteo de contraseña).

## Complexity Tracking

*Sin violaciones — tabla no aplica.*
