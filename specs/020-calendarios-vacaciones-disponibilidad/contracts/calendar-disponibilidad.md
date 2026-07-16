# Contract: Calendarios, Festivos, Horario Laboral, Ausencias y Disponibilidad (spec 020)

Endpoints nuevos, documentados en Swagger vía Flask-RESTX (Principio I) antes de implementarse.
`clients`/`resources` ganan campos nuevos en sus endpoints ya existentes (sin ruta nueva); el
resto vive en un namespace nuevo `backend/api/routes/calendar.py`.

## Cambios en endpoints existentes

### `clients` (`backend/api/routes/clients.py`)

`POST /api/clients`, `PATCH /api/clients/{id}`, `GET /api/clients/{id}` ganan los campos
`timezone` (string, IANA tz id) y `country` (string, ISO alpha-2) en body/respuesta. Mismo
permiso de módulo `clients` ya vigente — sin permiso nuevo.

### `resources` (`backend/api/routes/resources.py`)

`PATCH /api/resources/{id}` gana el campo `timezone` (string, IANA tz id), agregado a
`_PROFILE_TEXT_FIELDS`/`_resource_out`. Mismo enforcement ya vigente
(`enforce_module("resources", allow_own_resource_edit=True)`).

## Festivos

### `GET /api/holidays?country=CO` — listar festivos de un país

**Permiso**: `require_authenticated()` (lectura abierta a cualquier usuario autenticado — se
usa para renderizar ambos calendarios).

**200**:
```json
{"items": [{"id": "uuid", "country": "CO", "holiday_date": "2026-10-12", "name": "Día de la Raza", "active": true}]}
```

### `POST /api/holidays` — crear un festivo (mantenimiento del catálogo)

**Permiso**: `require_permission("holidays", "manage")` (nuevo permiso, otorgado a Admin/RRHH en
el seed).

**Body**: `{"country": "CO", "holiday_date": "2026-10-12", "name": "Día de la Raza"}`

**201**: el festivo creado. **400** `validation_error`: fecha inválida o duplicado
(`country`+`holiday_date`+`name` ya existe).

### `PATCH /api/holidays/{id}/deactivate` / `/activate`

Mismo patrón que `catalog_*` — **204**/**200** respectivamente. Mismo permiso `holidays:manage`.

## Horario laboral

### `GET /api/resources/{id}/work-schedule` — franjas semanales de un recurso

**Permiso**: `enforce_module("resources", allow_own_resource_edit=True)` (ver perfil propio o con
permiso de edición de recursos).

**200**:
```json
{"items": [{"weekday": 0, "start_time": "08:00", "end_time": "17:00"}], "is_default": false}
```

`is_default: true` cuando el recurso no tiene filas propias y se está devolviendo el horario por
defecto documentado en `spec.md` (no hay filas reales en `work_schedules`).

### `PUT /api/resources/{id}/work-schedule` — reemplaza las franjas semanales completas

**Body**: `{"items": [{"weekday": 0, "start_time": "08:00", "end_time": "17:00"}, ...]}`

**200**: igual forma que el `GET`. **400** `validation_error`: `weekday` fuera de 0-6,
`end_time <= start_time`, o `weekday` repetido en el mismo body.

## Ausencias (RRHH + Jefe directo)

### `POST /api/absence-requests` — crear una solicitud

**Permiso**: `require_permission("absence_requests", "create")`.

**Body** (`multipart/form-data` si incluye adjuntos, igual criterio que
`POST /api/tickets/{id}/comments`):
```json
{"absence_type_id": "uuid", "start_date": "2026-08-01", "end_date": "2026-08-05", "notes": "string | null"}
```
Campo adicional `files` (0 o más) para adjuntos opcionales (FR-008a).

**201**: la solicitud creada (ver forma de respuesta en `GET` de abajo).

**400** `validation_error`: `end_date < start_date`, tipo inexistente, o solapamiento con otra
solicitud propia `pending`/`approved` (FR-009).

### `GET /api/absence-requests?scope=own|manager|hr` — listar solicitudes

**Permiso**: `require_authenticated()`, con filtrado condicional dentro del handler (mismo patrón
que `tickets:view` vs `tickets:view_own`):
- `scope=own` (default): solicitudes del propio recurso vinculado al usuario autenticado.
- `scope=manager`: solicitudes de recursos cuyo `manager_id` es el recurso del usuario
  autenticado (**403** si el usuario no es jefe de nadie).
- `scope=hr`: requiere `absence_requests:view_all` (rol RRHH) — todas las solicitudes.

**200**:
```json
{
  "items": [{
    "id": "uuid",
    "resource": {"id": "uuid", "full_name": "string"},
    "absence_type": {"id": "uuid", "name": "Incapacidad médica"},
    "start_date": "2026-08-01",
    "end_date": "2026-08-05",
    "manager_status": "pending | approved | rejected",
    "hr_status": "pending | approved | rejected",
    "overall_status": "pending | approved | rejected",
    "notes": "string | null",
    "attachments": [{"id": "uuid", "filename": "string", "content_type": "string", "size_bytes": 0}],
    "created_at": "iso8601"
  }]
}
```

### `PATCH /api/absence-requests/{id}/decision` — aprobar/rechazar (Jefe directo o RRHH)

**Permiso**: `require_authenticated()`, resuelto dentro del handler según `body.role`:
- `role="manager"`: exige que el recurso del usuario autenticado sea `manager_id` de
  `absence_requests.resource_id` — **403** si no.
- `role="hr"`: exige `absence_requests:decide_hr` (rol RRHH) — **403** si no.
- En ambos casos, **403** `own_request` si el recurso del usuario autenticado ==
  `absence_requests.resource_id` (FR-012, nadie decide sobre su propia solicitud).

**Body**: `{"role": "manager" | "hr", "decision": "approved" | "rejected"}`

**200**: la solicitud actualizada (misma forma que un ítem de `GET`), con `overall_status`
recalculado por `absence_service` (Decisión 4 de `research.md`).

**409** `already_decided`: ese lado (`manager`/`hr`) ya tiene una decisión distinta de `pending`.

### `GET/POST/DELETE /api/absence-requests/{id}/attachments` — adjuntos

Mismo contrato que `GET/POST/DELETE /api/clients/{id}/access-attachments` (spec 018): multipart
`file`, reglas de tamaño/tipo ya vigentes, descarga con resolución segura de ruta
(`attachment_storage.open_path`). Permiso: mismo que ver/crear la solicitud padre (dueño, su
Jefe directo, o RRHH).

## Disponibilidad (consumido por el panel de asignación)

### `GET /api/resources/availability?resource_ids=id1,id2&at=2026-07-16T14:00:00Z`

**Permiso**: `require_permission("tickets", "assign")` (mismo permiso que ya protege el flujo de
asignación — sin permiso nuevo, ver Decisión 7/8 de `research.md`).

`at` es opcional (default: ahora, UTC). `resource_ids` opcional (default: todos los recursos
activos).

**200**:
```json
{
  "items": [
    {
      "resource_id": "uuid",
      "available": false,
      "reason": "outside_hours | holiday | absence | null",
      "detail": "string | null"
    }
  ]
}
```

`reason`/`detail` son `null` cuando `available=true`. Orden de evaluación fijado por FR-013:
`absence` (ausencia aprobada vigente) > `holiday` (festivo del país) > `outside_hours` (fuera de
horario laboral). Un recurso sin `timezone`/`calendar_country`/horario configurado siempre
devuelve `available: true` (FR-016).

**No afecta** a `POST /api/tickets/{id}/assign`, que sigue aceptando cualquier `assignee_id` sin
consultar disponibilidad (FR-015 — la asignación nunca se bloquea).
