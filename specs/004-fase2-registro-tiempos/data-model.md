# Data Model: Fase 2 — Registro diario de tiempos por recurso

**Date**: 2026-07-07 | **Feature**: specs/004-fase2-registro-tiempos

Extiende el MER de Fase 0/1 (`docs/MER.md`). Migraciones: `015_create_work_sessions.py`,
`016_work_sessions_rls.py`, `017_work_sessions_permissions.py` (catálogo de permisos).

## Entidades

### work_sessions

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, gen_random_uuid() | Identificador |
| resource_id | UUID | NOT NULL, FK resources(id) | Recurso que registra el tiempo (inmutable, FR-013) |
| ticket_id | UUID | NOT NULL, FK tickets(id) | Ticket sobre el que se trabajó |
| work_date | DATE | NOT NULL | Fecha del trabajo realizado (no futura, FR-006) |
| duration_minutes | INTEGER | NOT NULL, CHECK > 0 | Tiempo trabajado, en minutos (FR-005) |
| note | TEXT | NULLABLE | Nota corta opcional de lo realizado |
| created_by | UUID | NOT NULL, FK users(id) | Usuario que cargó el registro originalmente |
| updated_by | UUID | NULLABLE, FK users(id) | Usuario que hizo la última edición (si aplica) |
| deleted_at | TIMESTAMPTZ | NULLABLE | Soft-delete (FR-012): el registro se excluye de listados/reportes sin perder su fila, para que `work_session_edits` conserve una referencia válida |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL, now() | Auditoría mínima |

**Índices**: `(resource_id, work_date)` para el resumen diario y el reporte (US3),
`(ticket_id)` para consultas por ticket.

**Reglas de negocio**:
- `resource_id` NUNCA cambia tras la creación (FR-013) — una edición solo puede tocar
  `duration_minutes`, `note` o (Admin) `work_date`/`ticket_id` en corrección administrativa.
- El dominio (`WorkSessionService`) valida en cada alta/edición, antes de tocar la base de
  datos:
  - `resource_id` participa del `ticket_id` indicado (es el `assignee_id` actual, o figura en
    `ticket_assignments` para ese ticket) — excepto llamadas de Admin (FR-002).
  - `SUM(duration_minutes)` del recurso en `work_date`, incluyendo la entrada nueva/editada,
    no supera 1440 minutos (24h) (FR-004).
  - `work_date` no es posterior a la fecha actual (FR-006).
  - `duration_minutes > 0` (FR-005).
  - El ticket referenciado no está en estado `cerrado`, salvo que quien registra sea Admin
    (FR-009).
  - Edición/borrado solo si `hoy - work_date <= 7 días corridos` (ventana de edición, FR-007),
    salvo Admin (FR-008).
- El borrado es un **soft-delete** (`deleted_at = now()`): la fila de `work_sessions` nunca se
  elimina físicamente, para que la fila `action='deleted'` de `work_session_edits` conserve una
  referencia (`work_session_id`) válida. Todas las consultas de listado/reporte filtran
  `deleted_at IS NULL`.
- RLS: habilitado como red de seguridad de datos (mismo patrón que `tickets`,
  `012_tickets_rls.py`); la restricción real "un recurso ve solo lo suyo, Coordinador/QM/Admin
  ven todo" (FR-010) se aplica en dominio + API mediante los permisos
  `work_sessions:view_own` / `work_sessions:view_all` (research.md, Decisión 4 y 6).

### work_session_edits (append-only — historial auditable, FR-012)

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, gen_random_uuid() | Identificador |
| work_session_id | UUID | NOT NULL, FK work_sessions(id) | Registro de tiempo afectado |
| action | TEXT | NOT NULL, CHECK IN ('created','updated','deleted') | Tipo de evento |
| previous_values | JSONB | NULLABLE | Snapshot de los campos antes del cambio (NULL en 'created') |
| new_values | JSONB | NULLABLE | Snapshot de los campos después del cambio (NULL en 'deleted') |
| edited_by | UUID | NOT NULL, FK users(id) | Quién ejecutó la acción |
| edited_at | TIMESTAMPTZ | NOT NULL, now() | Cuándo |

**Reglas de negocio**:
- Tabla append-only: nunca se actualiza ni se borra una fila existente (mismo espíritu que
  `ticket_status_transitions`/`ticket_assignments` de Fase 1).
- Toda alta, edición o borrado de un `work_session` genera exactamente una fila aquí, dentro de
  la misma transacción de base de datos que la operación principal.
- RLS: mismo patrón app-level que `work_sessions` — no expone datos entre recursos por sí sola,
  la restricción de lectura es responsabilidad de dominio+API.

## Relaciones

```
resources (Fase 0)  ──1:N──  work_sessions  ──N:1──  tickets (Fase 1)
users (Fase 0)      ──1:N──  work_sessions.created_by / updated_by
work_sessions       ──1:N──  work_session_edits
```

## Vista derivada: Resumen diario de recurso (no persistida)

No es una tabla — se calcula en `WorkSessionService.get_daily_summary(resource_id, date_range)`
a partir de `work_sessions` (research.md, Decisión 5):

- Agrega `SUM(duration_minutes)` por `(resource_id, work_date)` vía repositorio (SQL `GROUP BY`).
- El servicio de dominio completa, para cada día del rango solicitado sin filas devueltas por la
  query, una entrada `{work_date, total_minutes: 0, sin_registro: true}` — para que US3/FR-011
  (días sin registro visibles) no dependa de una consulta SQL adicional.

## Catálogo de permisos (extiende el mecanismo de `001-fase0-maestros`)

| Permiso | Roles con el permiso | Uso |
|---------|----------------------|-----|
| `work_sessions:view_own` | Todos los roles internos | Ver/listar los propios registros de tiempo |
| `work_sessions:manage` | Todos los roles internos | Crear/editar/eliminar los propios registros (dentro de la ventana de edición) |
| `work_sessions:view_all` | Coordinador, QM, Admin | Ver el reporte agregado de cualquier recurso (US3) |
| `work_sessions:manage_all` | Admin | Editar/eliminar registros de cualquier recurso, incluso fuera de la ventana de edición o contra tickets `cerrado` (corrección administrativa) |
