# Research — Calendarios Multi-Zona Horaria, Festivos, Vacaciones (RRHH) y Disponibilidad

No quedaron `NEEDS CLARIFICATION` en el Technical Context del plan. Se documentan igual como
research formal porque cada decisión tenía más de una alternativa razonable.

## Decisión 1 — Librería de calendario: FullCalendar (nueva dependencia, Principio V)

- **Decisión**: agregar `@fullcalendar/core`, `@fullcalendar/react`, `@fullcalendar/daygrid`,
  `@fullcalendar/timegrid` al frontend. **Aprobación documentada aquí, per Principio V**
  (gobernanza de librerías): librería MIT, activamente mantenida, compatible con React 19,
  usada solo para renderizar los calendarios de Cliente/Equipo (spec 020 US3) — no reemplaza
  ningún otro componente Ant Design existente.
- **Rationale**: Ant Design 5 solo trae un `Calendar` de celda mensual/anual; no soporta vistas
  día/semana con franjas horarias por miembro (necesarias para mostrar el horario laboral y los
  festivos superpuestos por zona horaria del Equipo), ni una ruta clara de integración futura con
  Google Calendar (el propio requerimiento del usuario pide "preparada para futuras
  integraciones"). FullCalendar tiene un plugin oficial (`@fullcalendar/google-calendar`) que se
  puede sumar en una fase posterior sin cambiar el motor de renderizado.
- **Alternativas consideradas**: (a) construir las vistas día/semana a mano sobre `antd`
  (`Table`/`Row`) — rechazada, reinventa manejo de husos horarios y solapamiento de eventos ya
  resuelto por una librería madura; (b) `react-big-calendar` — rechazada, su soporte de husos
  horarios múltiples simultáneos (un lane por miembro del equipo, cada uno en su propia zona) es
  más limitado que el de FullCalendar (`timeZone` por evento vía `resourceTimeGrid` no aplica
  igual de bien a "N usuarios, N zonas horarias distintas en la misma vista").

## Decisión 2 — Catálogo de festivos: tabla interna editable, sin servicio externo

- **Decisión**: tabla `holidays` (país, fecha, nombre) mantenida manualmente vía endpoint propio,
  sin integrar una API/librería externa de feriados.
- **Rationale**: Principio V exige aprobación previa documentada para toda dependencia nueva; no
  hay presupuesto de esta fase para evaluar/aprobar un proveedor externo de feriados, y el spec
  (`Assumptions`) ya fija esto como default razonable. Carga inicial vía seed de migración con los
  países donde ya hay Clientes/Recursos activos (según `clients.country` / `resources.timezone`
  reales al momento de escribir esta fase), ampliable después por un administrador.
- **Alternativas consideradas**: paquete `python-holidays` (cálculo algorítmico de feriados por
  país) — es una dependencia nueva no aprobada; se deja como candidato para una fase futura si el
  mantenimiento manual resulta costoso, pero no se introduce ahora sin la aprobación documentada
  que exige el Principio V (fuera del alcance de esta sesión).

## Decisión 3 — Horario laboral: tabla `work_schedules` por recurso y día de semana

- **Decisión**: tabla `work_schedules` (FK `resource_id`, `weekday` 0-6, `start_time`,
  `end_time`), cero o más filas por recurso. Si un recurso no tiene filas, el servicio de
  disponibilidad aplica el default documentado en el spec (`Assumptions`: lunes a viernes,
  jornada estándar, en la zona horaria del propio usuario) sin persistir nada — evita escribir
  filas "default" para cada recurso nuevo.
- **Rationale**: modelo simple y consultable (`SELECT ... WHERE resource_id = ? AND weekday = ?`)
  sin duplicar lógica de husos horarios (las horas se guardan "naive", se interpretan siempre en
  el `timezone` del propio recurso al evaluar disponibilidad — igual que ya hace `calendar_country`
  hoy para festivos).
- **Alternativas consideradas**: columna JSON en `resources` con el horario semanal completo —
  rechazada, dificulta filtrar/editar un solo día sin reescribir el blob completo y no sigue el
  patrón relacional ya usado en el resto del esquema (`resource_skills`, `resource_compensation`).

## Decisión 4 — Cadena de aprobación de ausencias: dos columnas de estado independientes

- **Decisión**: `absence_requests` guarda `manager_status` y `hr_status` (cada uno
  `pending`/`approved`/`rejected`) por separado, más un `overall_status` calculado en el dominio
  (Capa 1): `rejected` si cualquiera de los dos es `rejected`; `approved` solo si ambos son
  `approved`; `pending` en cualquier otro caso. Si el solicitante no tiene `manager_id` en su
  ficha de Recurso, `manager_status` nace en `approved` automáticamente (no hay jefe que decida) y
  el resultado depende solo de `hr_status`.
- **Rationale**: cumple la aclaración explícita del usuario ("debe ser aprobado por jefe y
  RRHH") sin modelar una máquina de estados nueva — es una regla pura, testeable con pocos casos,
  que vive en `backend/domain/services/absence_service.py` (Principio I: lógica de negocio fuera
  de Flask/SQLAlchemy).
- **Alternativas consideradas**: un solo campo `status` con transiciones secuenciales obligatorias
  (jefe primero, luego RRHH) — rechazada porque el usuario no pidió un orden estricto, solo que
  "debe ser aprobado por jefe y RRHH"; forzar secuencia agregaría una regla no solicitada y un
  caso borde extra (¿qué pasa si el jefe tarda?) sin beneficio claro.

## Decisión 5 — Adjuntos de solicitudes de ausencia: tabla dedicada + storage genérico existente

- **Decisión**: nueva tabla `absence_request_attachments` (FK `absence_request_id`,
  `ON DELETE CASCADE`), mismo shape que `client_access_attachments` (spec 018). Reutiliza
  `backend/infra/storage/attachments.py::save(entity_id, filename, data, entity_kind=...)` ya
  generalizado, con `entity_kind="absence_requests"` (→ `uploads/absence_requests/{id}/...`).
  Mismas reglas de tipo/tamaño ya vigentes (`MAX_ATTACHMENT_BYTES`, `ALLOWED_EXTENSIONS`, ya
  incluye `.pdf`, imágenes, `.docx` — cubre certificados de incapacidad escaneados).
- **Rationale**: evita reimplementar validación de archivo y manejo seguro de rutas; sigue el
  precedente directo ya usado dos veces en el repo (Tickets, spec 018 Clientes). Tabla dedicada
  (no reutilizar `comment_attachments`) porque una solicitud de ausencia no es un comentario de
  ticket ni comparte su ciclo de vida.
- **Alternativas consideradas**: ninguna — mismo patrón fijado por precedente, sin necesidad de
  evaluar alternativas nuevas.

## Decisión 6 — RLS: `absence_requests` y `absence_request_attachments` sí, `holidays` y
`work_schedules` no

- **Decisión**: Row Level Security habilitado (mismo patrón app-level que
  `031_client_access_rls.py`) solo en `absence_requests` y `absence_request_attachments`.
  `holidays` (festivos por país) y `work_schedules` (horario laboral) quedan sin RLS, igual que
  las tablas `catalog_*` existentes.
- **Rationale**: Principio IV (NON-NEGOTIABLE) exige RLS en tablas con **datos sensibles**. Una
  solicitud de ausencia puede contener el tipo "Incapacidad médica" y un documento adjunto —
  información de salud, sensible. Los festivos por país y el horario laboral son datos de
  referencia no sensibles (comparables a `catalog_teams`, `catalog_tools`, que tampoco tienen
  RLS), consultables por cualquier usuario autenticado para renderizar los calendarios.
- **Alternativas consideradas**: RLS en las cuatro tablas nuevas por uniformidad — rechazada,
  agregar RLS a tablas sin datos sensibles no está exigido por la Constitución y solo añade
  policies a mantener sin beneficio de seguridad real.

## Decisión 7 — Endpoint de disponibilidad: nuevo recurso `GET /api/resources/availability`,
no se toca `POST /api/tickets/{id}/assign`

- **Decisión**: nuevo endpoint de solo lectura `GET /api/resources/availability` (acepta
  `resource_ids` y un instante `at`, default ahora) que devuelve, por recurso, si está disponible
  y el motivo si no lo está. `AssignModal.tsx` lo consulta junto a la carga actual (mismo patrón
  ya usado con `ticketService.panel()`), y **no** se modifica el endpoint
  `POST /api/tickets/{id}/assign` — cumple FR-015 (la asignación nunca se bloquea) sin tocar el
  endpoint de acción crítica que el Principio VI protege explícitamente ("no puede ser
  refactorizado para acoplarlo a la UI sin aprobación explícita de arquitectura").
- **Rationale**: mantiene el endpoint de asignación agnóstico al caller (humano o futuro Triage
  Agent, Principio VI) — la disponibilidad es información de apoyo para quien decide, no una
  precondición del endpoint. Encaja en la directriz de alcance de esta sesión ("controladores de
  asignación") porque es el controlador que sostiene directamente el flujo de asignación aunque
  viva en un archivo nuevo (`backend/api/routes/calendar.py`) en vez de en `tickets.py`.
- **Alternativas consideradas**: devolver la disponibilidad embebida en
  `GET /api/resources` — rechazada, mezclaría un cálculo dependiente del instante de consulta
  (`at`) con el CRUD general de recursos, que se cachea/lista sin ese contexto en otras pantallas
  (Maestros > Recursos).

## Decisión 8 — Permisos nuevos: módulo `absence_requests`, sin tocar `tickets:assign`

- **Decisión**: permisos nuevos `absence_requests:create` (equipo interno, no `Encargado`),
  `absence_requests:view_all` y `absence_requests:decide_hr` (rol RRHH). La decisión del Jefe
  directo sobre la solicitud de un subordinado **no** usa un permiso nuevo: se verifica por
  pertenencia (`request.resource.manager_id == recurso del usuario autenticado`), mismo patrón ya
  usado por `enforce_module(..., allow_own_resource_edit=True)` / `_is_own_resource` en
  `backend/api/middleware/rbac.py`. El endpoint de disponibilidad (`GET
  /api/resources/availability`) reutiliza el permiso ya existente `tickets:assign` — solo lo
  consume la pantalla de asignación.
- **Rationale**: sigue el precedente exacto ya usado para "Encargado ve/actúa solo sobre lo
  propio" (spec 021 histórica) y evita crear un permiso `absence_requests:decide_manager` que en
  la práctica siempre se evaluaría igual (comparar `manager_id`), agregando superficie sin
  beneficio.
- **Alternativas consideradas**: permiso `absence_requests:decide_manager` asignado a todos los
  roles — rechazada, un permiso de módulo no captura "solo tus propios subordinados"; requeriría
  la misma verificación de pertenencia igual, haciendo el permiso redundante.
