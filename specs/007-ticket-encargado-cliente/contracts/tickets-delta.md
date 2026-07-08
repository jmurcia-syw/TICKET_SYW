# Contrato — Delta sobre `tickets` y `client-contacts`

Cambios sobre los endpoints ya existentes (Fase 1/2.1). No se agregan namespaces nuevos.

## `POST /api/tickets`

**Input** (`TicketInput`) — nuevo campo opcional:

| Campo | Tipo | Requerido | Notas |
|-------|------|-----------|-------|
| `client_contact_id` | string (UUID) | No | Debe pertenecer al `client_id` enviado (409 `client_contact_mismatch` si no); ignorado si el caller tiene rol Encargado (ese flujo no lo lee, ver `tickets.py` rama `is_encargado`). |

**Nuevas respuestas de error**:
- `404 not_found` — `client_contact_id` no existe.
- `409 client_contact_mismatch` — el Encargado indicado no pertenece al `client_id` del ticket.

## `PATCH /api/tickets/{id}`

**Input** — `client_contact_id` se agrega a `PATCHABLE_FIELDS`.

**Nuevas respuestas de error**:
- `404 not_found` — `client_contact_id` no existe.
- `409 client_contact_mismatch` — no pertenece al `client_id` actual del ticket.
- `409 field_locked` — ticket en estado `cerrado`/`cancelado` (mismo mecanismo ya existente,
  `locked_fields`).
- `409 requester_immutable` — el ticket fue creado por un usuario con rol Encargado; el Encargado
  solicitante no se puede editar manualmente (FR-009).

## `GET /api/tickets/{id}` (detalle)

**Output** (`TicketDetail`) — nuevo campo:

| Campo | Tipo | Notas |
|-------|------|-------|
| `client_contact_id` | string \| null | Valor crudo (ver data-model.md) — permite al frontend distinguir origen manual vs. automático. |

`requester` (ya existente) no cambia de forma; ahora puede resolverse desde `client_contact_id`
además del comportamiento ya existente (creador con rol Encargado).

`locked_fields` (ya existente) — puede incluir `client_contact_id` cuando el ticket está
`cerrado`/`cancelado`, igual que otros campos de clasificación.

## `GET /api/client-contacts`

**Cambio de permiso** (antes: `client_contacts:manage` únicamente):

| Antes | Ahora |
|-------|-------|
| `client_contacts:manage` | `client_contacts:manage` **OR** `tickets:create` **OR** `tickets:edit` |

`POST /api/client-contacts` no cambia — sigue exigiendo `client_contacts:manage` exclusivamente.

**Nueva respuesta**:
- `403` ahora solo aplica a callers sin ninguno de los tres permisos (antes aplicaba a cualquiera
  sin `client_contacts:manage`, incluyendo Resolutor).
