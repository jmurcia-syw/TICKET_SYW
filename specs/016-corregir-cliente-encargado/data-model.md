# Data Model: Corregir el Cliente de un Usuario/cliente y desambiguar Proyectos homónimos

**Feature**: `016-corregir-cliente-encargado` · **Date**: 2026-07-14
**Migración**: ninguna — no se agregan tablas ni columnas.

## Entidades — sin cambios de esquema

### ClientContact (`client_contacts`) — comportamiento modificado, esquema sin cambios

La columna `client_id` deja de ser estrictamente de solo-escritura-en-creación: el servicio de
aplicación puede actualizarla cuando el contacto tiene 0 `project_members` y se le agrega un
Proyecto de un Cliente distinto. El esquema (`id, user_id, client_id, created_at`) no cambia.

Nuevo método de repositorio: `ClientContactRepository.update_client_id(contact_id: uuid.UUID,
client_id: uuid.UUID) -> None` — `UPDATE client_contacts SET client_id = :client_id WHERE id =
:contact_id`.

### ProjectMember (`project_members`) — sin cambios

Reutilizada tal cual (spec 010/015). Se usa `list_project_ids_by_user(user_id)` (ya existente)
para determinar si el contacto tiene 0 membresías activas antes de decidir si se permite
corregir el Cliente.

## Regla de negocio actualizada (servicio de dominio)

`ClientContactService.resolve_common_client` (spec 015, sin cambios en su firma) se sigue usando
para resolver y validar el Proyecto a agregar (existe, activo, un único Cliente). Lo que cambia
es la lógica del **endpoint** que la invoca (`POST /api/client-contacts/{id}/projects`):

```
existing_project_ids = project_member_repo.list_project_ids_by_user(contact.user_id)
resolved_client_id = client_contact_service.resolve_common_client([project_id], projects_repo)

if existing_project_ids:
    if resolved_client_id != contact.client_id:
        → 400 validation_error (comportamiento de spec 015, sin cambios)
else:
    if resolved_client_id != contact.client_id:
        client_contact_repo.update_client_id(contact.id, resolved_client_id)
        # contact.client_id se actualiza en memoria para la respuesta
```

## Invariantes (actualizadas)

- Un Usuario/cliente con 1+ Proyectos asignados: todos sus Proyectos DEBEN compartir el mismo
  Cliente (invariante de spec 015, sin cambios).
- Un Usuario/cliente con 0 Proyectos asignados: su próximo Proyecto agregado puede ser de
  cualquier Cliente, y ese Cliente reemplaza al `client_id` actual del contacto.
- La corrección de Cliente no afecta tickets históricos — `tickets.client_contact_id` no
  referencia `client_id` directamente, así que ningún ticket cambia de dueño ni de Cliente
  visible por este cambio (spec 015, sin cambios).

## Diagrama de relaciones (sin cambios de esquema)

```
client_contacts (user_id → users, client_id → clients)   [client_id ahora corregible bajo 0 members]
users ──< project_members >── projects                    [sin cambios, spec 010/015]
```
