# Contract: Client Contacts (Usuario/cliente) — cambios

Endpoint existente `GET /api/client-contacts` (spec `007`). Reglas de acceso sin cambios
(`client_contacts:manage`, o `tickets:create`/`tickets:edit`).

## GET /api/client-contacts — filtros nuevos

**Query params**:
- `client_id` (existente — se mantiene por compatibilidad).
- `project_id` (**nuevo**, opcional): devuelve solo los Usuario/cliente cuyo `user_id` está en
  `project_members` de ese proyecto. Es la fuente del selector de solicitante del ticket
  (spec `010`, US2).
- `email` (**nuevo**, opcional): búsqueda parcial case-insensitive sobre el email.
- `username` (**nuevo**, opcional): búsqueda parcial case-insensitive sobre el usuario.
- Los filtros se combinan en AND.

**200**: shape actual (`items[]` con `id, user_id, client_id, email, username, client_name,
created_at`) **+ `projects[]`** (`{id, name}` de los proyectos vinculados vía
`project_members`).

**Errores**: sin cambios (400/401/403/500).

## POST /api/client-contacts — alta por Proyecto

La relación operativa del Usuario/cliente es con el **Proyecto** (requerimiento del
solicitante, spec `010`): el body acepta `project_id` y a partir de él (a) el `client_id` se
**deriva** del proyecto y (b) se crea automáticamente la membresía en `project_members`.
`client_id` directo se mantiene como **forma legada** (spec `007`) para contactos aún sin
proyecto. Se requiere uno de los dos (400 si faltan ambos).

**Errores nuevos**: 404 `not_found` (proyecto), 409 `project_inactive`.

## GET /api/client-contacts/me/projects (nuevo)

Proyectos **activos** a los que está vinculado el usuario autenticado (vía `project_members`).
Fuente del selector de proyecto del autoservicio del Usuario/cliente (FR-007). Solo requiere
JWT (`@require_authenticated`) — cada usuario ve únicamente sus propias membresías.

**200**:
```json
{ "items": [ { "id": "uuid", "name": "Proyecto A", "client_id": "uuid", "active": true } ], "total": 1 }
```

## POST /api/client-contacts — cambios de texto y rol

- El rol se resuelve por la constante `USUARIO_CLIENTE_ROLE_NAME = "Usuario/cliente"` (antes
  literal `"Encargado"`).
- Error 500 `role_not_configured` ahora dice "El rol Usuario/cliente no está configurado".
- Descripciones de Swagger actualizadas ("Encargado" → "Usuario/cliente").
- Comportamiento funcional sin cambios (FR-003).
