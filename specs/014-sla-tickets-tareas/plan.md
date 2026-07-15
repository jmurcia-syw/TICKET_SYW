# Implementation Plan: SLAs por Proyecto y Prioridad

**Branch**: `develp_Jp` | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-sla-tickets-tareas/spec.md`

## Summary

Hoy el contador de SLA es un placeholder estático (`—:—:—`, "SLA pausado (Fase 4)", "Vencen hoy"
fijo en 0). La solución agrega un **SLA Engine** en el dominio (Capa 1) que:

1. Resuelve el tiempo límite aplicable a un ticket/tarea buscando la regla exacta por Proyecto ×
   Prioridad (sin jerarquía de fallback — ver `research.md` Decisión 3, revisada 2026-07-14 según
   `docs/SLAv1.xlsx`).
2. Calcula el consumo acumulado de la **fase de SLA vigente** (2 fases secuenciales: Contacto /
   Diagnóstico-Análisis-Ejecución — Decisión 5) a partir de las transiciones de estado ya
   existentes, usando un flag+fase por estado (`SLA_PHASE_FOR_STATE`, `STATE_COUNTS_FOR_SLA`)
   definido junto a la FSM actual — reutilizando `backend/domain/fsm/ticket_fsm.py` como fuente de
   verdad de los estados, sin tocar sus transiciones.
3. Persiste un snapshot de consumo por ticket y por fase vigente (acumulado + timestamp de la
   última pausa/reanudación + resultado congelado de la fase Contacto) actualizado en cada cambio
   de estado, evitando reconstruir el historial completo en cada lectura.
4. Expone el estado de SLA (fase/corriendo/pausado/vencido/sin-config) vía el detalle de ticket ya
   existente y nuevos campos en el listado/dashboard.
5. Genera notificaciones de vencimiento reutilizando `notification_service.py`, disparadas por una
   tarea periódica Celery (ya aprobada en la Constitución para "SLA timers").

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript strict + React 19 (frontend)

**Primary Dependencies**: Flask + Flask-RESTX, SQLAlchemy + Alembic, `python-transitions`
(reutilizado, sin cambios), **Celery + Redis** (ya aprobados en la Constitución específicamente
para "SLA timers" — primer uso real de esta pieza del stack). Frontend: Ant Design 5, Zustand,
`date-fns` (formateo de duraciones). **Cero dependencias nuevas** fuera de activar el worker
Celery ya listado en el stack aprobado (Principio V).

**Storage**: PostgreSQL. Nueva tabla `sla_rules` (reglas configurables, keyed por
`project_id`+`priority`) y nuevas columnas en `tickets` para el snapshot de consumo de la fase
vigente (`sla_phase`, `sla_phase_limit_minutes`, `sla_consumed_seconds`, `sla_last_resume_at`,
`sla_status`, `sla_contact_result`, `sla_contact_consumed_seconds`). Se evita una tabla de
historial de transiciones separada: el snapshot se recalcula incrementalmente en cada cambio de
estado, consistente con que hoy no existe un log de transiciones dedicado (el "Historial de
estados" de la UI se deriva de los comentarios tipificados existentes).

**Testing**: pytest dirigido (`test_sla_rules.py`, `test_sla_engine.py`, `test_sla_notifications.py`),
≤ 5-10 registros de prueba por test (Principio VII). No se ejecuta la suite completa.

**Target Platform**: Web (frontend Vite/React en navegador; backend Flask + worker Celery en
Docker Compose).

**Project Type**: Web application (backend + frontend existentes, se agrega un worker Celery
nuevo al `docker-compose.yml`).

**Performance Goals**: El cálculo de estado de SLA por ticket es O(1) (lectura del snapshot, sin
recorrer historial); la tarea periódica de detección de vencimientos corre cada 5 minutos sobre
tickets activos con SLA configurado (no sobre toda la tabla).

**Constraints**:
- El motor de SLA vive en `backend/domain/` sin imports de Flask/SQLAlchemy (Principio I/II) —
  recibe el estado actual y los timestamps como parámetros puros, no consulta la DB directamente.
- No se automatiza la FSM (Fase 6 sigue pendiente): el snapshot de SLA se actualiza como efecto
  secundario de los endpoints de transición ya existentes (`/status`, `/testing`, `/resolution`,
  `/close`, `/cancel`), no se agregan transiciones nuevas.
- Los calendarios de negocio (feriados, 5x8/7x24) quedan fuera de alcance (ver Assumptions del
  spec) — el contador es 24x7 continuo.
- Errores del cálculo de SLA nunca deben bloquear una transición de estado válida (el SLA es
  informativo, no una regla de negocio que impida avanzar el ticket) — FR-014, clarificación
  2026-07-14: el efecto lateral de `sla_service` se envuelve en manejo de errores propio dentro
  del endpoint de transición, sin poder abortar la transición FSM ya aplicada.
- El SLA solo aplica a `record_type` = "Ticket" (FR-012, clarificación 2026-07-14) — Tareas y
  Subtareas comparten tabla/columnas pero `sla_service.resolve_rule`/`apply_transition` deben
  hacer no-op (dejar `sla_*` en `NULL`) cuando el registro no es un Ticket.

**Scale/Scope**: 1 tabla nueva (`sla_rules`), 7 columnas nuevas en `tickets` (aplicables también
a Tareas por compartir tabla), 1 servicio de dominio (`sla_service.py`), 1 tarea periódica Celery,
~4 endpoints nuevos (CRUD reglas de SLA + lectura de estado agregado para dashboard/listado),
3 componentes frontend actualizados (`TicketDetailPage`, `TicketsPage` listado, `StatCard` del
dashboard) + 1 pantalla nueva de configuración de reglas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|-----------|-----------|--------|
| I. API-First | Contrato Swagger de `sla_rules` y de los campos de SLA en `_ticket_detail_out` se define en `contracts/` antes de implementar. `POST/PATCH /api/sla-rules` son endpoints independientes, no acoplados a ninguna pantalla. | ✅ PASS |
| II. Clean Architecture | `sla_service.py` (Capa 1, dominio puro) calcula consumo/estado a partir de (estado actual, timestamps, regla aplicable) sin tocar SQLAlchemy. Los repositorios (Capa 2) leen/escriben el snapshot. Las rutas (Capa 3) solo orquestan. | ✅ PASS |
| III. Tipado estricto | Enums Python (`SlaStatus`) con type hints en el servicio de dominio; tipos TS estrictos para el nuevo `TicketSlaState` en `frontend/src/types/`. | ✅ PASS |
| IV. Seguridad en profundidad | CRUD de `sla_rules` protegido por permiso nuevo `sla_rules:manage` (Admin/Coordinador, FR-013); lectura de estado de SLA hereda el permiso `tickets:view`/`view_own` ya existente — ningún dato nuevo expuesto sin RLS ya vigente en `tickets`. | ✅ PASS |
| V. Gobernanza de librerías | Celery + Redis ya están en el stack aprobado de la Constitución explícitamente para "SLA timers" — se activa el worker, no se agrega una dependencia nueva. Cualquier librería adicional de cálculo de duraciones usa `date-fns` (frontend) / `datetime` stdlib (backend). | ✅ PASS |
| VI. AI-Native | El estado de SLA (consumido/límite/vencido) se expone como dato estructurado en el detalle del ticket y en el listado — insumo directo para el futuro AI Dispatcher (Fase 5+) sin requerir cambios de arquitectura. | ✅ PASS |
| VII. Alcance de sesión / testing | Tests nuevos ultra-limitados (≤ 5-10 registros), sin ejecutar la suite completa; el trabajo se acota a los archivos de esta feature (dominio SLA, migración, endpoints de reglas, 3 componentes frontend puntuales). | ✅ PASS |

No hay violaciones que requieran registrarse en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/014-sla-tickets-tareas/
├── plan.md              # Este archivo (/speckit-plan)
├── research.md          # Fase 0 (/speckit-plan)
├── data-model.md         # Fase 1 (/speckit-plan)
├── quickstart.md        # Fase 1 (/speckit-plan)
├── contracts/           # Fase 1 (/speckit-plan)
│   └── sla-contract.md
└── tasks.md             # Fase 2 (/speckit-tasks — no la crea /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   ├── entities/
│   │   └── sla_rule.py            # Entidad SlaRule (dataclass pura)
│   ├── fsm/
│   │   └── ticket_fsm.py          # Se añade dict STATE_COUNTS_FOR_SLA (solo lectura, sin nuevas transiciones)
│   └── services/
│       └── sla_service.py         # Motor de cálculo: resolver regla aplicable, consumo, estado
├── infra/
│   ├── models/
│   │   └── sla_rule_model.py      # Modelo SQLAlchemy sla_rules + columnas SLA en TicketModel
│   ├── repositories/
│   │   └── sla_rule_repo.py       # CRUD reglas + lectura agregada para listado/dashboard
│   └── migrations/versions/
│       └── 028_sla_rules.py       # Tabla sla_rules + columnas sla_* en tickets
├── api/routes/
│   ├── sla_rules.py               # CRUD /api/sla-rules (nuevo namespace)
│   └── tickets.py                 # Se extiende _ticket_detail_out con bloque "sla"; sin nuevas rutas
└── workers/
    └── sla_tasks.py                # Tarea periódica Celery: detectar vencimientos → notificar

frontend/src/
├── types/
│   └── sla.ts                      # TicketSlaState, SlaRule
├── services/
│   └── slaService.ts               # CRUD reglas + helpers de formato
├── components/
│   ├── tickets/
│   │   └── SlaCounter.tsx          # Reemplaza el placeholder "—:—:—" en TicketDetailPage
│   └── sla/
│       └── SlaRuleForm.tsx         # Alta/edición de regla (Admin/Coordinador)
└── pages/
    ├── SlaRulesPage.tsx             # Listado + CRUD de reglas (nueva, bajo Maestros)
    ├── TicketDetailPage.tsx         # Se reemplaza el placeholder existente por <SlaCounter>
    └── TicketsPage.tsx              # Columna/indicador de SLA en la tabla + stat "Vencen hoy" real
```

**Structure Decision**: Se mantiene la estructura de tres capas ya vigente (`backend/domain` /
`backend/infra` / `backend/api`) y la separación `frontend/src/{types,services,components,pages}`.
Único elemento nuevo de infraestructura: `backend/workers/` para la tarea periódica Celery (el
stack Celery+Redis está aprobado pero aún no tiene código en el repo — esta es su primera
materialización, consistente con la Constitución).

## Complexity Tracking

*Sin violaciones que justificar.*
