# Research — Accesos y conexiones múltiples del Cliente

No quedaron `NEEDS CLARIFICATION` en el Technical Context del plan: todas las decisiones de esta
sección se resolvieron contra el código real del repo (no contra suposiciones). Se documentan
igual como research formal porque cada una tenía más de una alternativa razonable.

## Decisión 1 — Modelo de datos: tabla hija dedicada `client_access`

- **Decisión**: nueva tabla `client_access` (FK `client_id`), 1-a-muchos, en vez de una columna
  JSON en `clients` o de reutilizar `client_systems`.
- **Rationale**: `client_systems` ya modela un concepto distinto (portafolio de software:
  tipo/marca/versión) con su propio repositorio y UI (`list_systems/add_system/delete_system` en
  `client_repo.py`); mezclar "accesos" ahí rompería su semántica. Una tabla dedicada permite
  reutilizar exactamente el mismo patrón (repositorio + endpoints + tabla en UI) sin acoplar dos
  conceptos de negocio distintos. Un JSON column en `clients` sería más simple de migrar pero
  impide indexar/filtrar por tipo o ambiente y complica el enmascarado selectivo de un solo campo
  sensible (`password`) sin decodificar todo el blob.
- **Alternativas consideradas**: (a) columna JSONB en `clients` — rechazada por lo anterior; (b)
  extender `client_systems` con columnas nullable de acceso — rechazada por mezclar dos entidades
  de negocio no relacionadas.

## Decisión 2 — Adjuntos: generalizar `attachments.py` existente

- **Decisión**: generalizar `backend/infra/storage/attachments.py` (hoy `save(ticket_id, ...)`
  hardcodea la ruta `uploads/tickets/{ticket_id}/...`) para aceptar un tipo de entidad, guardando
  en `uploads/clients/{client_id}/...` para este caso. Nueva tabla `client_access_attachments`
  (FK `client_id` — no por cada registro individual de acceso, ver Decisión 3) con las mismas
  reglas de tamaño/extensión ya vigentes (`MAX_ATTACHMENT_BYTES`, `ALLOWED_EXTENSIONS`).
- **Rationale**: evita reimplementar validación de tipo/tamaño de archivo y manejo seguro de
  rutas (`open_path` ya previene path traversal) — ya endurecido y probado en producción para
  adjuntos de Tickets. No se agrega ninguna dependencia nueva.
- **Alternativas consideradas**: almacenamiento en base64 dentro de una columna — rechazada,
  ningún otro adjunto del sistema usa ese approach y complicaría el límite de 10 MB ya vigente.

## Decisión 3 — Alcance del adjunto: por cliente, no por registro de acceso individual

- **Decisión**: los adjuntos (`OBS-0001`: "instructivo de instalación/configuración") se asocian
  a la sección de accesos y conexiones del cliente en su conjunto, no a un registro `ClientAccess`
  puntual.
- **Rationale**: el criterio de aceptación original de `OBS-0001` dice explícitamente "adjuntar
  uno o varios archivos... asociados al cliente", no "asociados a cada acceso". Un instructivo de
  instalación normalmente cubre el ambiente completo, no un único usuario/contraseña.
- **Alternativas consideradas**: adjunto por registro de acceso (FK `client_access_id`) —
  rechazada por sobre-especificar respecto al criterio de aceptación original y complicar la UI
  (un adjunto por fila en vez de una sección de adjuntos general).

## Decisión 4 — Migración de datos existentes

- **Decisión**: dentro de la misma migración Alembic que crea `client_access`, un `data migration`
  step recorre `clients` y, por cada fila con `vpn_ips` y/o `vpn_credentials` no nulos, inserta un
  `client_access` con `type='vpn'`, `host=<vpn_ips desencriptado>`, `password=<vpn_credentials
  desencriptado>`, `user=NULL`, `environment=NULL`. Clientes con ambos campos vacíos no generan
  fila. `downgrade()` reconstruye `vpn_ips`/`vpn_credentials` desde el primer `client_access` tipo
  `vpn` de cada cliente (best-effort, documentado como limitación si un cliente ya tiene más de un
  acceso VPN al momento del rollback).
- **Rationale**: cumple FR-007/FR-008/SC-004 (sin pérdida de datos) sin intervención manual, y es
  reversible como exige el Technical Context.
- **Alternativas consideradas**: script de migración de datos separado, fuera de Alembic —
  rechazada porque el resto del repo migra datos de negocio dentro de la misma migración de
  esquema cuando el volumen es bajo (mismo patrón que otras migraciones de este proyecto).

## Decisión 5 — RLS en las tablas nuevas

- **Decisión**: replicar exactamente el patrón app-level de `020_client_contacts_rls.py` (policy
  `USING (current_setting('app.authenticated', true) IS NOT DISTINCT FROM 'true' OR current_user
  = 'sywork_user')`) en `client_access` y `client_access_attachments`, en una migración separada
  (`031_client_access_rls.py`) después de la creación de tablas.
- **Rationale**: Principio IV (NON-NEGOTIABLE) exige RLS en toda tabla con datos sensibles;
  `client_access` contiene contraseñas. Seguir el patrón ya existente evita introducir una
  variante nueva de política RLS sin necesidad.
- **Alternativas consideradas**: ninguna — el patrón está fijado por la Constitución y por
  precedente directo (`012_tickets_rls.py`, `016_work_sessions_rls.py`, `020_client_contacts_rls.py`).

## Decisión 6 — Presentación en UI: `Tabs` dentro del modal existente, no una página nueva

- **Decisión**: el modal "Detalle del cliente" (`ClientsPage.tsx`) gana un componente Ant Design
  `Tabs` con al menos dos pestañas: "Datos generales" (contenido actual) y "Accesos y conexiones"
  (tabla ancha horizontal + alta rápida inline, mismo patrón que la sección "Portafolio de
  software" ya existente ahí mismo). El modal se ensancha (`width` mayor) solo para acomodar la
  tabla horizontal de accesos.
- **Rationale**: cumple FR-011/FR-012 (espacio propio, independiente del guardado principal) sin
  introducir una ruta/página nueva ni un Drawer adicional — reutiliza un patrón de composición ya
  presente en el mismo archivo (`systemForm`/`systems` conviven con los datos generales del
  modal). Las altas/bajas de accesos usan sus propios endpoints (`add_access`/`delete_access`),
  igual que `add_system`/`delete_system`, sin depender del botón "Guardar" del formulario principal.
- **Alternativas consideradas**: página independiente `/clients/:id` con ruta propia — rechazada
  por ser un cambio de navegación mayor no pedido por ninguna de las tres observaciones ni por la
  aclaración del usuario, que solo pidió "pestaña" y "no depender de la misma sesión de guardado".

## Decisión 7 — Enmascarado de contraseña

- **Decisión**: en el formulario de alta/edición de un registro de acceso, el campo contraseña
  usa `Input.Password` de Ant Design (enmascarado nativo con ícono de revelar/ocultar). En la
  tabla de listado y en el tab de detalle, se replica el patrón ya usado para `vpn_credentials`
  hoy (`••••••••` + botón `EyeOutlined`/`EyeInvisibleOutlined` atado a `include_sensitive`).
- **Rationale**: `Input.Password` es el componente estándar de Ant Design ya aprobado (Principio
  V) para este propósito exacto — no requiere ninguna librería nueva. El patrón de revelado en
  listado ya existe en el propio archivo (`revealVpn` state), solo se generaliza a "por fila".
- **Alternativas consideradas**: enmascarado custom con `Input.TextArea` + regex de sustitución de
  caracteres — rechazada, reinventa algo que `Input.Password` ya resuelve.
