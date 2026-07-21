# Quickstart: Historial de Estados con SLA Visual y Reasignación de Resolutores

## Prerrequisitos

- Stack levantado con Docker Compose (`docker compose up -d`, ver `docs/` del repo).
- Un Ticket existente con al menos 2 transiciones de estado registradas y un `assignee_id`
  asignado (usar cualquiera creado por el flujo normal de spec 002/014).
- Un segundo Recurso activo distinto del `assignee_id` actual del ticket.
- Usuario autenticado con permiso `tickets:assign` (rol Coordinador/Jefe de equipo).

## Escenario 1 — SLA visual en Historial de Estados (US1)

1. `GET /api/tickets/{ticket_id}` — confirmar que `transitions[]` trae `elapsed_seconds`,
   `sla_phase_closed` y `sla_met` por cada fila (ver [contracts/reassign.md](contracts/reassign.md)).
2. Abrir el ticket en `TicketDetailPage` → Card "Historial de estados".
3. **Verificar**: la fila de la transición que cerró la fase Contacto muestra el tiempo
   transcurrido + ✅ (si `sla_contact_result == "cumplido"`) o ⚠️/❌ (si `"vencido"`).
4. **Verificar**: la primera transición del ticket no muestra tiempo ni ícono.
5. **Verificar**: en un ticket cuyo Proyecto/Prioridad no tiene `SlaRule` configurada, ninguna
   fila muestra ícono de cumplimiento, solo tiempo transcurrido.

## Escenario 2 — Reasignar el ticket (US2)

1. En el detalle del ticket, click en "Reasignar" (junto a la ficha de asignación actual).
2. Seleccionar el segundo Recurso activo y confirmar (con o sin motivo).
3. `POST /api/tickets/{ticket_id}/reassign` con `{"assignee_id": "<nuevo-recurso>"}`.
4. **Verificar** (200): `ticket.assignee_id` actualizado al nuevo recurso; el ticket conserva su
   `status` (sin cambio de FSM).
5. **Verificar**: `GET /api/tickets/{ticket_id}` trae la nueva entrada en `reassignments[]` con
   `previous_assignee_id` = resolutor anterior y `new_assignee_id` = nuevo resolutor.
6. **Verificar** en UI: el bloque de actividad muestra "Resolutor A ➡️ Resolutor B" con autor y
   fecha.
7. Repetir el paso 3 seleccionando el mismo resolutor ya asignado → esperar 400
   (`validation_error`), sin nueva entrada en `reassignments[]`.
8. Repetir sobre un ticket en estado `cerrado` → esperar 409 (`ticket_closed`).
9. Repetir sin el permiso `tickets:assign` → esperar 403, sin nueva entrada en `reassignments[]`.

## Validación de código (alcance acotado, Principio VII)

- Backend: `pytest backend/tests/domain/test_sla_service.py backend/tests/api/test_reassign.py`
  (NO ejecutar la suite completa; tests nuevos con ≤10 registros de prueba).
- Frontend: verificación manual en navegador (Card "Historial de estados" + modal "Reasignar");
  sin suite de tests nueva para este cambio visual.
