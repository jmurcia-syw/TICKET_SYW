# Data Model: Fase 0 — Maestros

**Date**: 2026-06-29 | **Feature**: specs/001-fase0-maestros

---

## Entidades

### clients

Nodo raiz del modelo de datos. RLS root — todas las politicas de aislamiento parten de aqui.

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Identificador unico |
| name | TEXT | NOT NULL, UNIQUE | Nombre de la organizacion cliente |
| slug | TEXT | NOT NULL, UNIQUE | Identificador URL-friendly (auto-generado desde name) |
| active | BOOLEAN | NOT NULL, default TRUE | Estado activo/inactivo |
| contact_name | TEXT | | Nombre del contacto principal |
| contact_email | TEXT | | Email del contacto principal |
| contact_phone | TEXT | | Telefono del contacto |
| vpn_ips | BYTEA | cifrado pgcrypto AES-256 | IPs de acceso VPN del cliente |
| vpn_credentials | BYTEA | cifrado pgcrypto AES-256 | Credenciales de acceso VPN |
| notes | TEXT | | Notas adicionales (no cifradas) |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Fecha de creacion |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | Ultima modificacion |

**RLS Policy**:
```sql
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
CREATE POLICY clients_access ON clients
  USING (
    current_setting('app.user_role') IN ('admin', 'coordinator')
    OR id = ANY(
      SELECT client_id FROM projects
      WHERE id = ANY(
        SELECT project_id FROM tickets
        WHERE assignee_id = current_setting('app.user_id')::uuid
      )
    )
  );
```

**Reglas de negocio**:
- `name` debe ser unico (validacion en domain + UNIQUE constraint DB)
- No se puede desactivar un cliente sin confirmacion si tiene proyectos activos
- Al desactivar, los proyectos activos NO se desactivan automaticamente (requiere accion manual)
- `vpn_ips` y `vpn_credentials` solo accesibles para roles admin y coordinator

---

### projects

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Identificador unico |
| client_id | UUID | NOT NULL, FK clients(id) | Cliente propietario |
| name | TEXT | NOT NULL | Nombre del proyecto |
| description | TEXT | | Descripcion del proyecto |
| active | BOOLEAN | NOT NULL, default TRUE | Estado activo/inactivo |
| start_date | DATE | NOT NULL | Fecha de inicio |
| end_date_estimated | DATE | | Fecha de fin estimada |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Fecha de creacion |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | Ultima modificacion |

**Constraints**:
```sql
UNIQUE (client_id, name)  -- nombre unico por cliente, no globalmente
CHECK (end_date_estimated IS NULL OR end_date_estimated >= start_date)
```

**Reglas de negocio**:
- No se puede crear proyecto para un cliente inactivo
- Nombre unico dentro del mismo cliente (no globalmente)
- Proyectos inactivos no aparecen en selectores de creacion de tickets

---

### skills

Catalogo de etiquetas de habilidades tecnicas. Controlado exclusivamente por Admin.

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Identificador unico |
| code | TEXT | NOT NULL, UNIQUE | Etiqueta tecnica (JDE_GL, API_REST, etc.) |
| label | TEXT | NOT NULL | Nombre legible (JDE General Ledger) |
| active | BOOLEAN | NOT NULL, default TRUE | Activo/inactivo |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Fecha de creacion |

**Reglas de negocio**:
- `code` en UPPER_SNAKE_CASE, unico globalmente
- No se puede eliminar (ni desactivar) un skill asignado a al menos un recurso activo
- Skills desactivados no aparecen en el selector de asignacion a recursos

---

### resources

Miembros del equipo interno de SyWork.

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Identificador unico |
| user_id | UUID | FK users(id), UNIQUE | Cuenta de acceso asociada |
| full_name | TEXT | NOT NULL | Nombre completo |
| email | TEXT | NOT NULL, UNIQUE | Email @sywork.net (igual al de autenticacion) |
| active | BOOLEAN | NOT NULL, default TRUE | Estado activo/inactivo |
| notes | TEXT | | Notas del perfil (visible para Admin/Coordinador) |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Fecha de creacion |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | Ultima modificacion |

**Reglas de negocio**:
- Email unico globalmente (es el identificador de identidad)
- Un recurso sin skills asignados puede existir, pero genera advertencia en asignacion de tickets
- RLS: Resolutor solo puede leer/actualizar su propio registro

---

### resource_skills (tabla de union)

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| resource_id | UUID | NOT NULL, FK resources(id) | Recurso |
| skill_id | UUID | NOT NULL, FK skills(id) | Skill asignado |
| assigned_at | TIMESTAMPTZ | NOT NULL, default now() | Fecha de asignacion |

**Constraints**: `PRIMARY KEY (resource_id, skill_id)`

---

### users

Cuentas de acceso al sistema. Vinculada 0..1 con resources (un recurso puede aun no tener cuenta,
o una cuenta puede existir sin recurso asociado, ej. cuentas administrativas puras).

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Identificador unico |
| email | TEXT | NOT NULL, UNIQUE | Email @sywork.net |
| username | TEXT | NOT NULL, UNIQUE | Nombre de usuario para login provisional |
| role_id | UUID | NOT NULL, FK roles(id) | Rol dinamico asignado |
| password_hash | TEXT | NULLABLE | Hash de contraseña para login provisional (FR-022b); null si solo usa Google OAuth2 |
| active | BOOLEAN | NOT NULL, default TRUE | Estado activo/inactivo |
| google_sub | TEXT | UNIQUE, NULLABLE | Subject ID de Google OAuth2 |
| last_login_at | TIMESTAMPTZ | | Ultimo login exitoso (por cualquiera de los dos metodos) |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Fecha de creacion |

**Constraints**:
```sql
CHECK (email LIKE '%@sywork.net')
```

**Reglas de negocio**:
- Solo emails @sywork.net son aceptados (validado en callback OAuth2 y en constraint DB)
- Exactamente un rol por usuario (FK `role_id`, nunca nulo)
- No se puede desactivar ni degradar al ultimo Admin activo
- El middleware verifica `users.active` en cada request; si false devuelve 401
- `password_hash` es opcional: un usuario puede autenticarse solo con Google, solo con login
  provisional (si un Admin le asigna username+password), o con ambos

---

### roles

Rol dinamico gestionable por Admin (FR-015). Sembrado con 4 roles iniciales, extensible.

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Identificador unico |
| name | TEXT | NOT NULL, UNIQUE | Nombre del rol (ej. Admin, Coordinador, QM, Resolutor) |
| description | TEXT | | Descripcion del rol |
| active | BOOLEAN | NOT NULL, default TRUE | Estado activo/inactivo |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Fecha de creacion |

**Reglas de negocio**:
- El rol `Admin` no puede desactivarse ni eliminarse
- No se puede desactivar un rol con usuarios activos asignados
- Seed inicial: Admin, Coordinador, QM, Resolutor (ver migracion `009_roles_permissions_login.py`)

---

### permissions

Permiso granular modulo + accion (FR-015b). Catalogo administrado por Admin.

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Identificador unico |
| module | TEXT | NOT NULL | Modulo (ej. `clients`, `projects`, `resources`, `roles`) |
| action | TEXT | NOT NULL | Accion (`view`, `create`, `edit`, `deactivate`) |
| description | TEXT | | Descripcion legible |

**Constraints**: `UNIQUE (module, action)`

**Reglas de negocio**:
- No se puede eliminar un permiso asignado a algun rol (409 `permission_in_use`)

---

### role_permissions (tabla de union)

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| role_id | UUID | NOT NULL, FK roles(id) | Rol |
| permission_id | UUID | NOT NULL, FK permissions(id) | Permiso asignado |

**Constraints**: `PRIMARY KEY (role_id, permission_id)`

**Reglas de negocio**:
- `PUT /api/roles/{id}/permissions` reemplaza la lista completa (no incremental)

---

## Diagrama de relaciones

```
clients (1) ──── (N) projects
    │
    └── RLS root para tickets (Fase 1)

users (0..1) ──── (0..1) resources
  │                   │
  │                   └── (N) resource_skills (N) ──── (1) skills
  │
  └── (N) role_permissions (N) ──── (1) roles ──── (N) permissions
      [via role_id FK; role_permissions conecta roles ↔ permissions]
```

---

## Migraciones Alembic (orden de ejecucion)

1. `001_create_users.py` — tabla users (email, username, role_id, password_hash, google_sub)
2. `002_create_clients.py` — tabla clients + extension pgcrypto + columnas cifradas
3. `003_create_projects.py` — tabla projects + FK client_id
4. `004_create_skills_resources.py` — tablas skills, resources, resource_skills + seed de skills
5. `008_enable_rls_policies.py` — habilitar RLS y crear politicas en clients, resources, users
6. `009_roles_permissions_login.py` — tablas roles, permissions, role_permissions; seed de los
   4 roles iniciales y su matriz de permisos; agrega `username`/`password_hash` a users
