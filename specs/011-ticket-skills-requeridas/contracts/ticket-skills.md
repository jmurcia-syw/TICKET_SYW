# Contract: Skills Requeridas del Ticket

## `PATCH /api/tickets/{id}/skills`

Reemplaza el conjunto completo de Skills requeridas de un Ticket/Tarea/Subtarea (no es
incremental — envía siempre la lista final deseada). Mismo criterio que
`PATCH /api/resources/{id}/skills`.

**Auth**: JWT + permiso `tickets:edit` (Coordinador, Resolutor, Admin — FR-005).

**No dispara**: notificaciones, transición de estado, ni exige comentario tipificado (FR-006).
Funciona en cualquier estado del ticket, incluidos Cerrado y Cancelado (FR-002).

### Request

```json
{
  "skill_ids": ["<uuid-skill-1>", "<uuid-skill-2>"]
}
```

- `skill_ids`: array de UUIDs de Skills del catálogo existente (spec `010`). Array vacío `[]` es
  válido (deja el ticket sin Skills requeridas). IDs que no correspondan a un Skill existente se
  ignoran silenciosamente (mismo comportamiento que el endpoint análogo de recursos).

### Response 200

```json
{
  "id": "<uuid-ticket>",
  "ticket_number": "TK-000123",
  "...": "resto de los campos del detalle del ticket, sin cambios",
  "skills": [
    { "id": "<uuid-skill-1>", "code": "JDE_GL", "label": "JDE General Ledger" },
    { "id": "<uuid-skill-2>", "code": "SQL_JDE", "label": "SQL sobre JDE" }
  ]
}
```

### Errores

| Status | code | Motivo |
|--------|------|--------|
| 400 | `validation_error` | `id` (ticket) inválido o cuerpo sin `skill_ids` como array |
| 401 | — | JWT ausente o inválido |
| 403 | — | Falta el permiso `tickets:edit` |
| 404 | `not_found` | El ticket no existe |
| 500 | `server_error` | Error interno |

## `GET /api/tickets/{id}` (extensión, sin romper compatibilidad)

El payload de detalle existente agrega el campo `skills` (mismo shape que arriba) junto al resto
de la clasificación del ticket (`tool_id`, `process_id`, etc.). Ticket sin Skills requeridas
devuelve `"skills": []` (FR-004, User Story 3 AC2).

No se agrega ningún campo `skill_ids` al `POST /api/tickets` (creación) ni al
`PATCH /api/tickets/{id}` genérico — la asociación de Skills se gestiona exclusivamente por el
endpoint dedicado de arriba (research.md, Decisión 2).

## `DELETE /api/skills/{id}` (extensión, FR-007)

El chequeo `skill_in_use` que ya bloqueaba eliminar una Skill asignada a algún Recurso activo
ahora también considera si la Skill está asignada como requerida a algún ticket (cualquier
estado). Response `409 skill_in_use` sin cambios de shape, agrega `ticket_count` cuando aplica.
