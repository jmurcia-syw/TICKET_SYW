# Implementation Plan: Festivos sincronizados por API, categorización visual y cumpleaños en el Calendario

**Branch**: `021-festivos-api-cumpleanos` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/021-festivos-api-cumpleanos/spec.md`

## Summary

Amplía el módulo de Calendarios (spec 020) para que los festivos oficiales por país se
mantengan al día automáticamente vía una API pública de festivos (`date.nager.at`), en vez de
depender de carga manual — corrige de inmediato el vacío detectado en Colombia (faltaba el 20 de
julio y el resto del calendario Ley Emiliani). Agrega una categoría (`Oficial` vs.
`Regional/Religioso`) para distinguir visualmente festivos nacionales de celebraciones locales
que no afectan disponibilidad, y muestra automáticamente los cumpleaños de cada Recurso (ya
existente vía `birth_date`) como evento anual en la pestaña Equipo del calendario. Sin cambios al
endpoint `POST /api/tickets/{id}/assign` ni al resto del alcance de spec 020.

## Technical Context

**Language/Version**: Python 3.12 (Flask, backend) · TypeScript 5.6 strict + React 19 (frontend)

**Primary Dependencies**: `requests` (backend) — ya presente en `requirements.txt`, primera
materialización real de uso en este código; **nueva integración externa aprobada aquí**
(Principio V, ver `research.md` Decisión 1): API pública `date.nager.at`, sin API key. Reutiliza
Celery + Redis (ya aprobado, spec 014) para la tarea periódica de sincronización — sin nueva
dependencia de scheduling. Frontend: sin librerías nuevas (se descarta `@fullcalendar/rrule`, ver
`research.md` Decisión 7); reutiliza FullCalendar ya aprobado en spec 020.

**Storage**: PostgreSQL 16 — 2 columnas nuevas en `holidays` (`category`, `source`) + 1 tabla
nueva (`holiday_sync_status`, sin RLS). Sin cambios a `absence_requests`/`work_schedules`/otras
tablas de spec 020.

**Testing**: pytest en backend, ultra-limitado por Principio VII (≤10 registros por test) —
casos nuevos en `test_availability_service.py` (filtro por categoría) y un test unitario nuevo
para la lógica de decisión de sincronización (`holiday_sync_service.py`, si se extrae como
función pura) o del repositorio de sync status. La llamada HTTP real a Nager.Date se mockea en
tests (sin dependencia de red en CI/pruebas locales). Sin framework de tests de frontend
configurado (verificación manual en navegador vía Docker, igual que specs previas).

**Target Platform**: Web app en Docker Compose on-premise — sin cambios de infraestructura; el
contenedor `sywork_worker` (ya existente) gana una tarea periódica nueva.

**Project Type**: Web application (monorepo `backend/` + `frontend/`, Option 2).

**Performance Goals**: SC-001/SC-002 — el listado de festivos de un país recién configurado
queda disponible en la misma respuesta HTTP en la que se solicita por primera vez (intento
inline con timeout corto, research.md Decisión 2), sin que el usuario tenga que refrescar la
página más de una vez.

**Constraints**: FR-003 (una falla de la fuente externa NUNCA debe bloquear otra funcionalidad
del sistema) — el intento inline usa timeout corto y captura cualquier excepción de red sin
propagarla como error HTTP; la tarea periódica reintenta por su cuenta. FR-007 (solo festivos
"Oficial" afectan disponibilidad) — cambio aislado a `availability_service.py`, sin tocar
`POST /api/tickets/{id}/assign`. Alcance de esta sesión limitado a: la tabla/entidad `holidays` y
su categorización, la nueva tabla de estado de sincronización, la tarea Celery de sincronización,
y las vistas de calendario correspondientes — sin refactors fuera de ese alcance.

**Scale/Scope**: Países realmente en uso hoy por Clientes/Recursos activos (actualmente Colombia
y México); la sincronización no intenta cubrir los ~200 países soportados por la fuente externa
de una sola vez.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|---|---|---|
| I. API-First y Dominio Primero | El nuevo endpoint `PATCH /api/holidays/{id}` se documenta en Swagger antes del handler. El filtro "solo festivos Oficial afectan disponibilidad" vive en `backend/domain/services/availability_service.py` (Capa 1, función pura ya testeada). `POST /api/tickets/{id}/assign` permanece intacto. | PASS |
| II. Clean Architecture (3 capas) | La llamada HTTP a Nager.Date vive en infraestructura (`backend/infra/external/holiday_api_client.py`, nuevo), nunca en el dominio. La tarea Celery (`backend/workers/holiday_sync_tasks.py`) orquesta repos + cliente externo, igual patrón que `sla_tasks.py`. El dominio solo decide "qué categoría cuenta para disponibilidad", sin saber de HTTP ni de Nager.Date. | PASS |
| III. Tipado estricto | Sin `any` nuevo en frontend (`Holiday` type se extiende con `category`/`source` como union types literales). Type hints en el cliente HTTP y en la tarea Celery. | PASS |
| IV. Seguridad en profundidad | Sin credenciales nuevas (Nager.Date no requiere API key — evita el problema de secretos para este dato público). `holiday_sync_status` sin RLS, mismo criterio que `holidays`/`work_schedules` (dato no sensible). | PASS |
| V. Gobernanza de librerías | **Nueva integración externa**: API pública `date.nager.at`, consumida con `requests` (ya presente en `requirements.txt`, sin línea nueva de dependencia). Aprobación documentada en este plan y en `research.md` Decisión 1. Se descarta explícitamente `@fullcalendar/rrule` (Decisión 7) para no sumar una dependencia frontend innecesaria. | PASS (con alta documentada) |
| VI. AI-Native | Sin impacto — no se toca ningún endpoint de acción crítica (`/assign`, `/status`). La categorización de festivos es un dato adicional de contexto, no una decisión que la IA deba tomar en esta fase. | PASS |
| VII. Alcance de sesión / testing ultra-limitado | Cambios acotados a: columnas/tabla nuevas de `holidays`, el cliente HTTP externo, la tarea Celery de sincronización, el filtro de disponibilidad por categoría, y las vistas de Calendario (color por categoría + cumpleaños). Tests backend nuevos ≤10 registros de prueba, HTTP externo mockeado, sin correr la suite completa. | PASS |

**Resultado**: Sin violaciones. No se requiere `Complexity Tracking` — la única adición de alcance
(integración con Nager.Date) está cubierta por el proceso de aprobación del Principio V,
documentado arriba, y no introduce ninguna dependencia nueva en `requirements.txt`/`package.json`.

## Project Structure

### Documentation (this feature)

```text
specs/021-festivos-api-cumpleanos/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/            # Fase 1
│   └── festivos-api-cumpleanos.md
└── tasks.md              # Fase 2 (/speckit-tasks, no generado por /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   ├── entities/
│   │   └── calendar.py                 # + category, source en Holiday
│   └── services/
│       └── availability_service.py     # + filtro category == "oficial" en _has_holiday_today
├── infra/
│   ├── external/
│   │   └── holiday_api_client.py       # NUEVO: cliente HTTP para date.nager.at (Capa 2)
│   ├── models/
│   │   └── calendar_model.py           # + category, source en HolidayModel;
│   │                                    #   NUEVO: HolidaySyncStatusModel
│   ├── repositories/
│   │   └── calendar_repo.py            # + HolidayRepository: filtro por categoría,
│   │                                    #   marcar source="manual" en writes;
│   │                                    #   NUEVO: HolidaySyncStatusRepository
│   ├── migrations/versions/
│   │   └── 040_holidays_categoria_sync.py   # NUEVO: category/source + holiday_sync_status
│   └── workers/
│       └── holiday_sync_tasks.py       # NUEVO: tarea periódica Celery (mismo patrón que sla_tasks.py)
└── api/
    └── routes/
        └── calendar.py                  # GET /holidays: intento inline de sync + campos
                                          # category/source; NUEVO PATCH /holidays/{id}

frontend/
├── src/
│   ├── types/
│   │   └── calendar.ts                 # + category, source en Holiday
│   ├── services/
│   │   └── calendarService.ts          # + updateHoliday(id, data)
│   └── pages/
│       └── CalendarPage.tsx            # + color por categoría, leyenda, eventos de
│                                        #   cumpleaños en la pestaña Equipo (derivados de
│                                        #   Resource.birth_date, sin llamada nueva al backend)
```

**Structure Decision**: Extiende el layout ya establecido por spec 020 (mismo namespace
`calendar.py` en dominio/infra/api, mismo archivo `CalendarPage.tsx`). Se agrega
`backend/infra/external/` como ubicación nueva pero coherente con Clean Architecture (Capa 2,
adaptador hacia un servicio externo) — no existía antes porque ninguna fase anterior había
necesitado un cliente HTTP saliente real. La tarea Celery sigue el patrón exacto de
`backend/workers/sla_tasks.py` (spec 014).

## Complexity Tracking

*No aplica — Constitution Check sin violaciones. La integración con Nager.Date está resuelta
como una aprobación documentada del Principio V (sin dependencia nueva en el gestor de
paquetes), no como una excepción/violación.*
