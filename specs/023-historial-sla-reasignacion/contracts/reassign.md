# Contrato: Reasignación de resolutor + Historial de estados enriquecido

## `POST /api/tickets/{ticket_id}/reassign`

Endpoint nuevo e independiente de `/assign` (research.md Decisión 3). No dispara el FSM; solo
cambia `assignee_id` y registra el evento.

**Auth**: JWT + permiso `tickets:assign` (mismo permiso que `/assign`).

### Request

```json
{
  "assignee_id": "uuid-del-nuevo-resolutor",
  "reason": "Escalamiento por complejidad técnica"
}
```

- `assignee_id` (string, requerido): UUID del recurso al que se reasigna.
- `reason` (string, opcional): motivo de la reasignación.

### Responses

| Código | Caso | Body |
|--------|------|------|
| 200 | Reasignación registrada | `{ "ticket": <TicketDetail>, "reassignment": { "id", "previous_assignee_id", "new_assignee_id", "missing_skills": string[] } }` |
| 400 | `assignee_id` faltante, o igual al resolutor actual (FR-010) | `{ "error": "validation_error", "message": "..." }` |
| 401 | No autenticado | `{ "error": "unauthorized", "message": "..." }` |
| 403 | Sin permiso `tickets:assign` | `{ "error": "forbidden", "message": "..." }` |
| 404 | Ticket o recurso no encontrado | `{ "error": "not_found", "message": "..." }` |
| 409 | Ticket en estado terminal (`cerrado`/`cancelado`, FR-007) | `{ "error": "ticket_closed", "message": "..." }` |
| 500 | Error interno | `{ "error": "server_error", "message": "..." }` |

`missing_skills` viene vacío (`[]`) cuando el nuevo resolutor cumple todas las Skills requeridas
del ticket; si no, lista los códigos faltantes para que el frontend muestre la advertencia no
bloqueante (FR-011) — la reasignación ya se aplicó de todas formas.

## Extensión de `GET /api/tickets/{ticket_id}` — bloque `transitions`

Cada elemento de `transitions[]` agrega tres campos derivados (no persistidos):

```json
{
  "id": "uuid",
  "from_status": "contacto",
  "to_status": "en_analisis",
  "actor_id": "uuid",
  "comment_id": "uuid-or-null",
  "created_at": "2026-07-20T14:03:00Z",
  "elapsed_seconds": 5400,
  "sla_phase_closed": null,
  "sla_met": null
}
```

- Primera transición del ticket: `elapsed_seconds: null`, `sla_phase_closed: null`, `sla_met: null`.
- Transición que cierra la fase Contacto (entrar a `contacto`, ver research.md Decisión 1):
  `sla_phase_closed: "contacto"`, `sla_met: true|false` según `sla_contact_result`.
- Transición que cierra la fase Ejecución (entrar a `resuelto`/`cerrado`/`cancelado`):
  `sla_phase_closed: "ejecucion"`, `sla_met: true|false`.
- Cualquier otra transición interna de una fase, o ticket sin regla de SLA (`sla_rule_id` nulo):
  `elapsed_seconds` con el valor calculado, `sla_phase_closed: null`, `sla_met: null` (FR-003).

## Nuevo bloque `reassignments` en `GET /api/tickets/{ticket_id}`

```json
{
  "reassignments": [
    {
      "id": "uuid",
      "actor_id": "uuid",
      "previous_assignee_id": "uuid-or-null",
      "new_assignee_id": "uuid",
      "reason": "string-or-null",
      "created_at": "2026-07-21T09:00:00Z"
    }
  ]
}
```
