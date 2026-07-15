# Contract: Accesos y conexiones del Cliente (spec 018)

Endpoints nuevos sobre `backend/api/routes/clients.py`, mismo namespace Flask-RESTX que ya
documenta `clients`. Todos requieren el mismo permiso de módulo `clients` que ya rige
creación/edición/detalle de Cliente — no se introduce un permiso nuevo. El campo `password` de
la respuesta solo se incluye cuando el caller tiene `include_sensitive=True` (mismo criterio que
`vpn_ips`/`vpn_credentials` hoy).

## GET /api/clients/{client_id}/access — listar accesos del cliente

**200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "client_id": "uuid",
      "access_type": "vpn | system_url | remote_desktop",
      "environment": "dev | test | prod | null",
      "username": "string | null",
      "password": "string | null (solo si include_sensitive)",
      "host": "string | null",
      "notes": "string | null",
      "created_at": "iso8601",
      "updated_at": "iso8601"
    }
  ]
}
```

**404**: cliente no encontrado.

## POST /api/clients/{client_id}/access — crear un registro de acceso

**Body**:
```json
{
  "access_type": "vpn | system_url | remote_desktop",
  "environment": "dev | test | prod | null",
  "username": "string | null",
  "password": "string | null",
  "host": "string | null",
  "notes": "string | null"
}
```

**201**: el registro creado (misma forma que un ítem de `GET .../access`), con
`Location: /api/clients/{client_id}/access/{id}`.

**400** `validation_error`: `access_type` inválido, o `environment` presente cuando
`access_type != 'system_url'`.

**404**: cliente no encontrado.

## PATCH /api/clients/{client_id}/access/{access_id} — editar un registro de acceso

**Body**: cualquier subconjunto de los campos de creación (PATCH parcial, mismo patrón que
`PATCH /api/clients/{id}`).

**200**: el registro actualizado. **400/404**: igual que arriba, más 404 si `access_id` no
pertenece a `client_id`.

## DELETE /api/clients/{client_id}/access/{access_id} — eliminar un registro de acceso

**204**. **404** si `access_id` no existe o no pertenece a `client_id`. No afecta a los demás
registros del cliente (FR-002) — sin borrado en cascada más allá del propio registro.

## GET /api/clients/{client_id}/access-attachments — listar adjuntos de la sección

**200**:
```json
{
  "items": [
    {"id": "uuid", "filename": "string", "content_type": "string", "size_bytes": 0, "created_at": "iso8601"}
  ]
}
```

## POST /api/clients/{client_id}/access-attachments — subir un adjunto

**Body**: `multipart/form-data`, campo `file`. Mismas reglas de tipo/tamaño ya vigentes en
`attachment_storage.validate` (10 MB, extensiones ya permitidas para adjuntos de Tickets).

**201**: el adjunto creado (misma forma que un ítem del listado).

**400** `attachment_error`: tipo o tamaño no permitido (mismo código ya usado en adjuntos de
Tickets).

## GET /api/clients/{client_id}/access-attachments/{attachment_id} — descargar un adjunto

**200**: el archivo (`Content-Type` según `content_type` guardado). **404**: adjunto no
encontrado o no pertenece a `client_id`. Mismo mecanismo de resolución segura de ruta que
`attachment_storage.open_path` (previene path traversal).

## DELETE /api/clients/{client_id}/access-attachments/{attachment_id} — eliminar un adjunto

**204**. **404** si no existe o no pertenece a `client_id`.

## Sin cambios en endpoints existentes

`GET/POST/PATCH /api/clients` y `GET /api/clients/{id}` mantienen su forma actual —
`vpn_ips`/`vpn_credentials` siguen presentes en la respuesta como columnas legacy (ver
`data-model.md`, "Notas de migración") pero dejan de editarse desde el formulario de
creación/edición del frontend (reemplazadas por la pestaña de Accesos y conexiones).
