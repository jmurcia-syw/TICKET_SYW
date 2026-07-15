# Data Model: Encargado (Usuario/cliente) en múltiples Proyectos

**Feature**: `015-encargado-multiples-proyectos` · **Date**: 2026-07-14
**Migración**: ninguna — no se agregan tablas ni columnas.

## Entidades — sin cambios de esquema

Esta feature no crea ni modifica tablas. Reutiliza dos entidades ya existentes (spec 010):

### ClientContact (`client_contacts`) — sin cambios

Columnas existentes (`id`, `user_id`, `client_id`, `created_at`) se mantienen igual. `client_id`
sigue siendo singular: un Usuario/cliente pertenece a un único Cliente. Lo que cambia es
**cuántos** `project_members` puede tener asociados (antes: como máximo 1 al momento del alta,
por límite de la API; ahora: 0..N, gestionables en cualquier momento).

### ProjectMember (`project_members`) — reutilizada sin cambios de esquema

Ya es la relación muchos-a-muchos persona↔Proyecto (spec 010, `UNIQUE(project_id, user_id)`).
Esta feature simplemente deja de limitar, en la capa de API/UI, cuántas filas puede tener un
`user_id` que además es un Usuario/cliente.

## Cambios de comportamiento (servicio de dominio)

`ClientContactService` (`backend/domain/services/client_contact_service.py`) agrega un método
nuevo:

```
resolve_common_client(project_ids: list[uuid.UUID], projects_repo) -> uuid.UUID
```

- Resuelve cada `project_id` contra `projects_repo`.
- 404 (`not_found`) si algún Proyecto no existe.
- 409 (`project_inactive`) si algún Proyecto está inactivo.
- 400 (`validation_error`) si los Proyectos resueltos no comparten todos el mismo `client_id`.
- Devuelve el `client_id` común (usado para crear/validar el `client_contacts.client_id`).

Este método es usado tanto por el alta (`POST /api/client-contacts`, con la lista completa de
`project_ids`) como por el agregado posterior de un Proyecto
(`POST /api/client-contacts/{id}/projects`, con `[project_id_existente_del_contacto,
project_id_nuevo]` para validar consistencia de Cliente antes de insertar).

## Invariantes

- Todos los `project_members` de un mismo `client_contacts.user_id` deben pertenecer a Proyectos
  del mismo `client_id` que el contacto (ver Decisión 3 en `research.md`).
- Quitar un `project_members` no borra el `client_contacts` ni ningún `ticket` histórico —
  `tickets.client_contact_id` no tiene FK hacia `project_members`, es independiente (spec 007).
- No se permite duplicar `(project_id, user_id)` — ya garantizado por el `UNIQUE` existente;
  la validación de aplicación solo evita el viaje a BD con un 409 amigable.

## Diagrama de relaciones (sin cambios de esquema)

```
users ──< project_members >── projects        (ya existente, spec 010 — ahora sin límite de UI)
client_contacts (user_id → users, client_id → clients)   [sin cambios de esquema]
tickets.client_contact_id                                 [sin cambios de esquema ni de FK]
```
