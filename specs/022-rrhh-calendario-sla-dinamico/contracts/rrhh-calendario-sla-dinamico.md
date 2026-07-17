# Contract: RRHH — Franjas Horarias, Calendario Superpuesto y Motor de SLA Dinámico (spec 022)

Extiende `backend/api/routes/calendar.py` (spec 020/021). No se toca ningún endpoint de
`backend/api/routes/tickets.py` — el motor de SLA dinámico cambia de comportamiento interno en
`sla_service`, no de contrato en los endpoints de Ticket.

## Franjas Horarias (endpoints nuevos)

**Permiso**: `require_permission("work_hour_templates", "manage")` (RRHH y Admin — migración `044`)
para crear/editar/desactivar. Lectura (`GET`) disponible para cualquier usuario autenticado con
acceso a Maestros/Calendario (mismo criterio que festivos).

### `GET /api/work-hour-templates?country=CO`

Lista las Franjas Horarias (activas e inactivas) de un país, con sus slots semanales:

```json
{"items": [{
  "id": "uuid", "country": "CO", "name": "Colombia — Estándar",
  "timezone": "America/Bogota", "active": true,
  "slots": [{"weekday": 0, "start_time": "08:00", "end_time": "17:00"}, "..."]
}]}
```

### `POST /api/work-hour-templates`

**Body**:
```json
{"country": "CO", "name": "Colombia — Estándar", "timezone": "America/Bogota",
 "slots": [{"weekday": 0, "start_time": "08:00", "end_time": "17:00"}, "..."]}
```

**201**: la plantilla creada (misma forma que `GET`). **400** `validation_error` si `timezone` no
es una zona IANA válida, o si algún slot tiene `end_time <= start_time`.

### `PATCH /api/work-hour-templates/{id}`

Actualización parcial (nombre, timezone, `active`, o reemplazo completo de `slots`). **200**: la
plantilla actualizada. Efecto lateral (FR-003, sin exponerse como parámetro): todo recurso con
`work_hour_template_id = {id}` y `schedule_mode = "heredado"` refleja el nuevo horario en la
siguiente consulta de disponibilidad — no requiere ninguna llamada adicional del cliente. **404**
si no existe.

### `GET /api/work-hour-templates/personalized`

Lista los recursos con `schedule_mode = "personalizado"` (FR-005):

```json
{"items": [{"resource_id": "uuid", "full_name": "string", "calendar_country": "CO"}]}
```

## Horario del Recurso (extiende endpoints ya existentes)

### `PUT /api/resources/{id}/work-schedule` (sin cambio de permiso —
`enforce_module("resources", allow_own_resource_edit=True)`, ya existente)

**Efecto lateral nuevo**: al invocarse (por el propio usuario o por un rol con permiso de
edición), el recurso pasa automáticamente a `schedule_mode = "personalizado"` y
`work_hour_template_id = NULL` (FR-004), sin importar si tenía una Franja asignada antes. El
cuerpo/forma de la petición no cambia.

### `PATCH /api/resources/{id}/work-hour-template`

**Endpoint nuevo** — asigna (o reasigna) una Franja Horaria a un recurso desde la pantalla de
RRHH.

**Body**: `{"work_hour_template_id": "uuid"}`

**200**: `{"resource_id": "uuid", "schedule_mode": "heredado", "work_hour_template_id": "uuid"}`.
Efecto lateral: descarta las filas propias de `work_schedules` del recurso si existían (deja de
ser personalizado). **404** si la plantilla no existe o no coincide el país del recurso —
`validation_error` en ese caso (`country_mismatch`).

## Ausencias/Permisos parciales por horas (extiende endpoint ya existente)

### `POST /api/absence-requests` (spec 020, sin cambio de permiso)

**Body**, campos nuevos opcionales `start_time`/`end_time`:

```json
{"absence_type_id": "uuid", "start_date": "2026-07-20", "end_date": "2026-07-20",
 "start_time": "14:00", "end_time": "16:00", "notes": "Cita médica"}
```

Si se omiten `start_time`/`end_time`, comportamiento idéntico al actual (día completo). **400**
`validation_error` si solo uno de los dos viene informado, si `start_date != end_date` con horas
presentes, si `end_time <= start_time`, o si se solapa con otra solicitud propia vigente en el
mismo rango de horas (mismo código `overlap` ya usado para el solape por fechas).

### `GET /api/absence-requests` (sin cambio de permiso)

Cada ítem gana `start_time`/`end_time` (nulos si es de día completo) en la respuesta.

## SLA — sin cambio de contrato en Tickets, cambio de comportamiento interno

`GET /api/tickets/{id}` y `GET /api/tickets` (spec 014) mantienen exactamente la misma forma del
bloque `sla` en la respuesta, con un campo nuevo:

```json
{"sla": {"phase": "ejecucion", "status": "pausado", "consumed_seconds": 3600,
         "phase_limit_minutes": 480, "pause_reason": "outside_hours"}}
```

`pause_reason` (nuevo, nullable): `null` si `status != "pausado"`; `"ticket_status"` si la pausa
es por estado del ticket (`pendiente_usuario`, comportamiento ya existente); `"outside_hours"` |
`"holiday"` | `"absence"` si es por disponibilidad del recurso asignado (motor dinámico, research
Decisión 6). El valor numérico de `consumed_seconds` ya refleja el cálculo dinámico sin necesidad
de que el cliente haga nada distinto.

## Carga de trabajo (endpoint nuevo)

### `GET /api/resources/{id}/workload?date=2026-07-20`

**Permiso**: `resources:view` — mismo `enforce_module("resources")` ya aplicado a
`ResourceList`/`ResourceDetail` en `backend/api/routes/resources.py` para peticiones GET (nuevo
recurso `ResourceWorkload` agregado al mismo grupo de enforcement, ver research.md Decisión 9).
`date` opcional, default hoy.

**200**:
```json
{"resource_id": "uuid", "date": "2026-07-20",
 "committed_minutes": 320, "available_minutes_remaining": 160,
 "tickets": [{"ticket_id": "uuid", "ticket_number": "TK-000123",
              "priority": "critical", "severity": "s1", "remaining_minutes": 45}]}
```

`committed_minutes`: suma de `phase_limit_minutes - consumed_seconds/60` de los tickets con SLA
activo asignados al recurso. `available_minutes_remaining`: minutos de disponibilidad real que le
quedan al recurso ese día, según su horario efectivo (heredado o personalizado) y calendario
(festivos/ausencias). No persiste nada — cómputo puro de lectura (research.md Decisión 9).

## Vista diaria priorizada — sin endpoint nuevo

**Corrección tras `/speckit-analyze` (hallazgo I1)**: el `Ticket` no tiene ningún campo de fecha
propio (no hay "fecha programada" ni "vencimiento" en la entidad — confirmado por inspección de
`backend/domain/entities/ticket.py`), y el listado de tickets **no** tiene hoy un parámetro
`date`. La vista de Día **no** filtra tickets por fecha: usa
`GET /api/tickets?assignee_id={id}` (filtro `assignee_id` ya existente) trayendo los tickets
abiertos actualmente asignados a ese recurso — "Día" identifica de quién se ve la agenda, no una
fecha del ticket (ver spec.md, Assumptions). El ordenamiento estricto por Prioridad → Severidad
(FR-015) se aplica **en el cliente** sobre la respuesta ya recibida (no requiere un parámetro de
orden nuevo en el backend), igual que el resaltado visual de criticidad alta (FR-016).

## Cableado del motor de SLA dinámico (aclaración tras `/speckit-analyze`, hallazgo C1)

Las funciones nuevas de `sla_service` (`compute_available_seconds`,
`compute_consumed_seconds`/`compute_state` extendidos) no cambian ningún contrato HTTP por sí
solas — el cambio de contrato ya descrito arriba (`pause_reason` en el bloque `sla`) solo aparece
si los tres puntos de Capa 3 que orquestan estas funciones resuelven y pasan el contexto de
calendario antes de invocarlas:

- `GET /api/tickets/{id}` y el listado `GET /api/tickets` (`backend/api/routes/tickets.py`,
  líneas 358 y 454 en el código actual): antes de llamar a `compute_state`, resuelven
  `ResourceRepository.get_by_id(ticket.assignee_id)`, los slots efectivos del recurso
  (`WorkHourTemplateRepository` o `WorkScheduleRepository` según `schedule_mode`),
  `HolidayRepository.list_by_country(...)` (ya existente) y
  `AbsenceRequestRepository.list_approved_between(...)` (nuevo, ver data-model.md).
- La tarea periódica `check_sla_breaches` (`backend/workers/sla_tasks.py`) resuelve el mismo
  contexto por cada ticket con SLA corriendo antes de invocar `sla_service.is_breach`/
  `compute_state` — hoy esa tarea no importa nada de calendario/festivos/horario/ausencias.

Sin este cableado, `pause_reason` nunca aparecería distinto de `null`/`"ticket_status"` y
`consumed_seconds` seguiría siendo wall-clock puro pese a que las funciones de dominio ya
existan — ver research.md Decisión 10 y `tasks.md` (tareas T032a-T032c).
