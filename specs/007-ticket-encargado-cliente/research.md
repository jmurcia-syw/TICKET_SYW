# Research: Selección manual del Encargado solicitante en el Ticket

Todas las incógnitas se resolvieron por inspección directa del código existente (Fase 2.1 ya
construyó `client_contacts` y `_requester()`); no requirió investigación externa.

## Decisión 1 — Cómo modelar la referencia (columna nueva vs. reutilizar `created_by`)

- **Decision**: Nueva columna `tickets.client_contact_id` (UUID nullable, FK →
  `client_contacts.id`, `ON DELETE SET NULL`), distinta de `created_by`.
- **Rationale**: `created_by` es siempre quien creó el ticket en el sistema (personal interno en
  el flujo que pide esta funcionalidad); el Encargado solicitante es una persona distinta del lado
  del cliente. Reutilizar `created_by` mezclaría dos conceptos y rompería el caso ya existente de
  Fase 2.1 (Encargado que crea su propio ticket, donde `created_by` SÍ es el Encargado).
- **Alternatives considered**: Guardar el `user_id` del Encargado directamente (sin pasar por
  `client_contacts`) — descartado: pierde la garantía de "pertenece al cliente del ticket"
  (FR-002), que `client_contacts` ya modela vía su propio `client_id`; habría que duplicar esa
  validación contra la tabla `users` en vez de reutilizar la relación ya existente.

## Decisión 2 — `_requester()` con dos orígenes posibles

- **Decision**: `_requester()` (en `backend/api/routes/tickets.py`) prioriza
  `ticket.client_contact_id` si está presente (resuelve el `client_contact` → su `user`); si no,
  cae al comportamiento ya existente (resolver `created_by` y chequear si su rol es "Encargado").
  La forma de salida (`{id, name, is_encargado}`) no cambia — compatibilidad total con el frontend
  ya existente (`TicketDetailPage.tsx` ya renderiza ese Tag condicionado a `is_encargado`, sin
  necesidad de tocar esa parte de la UI).
- **Rationale**: Minimiza el cambio — un ticket nunca tiene ambos orígenes a la vez (FR-009:
  cuando el creador es Encargado, el flujo de creación no expone el selector, así que
  `client_contact_id` queda `null` en ese caso), así que la prioridad nunca es ambigua en la
  práctica; se implementa igual como salvaguarda explícita.
- **Alternatives considered**: Exponer un campo `requester_origin: 'auto' | 'manual'` — descartado
  por ahora: el frontend puede derivar lo mismo comparando `ticket.client_contact_id` (nuevo campo
  crudo que si se expone) contra `null`, sin necesidad de un campo adicional solo para eso.

## Decisión 3 — Bloqueo de edición (FR-008/FR-009)

- **Decision**: Dos mecanismos distintos, cada uno en su capa natural:
  1. **Por estado del ticket** (FR-008): `client_contact_id` se agrega a
     `FIELD_LOCKS["cerrado"]` y `FIELD_LOCKS["cancelado"]` en `backend/domain/entities/ticket.py`
     — mismo mecanismo ya usado para `estimated_resolution_minutes`, sin inventar uno nuevo.
  2. **Por origen del solicitante** (FR-009): validación explícita en
     `TicketService.validate_patch` — si `client_contact_id` viene en el PATCH y el `created_by`
     del ticket tiene rol Encargado, rechaza con 409 (mismo patrón de error que `field_locked`).
- **Rationale**: Son dos ejes distintos (uno temporal por estado, otro estructural por cómo nació
  el ticket) — forzarlos en un solo mecanismo (`FIELD_LOCKS`, que solo conoce el estado) sería
  incorrecto: un ticket "nuevo" creado por un Encargado igual debe rechazar la edición manual,
  aunque el estado no lo bloquee.
- **Alternatives considered**: Confiar solo en que el frontend no muestre el selector — rechazado
  por Principio IV (seguridad en profundidad): un PATCH directo a la API debe quedar protegido
  igual.

## Decisión 4 — Gap de permiso en `GET /api/client-contacts`

- **Decision**: Cambiar `@require_permission("client_contacts", "manage")` del método `GET` por
  `@require_authenticated()` + chequeo manual
  `current_user_has("client_contacts","manage") or current_user_has("tickets","create") or
  current_user_has("tickets","edit")`. El método `POST` (alta de Encargados) no cambia — sigue
  exigiendo `client_contacts:manage` exclusivamente.
- **Rationale**: La Historia 1 del spec dice explícitamente "Un Coordinador **o Resolutor**"; hoy
  el Resolutor tiene `tickets:create`/`tickets:edit` pero no `client_contacts:manage`
  (`021_encargado_role_permissions.py`), así que no podría cargar la lista de Encargados de un
  cliente al crear/editar un ticket — el flujo pedido literalmente no funcionaría sin este cambio.
  Mismo patrón ya aplicado en Fase 2.1 cuando se descubrió que `notifications.py` tenía el gap
  simétrico con Encargado/`tickets:view_own`.
- **Alternatives considered**: Duplicar el listado en un endpoint nuevo de solo lectura dentro de
  `tickets` — descartado: más superficie de API para el mismo dato, contra la directriz de mínimo
  cambio necesario.

## Decisión 5 — Reutilización del listado ya existente en frontend

- **Decision**: `clientContactService.list({ client_id })` (ya existe, Fase 2.1) alcanza para
  poblar el `Select` de Encargados tanto en `TicketsPage.tsx` (creación) como en
  `TicketDetailPage.tsx` (edición) — no se crea ningún servicio ni tipo nuevo en frontend.
- **Rationale**: El endpoint ya soporta el filtro `client_id` (`ClientContactRepository.
  list_paginated(client_id=...)`); el único cambio real de contrato es el de permiso (Decisión 4).
- **Alternatives considered**: Ninguna — la pieza ya existía completa, solo bloqueada por permiso.

**Output**: Todas las incógnitas del Technical Context quedaron resueltas; no quedan
`NEEDS CLARIFICATION` pendientes para el diseño de Fase 1.
