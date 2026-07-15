# Contract: Client Contacts (Usuario/cliente) — cambios (spec 016)

Cambios sobre `POST /api/client-contacts/{contact_id}/projects` (introducido en spec 015).
Permiso sin cambios: `client_contacts:manage`.

## POST /api/client-contacts/{contact_id}/projects — corrección de Cliente con 0 Proyectos

**Body**: sin cambios — `{ "project_id": "uuid" }`.

**Regla nueva**: si el Usuario/cliente **no tiene ningún Proyecto asignado actualmente**, el
Proyecto puede pertenecer a **cualquier** Cliente activo — no solo al Cliente ya guardado en el
contacto. En ese caso, el Cliente del contacto se actualiza para coincidir con el Cliente del
Proyecto agregado.

Si el Usuario/cliente **ya tiene 1 o más Proyectos asignados**, se mantiene la regla de spec 015
sin cambios: el Proyecto debe pertenecer al mismo Cliente que los ya asignados, o se rechaza con
400.

**201** (sin cambios de forma): `{ "id": "uuid-project-member", "project_id": "uuid", "name":
"Proyecto X" }`. El Cliente corregido (si aplica) se refleja de inmediato en
`GET /api/client-contacts` (campo `client_id`/`client_name` de ese contacto).

**Errores**: sin cambios de catálogo (400/404/409) — el 400 `validation_error` por "Cliente
distinto" solo se dispara ahora cuando el contacto **ya tiene** al menos un Proyecto asignado.

## GET /api/client-contacts — sin cambios de contrato

El `client_id`/`client_name` devuelto para cada contacto refleja el valor corregido en cuanto se
agrega el primer Proyecto tras haber quedado en cero (spec 016). Los filtros `client_id`/
`project_id` existentes (spec 010/015) no cambian su comportamiento.
