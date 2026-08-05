# Research: Ajustes Globales — Seguridad/Permisos, Notificaciones, Motor de SLA, Bugs de UI y Rendimiento

## Decisión 1 — Filtro "asignado a mí" del Resolutor: aplicación, no RLS

**Decision**: El nuevo permiso `tickets:view_assigned` (Resolutor) se aplica en el repositorio
(Capa 2, `TicketRepository.list()`) y en la ruta (Capa 3, `GET /api/tickets`), igual patrón que
`tickets:view_own` ya usado para el rol Usuario/cliente (migración `021`). **No se toca** la
política RLS de `tickets` (migración `012`).

**Rationale**: La migración `012` deja la lectura de `tickets`/`ticket_status_transitions`
abierta a cualquier sesión autenticada de la app **a propósito** ("los resolutores usan el
historial de tickets como base de conocimiento — SDD V3 'Concepto de Skills'"). Restringir esto a
nivel de RLS rompería esa capacidad ya documentada y usada (un Resolutor consultando cómo se
resolvió un caso similar de otro cliente). El requisito de esta feature es una restricción de
**vista por defecto** (spec `038` FR-003/FR-004: "restringir el acceso a la vista global"), no una
prohibición absoluta de lectura a nivel de datos — se resuelve correctamente en la capa de
aplicación, igual que ya hace `tickets:view_own`.

**Alternatives considered**: Agregar una política RLS por `assignee_id` — rechazada porque
regresiona la capacidad de "base de conocimiento" de migración `012` sin que el spec lo pida, y
porque el propio Principio IV ya documenta que la protección de escritura/transición (más
sensible que la lectura) se resuelve en dominio+API, no en RLS, con RLS como red de seguridad
adicional contra acceso no autenticado.

## Decisión 2 — Permiso nuevo `tickets:view_assigned` en vez de reutilizar `tickets:view_own`

**Decision**: Nueva migración Alembic `052_*` agrega el permiso `tickets:view_assigned` (módulo
`tickets`, acción `view_assigned`) asignado al rol Resolutor. El rol Resolutor deja de tener
`tickets:view` (acceso global) — si lo tenía — y conserva solo `tickets:view_assigned`.

**Rationale**: `tickets:view_own` (migración `021`) ya tiene una semántica específica y usada en
varios puntos del código (`notifications.py`, detalle de ticket con 404-vs-403): "propio" significa
tickets creados por el Usuario/cliente vía su `client_contact_id`. Redefinir esa misma acción para
significar también "asignado a mí como resolutor" mezclaría dos criterios de scoping distintos
bajo el mismo nombre de permiso y arriesga una regresión silenciosa en el flujo de autoservicio
del Usuario/cliente. Un permiso nuevo y explícito es más seguro y más barato de auditar.

**Alternatives considered**: Sobrecargar `tickets:view_own` con lógica condicional por rol —
rechazado por el riesgo de regresión arriba descrito y porque viola la claridad de una matriz
RBAC "módulo × acción" plana que ya usa el resto del sistema.

## Decisión 3 — SLA de Contacto: mapeo de fase por estado

**Decision**: En `backend/domain/fsm/ticket_fsm.py`, `SLA_PHASE_FOR_STATE["contacto"]` cambia de
`"ejecucion"` a `"contacto"` (el estado FSM `contacto` — alcanzado al asignar resolutor — pasa a
seguir contando como fase de SLA "Contacto"); `SLA_PHASE_FOR_STATE["en_analisis"]` se mantiene en
`"ejecucion"`, que es donde ya ocurre hoy el congelamiento de Contacto al entrar a ese estado.

**Rationale**: Hoy el comentario del propio código (línea 46-48 de `ticket_fsm.py`) documenta que
"al ENTRAR al estado `contacto` es cuando la fase de Contacto se da por completada" — es decir, el
SLA de Contacto se congela en el momento de la asignación, no cuando el resolutor efectivamente
inicia el análisis. La spec `038` (FR-009/FR-010) pide explícitamente que el reloj de Contacto siga
corriendo durante todo el tiempo que el ticket está asignado pero aún no analizado, y se congele
recién al pasar a "En Análisis" — esto es un cambio de comportamiento deliberado, no un bug del
código anterior (que cumplía su propia especificación de spec `014`).

**Alternatives considered**: Ninguna — el requisito es explícito y no admite una interpretación
alternativa razonable.

## Decisión 4 — SLA de Resolución: reemplaza el congelamiento en "Resuelto"

**Decision**: `STATE_COUNTS_FOR_SLA["resuelto"]` cambia de `False` a `True` (el tiempo en estado
"Resuelto" vuelve a contar); la lógica de congelamiento de `sla_service.py` (hoy dispara al
detectar `new_status in ("resuelto", "cerrado", "cancelado")`) se acota a `("cerrado",
"cancelado")` únicamente. El ticket "Resuelto" que es rechazado (`reject_resolution` → vuelve a
`en_ejecucion`) sigue sumando tiempo sin reinicio, ya que nunca se congeló al entrar a "Resuelto".

**Rationale**: Requisito explícito de la spec `038` (FR-011/FR-012): "el reloj de SLA debe
mantenerse activo... hasta que el ticket pase a estado Cerrado (no detenerse al pasar a
Resuelto)". Esto reemplaza el comportamiento de congelamiento en "Resuelto" introducido por las
specs `014`/`023`/`033`. "Cancelado" se mantiene como estado final congelado sin cambios, al ser
irreversible.

**Alternatives considered**: Congelar en "Resuelto" pero mostrar un contador visual aparte para el
tiempo en espera de aceptación del cliente — rechazada por ser una funcionalidad no pedida y de
mayor alcance que la corrección solicitada.

## Decisión 5 — Entrada de auditoría inicial sin tabla nueva

**Decision**: Al crear un Ticket/Tarea, `ticket_service.py` inserta una fila en
`ticket_status_transitions` (tabla ya existente) con `from_status = "creado"` (valor sentinel, no
es un estado real del FSM), `to_status = <estado inicial del ticket>`, `actor_id = <creador>`,
`comment_id = NULL`. `_transitions_with_sla()` (ya en `backend/api/routes/tickets.py`) y el
frontend que renderiza el Historial de Estados reconocen `from_status == "creado"` para mostrar
"Ticket creado en estado {to_status}" en vez del formato habitual "cambio de X a Y".

**Rationale**: `ticket_status_transitions.from_status`/`to_status` son `Text NOT NULL` (sin
`CHECK` de enum) — permite un valor sentinel sin migración de esquema. Reutilizar la tabla
existente evita una migración nueva y mantiene el Historial de Estados como fuente única del
timeline completo (creación + transiciones), consistente con Principio VI (Gold Standard Dataset).

**Alternatives considered**: Tabla nueva `ticket_audit_log` — rechazada por violar el principio de
"cero complejidad no justificada" (Principio VII) cuando la tabla existente ya cubre el caso con
un valor sentinel.

## Decisión 6 — Correo de bienvenida: reutiliza el token de reseteo de contraseña (spec `003`)

**Decision**: El flujo "Notificar al Usuario" (US5) genera el mismo tipo de token de un solo uso
ya usado por "¿Olvidaste tu contraseña?" (spec `003`), con la misma expiración de 30 minutos ya
implementada ahí, y agrega `send_welcome_email()` a `backend/infra/email/mailer.py` (mismo
archivo, mismo mecanismo SMTP por variables de entorno que `send_password_reset_email()`), con una
plantilla HTML renderizada vía Jinja2 (ya incluido con Flask, sin dependencia nueva).

**Rationale**: La spec `038` pide exactamente "un enlace para cambiar la contraseña con validez
restringida a 30 minutos" — coincide exactamente con el mecanismo ya construido y probado en spec
`003`. Reimplementar un token/expiración paralelo sería duplicar lógica de seguridad sensible sin
necesidad.

**Alternatives considered**: Servicio de plantillas de correo de terceros (ej. un motor de
templating adicional) — rechazado por Principio V (cero dependencias nuevas sin aprobación);
Jinja2 ya está disponible transitivamente vía Flask y es suficiente para una plantilla HTML simple
con logo embebido (data URI o referencia a asset servido por el propio backend).

## Decisión 7 — "Copiar Contraseña": manejo de fallo del Clipboard API

**Decision**: `handleCopyPassword` en `TeamPage.tsx` pasa a `await navigator.clipboard.writeText(...)`
dentro de un `try/catch`; en éxito muestra el toast de éxito ya existente, en fallo (rechazo de la
promesa — típico en contexto no seguro, es decir HTTP sin TLS en vez de `localhost`/HTTPS, o
permiso de portapapeles denegado) muestra un toast de error explícito en vez de un éxito falso.

**Rationale**: El código actual (`TeamPage.tsx:248-251`) llama a `navigator.clipboard.writeText(...)`
sin `await` ni manejo de rechazo, y muestra el toast de éxito incondicionalmente — si la promesa
se rechaza (API no disponible en un contexto no seguro, típico al acceder por IP/HTTP en vez de
`localhost`), el usuario ve "Contraseña copiada" aunque el portapapeles no haya cambiado. Esto
coincide exactamente con el bug reportado.

**Alternatives considered**: Fallback con `document.execCommand('copy')` sobre un `<textarea>`
oculto para contextos no seguros — se deja como mitigación opcional dentro de la misma tarea si el
entorno de despliegue real (HTTP sin TLS) lo requiere; no es una dependencia nueva, es API nativa
del navegador.

## Decisión 8 — Parpadeo generalizado de UI: diagnóstico antes de tocar código

**Decision**: Antes de aplicar un fix, la implementación de US3 debe reproducir el parpadeo en
Docker real y determinar la causa concreta entre los candidatos: (a) el listener de scroll ya
corregido en spec `036` (zona muerta 12px + RAF) no cubre el nuevo caso porque el parpadeo ahora
también afecta al menú lateral, fuera del árbol de `TicketDetailPage`; (b) un componente que hace
polling (ej. `NotificationBell`, 60s) y fuerza un re-render de un provider que envuelve todo el
layout (incluido el menú); (c) el propio `Layout.Sider` de Ant Design re-renderizando en cada
cambio de estado de un padre no memoizado. No se asume la causa de antemano en el spec — es un
requisito de investigación dirigida, no una reescritura general del layout (Principio VII: alcance
acotado).

**Rationale**: El reporte original dice explícitamente que el parpadeo "ahora afecta también al
menú y a los componentes principales" — es decir, es un problema nuevo o más amplio que el ya
corregido en spec `036`, no el mismo bug reapareciendo. Diagnosticar antes de tocar código evita
un fix a ciegas que no ataque la causa real.

**Alternatives considered**: Aplicar el mismo patrón de zona muerta+RAF a todos los listeners de
scroll de la app de forma preventiva — rechazado por exceder el alcance pedido (Principio VII
prohíbe refactors no solicitados fuera del alcance).

## Decisión 9 — Credenciales cruzadas entre pestañas de Accesos del Cliente: estado de formulario por pestaña

**Decision**: En `ClientsPage.tsx`, el bug se origina en que el formulario de credenciales
(`editingCredential`/`credentialsByAccess`) no resetea o no aísla correctamente los campos del
`Form` de Ant Design al cambiar de pestaña/tipo de acceso activo — la instancia de formulario
conserva valores del tipo anterior y los aplica al guardar el nuevo. El fix acota el `key` del
componente de formulario de credenciales al `accessId`/tipo activo (forzando remount de React al
cambiar de pestaña) y/o llama a `form.resetFields()` explícitamente en el cambio de pestaña, sin
tocar el resto de la pantalla de Cliente.

**Rationale**: Es el patrón estándar de React/Ant Design para este tipo de bug (estado de
formulario compartido entre "instancias lógicas" distintas que reutilizan el mismo árbol de
componentes) y no requiere rediseñar la estructura de pestañas existente (spec `031`).

**Alternatives considered**: Un formulario completamente independiente por tipo de acceso en vez
de uno compartido parametrizado — rechazado por ser un cambio de mayor alcance del necesario para
corregir el bug puntual.

## Decisión 10 — Rendimiento de "Ver detalle de cliente": lazy load por pestaña + auditoría de red

**Decision**: La implementación debe primero perfilar (DevTools/Network) las peticiones actuales
disparadas al abrir el detalle de un Cliente con datos abundantes, identificar cuáles son
redundantes o innecesarias antes de que el usuario visite esa pestaña (Accesos, Proyectos,
Contactos), y diferir su carga a la selección real de la pestaña (`Tabs` de Ant Design ya soporta
`destroyInactiveTabPane`/carga bajo demanda sin librería nueva).

**Rationale**: FR-029/FR-030 piden reducir tiempo de carga y evitar peticiones redundantes; sin
perfilar primero no se puede afirmar cuál es el cuello de botella real (¿backend N+1, o frontend
disparando todas las pestañas de una vez?) — coherente con Principio VII de no optimizar a ciegas.

**Alternatives considered**: Ninguna sin datos de perfilado — cualquier optimización se decide
durante la implementación en base al perfilado real, no de antemano.

## Todas las [NEEDS CLARIFICATION] resueltas

El spec (`spec.md`) no dejó marcadores `[NEEDS CLARIFICATION]` pendientes — las decisiones de
alcance ambiguas (rol QM sobre la vista global de Tickets, reemplazo del congelamiento de SLA en
"Resuelto") ya quedaron documentadas en la sección "Assumptions" del spec y se ratifican aquí como
Decisiones 3-4.
