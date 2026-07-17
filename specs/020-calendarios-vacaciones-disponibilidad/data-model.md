# Data Model — Calendarios, Festivos, Vacaciones (RRHH) y Disponibilidad

## Cambios en entidades existentes

### `clients` (+ columnas)

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `timezone` | text | Sí | IANA tz id (ej. `America/Bogota`). `NULL` = sin configurar (FR-016 aplica también a Clientes). |
| `country` | text | Sí | Código ISO 3166-1 alpha-2, mismo catálogo de país que `react-phone-number-input` ya usa en el frontend. Determina qué festivos de `holidays` se muestran (FR-001, FR-004). |

### `resources` (+ columna)

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `timezone` | text | Sí | IANA tz id. `calendar_country` (ya existente, texto libre) sigue siendo el país que determina festivos (FR-002, FR-005); `timezone` es explícito porque un mismo país puede abarcar más de una zona horaria. |

`manager_id` (ya existente, FK autorreferencial `resources.id`) se reutiliza como "Jefe directo"
de la cadena de aprobación (US2) — sin cambios de esquema.

## Entidades nuevas

### `holidays`

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `id` | UUID (PK) | No | `gen_random_uuid()` |
| `country` | text | No | Código ISO 3166-1 alpha-2 |
| `holiday_date` | date | No | — |
| `name` | text | No | — |
| `active` | boolean | No | default `true` (permite desactivar sin borrar histórico) |
| `created_at` | timestamptz | No | `now()` |

**Índice/unicidad**: `UNIQUE (country, holiday_date, name)`. **Sin RLS** (dato de referencia no
sensible — Decisión 6 de `research.md`).

### `work_schedules`

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `id` | UUID (PK) | No | `gen_random_uuid()` |
| `resource_id` | UUID (FK → `resources.id`, `ON DELETE CASCADE`) | No | — |
| `weekday` | smallint | No | `0`=lunes … `6`=domingo |
| `start_time` | time | No | Hora local del recurso (su `timezone`) |
| `end_time` | time | No | Debe ser `> start_time` |
| `created_at` | timestamptz | No | `now()` |

**Índice**: `UNIQUE (resource_id, weekday)` (una franja por día por recurso en esta fase — varias
franjas en el mismo día queda fuera de alcance). Cero filas para un recurso ⇒ se aplica el
horario por defecto documentado en `spec.md` → Assumptions (FR-006). **Sin RLS** (Decisión 6).

### `catalog_absence_types` (tabla nueva, mismo patrón que `catalog_teams`/`catalog_tools`)

Reutiliza `_CatalogMixin` de `backend/infra/models/catalog_model.py` (`id`, `name`, `active`,
`created_at`). Se agrega a `CATALOG_MODELS` como clave `"absence-types"`, expuesto por el
`CatalogList`/`CatalogDeactivate`/`CatalogActivate` genérico ya existente en
`backend/api/routes/catalogs.py` — **sin endpoints nuevos** para el catálogo en sí.

**Seed inicial** (migración): `Vacaciones`, `Incapacidad médica`, `Permiso personal`, `Otro`.

### `absence_requests`

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `id` | UUID (PK) | No | `gen_random_uuid()` |
| `resource_id` | UUID (FK → `resources.id`) | No | Solicitante |
| `absence_type_id` | UUID (FK → `catalog_absence_types.id`) | No | — |
| `start_date` | date | No | — |
| `end_date` | date | No | `>= start_date` (FR-009) |
| `manager_status` | text | No | `pending` \| `approved` \| `rejected`, default `pending`. Nace en `approved` si el recurso no tiene `manager_id` (Decisión 4). |
| `manager_decided_by` | UUID (FK → `users.id`) | Sí | — |
| `manager_decided_at` | timestamptz | Sí | — |
| `hr_status` | text | No | `pending` \| `approved` \| `rejected`, default `pending` |
| `hr_decided_by` | UUID (FK → `users.id`) | Sí | — |
| `hr_decided_at` | timestamptz | Sí | — |
| `notes` | text | Sí | Comentario libre del solicitante |
| `created_at` | timestamptz | No | `now()` |
| `updated_at` | timestamptz | No | `now()`, `onupdate=now()` |

`overall_status` **no se persiste** como columna — se calcula en
`backend/domain/services/absence_service.py` a partir de `manager_status`/`hr_status` (Decisión 4)
y se serializa en las respuestas de API. Mantenerlo fuera de la tabla evita que quede
desincronizado si se cambia una de las dos decisiones.

**Reglas de validación** (derivadas de Requirements del spec):
- `end_date >= start_date` (FR-009).
- No puede solaparse con otra solicitud del mismo `resource_id` en estado `manager_status` o
  `hr_status` = `pending`/`approved` (FR-009, edge case).
- Ni el Jefe directo ni RRHH pueden decidir sobre su propia solicitud (FR-012): al recibir una
  decisión, el servicio de dominio rechaza si `decided_by`'s recurso vinculado ==
  `absence_request.resource_id`.
- Una solicitud con `manager_status`/`hr_status` ya distinto de `pending` no admite nueva decisión
  del mismo lado (idempotencia simple, sin "reabrir").

**Sin RLS** a nivel de columna cifrada (a diferencia de `client_access`, no hay credenciales) pero
**sí RLS a nivel de tabla** (Decisión 6) por ser información de salud/HR sensible.

### `absence_request_attachments`

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `id` | UUID (PK) | No | `gen_random_uuid()` |
| `absence_request_id` | UUID (FK → `absence_requests.id`, `ON DELETE CASCADE`) | No | — |
| `filename` | text | No | — |
| `content_type` | text | No | — |
| `size_bytes` | integer | No | ≤ `MAX_ATTACHMENT_BYTES` (10 MB, límite ya vigente) |
| `storage_path` | text | No | `absence_requests/{absence_request_id}/{uuid}-{filename}` |
| `created_at` | timestamptz | No | `now()` |

**Relaciones**: `absence_requests (1) ──< absence_request_attachments (N)`. **RLS habilitado**
(Decisión 6).

## Row Level Security (nuevas policies)

```sql
ALTER TABLE absence_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY absence_requests_app_access ON absence_requests
  USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true'
         OR current_user = 'sywork_user');

ALTER TABLE absence_request_attachments ENABLE ROW LEVEL SECURITY;
CREATE POLICY absence_request_attachments_app_access ON absence_request_attachments
  USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true'
         OR current_user = 'sywork_user');
```

Mismo patrón app-level que `client_access`/`client_contacts`/`work_sessions` (ver
`031_client_access_rls.py`).

## Rol y permisos nuevos (seed de migración, mismo patrón que `021_encargado_role_permissions.py`)

| Módulo | Acción | Roles |
|---|---|---|
| `absence_requests` | `create` | Todos los roles internos vinculados a un Recurso (Admin, Coordinador, QM, Resolutor, RRHH) — **no** `Encargado` (contacto externo, no es equipo de trabajo) |
| `absence_requests` | `view_all` | RRHH |
| `absence_requests` | `decide_hr` | RRHH |

Rol nuevo: **RRHH** (`roles.name = 'RRHH'`), creado igual que el rol `Encargado` en `021_...py`.
La decisión del Jefe directo no usa un permiso de módulo — se verifica por pertenencia
(`absence_requests.resource_id`'s `manager_id` == recurso del usuario autenticado), igual que
`_is_own_resource` en `backend/api/middleware/rbac.py` (Decisión 8 de `research.md`).

## Actualización de tipos existentes (dominio)

- `backend/domain/entities/client.py`: `Client` gana `timezone: Optional[str]`,
  `country: Optional[str]`.
- `backend/domain/entities/resource.py`: `Resource` gana `timezone: Optional[str]`.
- `backend/domain/entities/calendar.py` (**nuevo archivo**): `@dataclass Holiday`,
  `@dataclass WorkScheduleSlot`, `@dataclass AbsenceRequest`, `@dataclass
  AbsenceRequestAttachment`, `@dataclass Availability` (value object:
  `available: bool`, `reason: Optional[str]`, `detail: Optional[str]` — usado solo como
  resultado de servicio, no persistido).
- `frontend/src/types/calendar.ts` (**nuevo archivo**): `Holiday`, `WorkScheduleSlot`,
  `AbsenceRequest`, `AbsenceRequestAttachment`, `Availability` (interfaces TS, sin `any`).
- `frontend/src/types/client.ts` / `frontend/src/types/resource.ts`: agregan `timezone`
  (y `country` en Client).
