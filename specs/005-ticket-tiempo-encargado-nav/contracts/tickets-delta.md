# API Contract Delta: `tickets` — visibilidad "solo propios" y creación por Encargado

Extiende `specs/002-fase1-tickets/contracts/tickets.md`. Solo se documentan los cambios; el resto
del contrato (FSM, comentarios, cierre, cancelación) no se modifica.

## GET /api/tickets — permiso `tickets:view` **o** `tickets:view_own`

- Con `tickets:view` (Admin/Coordinador/QM/Resolutor, sin cambios): ve todos los tickets, igual
  que hoy.
- Con solo `tickets:view_own` (Encargado): la lista se filtra automáticamente por
  `created_by = <usuario autenticado>`, ignorando cualquier otro filtro de asignación/cliente que
  intente enviar.

## GET /api/tickets/{id} — permiso `tickets:view` **o** `tickets:view_own`

- Con solo `tickets:view_own`: si el ticket solicitado no fue creado por el propio usuario, la
  respuesta es **404** (no 403 — evita confirmar la existencia de tickets ajenos).

## POST /api/tickets — permiso `tickets:create` (ya existente, ahora incluye a Encargado)

Cuando el usuario autenticado tiene rol Encargado:

- El body solo requiere `title` y `description`. Los campos `ticket_type`, `priority`,
  `severity`, `client_id` — si el Encargado los envía, se ignoran.
- El backend completa automáticamente: `ticket_type: "incident"`, `priority: "medium"`,
  `severity: "s3"`, y `client_id` resuelto desde `client_contacts` para ese usuario.
- Si el usuario Encargado no tiene fila en `client_contacts` (caso administrativo anómalo) →
  **409** `no_client_contact` ("tu cuenta no tiene un cliente asociado; contactá al equipo de
  soporte").
- Si el Cliente vinculado está inactivo → **409** `client_inactive` (mismo código que el
  contrato original de Fase 1).

Para el resto de los roles (Admin/Coordinador/QM/Resolutor), el contrato no cambia: los 6 campos
siguen siendo obligatorios como hoy.

## Detalle del ticket — campo de presentación nuevo

`GET /api/tickets/{id}` agrega, dentro del objeto de respuesta ya existente:

```json
{
  "...": "...",
  "requester": { "id": "uuid", "name": "...", "is_encargado": true } | null
}
```

`requester` es `created_by` resuelto a nombre + un flag `is_encargado` (true si el creador tiene
rol Encargado). El frontend usa este flag para mostrar la etiqueta "Encargado" en vez de "Creado
por" en el detalle (FR-009).

---

# API Contract: `client_contacts` (nuevo — alta de Encargados)

**Auth**: JWT Bearer + permiso `client_contacts:manage` (Admin, Coordinador).

## POST /api/client-contacts

Body: `{ "email": "...", "username": "...", "client_id": "uuid" }` — crea el `User` (rol
Encargado) y su fila en `client_contacts` en una sola operación atómica.

**Response 201**: `{ "id": "uuid", "user_id": "uuid", "client_id": "uuid", "email": "...", "client_name": "..." }`

**Response 409**: `email_in_use` si ya existe un usuario con ese email.

**Response 404**: `client_not_found` si el `client_id` no existe o está inactivo.

## GET /api/client-contacts

Lista paginada de Encargados con su Cliente asociado. Query: `client_id` (opcional), `page`,
`page_size`.
