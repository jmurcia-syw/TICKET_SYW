# API Contract: Auth, Users, Roles & Permissions

**Nota importante**: El enforcement de permisos a nivel de rutas de la API queda **fuera de
alcance de Fase 0** (ver FR-017 y Assumptions en spec.md); las rutas de maestros no exigen JWT
en esta fase. La matriz de "Roles" en este contrato describe el modelo de datos y el
comportamiento de navegacion/menus previsto (frontend), no un enforcement de backend activo aun.

---

## Auth — Base path: `/api/auth`

Login dual: Google OAuth2 (SSO existente) y login provisional usuario/contraseña (FR-022b),
coexistiendo sin que uno reemplace al otro. Ambos devuelven la misma forma de respuesta.

### POST /api/auth/login

Login provisional por `username_or_email` + `password`.

**Body**:
```json
{ "username_or_email": "carlos.rodriguez", "password": "secreto123" }
```

**Response 200**:
```json
{
  "access_token": "eyJ...",
  "user": {
    "id": "uuid",
    "email": "carlos.rodriguez@sywork.net",
    "username": "carlos.rodriguez",
    "role": { "id": "uuid", "name": "Resolutor" },
    "permissions": [{ "module": "resources", "action": "view" }]
  }
}
```

**Errors**:
- 400 `{ "error": "validation_error", "message": "username_or_email y password son requeridos" }`
- 401 `{ "error": "unauthorized", "message": "Usuario o contraseña incorrectos" }` (tambien si la
  cuenta esta inactiva — no distingue el motivo, ver FR-023)

---

### POST /api/auth/google

Login via Google OAuth2, restringido a dominio `@sywork.net`.

**Body**: `{ "id_token": "<google-id-token>" }`

**Response 200**: igual forma que `/api/auth/login`.

**Errors**:
- 400 `{ "error": "bad_request", "message": "id_token requerido" }`
- 401 `{ "error": "unauthorized", "message": "Acceso denegado" }` (dominio distinto, usuario no
  existente, o cuenta inactiva — mensaje generico, sin exponer el motivo)

---

### GET /api/auth/me

Perfil del usuario autenticado (requiere JWT valido y cuenta activa).

**Response 200**: `{ "user": { ...mismo objeto user que en /login } }`

**Errors**: 401 (sin token, token invalido, o cuenta desactivada tras emitir el JWT — FR-021)

---

## Users — Base path: `/api/users`

**Roles previstos**: Admin (CRUD completo, incluida la creación — FR-018b) — otros roles: solo `/me`.

### GET /api/users

Lista de usuarios del sistema. Solo Admin.

**Query params**: `page`, `page_size`, `role` (nombre de rol), `active`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "email": "juan.murcia@sywork.net",
      "username": "juan.murcia",
      "role": { "id": "uuid", "name": "Coordinador" },
      "active": true,
      "last_login_at": "2026-06-29T10:00:00Z",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/users

Crear un usuario nuevo con contraseña provisional generada (FR-018b). Solo Admin.

**Body**:
```json
{
  "email": "nueva.persona@sywork.net",
  "username": "nueva.persona",
  "role_id": "uuid"
}
```

**Response 201**:
```json
{
  "user": {
    "id": "uuid",
    "email": "nueva.persona@sywork.net",
    "username": "nueva.persona",
    "role": { "id": "uuid", "name": "Resolutor" },
    "active": true,
    "last_login_at": null,
    "created_at": "2026-07-01T00:00:00Z"
  },
  "provisional_password": "kQ3f8x2ZpN9"
}
```

Nota: `provisional_password` se devuelve en texto plano **únicamente en esta respuesta**; nunca se
persiste en texto plano ni se vuelve a exponer (`GET /api/users/{id}` no la incluye). El Admin
debe compartirla manualmente con la persona por un canal seguro.

**Errors**:
- 400 `{ "error": "invalid_email_domain", "message": "El email debe ser @sywork.net" }`
- 400 `{ "error": "validation_error", "message": "..." }` (campo faltante)
- 404 `{ "error": "role_not_found", "message": "Rol no encontrado" }`
- 409 `{ "error": "email_duplicate", "message": "..." }`
- 409 `{ "error": "username_duplicate", "message": "..." }`

---

### GET /api/users/{id}

Detalle de un usuario. **Response 200**: mismo objeto que un item de la lista.
**Errors**: 400 (UUID invalido), 404

---

### PATCH /api/users/{id}/role

Cambiar rol de un usuario. **Body**: `{ "role_id": "uuid" }`

**Response 200**: objeto usuario actualizado (con el nuevo `role` anidado).

**Errors**:
- 409 `{ "error": "last_admin", "message": "..." }` — no se puede degradar al ultimo Admin activo
- 400 (role_id faltante o invalido), 404 (usuario o rol no encontrado)

---

### PATCH /api/users/{id}/deactivate

**Response 200**: `{ "id": "uuid", "active": false }`
**Errors**: 409 `last_admin`, 400, 404

---

### PATCH /api/users/{id}/activate

Reactivar una cuenta previamente desactivada.

**Response 200**: `{ "id": "uuid", "active": true }`
**Errors**: 409 `{ "error": "already_active" }`, 400, 404

---

## Roles — Base path: `/api/roles`

Roles dinamicos gestionables por Admin (FR-015). El rol `Admin` no puede desactivarse ni
eliminarse.

### GET /api/roles

**Query params**: `page`, `page_size`, `active`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Coordinador",
      "description": "Coordina asignacion de tickets",
      "active": true,
      "permissions": [{ "id": "uuid", "module": "clients", "action": "view" }],
      "created_at": "2026-06-29T00:00:00Z"
    }
  ],
  "total": 4,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/roles

Crear un rol nuevo (sin permisos asignados; usar `PUT .../permissions` despues).

**Body**: `{ "name": "Auditor", "description": "Solo lectura de auditoria" }`

**Response 201**: objeto rol creado (con `Location` header).
**Errors**: 400 (nombre vacio), 409 `name_duplicate`

---

### GET /api/roles/{id}

**Response 200**: objeto rol con sus permisos. **Errors**: 400, 404

---

### PATCH /api/roles/{id}

Actualizar `name`/`description`. **Errors**: 400, 404, 409 `name_duplicate`

---

### PUT /api/roles/{id}/permissions

Reemplaza la lista completa de permisos del rol (no incremental).

**Body**: `{ "permission_ids": ["uuid1", "uuid2"] }`

**Response 200**: objeto rol con los permisos actualizados. **Errors**: 400, 404

---

### PATCH /api/roles/{id}/deactivate

Bloqueado para el rol Admin y para roles con usuarios activos asignados.

**Response 200**: `{ "id": "uuid", "active": false }`
**Errors**: 409 (rol Admin o con usuarios activos), 400, 404

---

### PATCH /api/roles/{id}/activate

**Response 200**: `{ "id": "uuid", "active": true }`
**Errors**: 409 `already_active`, 400, 404

---

## Permissions — Base path: `/api/permissions`

Catalogo de permisos granulares modulo + accion (FR-015b).

### GET /api/permissions

**Response 200**: `{ "items": [{ "id": "uuid", "module": "clients", "action": "view", "description": "..." }], "total": 20 }`

---

### POST /api/permissions

**Body**: `{ "module": "clients", "action": "view", "description": "Ver listado de clientes" }`

**Response 201**: permiso creado.
**Errors**: 400 (module/action vacios), 409 `module_action_duplicate`

---

### DELETE /api/permissions/{id}

**Response 204**: eliminado.
**Errors**: 409 `{ "error": "permission_in_use", "message": "..." }` si esta asignado a algun rol.

---

## Matriz de navegacion prevista (frontend, FR-017)

Los menus visibles dependen de los permisos `view` del rol del usuario autenticado. La tabla
siguiente refleja el seed inicial de 4 roles; Admin puede modificarla en cualquier momento desde
la pantalla Roles y Permisos.

Valores sembrados por `009_roles_permissions_login.py` (`ROLE_PROFILES`), formalizados en
`spec.md` como FR-001, FR-006b, FR-009, FR-010, FR-013 y FR-015b:

| Modulo | Admin | Coordinador | QM | Resolutor |
|--------|-------|------------|-----|---------|
| clients | todo | todo | todo | view |
| projects | todo | todo | view | view |
| resources | todo | todo | todo | view (solo propio, por ownership check aparte) |
| skills | todo | todo | todo | view |
| users | todo (incl. crear) | view | view | view |
| roles | todo | sin acceso | sin acceso | sin acceso |

("todo" = view + create + edit + deactivate del modulo)

Nota: como el enforcement de permisos es solo de frontend (FR-017) y las rutas de API no exigen
JWT aún, esta tabla hoy solo determina qué ítems de menú vería cada rol — el enforcement de
backend por permiso queda diferido a una fase futura.
