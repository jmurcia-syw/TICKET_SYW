# Feature Specification: Fase 1 — Tickets

**Feature Branch**: `002-fase1-tickets`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "Aplicación de Tickets (Fase 1 SDD V3): registro y gestión de
tickets con ciclo de vida manual de 9 estados según docs/Regla de actividad de estados.xlsx;
comentarios tipificados con adjuntos que disparan las transiciones de estado y notificaciones;
asignación de resolutores por el Coordinador (Triage Push) con endpoint independiente de
asignación que registra contexto para el Gold Standard Dataset; Panel de Asignación básico;
campos: tipo de registro, tipo, prioridad, severidad, herramienta, proceso, cliente, proyecto,
tiempo estimado de resolución, registro relacionado, niveles de escalamiento N1-N4"

## Clarifications

### Session 2026-07-02

- Q: ¿Se incluye el estado EN PRUEBAS (marcado con "?" en el Excel) en Fase 1? → A: Sí, en
  versión simple: el Resolutor lo activa y lo resuelve manualmente
  (EN EJECUCIÓN→EN PRUEBAS→EN EJECUCIÓN/RESUELTO), sin reasignación ni notificaciones
  especiales; se refinará en Fase 6 (motor FSM).
- Q: ¿Quién registra la "Respuesta de usuario" si el cliente no tiene acceso en Fase 1? → A:
  El Resolutor o Coordinador registra un comentario "Respuesta de usuario" en nombre del
  cliente (recibida por email/llamada), pudiendo adjuntar la evidencia.
- Q: ¿Alcance del enforcement de seguridad en API? → A: Enforcement completo en esta fase:
  JWT + permisos en TODAS las rutas de la API (tickets Y maestros), cerrando la deuda
  diferida de Fase 0 (FR-017 de la spec 001).

### Session 2026-07-06

- Q: ¿El campo "tipo de registro" (Ticket/Tarea) sigue siendo un valor fijo (CHECK
  constraint) o pasa a ser un catálogo administrable? → A: Pasa a ser un catálogo dinámico
  (`catalog_record_types`), con la misma mecánica CRUD que herramienta/proceso/tipo de
  resolución (`catalogs:view/create/deactivate`), sembrado con los valores "Ticket" y
  "Tarea". La restricción de dominio que bloquea crear tickets con valor "Tarea" (reservado
  para Fase 3) se mantiene sin cambios: solo el catálogo se vuelve administrable, no se
  desbloquea la funcionalidad de Tareas en esta fase.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registro y consulta de tickets (Priority: P1)

Un Coordinador (o cualquier usuario interno autorizado) registra manualmente un ticket recibido
del cliente: selecciona cliente y proyecto, clasifica el ticket (tipo, prioridad, severidad,
herramienta, proceso) y lo describe. El ticket nace siempre en estado NUEVO. Cualquier miembro
del equipo puede consultar el listado de tickets con filtros (cliente, proyecto, estado,
prioridad, resolutor asignado) y ver el detalle completo de un ticket, incluyendo su historial
de comentarios y cambios de estado.

**Why this priority**: Sin registro y consulta de tickets no existe la funcionalidad núcleo de
la aplicación. Es el MVP mínimo demostrable.

**Independent Test**: Crear un ticket completo desde la pantalla de tickets, verificar que nace
en NUEVO, aparece en el listado, y su detalle muestra todos los campos de clasificación.

**Acceptance Scenarios**:

1. **Given** un Coordinador autenticado en la pantalla de Tickets, **When** completa el
   formulario de nuevo ticket (cliente, proyecto, título, descripción, tipo, prioridad,
   severidad, herramienta, proceso), **Then** el ticket se crea en estado NUEVO con un
   número consecutivo visible y aparece en el listado.
2. **Given** un ticket existente, **When** cualquier usuario autorizado abre su detalle,
   **Then** ve todos los campos, el estado actual, el historial de comentarios ordenado
   cronológicamente y el historial de cambios de estado.
3. **Given** el listado de tickets, **When** el usuario filtra por estado "NUEVO" y cliente X,
   **Then** solo ve los tickets de ese cliente en ese estado.
4. **Given** un formulario de ticket con un proyecto de un cliente inactivo o un proyecto
   inactivo, **When** el usuario intenta seleccionarlo, **Then** el selector no lo ofrece
   (solo clientes y proyectos activos).

---

### User Story 2 - Triage Push: asignación y estados iniciales (Priority: P1)

Un Coordinador revisa los tickets en estado NUEVO y decide: (a) asignarlo directamente a un
Resolutor — el ticket pasa automáticamente a CONTACTO y el Resolutor recibe una notificación —
o (b) si requiere apoyo técnico, asignarlo al QM con el botón "Pre-Análisis" — el ticket pasa
a PRE-ANÁLISIS y el QM recibe la notificación. Cada asignación registra automáticamente un
comentario tipificado ("Asignado" o "Pre-Análisis") con quién asignó, a quién y cuándo, y
guarda el contexto de la decisión (skills del asignado, carga de trabajo actual, severidad y
prioridad del ticket) para el futuro entrenamiento del Triage Agent (Gold Standard Dataset).

**Why this priority**: El Triage Push es el flujo operativo central del Coordinador y la
semilla del AI Dispatcher futuro (Principio VI de la constitución). Junto con US1 forma el
ciclo mínimo completo: crear → asignar.

**Independent Test**: Con tickets en NUEVO, asignar uno a un Resolutor y verificar que pasa a
CONTACTO con comentario automático "Asignado" y registro de contexto; asignar otro al QM y
verificar que pasa a PRE-ANÁLISIS.

**Acceptance Scenarios**:

1. **Given** un ticket en NUEVO, **When** el Coordinador lo asigna a un Resolutor, **Then** el
   ticket pasa a CONTACTO, se crea un comentario automático tipo "Asignado" (interno) con
   asignador, asignado, fecha y hora, y el Resolutor recibe una notificación en la aplicación.
2. **Given** un ticket en NUEVO, **When** el Coordinador usa "Pre-Análisis" y selecciona al QM,
   **Then** el ticket pasa a PRE-ANÁLISIS asignado al QM, con comentario automático y
   notificación al QM.
3. **Given** un ticket en PRE-ANÁLISIS, **When** el QM lo reasigna a un Resolutor, **Then**
   el ticket pasa a CONTACTO con comentario automático y notificación al nuevo asignado.
4. **Given** cualquier asignación, **When** se consulta el registro de asignaciones, **Then**
   existe una entrada con el contexto completo de la decisión: skills del asignado, cantidad
   de tickets abiertos que tenía en ese momento, prioridad y severidad del ticket, quién
   asignó y cuándo.
5. **Given** un ticket asignado, **When** se intenta la asignación por la API directamente
   (sin pasar por la pantalla), **Then** el comportamiento es idéntico — la asignación es una
   función del backend agnóstica al caller.

---

### User Story 3 - Ciclo de vida por comentarios tipificados (Priority: P2)

Un Resolutor gestiona su ticket a través de comentarios tipificados que disparan las
transiciones de estado según la matriz de "Regla de actividad de estados": al enviar
"Confirmación de atención" (externo) el ticket pasa de CONTACTO a EN ANÁLISIS; al enviar
"Termina análisis" (interno) pasa a EN EJECUCIÓN; una "Solicitud de información" (externo)
lo lleva a PENDIENTE DE USUARIO y la respuesta del usuario lo devuelve a EN EJECUCIÓN; una
"Solicitud de cierre" (externo) lo lleva a RESUELTO; la aceptación del usuario (o 3 días sin
respuesta) permite al Resolutor cerrarlo (CERRADO) registrando el "Tipo de resolución" y un
comentario "Descripción solución". Los comentarios soportan adjuntos. Ciertos campos se
bloquean o desbloquean según el estado (p. ej. severidad/prioridad se bloquean en CONTACTO y
se desbloquean en EN ANÁLISIS junto con el tiempo estimado de resolución).

**Why this priority**: Es el corazón del ciclo de vida, pero requiere US1 y US2 operativos.
En Fase 1 las transiciones se ejecutan al registrar el comentario correspondiente de forma
manual (sin motor FSM automático, que llega en Fase 6) — el catálogo de estados y tipos de
comentario ya es el definitivo.

**Independent Test**: Recorrer el camino feliz completo de un ticket
(NUEVO → CONTACTO → EN ANÁLISIS → EN EJECUCIÓN → RESUELTO → CERRADO) usando solo comentarios
tipificados, verificando estado, bloqueos de campos y notificaciones en cada paso.

**Acceptance Scenarios**:

1. **Given** un ticket en CONTACTO asignado a un Resolutor, **When** el Resolutor envía un
   comentario tipo "Confirmación de atención", **Then** el ticket pasa a EN ANÁLISIS y se
   desbloquean los campos tiempo estimado de resolución, severidad y prioridad.
2. **Given** un ticket en EN ANÁLISIS, **When** el Resolutor registra el tiempo estimado y
   envía "Termina análisis", **Then** el ticket pasa a EN EJECUCIÓN y el campo tiempo de
   resolución queda bloqueado.
3. **Given** un ticket en EN ANÁLISIS o EN EJECUCIÓN, **When** el Resolutor envía "Solicitud
   de información", **Then** el ticket pasa a PENDIENTE DE USUARIO y se notifica al usuario
   final.
4. **Given** un ticket en PENDIENTE DE USUARIO, **When** el usuario responde, **Then** el
   ticket vuelve a EN EJECUCIÓN y el Resolutor recibe notificación.
5. **Given** un ticket en EN EJECUCIÓN, **When** el Resolutor envía "Solicitud de cierre",
   **Then** el ticket pasa a RESUELTO y se notifica al usuario.
6. **Given** un ticket en RESUELTO, **When** el usuario acepta la resolución (o pasan 3 días
   sin respuesta), **Then** el Resolutor puede cerrarlo registrando obligatoriamente el
   "Tipo de resolución" y un comentario "Descripción solución"; al cerrar se notifica al
   Coordinador y al QM.
7. **Given** un ticket en RESUELTO, **When** el usuario rechaza la resolución, **Then** el
   ticket vuelve a EN EJECUCIÓN con notificación al Resolutor.
8. **Given** cualquier comentario, **When** se adjunta uno o más archivos, **Then** los
   adjuntos quedan asociados al comentario y son descargables desde el detalle del ticket.
9. **Given** un ticket en un estado que no admite cierta transición, **When** se intenta el
   comentario tipificado correspondiente, **Then** el sistema lo rechaza con mensaje en
   español indicando el estado actual y las acciones válidas.

---

### User Story 4 - Panel de Asignación (Priority: P2)

Un Coordinador abre el Panel de Asignación y ve de un vistazo cuántos tickets tiene asignados
cada Resolutor (incluido el QM) y en qué estado se encuentran, con la lista de tickets en
NUEVO pendientes de triage. Desde el panel puede asignar directamente un ticket NUEVO a un
resolutor.

**Why this priority**: Herramienta de productividad del Coordinador; el triage funciona sin
él (desde el detalle del ticket), pero el panel es el diferenciador operativo de la fase.

**Independent Test**: Con varios tickets asignados a distintos resolutores en distintos
estados, verificar que la matriz resolutor × estado muestra los conteos correctos y que
asignar desde el panel produce el mismo efecto que asignar desde el detalle.

**Acceptance Scenarios**:

1. **Given** tickets asignados a 3 resolutores en estados distintos, **When** el Coordinador
   abre el Panel de Asignación, **Then** ve una matriz resolutor × estado con el conteo de
   tickets por celda y el total por resolutor.
2. **Given** tickets en estado NUEVO, **When** el Coordinador los ve en el panel, **Then**
   puede asignar cada uno a un resolutor sin salir del panel (mismo efecto que US2).
3. **Given** el panel abierto, **When** se filtra por una selección de estados (ej. solo
   CONTACTO y EN ANÁLISIS), **Then** los conteos reflejan solo esos estados.

---

### Edge Cases

**Registro y clasificación**
- Ticket sin proyecto: debe permitirse asociarlo solo a cliente cuando el trabajo no
  corresponde a un proyecto específico (soporte general).
- Cliente o proyecto desactivado después de creado el ticket → el ticket conserva la
  referencia y sigue siendo gestionable; solo se bloquea usarlos en tickets nuevos.
- Campos de clasificación (herramienta, proceso, tipo de registro) con valores fuera del
  catálogo → rechazar; los catálogos son administrables, no texto libre.
- Intentar crear un ticket con tipo de registro "Tarea" → rechazado por el dominio
  (reservado para Fase 3, FR-030), aun cuando el catálogo ya tenga el valor sembrado y
  administrable.

**Asignación**
- Asignar a un resolutor inactivo → rechazar con mensaje claro.
- Reasignación de un ticket ya asignado (CONTACTO o posterior) → permitida para
  Coordinador/QM; genera nuevo comentario "Asignado" y notificación; el registro de
  asignaciones conserva la historia completa.
- Asignación concurrente del mismo ticket por dos coordinadores → last-write-wins, el
  registro de asignaciones conserva ambas entradas en orden.
- Un ticket en NUEVO no puede recibir comentarios de avance (Confirmación de atención, etc.)
  antes de ser asignado.

**Ciclo de vida**
- Cierre sin "Tipo de resolución" → bloqueado; el campo es obligatorio para CERRADO.
- Cierre por inactividad: si el usuario no responde la Solicitud de cierre en 3 días, el
  Resolutor recibe una notificación y puede cerrar con comentario "Cerrado sin respuesta de
  usuario".
- CERRADO es estado final: no admite más transiciones ni comentarios que muevan el estado
  (los comentarios informativos siguen permitidos).
- El ticket puede pasar a CANCELADO desde cualquier estado no final por el Coordinador, con
  comentario obligatorio del motivo.
- Adjuntos: tamaño máximo por archivo y tipos permitidos definidos por configuración;
  archivos que excedan el límite → rechazo con mensaje claro.

**Seguridad y visibilidad**
- Usuario sin permiso del módulo tickets → no ve el menú ni accede por URL directa.
- Un Resolutor solo puede ejecutar transiciones sobre tickets que tiene asignados; el
  Coordinador y el QM pueden sobre cualquiera.

## Requirements *(mandatory)*

### Functional Requirements

**Registro y clasificación**

- **FR-001**: El sistema DEBE permitir crear tickets manualmente con: título, descripción,
  cliente (obligatorio), proyecto (opcional, solo proyectos activos del cliente), tipo de
  registro (catálogo administrable, sembrado con Ticket/Tarea — ver FR-029/FR-030; en esta
  fase el dominio solo permite crear con el valor Ticket, Tarea queda reservado para
  Fase 3), tipo (Incidente, Evolutivo, Preventivo), prioridad, severidad, herramienta
  (catálogo: JDE, Fusion, etc.), proceso (catálogo), y nivel de escalamiento (N1-N4,
  default N2).
- **FR-002**: Todo ticket DEBE nacer en estado NUEVO con número consecutivo único visible
  (formato legible para humanos) y fecha/hora de creación.
- **FR-003**: El sistema DEBE ofrecer un listado paginado de tickets con filtros combinables
  por cliente, proyecto, estado, prioridad, severidad, tipo, resolutor asignado y búsqueda de
  texto en título/número, con ordenamiento por columna.
- **FR-004**: El campo "registro relacionado" DEBE permitir vincular un ticket con otro
  existente (relación visible en ambos sentidos).
- **FR-005**: Los catálogos de herramienta, proceso y tipo de registro DEBEN ser
  administrables (crear/desactivar valores) por Admin y Coordinador; los demás campos de
  clasificación usan listas fijas (tipo, prioridad, severidad, escalamiento).
- **FR-006**: El detalle del ticket DEBE mostrar el historial completo: comentarios (con tipo,
  autor, fecha, adjuntos) y cambios de estado (de qué estado a cuál, quién, cuándo, comentario
  que lo disparó).

**Estados y transiciones (matriz "Regla de actividad de estados")**

- **FR-007**: El sistema DEBE implementar exactamente los 9 estados: NUEVO, PRE-ANÁLISIS,
  CONTACTO, EN ANÁLISIS, EN EJECUCIÓN, EN PRUEBAS, PENDIENTE DE USUARIO, RESUELTO, CERRADO,
  más CANCELADO como estado terminal alternativo.
- **FR-008**: Las transiciones válidas son únicamente las definidas en la matriz del Excel:
  NUEVO→CONTACTO (asignar resolutor), NUEVO→PRE-ANÁLISIS (asignar QM),
  PRE-ANÁLISIS→CONTACTO (reasignar a resolutor), PRE-ANÁLISIS→PENDIENTE DE USUARIO
  (solicitud de información), CONTACTO→EN ANÁLISIS (confirmación de atención),
  EN ANÁLISIS→EN EJECUCIÓN (termina análisis), EN ANÁLISIS→PENDIENTE DE USUARIO,
  EN EJECUCIÓN→PENDIENTE DE USUARIO, EN EJECUCIÓN→RESUELTO (solicitud de cierre),
  EN EJECUCIÓN→EN PRUEBAS y EN PRUEBAS→EN EJECUCIÓN/RESUELTO (manual simple, FR-009),
  PENDIENTE DE USUARIO→EN EJECUCIÓN (respuesta del usuario), RESUELTO→EN EJECUCIÓN (rechazo),
  RESUELTO→CERRADO (aceptación o 3 días), y →CANCELADO desde cualquier estado no final.
  Cualquier otra transición DEBE rechazarse con mensaje en español.
- **FR-009**: El estado EN PRUEBAS se incluye en versión simple (clarificado 2026-07-02):
  el Resolutor asignado puede pasar manualmente EN EJECUCIÓN→EN PRUEBAS y de EN PRUEBAS a
  EN EJECUCIÓN o RESUELTO. No implica reasignación ni notificaciones especiales; el ticket
  permanece asignado al mismo Resolutor y el tiempo de resolución sigue bloqueado (FR-010).
  La semántica completa (quién prueba, reasignación al funcional) se definirá con el motor
  FSM de Fase 6.
- **FR-010**: El sistema DEBE aplicar los bloqueos de campos por estado definidos en la
  matriz: en CONTACTO se bloquean tiempo del SLA, severidad y prioridad; en EN ANÁLISIS se
  desbloquean tiempo estimado de resolución, severidad y prioridad; en EN EJECUCIÓN y
  EN PRUEBAS se bloquea el tiempo de resolución; al aceptarse el cierre (o pasar 3 días) se
  habilita el campo "Tipo de resolución".
- **FR-011**: En esta fase los cambios de estado se ejecutan por acciones manuales del
  Coordinador/QM/Resolutor (asignar, registrar comentario tipificado, botones de
  aceptar/rechazar); no hay motor de automatización (Fase 6), pero cada transición DEBE
  quedar registrada con autor, fecha/hora y comentario asociado.
- **FR-012**: Para cerrar un ticket (CERRADO) el Resolutor DEBE registrar el campo "Tipo de
  resolución" (catálogo) y un comentario tipo "Descripción solución". Sin ambos, el cierre
  se bloquea.

**Comentarios tipificados y adjuntos**

- **FR-013**: El sistema DEBE soportar los tipos de comentario: Asignado (automático,
  interno), Pre-Análisis (automático, interno), Confirmación de atención (manual, externo),
  Solicitud de información (manual, externo), Termina análisis (manual, interno), Solicitud
  de cierre (manual, externo), Respuesta de usuario (externo), Descripción solución (manual,
  interno), Comentario interno (manual, sin efecto de estado) y Cancelación (manual,
  interno). El tipo es un dato estructurado, nunca texto libre.
- **FR-014**: Cada tipo de comentario manual DEBE estar disponible solo en los estados donde
  la matriz lo permite, y al registrarse DEBE ejecutar la transición correspondiente
  (FR-008) en la misma operación.
- **FR-015**: Los comentarios DEBEN soportar cero o más adjuntos (tamaño máximo y tipos
  permitidos configurables; default 10 MB por archivo, tipos ofimáticos + imágenes + logs).
- **FR-016**: Los comentarios externos DEBEN quedar marcados como visibles para el cliente
  (preparación para el Portal de Clientes de Fase 8); los internos nunca serán visibles
  fuera del equipo.
- **FR-017**: Dado que el usuario final no tiene acceso al sistema en Fase 1 (el portal es
  Fase 8), la "Respuesta de usuario" la registra el Resolutor o el Coordinador en nombre del
  cliente como comentario tipificado "Respuesta de usuario" (externo), pudiendo adjuntar la
  evidencia recibida (email, captura). Ese comentario ejecuta la transición
  PENDIENTE DE USUARIO→EN EJECUCIÓN igual que lo haría la respuesta directa del usuario.
  Lo mismo aplica a la aceptación/rechazo de la resolución en RESUELTO.

**Asignación (Triage Push) y Gold Standard Dataset**

- **FR-018**: La asignación DEBE ser una operación de backend independiente de la pantalla
  (mismo resultado desde el detalle del ticket, el Panel de Asignación o una llamada directa
  a la API), preparada para que en el futuro la ejecute un agente IA sin cambios de
  arquitectura (Principio VI).
- **FR-019**: Cada asignación DEBE registrar en un histórico inmutable: ticket, asignador,
  asignado, fecha/hora, estado resultante, y el contexto de decisión (skills del asignado al
  momento, número de tickets abiertos del asignado, prioridad y severidad del ticket) —
  el Gold Standard Dataset para el futuro Triage Agent.
- **FR-020**: Solo Coordinador, QM y Admin PUEDEN asignar o reasignar tickets; el nivel de
  acceso se gestiona con el modelo de permisos existente (nuevo módulo `tickets` con
  acciones, incluida una acción específica de asignación).
- **FR-021**: Al asignar, el sistema DEBE notificar al asignado mediante notificación
  interna en la aplicación (campana/contador). La integración con Google Chat es deseable
  pero queda explícitamente fuera del alcance de Fase 1.
- **FR-022**: En esta fase se activa el enforcement completo de seguridad en la API
  (clarificado 2026-07-02): TODAS las rutas (tickets y maestros) exigen JWT válido, usuario
  activo y el permiso módulo+acción correspondiente. Esto cierra la deuda diferida de
  Fase 0 (FR-017 de la spec 001). Excepciones públicas: login provisional, callback de
  Google OAuth2 y health check. Los errores 401/403 no exponen detalle del recurso (mismo
  criterio FR-023 de la spec 001).

**Notificaciones internas**

- **FR-023**: El sistema DEBE generar notificaciones internas por: asignación/reasignación,
  respuesta de usuario recibida, rechazo de resolución, aceptación de cierre, y ticket
  RESUELTO con más de 3 días sin respuesta del usuario. Cada usuario ve sus notificaciones
  no leídas y puede marcarlas como leídas.
- **FR-024**: Al cerrar un ticket (CERRADO), el sistema DEBE notificar al Coordinador y al QM.

**Panel de Asignación**

- **FR-025**: El Panel de Asignación DEBE mostrar la matriz resolutor × estado con conteo de
  tickets, el total por resolutor, y la lista de tickets NUEVOS pendientes de triage, con
  filtro por selección de estados.
- **FR-026**: Desde el panel, el Coordinador DEBE poder asignar tickets NUEVOS sin salir de
  la pantalla (misma operación de FR-018).

**Seguridad y permisos**

- **FR-027**: El acceso a tickets se gobierna con el modelo de roles/permisos existente:
  nuevo módulo `tickets` (ver, crear, editar, asignar, transicionar, cancelar) y módulo
  `assignment_panel` (ver). El seed inicial otorga: Admin y Coordinador todo; QM todo excepto
  cancelar; Resolutor ver, crear y transicionar únicamente sobre sus tickets asignados.
- **FR-028**: Un Resolutor NO PUEDE ejecutar transiciones sobre tickets no asignados a él
  (validación en backend, no solo UI).

**Catálogo de tipo de registro**

- **FR-029**: El catálogo de "tipo de registro" (valores Ticket, Tarea) DEBE ser administrable
  por Admin y Coordinador con la misma mecánica que herramienta/proceso/tipo de resolución
  (`catalogs:view/create/deactivate`, mismo endpoint genérico `/api/catalogs/{catalog}`); no
  se puede desactivar un valor en uso por tickets abiertos (no finales).
- **FR-030**: Aun siendo el catálogo dinámico, el dominio DEBE seguir bloqueando la creación
  de tickets con el valor "Tarea" en esta fase (reservado para Fase 3, FR-001); el intento
  DEBE rechazarse con mensaje en español, independientemente de que el valor esté activo en
  el catálogo.

### Key Entities

- **Ticket**: Registro central. Número consecutivo único, título, descripción, tipo de
  registro (FK catálogo `RecordTypeCatalog`, valores Ticket/Tarea; el dominio solo permite
  crear con Ticket en esta fase), tipo (Incidente/Evolutivo/Preventivo), prioridad, severidad,
  estado (9+CANCELADO), herramienta (FK catálogo), proceso (FK catálogo), cliente (FK),
  proyecto (FK opcional), resolutor asignado (FK Resource opcional), nivel de escalamiento
  (N1-N4), tiempo estimado de resolución, tipo de resolución (catálogo, solo al cerrar),
  registro relacionado (FK autorreferencial opcional), fechas de creación/actualización/cierre.
- **Comment**: Comentario tipificado de un ticket. Tipo (catálogo estructurado FR-013),
  visibilidad (interno/externo), autor, cuerpo, fecha, transición que disparó (opcional).
- **Attachment**: Archivo adjunto a un comentario. Nombre, tamaño, tipo de contenido,
  referencia de almacenamiento.
- **StatusTransition**: Historial de cambios de estado. Ticket, estado origen, estado
  destino, autor, fecha/hora, comentario asociado.
- **Assignment**: Registro inmutable del Gold Standard Dataset. Ticket, asignador, asignado,
  fecha/hora, estado resultante, contexto de decisión (skills del asignado, carga de tickets
  abiertos, prioridad, severidad).
- **Notification**: Notificación interna. Destinatario, tipo de evento, ticket relacionado,
  leída/no leída, fecha.
- **ToolCatalog / ProcessCatalog / ResolutionTypeCatalog / RecordTypeCatalog**: Catálogos
  administrables de herramienta, proceso, tipo de resolución y tipo de registro
  (Ticket/Tarea).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un Coordinador registra un ticket completo (con clasificación) en menos de
  2 minutos.
- **SC-002**: El 100% de los tickets nace en estado NUEVO y ninguna transición fuera de la
  matriz es posible, ni desde la UI ni por API directa.
- **SC-003**: Toda asignación queda registrada con su contexto completo de decisión — el
  histórico de asignaciones nunca pierde entradas ante reasignaciones.
- **SC-004**: El camino feliz completo (NUEVO→CERRADO) es ejecutable de principio a fin solo
  con comentarios tipificados y botones de la matriz, sin edición manual del campo estado.
- **SC-005**: El Panel de Asignación refleja los conteos reales por resolutor y estado con
  datos de al menos 500 tickets sin degradación perceptible (< 2 segundos de carga).
- **SC-006**: El asignado recibe su notificación interna en la siguiente carga/refresco de
  la aplicación en el 100% de las asignaciones.
- **SC-007**: Un Resolutor no logra ejecutar ninguna transición sobre tickets ajenos, ni
  desde la UI ni por API directa (100% de los intentos rechazados).
- **SC-008**: Los listados con filtros responden en menos de 1 segundo con hasta 5.000
  tickets.
- **SC-009**: Todos los mensajes de validación y error se muestran en español.

## Assumptions

- Los 4 maestros de Fase 0 (clientes, proyectos, recursos/skills, roles/permisos) están
  operativos y sembrados; los tickets referencian esas tablas.
- El SLA (tiempos de atención/análisis/resolución por prioridad y cliente) es Fase 4: en esta
  fase el "tiempo estimado de resolución" es un campo informativo editable por el Resolutor
  en EN ANÁLISIS, sin contadores ni alertas automáticas.
- El cierre automático a los 3 días NO es un job automático en esta fase: el sistema calcula
  y muestra la elegibilidad de cierre (y genera la notificación al Resolutor cuando consulta),
  pero la acción de cerrar siempre es manual.
- Recepción de tickets por email, portal de clientes e integraciones son Fases 8+; en Fase 1
  todo ticket se crea manualmente por el equipo interno.
- Las notificaciones son internas a la aplicación; email a usuarios finales y Google Chat
  quedan fuera de alcance (el Excel los marca como "deseable").
- Los adjuntos se almacenan en el servidor de la aplicación (on-premise); su cifrado en
  reposo no es requisito de esta fase (no contienen credenciales, a diferencia de los datos
  VPN de clientes).
- El número consecutivo del ticket es global (no por cliente) con prefijo legible.
- Volumen esperado: cientos de tickets/mes, ~10-30 usuarios concurrentes internos (mismo
  perfil de Fase 0).
- Last-write-wins para ediciones concurrentes de campos del ticket (mismo criterio que
  Fase 0); el historial de transiciones y asignaciones es append-only y no sufre conflictos.
