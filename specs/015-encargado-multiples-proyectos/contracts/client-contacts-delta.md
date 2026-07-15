# Contract: Client Contacts (Usuario/cliente) — cambios (spec 015)

Cambios sobre el recurso existente `/api/client-contacts` (spec 007/010). Permiso sin cambios:
`client_contacts:manage` para escritura; lectura además permitida con `tickets:create` /
`tickets:edit`.

## POST /api/client-contacts — alta con varios Proyectos

**Body** (reemplaza `project_id` singular):

```json
{
  "email": "contacto@clienteexterno.com",
  "username": "nombre.apellido",
  "project_ids": ["uuid-proyecto-a", "uuid-proyecto-b"],
  "client_id": "uuid-cliente (forma legada, sin proyecto)"
}
```

- `project_ids`: lista opcional de 0..N UUIDs de Proyecto. Se requiere `project_ids` (con al
  menos 1 elemento) **o** `client_id` — igual que hoy, ahora con lista en vez de escalar.
- Duplicados dentro de `project_ids` se ignoran (deduplicados antes de procesar).
- El `client_id` de la cuenta se deriva de los Proyectos (deben compartir todos el mismo
  Cliente — `resolve_common_client`, ver `data-model.md`).
- Se crea una fila `project_members` por cada `project_id` en la lista.

**Errores**:
- 400 `validation_error`: falta `project_ids`/`client_id`, o los Proyectos pertenecen a Clientes
  distintos.
- 404 `not_found`: algún `project_id` no existe.
- 409 `project_inactive`: algún Proyecto está inactivo.
- 409 `email_in_use`: sin cambios.

**200/201**: shape de respuesta sin cambios (`id, user_id, client_id, email, client_name,
provisional_password`).

## POST /api/client-contacts/{contact_id}/projects (nuevo)

Agrega un Proyecto a un Usuario/cliente ya existente.

**Body**: `{ "project_id": "uuid" }`

**Validaciones**: el Proyecto debe existir y estar activo, pertenecer al mismo `client_id` que
el contacto, y el contacto no debe ya ser miembro de ese Proyecto.

**201**: `{ "id": "uuid-project-member", "project_id": "uuid", "name": "Proyecto X" }`

**Errores**: 400 (Cliente distinto), 404 (contacto o proyecto no encontrado), 409 (proyecto
inactivo o ya asignado).

## DELETE /api/client-contacts/{contact_id}/projects/{project_id} (nuevo)

Quita al Usuario/cliente de ese Proyecto (elimina la fila `project_members` correspondiente).
No afecta al `client_contacts` ni a tickets históricos.

**204**: sin contenido.

**Errores**: 404 (contacto no encontrado, o el contacto no es miembro de ese Proyecto).

## GET /api/client-contacts — sin cambios de contrato

El campo `projects[]` en la respuesta ya soportaba 0..N elementos (spec 010); ahora refleja
correctamente altas con varios Proyectos y los agregados/quitados posteriores.
