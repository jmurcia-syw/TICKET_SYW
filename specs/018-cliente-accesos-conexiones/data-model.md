# Data Model — Accesos y conexiones múltiples del Cliente

## Entidades

### ClientAccess (tabla `client_access`)

Representa un registro individual de acceso/conexión al ambiente técnico de un cliente.
Sustituye conceptualmente a las columnas `clients.vpn_ips` / `clients.vpn_credentials`, que
quedan como columnas legacy (no se eliminan en este cambio — ver "Notas de migración").

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `id` | UUID (PK) | No | `gen_random_uuid()` |
| `client_id` | UUID (FK → `clients.id`) | No | `ON DELETE CASCADE` |
| `access_type` | text | No | Enum de aplicación: `vpn` \| `system_url` \| `remote_desktop` |
| `environment` | text | Sí | Enum de aplicación: `dev` \| `test` \| `prod`; solo relevante cuando `access_type = 'system_url'` (FR-001) |
| `username` | text | Sí | — |
| `password` | bytea (cifrado, mismo mecanismo que `vpn_credentials` hoy) | Sí | Enmascarado por defecto en toda UI (FR-005) |
| `host` | text | Sí | IP, URL o nombre de escritorio remoto según `access_type` |
| `notes` | text | Sí | — |
| `created_at` | timestamptz | No | `now()` |
| `updated_at` | timestamptz | No | `now()`, `onupdate=now()` |

**Relaciones**: `clients (1) ──< client_access (N)`.

**Reglas de validación** (derivadas de Requirements del spec):
- `access_type` MUST ser uno de los tres valores del enum (FR-001).
- `environment` solo se persiste si `access_type = 'system_url'`; para los otros dos tipos se
  ignora/se guarda `NULL` (FR-001, edge case implícito).
- Un cliente puede tener cero o más `client_access` (FR-009) — no hay mínimo.
- Eliminar un `client_access` no afecta a los demás del mismo cliente (FR-002).

### ClientAccessAttachment (tabla `client_access_attachments`)

Archivo adjunto asociado a la sección de accesos y conexiones de un cliente (no a un
`client_access` individual — ver Decisión 3 en `research.md`).

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `id` | UUID (PK) | No | `gen_random_uuid()` |
| `client_id` | UUID (FK → `clients.id`) | No | `ON DELETE CASCADE` |
| `filename` | text | No | Nombre original del archivo |
| `content_type` | text | No | — |
| `size_bytes` | integer | No | ≤ `MAX_ATTACHMENT_BYTES` (10 MB, límite ya vigente) |
| `storage_path` | text | No | Relativo a `uploads/`, formato `clients/{client_id}/{uuid}-{filename}` |
| `created_at` | timestamptz | No | `now()` |

**Relaciones**: `clients (1) ──< client_access_attachments (N)`.

**Reglas de validación**: mismas reglas de tipo/tamaño de archivo ya vigentes en
`backend/infra/storage/attachments.py` (`ALLOWED_EXTENSIONS`, `MAX_ATTACHMENT_BYTES`).

## Row Level Security

Ambas tablas habilitan RLS con la misma policy app-level que `client_contacts`
(`020_client_contacts_rls.py`):

```sql
ALTER TABLE client_access ENABLE ROW LEVEL SECURITY;
CREATE POLICY client_access_app_access ON client_access
  USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true'
         OR current_user = 'sywork_user');

ALTER TABLE client_access_attachments ENABLE ROW LEVEL SECURITY;
CREATE POLICY client_access_attachments_app_access ON client_access_attachments
  USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true'
         OR current_user = 'sywork_user');
```

## Notas de migración (`030_client_access.py`)

1. `CREATE TABLE client_access ...`, `CREATE TABLE client_access_attachments ...`.
2. Data migration (misma transacción): para cada fila de `clients` con `vpn_ips IS NOT NULL OR
   vpn_credentials IS NOT NULL`, insertar un `client_access` con `access_type='vpn'`,
   `host=<vpn_ips desencriptado>`, `password=<vpn_credentials re-cifrado en la nueva columna>`,
   `username=NULL`, `environment=NULL`.
3. `clients.vpn_ips` y `clients.vpn_credentials` **no se eliminan** en esta migración — quedan
   como columnas legacy sin uso en la API/UI nueva (retirarlas es un cambio separado, fuera de
   alcance de este spec, para no combinar en una sola migración un `DROP COLUMN` irreversible con
   la creación de la tabla nueva).
4. `downgrade()`: por cada cliente, toma el primer `client_access` con `access_type='vpn'`
   (ordenado por `created_at`) y reconstruye `vpn_ips`/`vpn_credentials`; luego `DROP TABLE` de
   ambas tablas nuevas. Documentado como best-effort si un cliente ya acumuló más de un acceso
   VPN antes del rollback (se preserva solo el más antiguo).

## Actualización de tipos existentes

- `backend/domain/entities/client.py`: agrega `@dataclass ClientAccess` y
  `@dataclass ClientAccessAttachment`, mismo estilo que `ClientSystem`.
- `frontend/src/types/client.ts`: agrega `ClientAccess`, `ClientAccessFormData`,
  `ClientAccessAttachment` (interfaces TS, sin `any`).
