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

Cuentas de acceso al sistema. Vinculada 1:1 con resources.

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Identificador unico |
| email | TEXT | NOT NULL, UNIQUE | Email Google @sywork.net |
| role | TEXT | NOT NULL | 'admin', 'coordinator', 'qm', 'resolver' |
| active | BOOLEAN | NOT NULL, default TRUE | Estado activo/inactivo |
| google_sub | TEXT | UNIQUE | Subject ID de Google OAuth2 |
| last_login_at | TIMESTAMPTZ | | Ultimo login exitoso |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Fecha de creacion |

**Constraints**:
```sql
CHECK (role IN ('admin', 'coordinator', 'qm', 'resolver'))
CHECK (email LIKE '%@sywork.net')
```

**Reglas de negocio**:
- Solo emails @sywork.net son aceptados (validado en callback OAuth2 y en constraint DB)
- Exactamente un rol por usuario
- No se puede desactivar ni degradar al ultimo Admin activo
- El middleware verifica `users.active` en cada request; si false devuelve 401

---

## Diagrama de relaciones

```
clients (1) ──── (N) projects
    │
    └── RLS root para tickets (Fase 1)

users (1) ──── (1) resources
                    │
                    └── (N) resource_skills (N) ──── (1) skills
```

---

## Migraciones Alembic (orden de ejecucion)

1. `001_create_users.py` — tabla users + constraint role + check email
2. `002_create_clients.py` — tabla clients + extension pgcrypto + columnas cifradas
3. `003_create_projects.py` — tabla projects + FK client_id
4. `004_create_skills.py` — tabla skills
5. `005_create_resources.py` — tabla resources + FK user_id
6. `006_create_resource_skills.py` — tabla de union resource_skills
7. `007_enable_rls.py` — habilitar RLS y crear politicas en clients, resources, users
8. `008_seed_initial_skills.py` — seed de skills iniciales (JDE_GL, API_REST, Oracle_Fusion, etc.)
