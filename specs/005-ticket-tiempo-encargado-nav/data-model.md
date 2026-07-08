# Data Model: Registro de tiempo en el ticket, rol Encargado y navegación

**Date**: 2026-07-08 | **Feature**: specs/005-ticket-tiempo-encargado-nav

Extiende el MER de Fase 0-2 (`docs/MER.md`). Migraciones:
`018_work_sessions_start_end.py`, `019_create_client_contacts.py`,
`020_client_contacts_rls.py`, `021_encargado_role_permissions.py`.

## Entidades

### work_sessions (extensión — sin cambios en columnas existentes)

| Columna nueva | Tipo | Constraints | Descripcion |
|---------------|------|-------------|-------------|
| started_at | TIMESTAMPTZ | NULLABLE | Hora de inicio del trabajo (informativa) |
| ended_at | TIMESTAMPTZ | NULLABLE | Hora de finalización (informativa) |

**Reglas de negocio nuevas**:
- `started_at`/`ended_at` son ambos opcionales, pero si se cargan, DEBEN venir juntos y
  `ended_at > started_at` (CHECK a nivel de dominio, no de DB, para poder dar un mensaje claro).
- Si `started_at`/`ended_at` están presentes, `duration_minutes` se recalcula automáticamente en
  el dominio (`(ended_at - started_at)` redondeado a minutos) al guardar — el usuario puede
  editar `duration_minutes` manualmente después sin que eso borre `started_at`/`ended_at` (quedan
  como referencia, ver research.md Decisión 1).
- Todas las reglas ya vigentes (`MAX_DAILY_MINUTES`, `EDIT_WINDOW_DAYS`, pertenencia al ticket,
  ticket no cerrado) siguen aplicando sobre `duration_minutes`, sin cambios.

### client_contacts (nueva — perfil del rol Encargado)

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, gen_random_uuid() | Identificador |
| user_id | UUID | NOT NULL, UNIQUE, FK users(id) | Cuenta de acceso del Encargado |
| client_id | UUID | NOT NULL, FK clients(id) | Cliente (empresa) fijo al que pertenece |
| created_at | TIMESTAMPTZ | NOT NULL, now() | Auditoría mínima |

**Reglas de negocio**:
- Un `user_id` solo puede tener una fila en `client_contacts` (1:1) — un Encargado pertenece a
  exactamente un Cliente (FR-007b).
- Al crear un ticket con un usuario Encargado autenticado, el backend resuelve `client_id` desde
  esta tabla — el Encargado nunca lo selecciona manualmente (research.md Decisión 4).
- RLS: mismo patrón app-level que las demás tablas (`012_tickets_rls.py`); la restricción real de
  "un Encargado solo ve su propia fila" no es necesaria a nivel de RLS porque el propio dominio
  ya resuelve `client_id` desde el `user_id` autenticado, nunca desde un parámetro externo.

## Relaciones

```
users (Fase 0)   ──1:1──  client_contacts  ──N:1──  clients (Fase 0)
tickets.created_by → users.id   (ya existente — sirve como "Encargado solicitante" cuando
                                  el creador tiene rol Encargado; sin columna nueva en tickets)
```

## Ticket — sin cambios de esquema, solo de presentación e interpretación

- **`created_by`** (ya existente, FK `users.id`): cuando el usuario referenciado tiene rol
  Encargado, el detalle del ticket lo muestra explícitamente como "Encargado solicitante"
  (distinto del `client_id` = Cliente/empresa). Cuando el creador tiene otro rol (Coordinador,
  etc.), se sigue mostrando como "Creado por" tal cual hoy.
- **`estimated_resolution_minutes`** (ya existente, sin cambios de tipo ni de `FIELD_LOCKS`): se
  presenta en el detalle convertido a horas (`minutos / 60`, redondeado a 1 decimal), con la
  etiqueta "Tiempo estimado de solución"; si es `NULL` se muestra "Sin estimar" (FR-006). El
  formulario de creación/edición sigue enviando minutos al backend (conversión solo en frontend).

## Catálogo de permisos (extiende el mecanismo de `001-fase0-maestros`/`004-fase2-registro-tiempos`)

| Permiso | Roles con el permiso | Uso |
|---------|----------------------|-----|
| `tickets:view_own` | Encargado | Ver/listar únicamente los tickets que el propio Encargado creó |
| `tickets:create` | Admin, Coordinador, QM, Resolutor (ya existente) **+ Encargado** | Se agrega Encargado a la lista de roles con este permiso ya existente (sin crear un permiso nuevo) |
| `client_contacts:manage` | Admin, Coordinador | Alta/consulta de perfiles Encargado↔Cliente |

**Rol nuevo**: `Encargado` — sin ningún otro permiso de módulo (`tickets:edit`, `assign`,
`transition`, `cancel`, `assignment_panel:*`, `catalogs:*`, `work_sessions:*`, maestros, roles,
etc. quedan explícitamente fuera).
