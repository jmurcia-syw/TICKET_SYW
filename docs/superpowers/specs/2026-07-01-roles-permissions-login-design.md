# Roles, Permisos y Login Provisional — Diseño

**Fecha**: 2026-07-01
**Estado**: Aprobado, pendiente de plan de implementación

## Contexto

Hoy el rol de un usuario es un valor fijo (`admin`, `coordinator`, `qm`, `resolver`) restringido por un `CHECK` en la tabla `users`. No existe ningún mecanismo de contraseña — la única forma de entrar es Google OAuth (`google_sub`). El decorator `require_role` en `backend/api/middleware/rbac.py` existe pero no está enganchado en ninguna ruta: ni siquiera las rutas de maestros (`clients`, `projects`, `resources`, `users`, `skills`) exigen JWT hoy. La visibilidad de menús en el frontend está hardcodeada en arrays `roles: Role[]` dentro de `config/navigation.tsx` y en el código muerto de `DashboardPage.tsx`.

Este documento cubre tres piezas relacionadas:
1. Modelo de datos dinámico de roles y permisos (reemplaza el enum fijo).
2. Login provisional por usuario/contraseña (coexiste con Google OAuth, no lo reemplaza).
3. Datos semilla: 4 roles y 4 usuarios de prueba con perfiles de permisos distintos.

## Decisiones de alcance (confirmadas con el usuario)

- **Roles 100% dinámicos**: se pueden crear/editar/borrar desde una pantalla CRUD, sin límite de 4.
- **Permisos 100% dinámicos**: también son entidades CRUD-eables (no un catálogo fijo en código), con granularidad **módulo + acción** (ej. `clients` + `create`).
- **Enforcement solo en frontend**: los permisos controlan qué ve/hace el usuario en la UI. El backend **no** valida permisos por endpoint en esta fase.
- **Las rutas de maestros (incluyendo las nuevas de roles/permisos) quedan sin autenticación**, igual que hoy. Solo `/api/auth/login` y `/api/auth/me` son rutas de autenticación real.
- **DEV_SKIP_AUTH se apaga**: el login provisional pasa a ser el mecanismo real para entrar a la SPA (activa el flujo `ProtectedRoute` + `DashboardPage` que hoy existe como código muerto), pero esto es sobre el *frontend/sesión*, no sobre las rutas de la API.
- **Google OAuth no se borra**: el login provisional es un mecanismo adicional, explícitamente temporal ("provisional").
- **Existe un rol Admin con acceso total** (incluida la creación de usuarios y la gestión de roles/permisos), separado de los 3 roles nuevos.
- La pantalla "Roles y Permisos" es exclusiva de Admin.

## 1. Modelo de datos

### `roles`
| columna | tipo | notas |
|---|---|---|
| id | UUID PK | |
| name | text | único |
| description | text | nullable |
| active | boolean | default true |
| created_at | timestamptz | |

### `permissions`
| columna | tipo | notas |
|---|---|---|
| id | UUID PK | |
| module | text | `clients`, `projects`, `resources`, `skills`, `users`, `roles` |
| action | text | `view`, `create`, `edit`, `deactivate` |
| description | text | nullable |

Único por `(module, action)`.

### `role_permissions`
| columna | tipo | notas |
|---|---|---|
| role_id | UUID FK → roles.id | |
| permission_id | UUID FK → permissions.id | |

PK compuesta `(role_id, permission_id)`.

### `users` (modificación de tabla existente)
- Se elimina la columna `role` (text) y su `CHECK (role IN (...))`.
- Se agrega `role_id` UUID FK → `roles.id` (nullable=false).
- Se agrega `username` text, único, nullable=false.
- Se agrega `password_hash` text, **nullable** (una cuenta creada solo por Google OAuth puede no tener password provisional).
- `google_sub`, `email`, `active`, `last_login_at`, `created_at` se mantienen igual.

### Migración de datos existentes
La migración de Alembic (próxima revisión tras `008`):
1. Crea `roles`, `permissions`, `role_permissions`.
2. Inserta los 4 roles semilla y el catálogo de 24 permisos (6 módulos × 4 acciones).
3. Agrega `role_id` a `users` como nullable primero, mapea cada fila existente por el valor viejo de `role` (texto) al `role_id` correspondiente por nombre, y si algún usuario existente no matchea ningún rol conocido la migración **falla** (no asigna un rol por defecto silenciosamente).
4. Vuelve `role_id` `NOT NULL`, elimina la columna `role` vieja y su `CHECK`.
5. Agrega `username` (nullable primero, se puebla para usuarios existentes a partir del prefijo del email, luego `NOT NULL` + único) y `password_hash` (nullable, se deja vacío para cuentas Google existentes).

## 2. Backend

### Servicios y repos (mismo patrón que los maestros existentes)
- `backend/domain/entities/role.py` — `Role` (entidad), `Permission`.
- `backend/domain/services/role_admin_service.py` — reglas: no se puede borrar/desactivar el rol `"Admin"`; no se puede borrar un permiso asignado a algún rol (409, mismo patrón que skills); no se puede desactivar un rol con usuarios activos asignados (409 con conteo, mismo patrón que clientes).
- `backend/infra/repositories/role_repo.py` — `RoleRepository`, `PermissionRepository`.
- Ambos servicios usan la jerarquía `DomainError` ya existente (`backend/domain/errors.py`).

### Rutas nuevas — sin autenticación, mismo estilo que clients/projects/etc.
`backend/api/routes/roles.py`:
- `GET /api/roles` — lista roles con sus permisos.
- `POST /api/roles` — crea rol.
- `GET /api/roles/{id}` / `PATCH /api/roles/{id}` — detalle / edición de nombre/descripción.
- `PATCH /api/roles/{id}/deactivate` / `/activate`.
- `PUT /api/roles/{id}/permissions` — reemplaza el set completo de permisos del rol (`{permission_ids: [...]}`, mismo patrón que `PATCH /api/resources/{id}/skills`).

`backend/api/routes/permissions.py`:
- `GET /api/permissions` — catálogo completo (para la matriz de asignación).
- `POST /api/permissions` — crea una definición de permiso nueva.
- `DELETE /api/permissions/{id}` — 409 si está asignado a algún rol.

### Login provisional — `backend/api/routes/auth.py` (se agrega, no se reemplaza el de Google)
- `POST /api/auth/login`: body `{username_or_email, password}`. Busca por `username` o `email`, verifica `password_hash` con `werkzeug.security.check_password_hash`. Si no matchea o el usuario no tiene `password_hash`: `401` genérico `"Usuario o contraseña incorrectos"` (no revela cuál falló). Si es correcto: actualiza `last_login_at`, emite JWT (`flask_jwt_extended.create_access_token`, igual que el login de Google) y responde:
  ```json
  {
    "access_token": "...",
    "user": {
      "id": "...", "email": "...", "username": "...",
      "role": {"id": "...", "name": "Coordinador"},
      "permissions": [{"module": "clients", "action": "view"}, ...]
    }
  }
  ```
- `GET /api/auth/me` se actualiza para devolver la misma forma enriquecida (rol + permisos), usado al refrescar la página para reconstruir el menú sin volver a loguearse. Sigue exigiendo JWT válido (`jwt_required_active`), como ya lo hace hoy.

Contraseñas: hash con `werkzeug.security.generate_password_hash` (PBKDF2-SHA256, ya viene con Flask). Nunca se loguea ni se devuelve `password_hash` en ninguna respuesta.

## 3. Datos semilla

**24 permisos**: producto cartesiano de módulos (`clients`, `projects`, `resources`, `skills`, `users`, `roles`) × acciones (`view`, `create`, `edit`, `deactivate`).

**4 roles y su asignación de permisos**:

| Rol | Clientes | Proyectos | Recursos | Skills | Usuarios | Roles y Permisos |
|---|---|---|---|---|---|---|
| Admin | todo | todo | todo | todo | todo (incl. crear) | todo |
| Coordinador | todo | todo | todo | todo | solo ver | sin acceso |
| QM | todo | solo ver | todo | todo | solo ver | sin acceso |
| Resolutor | solo ver | solo ver | solo ver | solo ver | solo ver | sin acceso |

("todo" = view + create + edit + deactivate del módulo. "solo ver" = únicamente `view`. "sin acceso" = ningún permiso del módulo → el menú no aparece.)

**4 usuarios** (dominio `@sywork.net`, contraseña provisional generada y comunicada al usuario al terminar la implementación, nunca hardcodeada en el repo en texto plano):
- `admin@sywork.net` / username `admin` — rol Admin
- `coordinador@sywork.net` / username `coordinador` — rol Coordinador
- `qm@sywork.net` / username `qm` — rol QM
- `resolutor@sywork.net` / username `resolutor` — rol Resolutor

## 4. Frontend

- **`LoginPage.tsx`**: deja de ser el stub de Google; se convierte en formulario usuario/contraseña que llama a `POST /api/auth/login` y guarda `{token, user}` en `authStore`.
- **`App.tsx`**: deja de usar `DevLayout` (bypass de dev). Se activa el flujo que ya existe sin conectar: `/login` pública, todo lo demás envuelto en `ProtectedRoute`, layout real = `DashboardPage.tsx`.
- **`authStore.ts`**: agrega `username`, `permissions: {module: string, action: string}[]`. `Role` deja de ser el union type fijo `'admin'|'coordinator'|'qm'|'resolver'` y pasa a ser `{id: string, name: string}`.
- **`config/navigation.tsx`**: el array estático `roles: Role[]` por ítem se reemplaza por una función que arma el menú "Maestros" iterando los `permissions` del usuario logueado — un módulo aparece en el menú si el usuario tiene el permiso `{module, action: "view"}` correspondiente.
- **`UsersPage.tsx`**: el selector de rol al cambiar el rol de un usuario carga `GET /api/roles` en vez de un array `ROLES` fijo; `ROLE_COLORS` pasa de un `Record` fijo por las 4 keys a una función/paleta que asigna color por nombre de rol de forma determinística (para no romper si se crean roles nuevos).
- **Pantalla nueva `RolesPermissionsPage.tsx`** (bajo "Maestros", solo visible con permiso `roles.view`): tabla de roles con CRUD (crear/editar/desactivar/activar, mismo patrón visual que las demás páginas de maestros); al editar un rol se abre una matriz módulo × acción con checkboxes que llama a `PUT /api/roles/{id}/permissions`. Pantalla separada `PermissionsPage` o sección dentro de la misma para crear/borrar definiciones de permiso (catálogo).

## 5. Manejo de errores y casos borde

- Borrar/desactivar el rol `"Admin"` → bloqueado explícitamente (no depende solo de que nadie lo intente; se valida en el servicio).
- Desactivar un rol con usuarios activos asignados → `409` con el conteo de usuarios afectados (mismo patrón que la desactivación de clientes con proyectos activos).
- Borrar un permiso asignado a algún rol → `409` (mismo patrón que borrar un skill en uso).
- Login con `username_or_email`/`password` inválidos → `401` genérico, mismo mensaje sin importar cuál campo falló.
- La regla de "no se puede degradar/desactivar al último Admin activo" (`RoleService` ya existente) se conserva, mapeada por `role.name == "Admin"` en vez del enum. Limitación conocida: si el rol se renombra desde la UI, esta protección específica deja de aplicar — mitigado bloqueando el borrado del rol Admin, pero no un renombrado.

## 6. Testing

Mismo patrón que la suite ya existente en `backend/tests/`:
- **Unitarios de dominio** (sin DB, repos falsos): reglas de `RoleAdminService` (bloqueo de borrar Admin, permiso en uso, rol con usuarios activos), verificación de hash/verificación de password.
- **Integración de API** (Flask test client + Postgres real, con limpieza vía nombres únicos): CRUD de roles, CRUD de permisos, asignación de permisos a un rol, login exitoso, login con credenciales inválidas, `/api/auth/me` con y sin token.

## Fuera de alcance (explícito)

- Enforcement de permisos en el backend (403 por endpoint) — queda para una fase futura.
- JWT obligatorio en las rutas de maestros — quedan abiertas, igual que hoy.
- Recuperación de contraseña / cambio de contraseña propio.
- Eliminar el login de Google — el código y la ruta quedan intactos.
