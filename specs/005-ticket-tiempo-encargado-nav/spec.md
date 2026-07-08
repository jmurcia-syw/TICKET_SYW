# Feature Specification: Registro de tiempo en el detalle del ticket, rol Encargado y navegación

**Feature Branch**: `005-ticket-tiempo-encargado-nav`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Quiero iniciar la Fase 2 del proyecto enfocándome en la gestión de
tiempos, navegación y un nuevo rol de usuario dentro del detalle del Ticket. Los requisitos
específicos son: 1) Registro de Tiempo Manual (Estilo Teamwork) visible dentro del detalle del
ticket, con desglose/historial de tiempos registrados (fecha, duración, nota, autor). 2) Campo
de Tiempo Estimado de solución en el ticket. 3) Nuevo rol por defecto 'Encargado' — usuario con
email pero sin perfil avanzado, con permisos de solo crear y ver sus propios tickets, visible
explícitamente en el ticket como el solicitante (distinto del Cliente). 4) Corrección de
navegación: al volver desde el detalle de un ticket abierto desde el Kanban, la app hoy no
respeta el origen; implementar breadcrumbs estilo Teamwork para volver exactamente a la pantalla
de origen."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar tiempo directamente desde el detalle del ticket (Priority: P1)

Un Resolutor (o cualquier recurso interno) abre el detalle de un ticket en el que participa y,
sin salir de esa pantalla, registra cuánto tiempo trabajó hoy en ese ticket: fecha, hora de
inicio, hora de finalización (la duración se calcula automáticamente a partir de ambas) y una
nota. Si prefiere, puede fijar la duración manualmente en vez de indicar las horas exactas.
Debajo del formulario ve el historial completo de todos los registros de tiempo de ese ticket —
quién los cargó, cuándo, cuánto y con qué nota — igual que el desglose de "Registros de tiempo"
de Teamwork.

**Why this priority**: Es el pedido central de esta fase — bajar la fricción de registrar tiempo
llevándolo al lugar donde el Resolutor ya está trabajando (el ticket), en vez de obligarlo a ir a
una pantalla separada. Reutiliza el motor de registro de tiempos ya construido (Fase 2 —
`work_sessions`), por lo que es la historia de mayor valor con menor riesgo técnico.

**Independent Test**: Abrir el detalle de un ticket asignado, cargar un registro de tiempo desde
la nueva sección, y verificar que aparece de inmediato en el historial de esa misma pantalla con
todos sus datos.

**Acceptance Scenarios**:

1. **Given** un Resolutor en el detalle de un ticket que le pertenece, **When** carga un registro
   de tiempo indicando fecha, hora de inicio, hora de finalización y una nota, **Then** el
   registro aparece en el historial con la duración calculada automáticamente, la nota y el
   nombre de quien lo cargó.
2. **Given** el mismo formulario, **When** el usuario fija la duración manualmente en vez de
   cargar horas de inicio/fin exactas, **Then** el registro se guarda igual, con esa duración.
3. **Given** un ticket con varios registros de tiempo de distintos recursos, **When** el usuario
   abre el detalle, **Then** ve el historial completo ordenado (más reciente primero) con el
   total de tiempo acumulado del ticket.
4. **Given** un registro de tiempo propio cargado dentro de la ventana de edición vigente,
   **When** el usuario lo edita o elimina desde el mismo historial, **Then** el cambio se refleja
   de inmediato sin salir del detalle del ticket.

---

### User Story 2 - Ver y definir el tiempo estimado de solución del ticket (Priority: P2)

Un Coordinador o Resolutor, al crear o trabajar un ticket, indica cuánto tiempo estima que tomará
resolverlo (en horas), y ese valor queda visible de forma prominente en el detalle del ticket,
junto al tiempo ya registrado, para poder comparar estimado vs. real de un vistazo.

**Why this priority**: Da contexto de planificación una vez que ya existe el registro de tiempo
real (US1); tiene valor por sí sola pero depende conceptualmente de poder compararse contra algo.

**Independent Test**: Crear un ticket indicando un tiempo estimado en horas y verificar que se
muestra en el detalle, junto al total de tiempo ya registrado por US1.

**Acceptance Scenarios**:

1. **Given** un Coordinador creando un ticket, **When** completa el campo "Tiempo estimado de
   solución" en horas, **Then** el ticket se crea con ese valor y se muestra en su detalle.
2. **Given** un ticket sin tiempo estimado definido, **When** se consulta su detalle, **Then**
   se ve claramente como "Sin estimar" en vez de mostrarse vacío o en blanco.
3. **Given** un ticket con tiempo estimado y con registros de tiempo cargados (US1), **When** se
   ve el detalle, **Then** el estimado y el total registrado se muestran uno junto al otro.

---

### User Story 3 - Rol "Encargado" que registra y sigue sus propios tickets (Priority: P2)

Una persona externa al equipo interno (el "Encargado" del lado del cliente) inicia sesión con su
cuenta, registra un ticket describiendo su necesidad, y puede ver el estado de los tickets que él
mismo registró — sin ver los de otros Encargados ni acceder a ninguna otra pantalla del sistema.
En el detalle de cada uno de sus tickets, cualquier usuario interno puede ver claramente que ese
Encargado es quien lo solicita, diferenciado del Cliente (la empresa) al que pertenece.

**Why this priority**: Habilita un canal de entrada de tickets directo desde el lado del cliente,
complementario al registro manual por Coordinador ya existente; no bloquea a US1/US2 pero es
igual de valiosa para el negocio.

**Independent Test**: Iniciar sesión como un usuario con rol Encargado, crear un ticket, y
verificar que solo ve ese ticket en su listado (no los de otros Encargados ni los del resto del
equipo interno).

**Acceptance Scenarios**:

1. **Given** un usuario con rol Encargado autenticado, **When** crea un ticket, **Then** el
   ticket queda registrado con ese Encargado como solicitante y sigue el ciclo de vida normal de
   Fase 1 (nace en NUEVO).
2. **Given** un Encargado con tickets propios y tickets de otros Encargados existentes en el
   sistema, **When** consulta su listado de tickets, **Then** solo ve los que él mismo registró.
3. **Given** un Coordinador o Resolutor viendo el detalle de un ticket creado por un Encargado,
   **When** revisa la información del ticket, **Then** ve explícitamente el nombre del Encargado
   solicitante, distinguido visualmente del Cliente (empresa) asociado.
4. **Given** un usuario con rol Encargado, **When** intenta acceder a cualquier pantalla que no
   sea la de creación/listado de sus propios tickets (Kanban, Panel de Asignación, Maestros,
   Registro de Tiempos, etc.), **Then** el sistema se lo impide.

---

### User Story 4 - Volver exactamente a la pantalla de origen al salir de un ticket (Priority: P3)

Un Coordinador que abrió un ticket desde el tablero Kanban, al terminar de revisarlo, hace clic en
"Volver" (o en la miga de pan del origen) y regresa exactamente al tablero Kanban tal como lo
había dejado — no a un listado distinto ni a ninguna pantalla de asignación.

**Why this priority**: Es una corrección de experiencia de uso — valiosa pero no bloquea ninguna
de las capacidades nuevas de esta fase; se prioriza última porque es independiente del resto.

**Independent Test**: Entrar al Kanban, abrir un ticket, y verificar que "Volver" regresa al
Kanban (no al listado de Tickets ni a ninguna otra pantalla).

**Acceptance Scenarios**:

1. **Given** un usuario que llegó al detalle de un ticket desde el tablero Kanban, **When** hace
   clic en "Volver", **Then** regresa al tablero Kanban.
2. **Given** un usuario que llegó al detalle de un ticket desde el listado de Tickets (con
   filtros aplicados), **When** hace clic en "Volver", **Then** regresa a ese listado con los
   mismos filtros que tenía antes de entrar.
3. **Given** un usuario que llegó al detalle de un ticket desde el Panel de Asignación, **When**
   hace clic en "Volver", **Then** regresa al Panel de Asignación — nunca a una pantalla de
   asignación de ticket individual.
4. **Given** un usuario que entra directamente a la URL de un ticket (sin navegar desde ninguna
   pantalla previa, ej. abrir el link en una pestaña nueva), **When** hace clic en "Volver",
   **Then** regresa al listado de Tickets (origen por defecto).

---

### Edge Cases

- ¿Qué pasa si se desactiva el Cliente (empresa) vinculado a un Encargado? El Encargado conserva
  el acceso a sus tickets existentes; solo se bloquea la creación de tickets nuevos, con un
  mensaje claro, igual que hoy ocurre para clientes inactivos (FR-001 de Fase 1).
- ¿Qué pasa si dos Encargados del mismo Cliente registran tickets? Cada uno ve solo los propios;
  el Coordinador/QM/Admin siguen viendo todos, con el Encargado solicitante visible en cada uno.
- ¿Qué pasa si el tiempo estimado se dejó sin definir y el ticket ya tiene tiempo real registrado
  (US1)? Se muestra el total registrado igual, y el estimado como "Sin estimar" (FR de US2).
- ¿Qué pasa si el usuario navega al detalle de un ticket desde una notificación o un enlace
  directo (sin pasar por Kanban/Tickets/Panel)? "Volver" usa el origen por defecto (listado de
  Tickets, ver Escenario 4 de US4).

## Requirements *(mandatory)*

### Functional Requirements

**Registro de tiempo en el detalle (US1)**

- **FR-001**: El detalle del ticket DEBE incluir una sección de "Registros de tiempo" donde
  cualquier recurso que participe del ticket (asignado actual o histórico) pueda cargar un nuevo
  registro con fecha, hora de inicio, hora de finalización y una nota opcional, sin salir de esa
  pantalla.
- **FR-001b**: La duración DEBE calcularse automáticamente a partir de la hora de inicio y de
  finalización; el usuario DEBE poder, en cambio, fijar la duración manualmente si no quiere
  indicar horas exactas (la hora de inicio/fin quedan entonces como referencia informativa, no
  obligatoria bit a bit).
- **FR-002**: La sección de "Registros de tiempo" DEBE mostrar el historial completo de
  registros de ese ticket — fecha, hora de inicio/fin (si se cargaron), duración, nota, y quién
  lo cargó — ordenado del más reciente al más antiguo, junto con el total de tiempo acumulado
  del ticket.
- **FR-003**: Un usuario DEBE poder editar o eliminar sus propios registros de tiempo desde esa
  misma sección, sujeto a las mismas reglas de negocio ya vigentes (ventana de edición, límite
  diario) definidas en la Fase 2 de registro de tiempos.
- **FR-004**: Esta sección reutiliza y **extiende** el motor de registro de tiempos ya existente
  (`work sessions`) de la Fase 2 anterior — se agregan los campos de hora de inicio/fin al
  registro existente (que hoy solo tiene fecha + duración + nota); las reglas de negocio ya
  vigentes (límite de 24h/día, ventana de edición de 7 días, pertenencia al ticket) siguen
  aplicando sobre la duración resultante, calculada o fijada manualmente.

**Tiempo estimado de solución (US2)**

- **FR-005**: El ticket DEBE tener un campo "Tiempo estimado de solución" expresado en horas,
  editable al crear el ticket y mientras el estado lo permita (mismas reglas de bloqueo por
  estado ya vigentes para este dato en Fase 1).
- **FR-006**: El detalle del ticket DEBE mostrar el tiempo estimado de forma prominente junto al
  total de tiempo ya registrado (US1), y mostrar explícitamente "Sin estimar" cuando no fue
  definido.

**Rol Encargado (US3)**

- **FR-007**: El sistema DEBE soportar un rol "Encargado" con una cuenta de acceso propia
  (email/contraseña, igual mecanismo de login que los demás roles).
- **FR-007b**: Cada Encargado DEBE quedar vinculado a exactamente un Cliente (empresa) específico
  al darlo de alta. Todo ticket que el Encargado crea DEBE asociarse automáticamente a ese
  Cliente, sin que el Encargado deba seleccionarlo manualmente.
- **FR-008**: Un usuario con rol Encargado SOLO DEBE poder: crear tickets nuevos (para su propio
  Cliente) y ver/consultar los tickets que él mismo creó — ninguna otra pantalla ni acción del
  sistema (Kanban, Panel de Asignación, Maestros, Registro/Reporte de Tiempos, gestión de otros
  tickets) le es accesible.
- **FR-009**: Todo ticket creado por un Encargado DEBE registrar quién es ese Encargado, y el
  detalle del ticket DEBE mostrarlo explícitamente de forma diferenciada del Cliente (empresa)
  asociado.
- **FR-010**: Un Encargado NUNCA DEBE ver tickets creados por otros Encargados, ni tickets creados
  internamente por Coordinador/QM/Admin/Resolutor que no sean propios.
- **FR-011**: Coordinador, QM y Admin DEBEN poder ver, en cualquier ticket, tanto el Encargado
  solicitante como el Cliente asociado, sin restricciones adicionales sobre lo ya vigente en
  Fase 1.

**Navegación (US4)**

- **FR-012**: El detalle del ticket DEBE mostrar una migas de pan (breadcrumb) o control de
  "Volver" que regrese exactamente a la pantalla de origen desde la que se navegó (Kanban,
  listado de Tickets con sus filtros, o Panel de Asignación).
- **FR-013**: Si no hay un origen de navegación identificable (ej. acceso directo por URL), el
  control de "Volver" DEBE regresar al listado de Tickets por defecto.
- **FR-014**: En ningún caso "Volver" desde el detalle de un ticket DEBE llevar a una pantalla de
  asignación de ticket individual.

### Key Entities

- **WorkSession (Registro de tiempo)**: Entidad ya existente de Fase 2, extendida en esta fase
  con hora de inicio y hora de finalización (opcionales; la duración se calcula a partir de
  ellas o se fija manualmente). Se agrega además un punto de entrada/visualización dentro del
  detalle del ticket, filtrado por `ticket_id`.
- **Ticket**: Se extiende con el campo de tiempo estimado (ya existe como dato interno desde
  Fase 1 — ver Assumptions) y con la referencia al Encargado solicitante.
- **Encargado**: Nuevo rol de usuario con cuenta de acceso propia, vinculado a un Cliente
  (empresa) específico y predefinido al darlo de alta. Todo ticket que crea queda asociado
  automáticamente a ese Cliente — no elige el Cliente manualmente como sí hace hoy un
  Coordinador. Un Encargado se identifica como el solicitante de los tickets que crea.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un Resolutor puede registrar el tiempo de un ticket sin salir del detalle en menos
  de 20 segundos desde que decide hacerlo.
- **SC-002**: El 100% de los registros de tiempo de un ticket son visibles en su historial dentro
  del propio detalle, sin necesitar navegar a otra pantalla.
- **SC-003**: El 100% de los tickets muestran su tiempo estimado (o "Sin estimar") junto al total
  de tiempo real registrado, sin cálculo manual por parte del usuario.
- **SC-004**: Un Encargado nunca ve, en el 100% de los casos probados, tickets que no creó él
  mismo.
- **SC-005**: El 100% de los accesos de "Volver" desde el detalle de un ticket regresan a la
  pantalla de origen correcta (Kanban, Tickets con filtros, o Panel de Asignación), sin pasar por
  ninguna pantalla de asignación.

## Assumptions

- El motor de registro de tiempos (entidad, reglas de límite diario/ventana de edición, permisos
  `work_sessions:*`) ya existe de la Fase 2 anterior; esta fase lo extiende con hora de inicio/fin
  (nuevos campos opcionales) pero reutiliza tal cual sus reglas de negocio existentes (límite
  diario, ventana de edición, pertenencia al ticket), aplicadas sobre la duración resultante.
- Las pantallas globales "Registro de Tiempos" y "Reporte de Tiempos" ya construidas se mantienen
  sin cambios como vistas complementarias (útiles para consolidado por recurso/período); esta
  fase agrega el registro embebido en el ticket como un segundo punto de entrada, no reemplaza
  las pantallas existentes.
- El campo de tiempo estimado ya existe en el modelo de datos desde Fase 1
  (`estimated_resolution_minutes`, opcional, bloqueado/desbloqueado por estado del ticket); esta
  fase reutiliza ese mismo dato — solo cambia su presentación (mostrarlo en horas, más prominente,
  junto al tiempo real) y sigue siendo opcional en la creación del ticket, con las mismas reglas
  de bloqueo por estado ya vigentes.
- El rol Encargado inicia sesión con el mismo mecanismo (email + contraseña) que los demás roles;
  no se define en esta fase ningún flujo de autoregistro público — las cuentas de Encargado las
  da de alta un Admin/Coordinador, igual que hoy se dan de alta los demás usuarios internos.
- No se define en esta fase ninguna notificación o portal adicional para el Encargado más allá de
  crear y consultar sus propios tickets — el Portal de Clientes completo queda para la Fase 8 del
  roadmap.
