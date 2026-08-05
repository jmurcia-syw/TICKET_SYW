# API Contract Changes: Ajustes Globales — Seguridad/Permisos, Notificaciones, Motor de SLA, Bugs de UI y Rendimiento

Todos los cambios son aditivos o de comportamiento sobre endpoints ya existentes y documentados en
Swagger (`/swagger`). Sin endpoints nuevos, salvo la extensión de payload marcada abajo. Debe
actualizarse el contrato Swagger correspondiente (Flask-RESTX) antes de tocar el código de la
ruta, por Principio I.

## `GET /api/tickets` (y equivalentes: Kanban, Mis Tareas)

- **Antes**: requiere `tickets:view` (acceso global) o `tickets:view_own` (Usuario/cliente,
  scoping por `client_contact_id`).
- **Después**: agrega el permiso `tickets:view_assigned` (Resolutor) — con solo este permiso, el
  listado se filtra server-side por `assignee_id = <resource_id del actor>`; el frontend además
  aplica ese mismo criterio como filtro por defecto visible/editable en Kanban/Listas/Mis Tareas.
  Sin este permiso ni `tickets:view`, el acceso a la ruta de listado global se deniega (403).
- **Sin cambio de forma de la respuesta** (mismos campos por ticket).

## `GET /api/tickets/{id}` (detalle)

- **Sin cambio de contrato**. El campo `transitions` (Historial de Estados) ahora puede incluir
  una primera entrada con `from_status: "creado"` — valor nuevo dentro de un campo `string` ya
  existente, no rompe consumidores que ya tratan `from_status` como texto libre.

## `GET /api/calendar/*` (vista de calendario)

- **Después**: con permisos de Resolutor (sin permiso de administración/RRHH), la respuesta se
  acota al propio recurso del actor — mismo criterio de scoping ya usado en otros endpoints
  (`work_sessions:view_own`), sin cambio de forma de la respuesta.

## Catálogos maestros (Clientes, Herramientas, Procesos, Tipos de resolución, Equipos, Tipos de
acceso, y equivalentes)

- **Sin cambio de contrato de API** — el ajuste es de comportamiento del **frontend** (no
  precargar estos catálogos completos al iniciar sesión si el usuario no tiene el permiso de
  administración correspondiente). Los endpoints ya están gateados por su propio permiso
  (`catalogs:*`, etc.) y devuelven 403 igual que hoy si se invocan sin él.

## `POST /api/users` (creación de usuario)

- **Después**: nuevo campo de payload opcional:

  ```json
  {
    "notify": false
  }
  ```

  - `notify` (`boolean`, opcional, default `false`): si es `true`, tras crear el usuario
    exitosamente el backend genera el mismo tipo de token de un solo uso ya usado por el flujo de
    reseteo de contraseña (spec `003`, expiración de 30 min) y envía el correo de bienvenida HTML.
  - Un fallo en el envío de correo **no** revierte la creación del usuario; la respuesta exitosa de
    creación incluye un indicador de si la notificación se envió correctamente (p. ej.
    `notification_sent: boolean`) para que la UI informe al administrador.
  - Sin cambio en los campos ya existentes del payload/respuesta.

## `POST /api/work-sessions` y `PATCH /api/work-sessions/{id}` (Registro de tiempo)

- **Después**: el campo `note` pasa de aceptar vacío/omitido a ser requerido (no vacío tras
  `strip()`); una petición sin `note` responde `400` con el mismo formato de error estándar
  (`{success: false, message, code}`, spec `013`) ya usado por el resto de validaciones del
  sistema. Sin cambio de nombre ni tipo del campo.

## `POST /api/tickets` (creación de Ticket/Tarea)

- **Sin cambio de payload**. `client_contact_id` ya es aceptado como opcional a nivel de API; el
  endurecimiento "obligatorio para Ticket, opcional para Tarea" se aplica como validación de
  negocio dentro del mismo endpoint según el tipo de registro (`record_type`) ya enviado, igual
  patrón que la validación existente de `project_id` obligatorio (OBS-0045, spec `033`).

## Endpoints de Accesos y Conexiones del Cliente (`/api/clients/{id}/access*`,
`/api/client-access/{id}/credentials*`)

- **Sin cambio de contrato**. El fix de credenciales cruzadas es un bug de estado del formulario en
  el frontend (ver research.md Decisión 9); el backend ya persiste cada credencial bajo su propio
  `client_access_id` correctamente.
