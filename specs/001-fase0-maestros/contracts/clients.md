# API Contract: Clients

**Base path**: `/api/clients`
**Auth**: JWT Bearer requerido en todos los endpoints (enforcement de backend diferido, ver FR-017)
**Roles con acceso (FR-001, permisos sembrados en `009_roles_permissions_login.py`)**: Admin,
Coordinador y QM — lectura y escritura completa (`clients`: view/create/edit/deactivate).
Resolutor — solo lectura (`clients: view`). Datos sensibles (`vpn_ips`, `vpn_credentials`)
visibles únicamente para Admin/Coordinador (FR-003), independientemente del permiso de módulo.

---

## GET /api/clients

Lista paginada de clientes.

**Query params**:
| Param | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| page | int | 1 | Numero de pagina |
| page_size | int | 20 | Registros por pagina (max 100) |
| search | string | — | Busqueda por nombre (ILIKE) |
| active | bool | — | Filtrar por estado activo/inactivo |

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Aris Mining Corp.",
      "slug": "aris-mining-corp",
      "active": true,
      "contact_name": "Juan Perez",
      "contact_email": "juan@aris.com",
      "contact_phone": "+56 9 1234 5678",
      "created_at": "2026-06-29T00:00:00Z",
      "updated_at": "2026-06-29T00:00:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20
}
```

Nota: `vpn_ips` y `vpn_credentials` NO se incluyen en el listado. Solo en GET /api/clients/{id}.

---

## GET /api/clients/{id}

Detalle de un cliente. Incluye datos sensibles para Admin/Coordinador.

**Response 200**:
```json
{
  "id": "uuid",
  "name": "Aris Mining Corp.",
  "slug": "aris-mining-corp",
  "active": true,
  "contact_name": "Juan Perez",
  "contact_email": "juan@aris.com",
  "contact_phone": "+56 9 1234 5678",
  "vpn_ips": "10.0.0.1, 10.0.0.2",
  "vpn_credentials": "usuario: admin / pass: ****",
  "notes": "Proyecto minero fase 2",
  "created_at": "2026-06-29T00:00:00Z",
  "updated_at": "2026-06-29T00:00:00Z"
}
```

**Errors**: 401 (sin token), 403 (rol insuficiente), 404 (no encontrado)

---

## POST /api/clients

Crear cliente. Solo Admin y Coordinador.

**Body**:
```json
{
  "name": "Aris Mining Corp.",
  "contact_name": "Juan Perez",
  "contact_email": "juan@aris.com",
  "contact_phone": "+56 9 1234 5678",
  "vpn_ips": "10.0.0.1, 10.0.0.2",
  "vpn_credentials": "usuario: admin / pass: secreto",
  "notes": "Proyecto minero"
}
```

**Response 201**: objeto cliente creado (sin vpn_credentials en respuesta).

**Errors**:
- 400 `{ "error": "name_duplicate", "message": "Ya existe un cliente con ese nombre" }`
- 401, 403

---

## PATCH /api/clients/{id}

Actualizar cliente parcialmente. Solo Admin y Coordinador.

**Body**: cualquier subconjunto de campos del POST.

**Response 200**: objeto cliente actualizado.

**Errors**: 400 (validacion), 401, 403, 404

---

## PATCH /api/clients/{id}/deactivate

Desactivar un cliente. Solo Admin.

**Body**: ninguno.

**Response 200**:
```json
{
  "id": "uuid",
  "active": false,
  "active_projects_count": 3,
  "open_tickets_count": 7,
  "warning": "El cliente tiene 3 proyectos activos y 7 tickets abiertos. Confirma la desactivacion."
}
```

Nota: Este endpoint devuelve el estado de impacto. El cliente queda desactivado al llamar.
La advertencia es informativa — la accion ya se ejecuto. El frontend DEBE mostrar dialogo de
confirmacion antes de llamar a este endpoint.

**Errors**: 401, 403, 404

---

## PATCH /api/clients/{id}/activate

Reactivar un cliente previamente desactivado. Solo Admin/Coordinador.

**Body**: ninguno.

**Response 200**: `{ "id": "uuid", "active": true }`

**Errors**: 409 `{ "error": "already_active" }`, 401, 403, 404
