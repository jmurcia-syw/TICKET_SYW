# Data Model: RRHH — Franjas Horarias, Calendario Superpuesto y Motor de SLA Dinámico

Extiende las entidades de `backend/domain/entities/calendar.py` y `resource.py` (spec 020/021).
No se modifica `Ticket` (solo lectura de `priority`/`severity`/asignación).

## Entidades nuevas

### WorkHourTemplate ("Franja Horaria" global)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID | PK |
| `country` | str | mismo dominio de valores que `Resource.calendar_country` / `Holiday.country` |
| `name` | str | etiqueta libre (ej. "Colombia — Estándar") |
| `timezone` | str | IANA tz (ej. `America/Bogota`) |
| `active` | bool | default `True`; una plantilla inactiva no se propaga a nuevos recursos, pero no borra la asignación de los que ya la tienen |
| `created_at` / `updated_at` | datetime | |

**Validación**: un país puede tener más de una Franja Horaria activa (ej. distintos horarios para
distintos perfiles); no hay restricción de unicidad por país — el recurso elige explícitamente
cuál heredar.

### WorkHourTemplateSlot

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID | PK |
| `template_id` | UUID | FK → `work_hour_templates.id`, `ondelete=CASCADE` |
| `weekday` | int | 0=lunes .. 6=domingo, mismo dominio que `WorkScheduleSlot.weekday` |
| `start_time` / `end_time` | time | naive, interpretadas en `WorkHourTemplate.timezone` |

Mismo shape que `WorkScheduleSlot` — permite reutilizar `_within_schedule()` de
`availability_service.py` sin cambios, pasándole los slots de la plantilla en vez de los propios
cuando el recurso está en modo `heredado`.

## Entidades extendidas

### Resource (`backend/domain/entities/resource.py`)

Campos nuevos:

| Campo | Tipo | Notas |
|-------|------|-------|
| `schedule_mode` | str | `"heredado"` \| `"personalizado"`; default `"heredado"` |
| `work_hour_template_id` | UUID \| None | FK → `work_hour_templates.id`, `ondelete=SET NULL`; `NULL` si `heredado` sin plantilla asignada aún, o si `personalizado` |

**Regla de negocio** (en `work_hour_template_service.py`, no en la entidad):
- Al editar el horario propio desde el Perfil → `schedule_mode = "personalizado"`,
  `work_hour_template_id = NULL` (las filas de `work_schedules` propias pasan a ser la fuente de
  verdad, tabla ya existente sin cambios).
- Al asignar una Franja Horaria desde la pantalla de RRHH → `schedule_mode = "heredado"`,
  `work_hour_template_id = <template.id>` (se descartan las filas propias de `work_schedules` si
  existían, dado que dejan de ser la fuente de verdad).

### AbsenceRequest (`backend/domain/entities/calendar.py`)

Campos nuevos (ambos opcionales):

| Campo | Tipo | Notas |
|-------|------|-------|
| `start_time` | time \| None | `NULL` = ausencia de día completo (comportamiento actual, sin cambios) |
| `end_time` | time \| None | debe ser `> start_time`; requiere `start_date == end_date` cuando se usan horas |

**Validación** (`absence_service.py`):
- `validate_date_range` sin cambios (día completo sigue igual).
- Nueva `validate_partial_hours(start_date, end_date, start_time, end_time)`: si alguno de
  `start_time`/`end_time` viene informado, el otro también debe venirlo, `start_date == end_date`,
  y `start_time < end_time`.
- `assert_no_overlap` se extiende: si ambas solicitudes (la nueva y una existente `pending`/
  `approved`) son del mismo día y ambas tienen rango horario, se comparan los rangos de horas
  además del rango de fechas.

## Cálculo derivado (no persistido)

### Disponibilidad efectiva de un recurso (extiende `availability_service.compute_availability`)

Sin cambios de firma. El llamador (ruta/repositorio) resuelve `work_schedule_slots` así:
- `schedule_mode == "personalizado"` → filas propias de `work_schedules` (como hoy).
- `schedule_mode == "heredado"` y `work_hour_template_id` no nulo → slots de
  `work_hour_template_slots` de esa plantilla.
- `schedule_mode == "heredado"` sin plantilla asignada → lista vacía (cae al default hardcodeado
  L-V 08:00-17:00, comportamiento ya existente sin cambios).

`active_absence` pasa a poder representar también una ausencia parcial: si la hora actual cae
dentro de `[start_time, end_time)` de una ausencia aprobada de ese día, cuenta igual que una
ausencia de día completo (`reason: "absence"`); fuera de ese rango horario, no aplica.

### SLA dinámico (extiende `sla_service`)

Nueva función `compute_available_seconds(resource, from_dt, to_dt, holidays, schedule_slots,
absences)` que suma, minuto a minuto (o por segmento contiguo), los intervalos entre `from_dt` y
`to_dt` en los que `availability_service` habría devuelto `available=True`. `sla_service` la usa
así:

- `compute_consumed_seconds(ticket, now, resource=None, holidays=None, schedule_slots=None,
  absences=None)`: parámetros nuevos **opcionales** (default `None` → preserva el wall-clock
  puro actual si algún llamador no los provee todavía). Cuando vienen informados, en vez de
  `consumed += (now - sla_last_resume_at).total_seconds()`, hace
  `consumed += compute_available_seconds(resource, sla_last_resume_at, now, holidays,
  schedule_slots, absences)`.
- `compute_state(ticket, now, resource=None, ...)`: mismos parámetros opcionales; gana un campo
  de lectura adicional `pause_reason` (`None` | `"outside_hours"` | `"holiday"` | `"absence"` |
  `"ticket_status"`) para que la UI distinga por qué no avanza el contador, sin cambiar los
  valores posibles de `sla_status`.
- `sla_consumed_seconds` (la base ya persistida en cada pausa/transición) **no se toca** — de ahí
  sale la propiedad "hacia adelante únicamente" (research.md Decisión 4).

**Cableado obligatorio (research.md Decisión 10 — hallazgo C1 de `/speckit-analyze`)**: estas
funciones no tienen efecto si nadie les pasa el contexto nuevo. Los tres puntos de Capa 3 que
invocan `compute_state`/`compute_consumed_seconds` hoy deben resolver y pasar
`resource`/`holidays`/`schedule_slots`/`absences` antes de llamarlas:

1. `backend/api/routes/tickets.py:358` y `:454` (lectura de ticket/listado).
2. `backend/workers/sla_tasks.py: check_sla_breaches` (tarea periódica).

La resolución en cada punto: `ResourceRepository.get_by_id(ticket.assignee_id)` →
`WorkHourTemplateRepository`/`WorkScheduleRepository` según `resource.schedule_mode` (heredado vs
personalizado) → `HolidayRepository.list_by_country(resource.calendar_country)` (ya existente,
sin cambios) → `AbsenceRequestRepository.list_approved_between(resource_id, from_date, to_date)`
(nuevo, ver abajo).

## Repositorios (Capa 2) — nuevos/extendidos

### `WorkHourTemplateRepository` (nuevo, en `backend/infra/repositories/calendar_repo.py`)

Mismo archivo y patrón que `HolidayRepository`/`WorkScheduleRepository`. Métodos: `list_by_country`,
`get_by_id`, `create`, `update`, `replace_slots(template_id, slots)`, `list_slots(template_id)`.
La persistencia de la Franja Horaria vive aquí — `work_hour_template_service.py` (Capa 1) solo
valida (timezone IANA, `end_time > start_time` por slot), nunca toca la base de datos (research.md
Decisión 12, mismo patrón que `absence_service.py` hoy).

### `ResourceRepository.list_by_schedule_mode(mode)` (nuevo método, en
`backend/infra/repositories/resource_repo.py`)

Lista recursos por `schedule_mode` (`"heredado"` | `"personalizado"`) — usado por la pantalla de
RRHH para el listado de Personalizados (FR-005) y por la propagación de cambios de una Franja
(quiénes la heredan).

### `AbsenceRequestRepository.list_approved_between(resource_id, start_date, end_date)` (nuevo
método, en `backend/infra/repositories/calendar_repo.py`)

Ranged — a diferencia de `get_active_absence` (un solo día) y de `list_overlapping` (incluye
`pending`), este método devuelve solo solicitudes con `manager_status="approved"` **y**
`hr_status="approved"` que se solapan con `[start_date, end_date]`. Es el método que
`compute_available_seconds` necesita para sumar disponibilidad a lo largo de un rango multi-día
(research.md Decisión 11).

### Carga de trabajo ("workload", no persistida)

Para un recurso: `Σ (sla_phase_limit_minutes − consumed_seconds/60)` de sus tickets con SLA activo
(`sla_status in ("corriendo", "pausado")`), comparado contra las horas disponibles restantes del
recurso hoy (según su horario efectivo). Expuesto solo en el endpoint `GET
/api/resources/{id}/workload` (ver `contracts/`) — no se guarda en ninguna tabla.

## Migraciones (Alembic, secuenciales desde `041`)

1. **`041_work_hour_templates.py`**: crea `work_hour_templates` y `work_hour_template_slots`.
2. **`042_resource_schedule_mode.py`**: agrega `schedule_mode` (default `'heredado'`) y
   `work_hour_template_id` a `resources`; **migración de datos**: `UPDATE resources SET
   schedule_mode = 'personalizado' WHERE id IN (SELECT DISTINCT resource_id FROM
   work_schedules)` (research.md Decisión 3, confirmado con el usuario).
3. **`043_absence_requests_partial_hours.py`**: agrega `start_time`/`end_time` nullable a
   `absence_requests` (columnas nuevas, sin backfill — filas existentes quedan `NULL` = día
   completo, compatible hacia atrás).
4. **`044_rrhh_work_hour_templates_permission.py`**: agrega permiso `work_hour_templates:manage`
   a los roles RRHH y Admin (mismo patrón que `039_rrhh_role_permissions.py`).
