# Data Model: Historial de Estados con SLA Visual y Reasignación de Resolutores

## Entidades

### Transición de estado (existente, enriquecida en lectura)

`ticket_status_transitions` (tabla existente, **sin cambio de esquema**) — `StatusTransitionModel`
(`backend/infra/models/ticket_model.py:106`).

| Campo | Origen | Notas |
|-------|--------|-------|
| `id`, `ticket_id`, `from_status`, `to_status`, `actor_id`, `comment_id`, `created_at` | Persistidos (sin cambio) | — |
| `elapsed_seconds` | **Derivado en lectura** | Segundos disponibles (Decisión 2, research.md) entre la transición anterior y esta. `null` en la primera transición del ticket (spec Edge Cases). |
| `sla_phase_closed` | **Derivado en lectura** | `"contacto"` \| `"ejecucion"` \| `null` — indica si esta transición cierra una fase de SLA (Decisión 1). |
| `sla_met` | **Derivado en lectura** | `true` (✅) / `false` (⚠️❌) / `null` (sin SLA aplicable — `sla_phase_closed` es `null`, o el ticket no tiene regla de SLA). |

Se calcula en `TicketRepository.list_transitions` (o una función nueva en `sla_service.py`,
p. ej. `compute_transition_compliance(ticket, transitions, resource, holidays, ...)`) reutilizando
el mismo contexto (`_resolve_sla_context`) que ya arma `_ticket_detail` para `ticket.sla`.

### Reasignación (nueva entidad)

`ticket_reassignments` (tabla nueva, append-only) — análoga a `AssignmentModel`.

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID PK | `gen_random_uuid()` |
| `ticket_id` | UUID FK → `tickets.id` | — |
| `actor_id` | UUID FK → `users.id` | Quien ejecuta la reasignación |
| `previous_assignee_id` | UUID FK → `resources.id`, nullable | `null` si el ticket no tenía resolutor previo |
| `new_assignee_id` | UUID FK → `resources.id` | Nuevo resolutor |
| `reason` | Text, nullable | Motivo opcional (error de asignación / escalamiento) |
| `created_at` | Timestamptz | `server_default=func.now()` |

**Validaciones de dominio** (en un `ReassignmentService` nuevo, Capa 1, sin import de
Flask/SQLAlchemy):
- Rechaza si `new_assignee_id == ticket.assignee_id` (FR-010 — no genera entrada duplicada).
- Rechaza si `ticket.status` es terminal (`cerrado`/`cancelado`) (FR-007).
- Rechaza si el nuevo recurso no existe o está inactivo (mismo criterio que `AssignmentService`).
- No rechaza (solo advierte) si el nuevo recurso no tiene las Skills requeridas del ticket
  (FR-011) — la advertencia es responsabilidad de la Capa 3 (frontend), el dominio solo expone el
  dato (`missing_skills: list[str]`) en el resultado.

**Relaciones**: `ticket_reassignments.ticket_id` → mismo ticket que sus `transitions`/`assignments`;
se expone en `_ticket_detail` como un nuevo bloque `reassignments: TicketReassignment[]`, mostrado
junto al Historial de Estados en el frontend (mismo timeline de actividad, orden por `created_at`).

## Contrato de API (extensión)

Ver [contracts/reassign.md](contracts/reassign.md) para el detalle del endpoint nuevo y el shape
enriquecido de `transitions`.
