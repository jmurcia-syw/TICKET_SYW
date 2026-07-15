# Quickstart: Skills Requeridas en el Ticket

Guía de validación end-to-end contra Docker real.

## Prerequisitos

```bash
docker compose up --build -d
docker compose logs backend | grep "Running upgrade"   # migración 027_ticket_skills aplicada
curl http://localhost:5000/health/
```

Login como Coordinador, QM o Admin (roles con permiso `tickets:edit` en este sistema — el
Resolutor no lo tiene) con al menos un ticket, y como Admin para el escenario de catálogo.

## Escenario 0 — Migración

1. Tras `alembic upgrade head`: `SELECT COUNT(*) FROM ticket_skills` → `0`.
2. Todos los tickets existentes siguen respondiendo en `GET /api/tickets/{id}` con `"skills": []`.

## Escenario 1 — Asignar Skills requeridas (US1, SC-001)

1. Abrir el detalle de un ticket sin Skills requeridas. `GET /api/tickets/{id}` → `"skills": []`.
2. `PATCH /api/tickets/{id}/skills` con `{"skill_ids": ["<id-JDE_GL>", "<id-SQL_JDE>"]}`.
3. **Esperado**: `200`, el detalle del ticket ahora lista ambas Skills.

## Escenario 2 — Cambiar Skills en cualquier estado (US2, SC-003)

1. Sobre un ticket en estado `Cerrado` (o `Cancelado`), sin reabrirlo ni comentar:
   `PATCH /api/tickets/{id}/skills` con un `skill_ids` distinto al actual.
2. **Esperado**: `200`; el cambio se aplica sin transición de estado ni notificación generada.

## Escenario 3 — Sin duplicados (FR-003)

1. `PATCH /api/tickets/{id}/skills` con `skill_ids` repitiendo el mismo UUID dos veces.
2. **Esperado**: el ticket queda con esa Skill una sola vez (la PK compuesta de `ticket_skills`
   lo garantiza).

## Escenario 4 — Visualización (US3, SC-004)

1. Un usuario distinto al que asignó las Skills, con acceso de lectura al ticket, hace
   `GET /api/tickets/{id}`.
2. **Esperado**: ve las mismas Skills requeridas listadas, sin necesidad de otra pantalla.

## Escenario 5 — Eliminar una Skill en uso por un ticket (Edge Case, FR-007)

1. Con una Skill ya asignada como requerida a un ticket, intentar eliminarla:
   `DELETE /api/skills/{id}` (Admin, catálogo spec `010`).
2. **Esperado**: `409 skill_in_use` — el catálogo de Skills no tiene "desactivar", solo eliminar;
   el sistema lo bloquea igual que ya bloquea eliminar una Skill asignada a un Recurso, así el
   ticket no pierde la referencia. El ticket sigue mostrando la Skill en su detalle sin cambios.

## Escenario 6 — Autoservicio sin acceso (Assumptions)

1. Loguear como Usuario/cliente (autoservicio) e intentar
   `PATCH /api/tickets/{id}/skills` sobre su propio ticket.
2. **Esperado**: `403` — el Usuario/cliente no tiene permiso `tickets:edit`.
