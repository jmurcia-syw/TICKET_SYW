# Implementation Plan: Calendarios Multi-Zona Horaria, Festivos, Vacaciones (RRHH) y Disponibilidad

**Branch**: `020-calendarios-vacaciones-disponibilidad` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/020-calendarios-vacaciones-disponibilidad/spec.md`

## Summary

Fase 5 del roadmap SDD V3 ("Asignación por disponibilidad + calendarios por país/recurso +
excepciones RRHH"). Se agregan `timezone`/`country` a Cliente y `timezone` a Recurso (que ya
tiene `calendar_country`), un catálogo de festivos por país, un horario laboral semanal por
recurso, un nuevo rol RRHH con un flujo de solicitudes de ausencia (vacaciones, incapacidad
médica, permiso personal, otro) con doble aprobación independiente (Jefe directo vía `manager_id`
ya existente + RRHH) y adjuntos opcionales, dos calendarios visuales (Cliente/Equipo, festivos
resaltados) con una librería nueva (FullCalendar, aprobada en `research.md` Decisión 1), y un
endpoint de disponibilidad de solo lectura que el panel de asignación de tickets consulta para
mostrar una alerta visual — sin bloquear nunca la asignación (FR-015).

## Technical Context

**Language/Version**: Python 3.12 (Flask, backend) · TypeScript 5.6 strict + React 19 (frontend)

**Primary Dependencies**: Flask-RESTX, SQLAlchemy + Alembic (existentes, sin cambios). **Nueva
dependencia frontend aprobada aquí** (Principio V, ver `research.md` Decisión 1):
`@fullcalendar/core`, `@fullcalendar/react`, `@fullcalendar/daygrid`, `@fullcalendar/timegrid`.
Reutiliza `backend/infra/storage/attachments.py` (ya generalizado desde spec 018) para adjuntos
de solicitudes de ausencia. Reutiliza el catálogo de países de `react-phone-number-input` (ya
aprobado) para los selectores de país de Cliente/Recurso.

**Storage**: PostgreSQL 16 — 4 tablas nuevas (`holidays`, `work_schedules`,
`catalog_absence_types`, `absence_requests`, `absence_request_attachments` — 5 en total) + 3
columnas nuevas (`clients.timezone`, `clients.country`, `resources.timezone`). RLS habilitado
solo en `absence_requests`/`absence_request_attachments` (datos de salud/HR sensibles); ver
Decisión 6 de `research.md`.

**Testing**: pytest en backend, ultra-limitado por Principio VII (≤10 registros por test, solo el
módulo/servicio tocado: `absence_service`, `availability_service`, endpoints nuevos). No hay
framework de tests de frontend configurado en este repo (verificación manual en navegador vía
Docker, igual que specs previas).

**Target Platform**: Web app en Docker Compose on-premise — sin cambios de infraestructura.

**Project Type**: Web application (monorepo `backend/` + `frontend/`, Option 2).

**Performance Goals**: SC-001 — el panel de asignación muestra disponibilidad de cada resolutor
candidato en <2s sin recargar la página (uso interno, decenas de recursos por consulta).

**Constraints**: FR-015 (NUNCA bloquear la asignación por disponibilidad) — el endpoint
`POST /api/tickets/{id}/assign` no se modifica (Decisión 7 de `research.md`, protege el
Principio VI sobre ese endpoint). Alcance de esta sesión limitado a: migraciones/modelos de
calendarios-países-festivos-vacaciones, controladores de asignación (incluye el nuevo endpoint de
disponibilidad) y las vistas correspondientes — sin refactors fuera de ese alcance (directriz
explícita del usuario + Principio VII).

**Scale/Scope**: Equipo interno de decenas de recursos, festivos de un puñado de países donde hay
Clientes/Recursos activos hoy. No toca Kanban, SLA ni el motor FSM.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|---|---|---|
| I. API-First y Dominio Primero | Todo endpoint nuevo se documenta en Swagger (Flask-RESTX) antes del handler. La regla de disponibilidad (orden ausencia > festivo > horario) y la regla de doble aprobación viven en `backend/domain/services/availability_service.py` y `absence_service.py` (Capa 1, sin imports de Flask/SQLAlchemy). `POST /api/tickets/{id}/assign` permanece intacto y agnóstico al caller. | PASS |
| II. Clean Architecture (3 capas) | Entidades nuevas en `backend/domain/entities/calendar.py`; modelos SQLAlchemy en `backend/infra/models/calendar_model.py` (+ extensión de `client_model.py`/`resource_model.py`/`catalog_model.py`); repositorios nuevos en `backend/infra/repositories/calendar_repo.py`; rutas Flask en `backend/api/routes/calendar.py` solo orquestan, sin lógica de negocio. | PASS |
| III. Tipado estricto | `frontend/src/types/calendar.ts` nuevo, sin `any`. Type hints en `availability_service.py`/`absence_service.py` y en las nuevas entidades de dominio. | PASS |
| IV. Seguridad en profundidad | RLS habilitado en `absence_requests`/`absence_request_attachments` (datos de salud/HR) — ver Decisión 6 de `research.md`. `holidays`/`work_schedules` sin RLS (dato de referencia, mismo criterio que catálogos existentes). Sin credenciales ni secretos nuevos en el frontend. | PASS |
| V. Gobernanza de librerías | **Nueva dependencia**: FullCalendar (`@fullcalendar/core`, `react`, `daygrid`, `timegrid`). Aprobación documentada en este plan y en `research.md` Decisión 1, siguiendo el proceso exigido ("aprobación previa documentada en el documento de Planificación de la fase"). Ninguna otra dependencia nueva. | PASS (con alta documentada) |
| VI. AI-Native | El endpoint de disponibilidad es de solo lectura y no altera `POST /api/tickets/{id}/assign`, que sigue siendo agnóstico al caller (humano o futuro Triage Agent) — la disponibilidad queda disponible como señal adicional para un futuro AI Dispatcher sin acoplar la UI al endpoint de acción. | PASS |
| VII. Alcance de sesión / testing ultra-limitado | Cambios acotados a: modelos/migraciones de calendarios-países-festivos-vacaciones, el controlador de disponibilidad/asignación, y las vistas de Cliente/Recurso/Calendario/Ausencias/AssignModal. Tests backend nuevos ≤10 registros de prueba, sin correr la suite completa. | PASS |

**Resultado**: Sin violaciones. No se requiere `Complexity Tracking` — la única adición de alcance
(FullCalendar) está cubierta por el proceso de aprobación del Principio V, documentado arriba.

## Project Structure

### Documentation (this feature)

```text
specs/020-calendarios-vacaciones-disponibilidad/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/            # Fase 1
│   └── calendar-disponibilidad.md
└── tasks.md              # Fase 2 (/speckit-tasks, no generado por /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   ├── entities/
│   │   ├── calendar.py                # NUEVO: Holiday, WorkScheduleSlot, AbsenceRequest,
│   │   │                               #        AbsenceRequestAttachment, Availability
│   │   ├── client.py                  # + timezone, country en Client
│   │   └── resource.py                # + timezone en Resource
│   └── services/
│       ├── availability_service.py    # NUEVO: cálculo puro de disponibilidad (FR-013/016)
│       └── absence_service.py         # NUEVO: validación de solicitudes + overall_status (FR-009/011/012)
├── infra/
│   ├── models/
│   │   ├── calendar_model.py          # NUEVO: HolidayModel, WorkScheduleModel,
│   │   │                               #        AbsenceRequestModel, AbsenceRequestAttachmentModel
│   │   ├── catalog_model.py           # + AbsenceTypeCatalogModel, CATALOG_MODELS["absence-types"]
│   │   ├── client_model.py            # + timezone, country
│   │   └── resource_model.py          # + timezone
│   ├── repositories/
│   │   ├── calendar_repo.py           # NUEVO: HolidayRepository, WorkScheduleRepository,
│   │   │                               #        AbsenceRequestRepository
│   │   ├── client_repo.py             # + timezone/country en create/update
│   │   └── resource_repo.py           # + timezone en update/perfil
│   └── migrations/versions/
│       ├── 034_client_resource_timezone.py
│       ├── 035_holidays_work_schedules.py
│       ├── 036_catalog_absence_types.py
│       ├── 037_absence_requests.py
│       ├── 038_absence_requests_rls.py
│       └── 039_rrhh_role_permissions.py
└── api/
    └── routes/
        ├── calendar.py                 # NUEVO: /holidays, /resources/{id}/work-schedule,
        │                                #        /absence-requests(/...), /resources/availability
        ├── clients.py                  # + timezone/country en body/respuesta
        └── resources.py                # + timezone en _PROFILE_TEXT_FIELDS/_resource_out

frontend/
├── src/
│   ├── types/
│   │   ├── calendar.ts                 # NUEVO: Holiday, WorkScheduleSlot, AbsenceRequest,
│   │   │                                #        AbsenceRequestAttachment, Availability
│   │   ├── client.ts                   # + timezone, country
│   │   └── resource.ts                 # + timezone
│   ├── services/
│   │   └── calendarService.ts          # NUEVO: llamadas a los endpoints de calendar.py
│   ├── components/
│   │   ├── resources/
│   │   │   └── WorkScheduleDrawer.tsx  # NUEVO: editor de franjas semanales por recurso
│   │   └── tickets/
│   │       └── AssignModal.tsx         # + badge de disponibilidad por resolutor (US1)
│   ├── pages/
│   │   ├── ClientsPage.tsx             # + campos timezone/country en el formulario
│   │   ├── TeamPage.tsx                # + campo timezone + botón "Horario laboral"
│   │   ├── CalendarPage.tsx            # NUEVO: tabs "Cliente" / "Equipo" (FullCalendar)
│   │   └── AbsenceRequestsPage.tsx     # NUEVO: "Mis solicitudes" + panel de aprobación (Jefe/RRHH)
│   ├── App.tsx                         # + rutas /calendar y /absence-requests
│   └── config/
│       └── navigation.tsx              # + entradas de menú "Calendarios" y "Vacaciones y Permisos"
└── package.json                        # + @fullcalendar/{core,react,daygrid,timegrid}
```

**Structure Decision**: Se mantiene el layout de repo existente (Clean Architecture 3 capas en
`backend/`, `pages/services/types/components` en `frontend/`). No se crean paquetes de alto nivel
nuevos — se sigue el mismo patrón de extensión ya validado en specs 014 (SLA) y 018 (Cliente
Accesos): entidades/modelos/repos nuevos junto a los existentes de su dominio, rutas nuevas en un
namespace propio (`calendar.py`) cuando el concepto no encaja en un archivo de rutas existente, y
páginas nuevas registradas en el router y el menú igual que `AssignmentPanelPage`/
`RolesPermissionsPage`.

## Complexity Tracking

*No aplica — Constitution Check sin violaciones. La única adición de alcance (dependencia
FullCalendar) está resuelta como una aprobación documentada del Principio V, no como una
excepción/violación.*
