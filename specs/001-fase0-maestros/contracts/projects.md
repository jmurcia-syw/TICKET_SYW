# API Contract: Projects

**Base path**: `/api/projects`
**Auth**: JWT Bearer requerido
**Roles con acceso (permisos sembrados)**: Admin y Coordinador — CRUD completo.
QM — solo lectura (`projects: view`). Resolutor — solo lectura (`projects: view`).
Enforcement de backend diferido (FR-017); esta tabla describe el permiso de módulo previsto
para el menú del frontend, no un 403 real de la API hoy.

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

---

## PATCH /api/projects/{id}/activate

Reactivar un proyecto previamente desactivado.

**Response 200**: `{ "id": "uuid", "active": true }`
**Errors**: 409 `{ "error": "already_active" }`, 401, 403, 404

---

## Ampliación SDD V3 (2026-07-02, FR-030)

Los payloads de proyecto (list, detail, create, update) incluyen ahora:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| overview | string \| null | Overview / resumen ejecutivo |
| sale_services_usd | number \| null | Valor de venta de servicios en USD (>= 0) |
| sale_licenses_usd | number \| null | Valor de venta de licencias en USD (>= 0) |
| sale_subscriptions_usd | number \| null | Valor de venta de suscripciones en USD (>= 0) |
| components_sold | string \| null | Componentes vendidos |

Montos negativos o no numericos → 400 `validation_error` con mensaje en español.
