# API Contract: Users & Roles

**Base path**: `/api/users`
**Auth**: JWT Bearer requerido
**Roles**: Admin (CRUD completo) — otros roles: 403 en la mayoria de endpoints

---

## GET /api/users

Lista de usuarios del sistema. Solo Admin.

**Query params**: `page`, `page_size`, `search` (email/nombre), `role`, `active`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "email": "juan.murcia@sywork.net",
      "role": "coordinator",
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

## GET /api/users/me

Perfil del usuario autenticado. Todos los roles.

**Response 200**:
```json
{
  "id": "uuid",
  "email": "carlos@sywork.net",
  "role": "resolver",
  "active": true,
  "resource_id": "uuid"
}
```

---

## PATCH /api/users/{id}/role

Cambiar rol de un usuario. Solo Admin.

**Body**: `{ "role": "coordinator" }`

**Response 200**: objeto usuario actualizado.

**Errors**:
- 409 `{ "error": "last_admin", "message": "No se puede cambiar el rol del ultimo Admin activo" }`
- 400 `{ "error": "invalid_role", "message": "Rol invalido. Valores permitidos: admin, coordinator, qm, resolver" }`
- 401, 403, 404

---

## PATCH /api/users/{id}/deactivate

Desactivar cuenta de usuario. Solo Admin.

**Response 200**: `{ "id": "uuid", "active": false }`

**Errors**:
- 409 `{ "error": "last_admin", "message": "No se puede desactivar al ultimo Admin activo" }`
- 401, 403, 404

---

## Matriz de permisos completa

| Endpoint | Admin | Coordinator | QM | Resolver |
|----------|-------|------------|-----|---------|
| GET /api/clients | SI | SI | NO | NO |
| POST /api/clients | SI | SI | NO | NO |
| PATCH /api/clients/{id} | SI | SI | NO | NO |
| GET /api/projects | SI | SI | NO | NO |
| POST /api/projects | SI | SI | NO | NO |
| GET /api/resources | SI | SI | SI | solo propio |
| POST /api/resources | SI | NO | NO | NO |
| PATCH /api/resources/{id} | SI | NO | NO | solo propio (campos limitados) |
| GET /api/skills | SI | SI | SI | SI |
| POST /api/skills | SI | NO | NO | NO |
| DELETE /api/skills/{id} | SI | NO | NO | NO |
| GET /api/users | SI | NO | NO | NO |
| GET /api/users/me | SI | SI | SI | SI |
| PATCH /api/users/{id}/role | SI | NO | NO | NO |
| PATCH /api/users/{id}/deactivate | SI | NO | NO | NO |
