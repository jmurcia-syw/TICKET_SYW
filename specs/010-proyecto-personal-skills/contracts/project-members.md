# Contract: Personal del Proyecto (project members)

Módulo de permisos: `projects` (existente) — GET requiere `projects:view`, mutaciones
`projects:edit`. Todas las rutas exigen JWT.

## GET /api/projects/{project_id}/members

Lista el personal asignado al proyecto, con el rol derivado del usuario.

**Query params**: `role_name` (opcional — p. ej. `Usuario/cliente`, filtra por nombre de rol).

**200**:
```json
{
  "items": [
    {
      "id": "uuid-member",
      "project_id": "uuid",
      "user_id": "uuid",
      "full_name": "Nombre (username si no hay recurso)",
      "email": "persona@dominio.com",
      "role_name": "Resolutor",
      "assigned_at": "2026-07-09T12:00:00+00:00"
    }
  ],
  "total": 1
}
```

**Errores**: 400 `validation_error` (UUID inválido) · 401 · 403 · 404 `not_found` (proyecto) ·
500.

## POST /api/projects/{project_id}/members

Asigna un usuario activo al proyecto.

**Body**: `{ "user_id": "uuid" }`

**201**: objeto member (shape del GET). Header `Location`.

**Errores**: 400 `validation_error` · 404 `not_found` (proyecto o usuario) · 409
`already_member` (ya asignado — la asignación es única) · 409 `user_inactive` (usuario
desactivado) · 401/403/500.

## DELETE /api/projects/{project_id}/members/{member_id}

Desasigna a la persona del proyecto. Por cascade sale de todos los subgrupos. No afecta
registros históricos (tickets, tiempos).

**204** sin cuerpo.

**Errores**: 400 · 404 `not_found` (member no existe o no pertenece al proyecto) · 401/403/500.
