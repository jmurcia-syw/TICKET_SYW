# Data Model — Festivos sincronizados por API, categorización visual y cumpleaños

## Cambios en entidades existentes

### `holidays` (+ columnas)

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `category` | text | No | `'oficial'` \| `'regional_religioso'`. Default `'oficial'` (compatibilidad con los festivos ya sembrados en spec 020, todos oficiales). CHECK constraint con los dos valores. |
| `source` | text | No | `'api'` \| `'manual'`. Default `'manual'` (compatibilidad con los festivos ya sembrados a mano). CHECK constraint. |

Toda escritura hecha por un Admin (crear, editar, activar/desactivar) fija `source='manual'` en
esa fila (Decisión 6 de `research.md`) — la sincronización automática nunca toca una fila con
`source='manual'`.

## Entidades nuevas

### `holiday_sync_status`

| Campo | Tipo | Nullable | Notas |
|---|---|---|---|
| `id` | UUID (PK) | No | `gen_random_uuid()` |
| `country` | text | No | Código ISO 3166-1 alpha-2 |
| `year` | smallint | No | Año sincronizado |
| `last_synced_at` | timestamptz | No | `now()` al momento del intento (éxito o fallo) |
| `success` | boolean | No | `true` si el último intento trajo datos válidos de la fuente externa |
| `error_message` | text | Sí | Detalle del último error, solo si `success = false` |

**Índice/unicidad**: `UNIQUE (country, year)`. **Sin RLS** (dato operativo interno, no sensible —
Decisión 8 de `research.md`). No expuesto directamente al frontend; solo lo consumen la tarea
periódica y el intento inline del endpoint `GET /api/holidays`.

## Sin cambios de esquema

- **Cumpleaños**: no crea entidad ni columna nueva. Se deriva en el frontend de
  `resources.birth_date`, ya existente (Decisión 7 de `research.md`).

## Row Level Security

Sin cambios respecto a spec 020: `holidays` y la nueva `holiday_sync_status` permanecen **sin
RLS** (dato de referencia/operativo, no datos sensibles de usuario).

## Actualización de tipos existentes (dominio)

- `backend/domain/entities/calendar.py::Holiday` — agrega `category: str = "oficial"` y
  `source: str = "manual"`.
- `backend/domain/services/availability_service.py::_has_holiday_today` — recibe únicamente
  festivos ya filtrados por `category == "oficial"` (el filtro se aplica en el repositorio antes
  de pasar la lista a la función de dominio, o dentro de la función misma — decisión de
  implementación en `/speckit-tasks`).
- `frontend/src/types/calendar.ts::Holiday` — agrega `category: 'oficial' | 'regional_religioso'`
  y `source: 'api' | 'manual'`.
