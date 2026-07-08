# Feature Specification: Refactorización visual y de navegación del detalle del Ticket (flujo tipo Teamwork)

**Feature Branch**: `006-ticket-detalle-tiempo-ui`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Refactorización Visual y de Navegación del Ticket (Inspirado en el flujo de Teamwork). Quiero mejorar la experiencia de usuario (UI/UX) en la vista de Detalles del Ticket y Mis Tareas, tomando como referencia el comportamiento de Teamwork. El objetivo es consolidar la información en un solo lugar y optimizar el registro de tiempos. Requerimientos: 1) Registro de tiempo integrado en un Modal limpio con histórico correlacionado al ticket; al cerrar el modal o volver arriba, se revela de forma fluida el histórico, los comentarios y la actividad del ticket. 2) Nuevos campos visuales: Fecha de inicio, Tiempo estimado (horas), Horas reales/calculadas totales, con indicadores de color sutiles para alertar sobre consumo de tiempo estimado vs. real, respetando la paleta actual. 3) Dejar la estructura visual y de navegación del Ticket y de 'Mis Tareas' preparada para futuras Listas de Tareas/Tickets y Subtareas, sin programar la lógica todavía."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar tiempo sin perder el contexto del ticket (Priority: P1)

Un Resolutor que está trabajando un ticket quiere registrar el tiempo que dedicó sin que la
pantalla se llene de una tabla larga y permanente de historial. Al tocar la acción de "Registrar
tiempo" se abre un modal limpio y enfocado donde carga el registro (fecha, hora de inicio/fin o
duración manual, nota) y puede ver el histórico de tiempos de ese mismo ticket para tener
contexto de lo ya registrado. Al cerrar el modal, o al volver a desplazarse hacia arriba en la
pantalla, el detalle del ticket revela de forma fluida y ordenada el histórico de tiempo, los
comentarios y la actividad — todo en un único flujo consolidado, sin tener que saltar entre
secciones desconectadas.

**Why this priority**: Es el pedido central — reduce la fricción y el "ruido visual" de tener el
registro de tiempo como un bloque grande y siempre visible, acercando la experiencia al patrón ya
conocido de Teamwork. Reutiliza el motor de `work_sessions` ya construido (Fase 2 / Fase 2.1), por
lo que es la historia de mayor valor con menor riesgo técnico.

**Independent Test**: Abrir el detalle de un ticket, tocar "Registrar tiempo", cargar un registro
desde el modal viendo el histórico correlacionado, cerrar el modal y verificar que el histórico,
los comentarios y la actividad se revelan en ese orden en la misma pantalla.

**Acceptance Scenarios**:

1. **Given** un Resolutor en el detalle de un ticket, **When** toca la acción de registrar tiempo,
   **Then** se abre un modal limpio con el formulario de carga y el histórico de tiempo de ese
   ticket, sin abandonar la pantalla del ticket.
2. **Given** el modal de tiempo abierto con histórico visible, **When** el usuario carga un nuevo
   registro, **Then** el histórico dentro del modal se actualiza de inmediato con el nuevo
   registro.
3. **Given** el modal de tiempo abierto, **When** el usuario lo cierra, **Then** la pantalla del
   ticket revela de forma fluida, en este orden, el resumen de tiempo, los comentarios y la
   actividad del ticket.
4. **Given** el detalle de un ticket con el resumen de tiempo colapsado, **When** el usuario
   se desplaza hacia arriba (scroll up) desde los comentarios, **Then** el resumen de tiempo se
   revela nuevamente de forma fluida sin recargar la página.

---

### User Story 2 - Comparar tiempo estimado vs. tiempo real de un vistazo (Priority: P2)

Un Coordinador o Resolutor que abre un ticket quiere saber, sin hacer cálculos, si el ticket va
dentro de lo estimado o si ya se pasó del tiempo previsto. El detalle del ticket muestra la fecha
de inicio, el tiempo estimado de solución (en horas) y el total de horas reales registradas, con
un indicador de color sutil (dentro de la paleta actual del producto) que señala si el consumo
está dentro de lo esperado, cerca del límite, o superado.

**Why this priority**: Da valor de gestión inmediato (visibilidad de desviaciones) apoyándose en
datos que, en su mayoría, ya existen (tiempo estimado y total de horas reales de Fase 2.1);
depende de que la sección de tiempo de la Historia 1 ya esté en pantalla.

**Independent Test**: Abrir un ticket con tiempo estimado definido y registros de tiempo cargados,
y verificar que se muestran fecha de inicio, estimado y real, con el color de alerta esperado
según el porcentaje consumido.

**Acceptance Scenarios**:

1. **Given** un ticket con tiempo estimado y menos del 80% de esas horas registradas, **When** el
   usuario abre el detalle, **Then** el indicador de consumo se muestra en el color "dentro de lo
   esperado" de la paleta actual.
2. **Given** un ticket con tiempo estimado y entre 80% y 100% de esas horas registradas, **When**
   el usuario abre el detalle, **Then** el indicador cambia al color de "atención" de la paleta
   actual.
3. **Given** un ticket con más horas reales registradas que las estimadas, **When** el usuario
   abre el detalle, **Then** el indicador cambia al color de "excedido" de la paleta actual.
4. **Given** un ticket sin tiempo estimado definido, **When** el usuario abre el detalle, **Then**
   se muestra el total de horas reales sin indicador de alerta (no hay base de comparación).

---

### User Story 3 - Pantalla "Mis Tareas" con filtros guardados y reutilizables (Priority: P3)

Un Resolutor que hoy tiene que ir a "Tickets" y aplicar manualmente el filtro "asignado a mí" cada
vez que entra, quiere una pantalla propia, **Mis Tareas**, que ya arranca mostrando sus tickets
asignados. Desde ahí (o desde "Tickets") puede además guardar otras combinaciones de filtros que
usa seguido (por ejemplo, por cliente o por estado) como vistas nombradas y reutilizables,
disponibles indistintamente en ambas pantallas — sin tener que recrear el filtro cada vez que
cambia de una pantalla a otra.

**Why this priority**: Reduce fricción repetitiva de filtrado y es la base concreta (ya no solo
visual) sobre la que se apoyará la futura organización por listas; se prioriza por debajo de las
Historias 1 y 2 porque no es parte del flujo central de trabajar un ticket puntual, pero por
encima de la preparación puramente visual de listas/subtareas porque ya es funcionalidad usable.

**Independent Test**: Abrir "Mis Tareas" y confirmar que arranca con el filtro "Asignado a mí"
aplicado; guardar un filtro adicional con otro criterio desde "Tickets"; volver a "Mis Tareas" y
confirmar que ese mismo filtro guardado está disponible para aplicarlo, y viceversa.

**Acceptance Scenarios**:

1. **Given** un usuario con tickets asignados, **When** abre "Mis Tareas" por primera vez,
   **Then** ve sus propios tickets con el filtro "Asignado a mí" ya aplicado, sin configurar nada.
2. **Given** el usuario está en "Tickets" o en "Mis Tareas" con una combinación de criterios de
   filtro aplicada, **When** la guarda con un nombre, **Then** esa combinación queda disponible
   como filtro guardado en ambas pantallas.
3. **Given** existe un filtro guardado, **When** el usuario lo selecciona desde cualquiera de las
   dos pantallas, **Then** se aplican esos criterios sin tener que volver a configurarlos
   manualmente.
4. **Given** el filtro por defecto "Asignado a mí", **When** el usuario intenta eliminarlo,
   **Then** el sistema no lo permite (solo puede dejar de aplicarlo); los filtros creados por el
   usuario sí pueden eliminarse.

---

### User Story 4 - Navegación preparada para listas y subtareas futuras (Priority: P4)

Un usuario que navega el detalle de un ticket o "Mis Tareas" ve una estructura visual que ya
sugiere jerarquía (ticket dentro de una lista, con espacio para subtareas), aunque hoy esa
jerarquía no tenga funcionalidad real todavía. Esto evita que la futura Fase 3 (Manejo de Tareas,
listas y subtareas — ver `constitution.md`) requiera un rediseño visual completo.

**Why this priority**: Es preparación de UI, no una funcionalidad usable por sí sola; es la de
menor prioridad porque no resuelve un problema inmediato del usuario, pero de bajo costo si se
hace junto con las historias anteriores mientras esas pantallas ya se están tocando.

**Independent Test**: Revisar visualmente el detalle del ticket y "Mis Tareas" y confirmar que
existe un lugar reservado en la jerarquía de navegación (breadcrumb o panel lateral) para "lista"
y para "subtareas", sin que aparezcan controles funcionales que prometan algo que el sistema no
hace todavía.

**Acceptance Scenarios**:

1. **Given** el detalle de un ticket, **When** el usuario lo revisa, **Then** ve un indicio visual
   de jerarquía (p. ej. "lista" a la que pertenecería) presentado como elemento informativo, no
   como control funcional.
2. **Given** el detalle de un ticket, **When** el usuario busca dónde se listarían subtareas,
   **Then** encuentra un espacio visualmente reservado y claramente identificado como "próximamente"
   (mismo lenguaje visual que otros placeholders ya existentes en el detalle del ticket).
3. **Given** "Mis Tareas", **When** el usuario la revisa, **Then** el agrupamiento visual de
   tickets ya sugiere que en el futuro podrán pertenecer a listas distintas.

---

### Edge Cases

- ¿Qué pasa si el usuario abre el modal de registrar tiempo y lo cierra sin guardar nada? El
  detalle del ticket debe revelar el flujo de histórico/comentarios/actividad igual que si hubiera
  guardado, sin perder el resto del estado de la pantalla (p. ej. la posición de scroll).
- ¿Qué pasa con un ticket que no tiene ningún registro de tiempo todavía? El modal debe mostrar
  claramente que no hay histórico ("Todavía no hay tiempo registrado") en vez de una tabla vacía
  sin explicación.
- ¿Qué pasa si el tiempo real registrado iguala exactamente el tiempo estimado (100%)? Debe
  tratarse como "atención" (mismo color que el borde superior del rango 80–100%), no como
  "excedido", ya que excedido implica superar el estimado.
- ¿Qué pasa con roles que no tienen permiso de registrar tiempo (`work_sessions:manage`)? Deben
  poder ver el histórico y el indicador de consumo en modo solo lectura, sin la acción de abrir el
  modal de carga.
- ¿Qué pasa en pantallas angostas (mobile/tablet) con el flujo de revelar/colapsar? El
  comportamiento fluido de scroll debe seguir siendo utilizable sin recortar contenido ni producir
  saltos bruscos de layout.
- ¿Qué pasa si un ticket todavía no tiene ningún registro de tiempo? No hay fecha de inicio que
  mostrar (no existe un primer registro del cual derivarla); el sistema debe indicarlo
  explícitamente (p. ej. "Aún sin iniciar") en vez de mostrar un campo vacío sin explicación.
- ¿Qué pasa si el usuario intenta guardar un filtro con el mismo nombre que uno ya existente? El
  sistema debe pedir un nombre distinto en vez de sobrescribir el filtro existente sin avisar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE ofrecer una acción de "Registrar tiempo" en el detalle del ticket
  que abra un modal dedicado, en vez de mostrar el formulario de carga embebido de forma
  permanente en la pantalla.
- **FR-002**: El modal de registro de tiempo DEBE mostrar el histórico de registros de tiempo
  correlacionado únicamente con el ticket actual (fecha, horario u origen de la duración, quién lo
  cargó, nota), reutilizando los datos ya existentes de `work_sessions`.
- **FR-003**: El modal DEBE permitir crear, editar y eliminar registros de tiempo del ticket
  (mismas reglas de ventana de edición y permisos ya vigentes), reflejando los cambios en el
  histórico del propio modal sin recargar la página.
- **FR-004**: Al cerrar el modal de tiempo, el sistema DEBE revelar de forma fluida (transición
  animada, sin salto brusco de layout) el resumen de tiempo, seguido de comentarios y actividad del
  ticket, en ese orden visual.
- **FR-005**: El sistema DEBE permitir volver a revelar el resumen de tiempo mediante scroll hacia
  arriba desde la sección de comentarios/actividad, sin recargar la página ni perder el estado de
  la conversación de comentarios.
- **FR-006**: El detalle del ticket DEBE mostrar la fecha de inicio — definida como la fecha del
  primer registro de tiempo cargado en el ticket, no la fecha de creación del ticket —, el tiempo
  estimado de solución (en horas) y el total de horas reales registradas, en una misma zona
  visual, para comparación directa. Si el ticket todavía no tiene registros de tiempo, no hay
  fecha de inicio que mostrar (ver Edge Cases).
- **FR-007**: El sistema DEBE mostrar un indicador visual de color sutil que refleje el porcentaje
  de tiempo estimado consumido por las horas reales registradas, usando (y no ampliando) la
  paleta de color ya definida del producto (colores de éxito/atención/error existentes).
- **FR-008**: Cuando el ticket no tenga tiempo estimado definido, el sistema DEBE mostrar el total
  de horas reales sin indicador de alerta de consumo.
- **FR-009**: El sistema DEBE reservar y rotular visualmente, en el detalle del ticket y en "Mis
  Tareas", un lugar para la pertenencia a una "lista" y para "subtareas", siguiendo el mismo
  lenguaje visual ya usado para funcionalidad futura (placeholders "Próximamente") sin implementar
  su lógica.
- **FR-010**: Los usuarios sin permiso de gestionar tiempo DEBEN poder ver el histórico de tiempo y
  el indicador de consumo en modo solo lectura, sin acceso a la acción de registrar/editar/eliminar.
- **FR-011**: El sistema DEBE preservar el comportamiento de navegación de origen ("Volver a...")
  ya existente en el detalle del ticket al introducir el nuevo flujo de revelado fluido.
- **FR-012**: El sistema DEBE ofrecer una pantalla dedicada "Mis Tareas" que, al abrirse, muestre
  por defecto los tickets asignados al usuario actual (filtro "Asignado a mí" preaplicado), sin
  reemplazar la pantalla general de "Tickets" existente.
- **FR-013**: El sistema DEBE permitir guardar la combinación de criterios de filtro activa (en
  "Tickets" o en "Mis Tareas") como un filtro nombrado y reutilizable.
- **FR-014**: Los filtros guardados DEBEN estar disponibles indistintamente desde "Tickets" y
  desde "Mis Tareas" — un filtro guardado en una de las dos pantallas DEBE poder aplicarse desde la
  otra sin volver a configurarlo.
- **FR-015**: "Asignado a mí" DEBE existir como filtro guardado por defecto, disponible sin que el
  usuario tenga que crearlo, y no debe poder eliminarse (solo dejar de aplicarse).
- **FR-016**: El sistema DEBE impedir guardar un filtro nuevo con el mismo nombre que uno ya
  existente del usuario, solicitando un nombre distinto.

### Key Entities

- **Registro de tiempo (Work Session)**: entidad ya existente; esta funcionalidad cambia dónde y
  cómo se presenta (modal en vez de tabla siempre visible), no su estructura de datos.
- **Ticket**: se le añade, a nivel visual, la fecha de inicio de trabajo — derivada del primer
  registro de tiempo cargado en el ticket, sin nuevo campo de datos en el ticket — y reutiliza
  `estimated_resolution_minutes` y el total ya calculado de horas reales.
- **Filtro guardado (vista reutilizable)**: conjunto nombrado de criterios de filtro (cliente,
  estado, asignado, etc.) creado por un usuario, reutilizable indistintamente entre "Tickets" y
  "Mis Tareas". "Asignado a mí" es un filtro guardado por defecto, no eliminable.
- **Lista / Subtarea**: conceptos de UI reservados para una fase futura (Fase 3 del roadmap de la
  constitución); en esta funcionalidad son solo un marcador visual, sin entidad de datos nueva.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un Resolutor puede registrar un tiempo de trabajo desde el detalle del ticket, sin
  navegar a otra pantalla, en menos de 3 pasos (abrir modal → completar → guardar).
- **SC-002**: Al cerrar el modal de tiempo, el histórico/comentarios/actividad quedan visibles en
  pantalla sin que el usuario tenga que hacer una acción adicional de navegación.
- **SC-003**: El 100% de los tickets con tiempo estimado definido muestran el indicador de consumo
  con el color correcto según el porcentaje consumido (verificable comparando horas
  reales/estimadas contra el color mostrado).
- **SC-004**: Ningún usuario sin permiso de gestión de tiempo puede crear, editar o eliminar un
  registro desde el nuevo modal (verificable por rol).
- **SC-005**: La reorganización visual no reduce la cantidad de información disponible hoy en el
  detalle del ticket (histórico completo, comentarios, actividad siguen accesibles, solo cambia el
  orden/momento en que se revelan).
- **SC-006**: Un usuario ve sus tickets asignados en "Mis Tareas" sin realizar ningún paso de
  configuración adicional al abrir la pantalla.
- **SC-007**: Un filtro guardado desde "Tickets" o desde "Mis Tareas" está disponible de inmediato
  en la otra pantalla, sin que el usuario tenga que volver a crearlo.

## Assumptions

- El registro de tiempo (creación/edición/borrado) sigue las mismas reglas de negocio ya vigentes
  de Fase 2.1 (ventana de edición de 7 días, permiso `work_sessions:manage`); esta funcionalidad es
  puramente de presentación/navegación, no cambia reglas de negocio de tiempos.
- Los colores de alerta de consumo de tiempo reutilizan los tokens ya definidos en la paleta
  actual del producto (éxito/atención/error), sin introducir una paleta nueva. Umbrales por
  defecto: menos de 80% consumido = color de éxito; 80%–100% = color de atención; más de 100% =
  color de error.
- La Historia 4 (estructura de listas/subtareas) es exclusivamente visual: no crea tablas,
  endpoints ni lógica de agrupamiento nuevos; usa el mismo patrón de placeholder "Próximamente" que
  ya existe hoy en el detalle del ticket (p. ej. SLA, Focus Room).
- "Mis Tareas" es una pantalla nueva y distinta de "Tickets"/Kanban (no un reemplazo); ambas
  conviven y comparten el mismo mecanismo de filtros guardados.
- Los filtros guardados se asocian al usuario que los crea y persisten entre sesiones de ese
  usuario en el mismo navegador; no requieren una tabla nueva en el backend para esta
  funcionalidad (persistencia del lado del cliente) — decisión para mantener el alcance acotado
  según la directriz del solicitante. Sincronizar filtros guardados entre dispositivos queda fuera
  de alcance de esta funcionalidad.
- El alcance de implementación de esta funcionalidad se limita a los archivos estrictamente
  necesarios para cumplir estos requerimientos (sin refactors masivos ni funcionalidad adicional no
  solicitada), y su validación se hará con pruebas dirigidas a los archivos/componentes
  modificados, no con la suite completa del proyecto — restricción explícita del solicitante para
  esta funcionalidad, a respetar en la planificación e implementación posteriores.
