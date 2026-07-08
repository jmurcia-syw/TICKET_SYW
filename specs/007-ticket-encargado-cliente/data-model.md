# Data Model: Selección manual del Encargado solicitante en el Ticket

## Cambio de esquema

### `tickets` (columna nueva)

| Columna | Tipo | Null | FK | Notas |
|---------|------|------|----|-------|
| `client_contact_id` | UUID | Sí | `client_contacts.id`, `ON DELETE SET NULL` | Encargado solicitante asignado manualmente (FR-001). `NULL` = sin asignar, o resuelto automáticamente desde `created_by` (Fase 2.1). |

Migración `022_tickets_client_contact.py`: `ALTER TABLE tickets ADD COLUMN client_contact_id UUID
NULL REFERENCES client_contacts(id) ON DELETE SET NULL`. Sin índice nuevo (no hay requerimiento de
filtrar tickets por Encargado en este alcance). Sin cambios de RLS — la política existente de
`tickets` (`012_tickets_rls.py`) ya cubre la fila completa; una columna nueva no amplía ni reduce
qué filas ve cada rol.

### Validaciones de negocio (no de esquema)

- **Pertenencia al cliente** (FR-002): si `client_contact_id` viene informado (al crear o editar),
  el `client_contact` resuelto DEBE tener `client_id == ticket.client_id`. Se valida en
  `TicketService.validate_create`/`validate_patch`, no con un CHECK de base de datos (requiere
  join, no expresable como CHECK simple).
- **Bloqueo por estado** (FR-008): `client_contact_id` se agrega a `FIELD_LOCKS["cerrado"]` y
  `FIELD_LOCKS["cancelado"]` (`backend/domain/entities/ticket.py`) — mismo mecanismo que ya usan
  `estimated_resolution_minutes`, `priority`, `severity`, etc.
- **Bloqueo por origen** (FR-009): si `ticket.created_by` tiene rol "Encargado", cualquier intento
  de `PATCH` sobre `client_contact_id` se rechaza (409), sin importar el estado. Ver research.md
  Decisión 3.

## Vista/serialización (API, sin nueva tabla)

### `TicketRequester` (ya existente, sin cambio de forma)

`{ id, name, is_encargado }` — ahora puede resolverse de dos orígenes (ver research.md Decisión
2), pero la forma de salida no cambia; el frontend que ya la consume (Fase 2.1) no necesita
tocarse para *mostrarlo*.

### `TicketDetail` (campo nuevo, crudo)

| Campo | Tipo | Notas |
|-------|------|-------|
| `client_contact_id` | string \| null | Valor crudo de la columna — lo usa el frontend para saber si el Encargado fue asignado manualmente (y por tanto es editable) o si el `requester` viene del origen automático (no editable, FR-009). Distinto de `requester`, que es el objeto ya resuelto para mostrar. |

## Entidades ya existentes (sin cambios de estructura)

- **Encargado (`client_contacts`)**: sin cambios — esta funcionalidad solo agrega una forma más de
  referenciarlo (desde `tickets`), reutilizando `id`, `user_id`, `client_id` ya existentes.
- **Cliente / Proyecto**: sin ningún cambio — siguen siendo campos independientes del ticket.
