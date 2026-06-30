# API Contract: Projects

**Base path**: `/api/projects`
**Auth**: JWT Bearer requerido
**Roles**: Admin y Coordinator (CRUD) — QM y Resolver: 403

---

## GET /api/projects

**Query params**: `page`, `page_size`, `search`, `client_id` (UUID, filtro por cliente), `active` (bool)

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "client_id": "uuid",
      "client_name": "Aris Mining Corp.",
      "name": "Aris – Lower Mine",
      "description": "Implementacion JDE modulo GL",
      "active": true,
      "start_date": "2026-01-15",
      "end_date_estimated": "2026-12-31",
      "created_at": "2026-06-29T00:00:00Z"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20
}
```

---

## GET /api/projects/{id}

**Response 200**: objeto proyecto completo.
**Errors**: 401, 403, 404

---

## POST /api/projects

**Body**:
```json
{
  "client_id": "uuid",
  "name": "Aris – Lower Mine",
  "description": "Implementacion JDE modulo GL",
  "start_date": "2026-01-15",
  "end_date_estimated": "2026-12-31"
}
```

**Response 201**: objeto proyecto creado.

**Errors**:
- 400 `{ "error": "client_inactive", "message": "No se puede crear un proyecto para un cliente inactivo" }`
- 400 `{ "error": "name_duplicate", "message": "Ya existe un proyecto con ese nombre para este cliente" }`
- 400 `{ "error": "invalid_dates", "message": "La fecha de fin no puede ser anterior a la fecha de inicio" }`
- 401, 403, 404 (client_id no encontrado)

---

## PATCH /api/projects/{id}

Actualizar proyecto parcialmente.
**Response 200**: objeto proyecto actualizado.
**Errors**: 400, 401, 403, 404

---

## PATCH /api/projects/{id}/deactivate

**Response 200**: `{ "id": "uuid", "active": false }`
**Errors**: 401, 403, 404
