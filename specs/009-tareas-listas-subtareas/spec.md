# Feature Specification: Listas de Tareas, Subtareas, ciclo de vida unificado y fix de Registro de tiempo

**Feature Branch**: `009-tareas-listas-subtareas`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description (dos mensajes): "no esta funcionado el Registros de tiempo en
ninguna, ni de la vista de ticket o tareas, las tareas también tiene niveles de aprobación, las
tareas son los mismos ticket pero con una interpretación diferente. quiero que tenga lo opción
de crear lista de tareas, y cuando se cree una tarea se pueda asociar esta lista de tareas,
quiero que te base en la sesión Aris – Lower Mine › Lista de TICKET_SYW/docs/mockup.html donde
es un desplegable izquierdo las listas donde se puede crear más y las tareas tiene varias tareas
y subtareas donde aparece toda la información como el estado, comentario. las tareas también
puede tener comentarios y todos los campos de ticket, solo cambian los niveles: por ejemplo en
el mockup 'Aris – Lower Mine' es un proyecto, las listas son 'F1: Definiciones y Alistamiento',
tareas son 'Documentos de Diseño Activos y Proyecto' y subtareas 'Revisar módulos de activos
fijo' — el 'ticket/tarea' sería 'Documentos de diseño activos y proyecto' — y en las tareas
también se puede asignar diferente persona y en cada subtarea también." + (follow-up) "las
tareas también pueden aparecer en el kanban y también puede tener los mismos estados, fases,
herramienta, proceso, todo lo de ticket."

**Contexto (continuación de la Fase 3, spec `008`)**: la spec `008` implementó la Tarea con (a)
`list_name` como **campo de texto libre** (research.md Decisión 3) y (b) una **FSM propia y
simplificada** de 4 estados (Pendiente/En progreso/Hecha/Cancelada, Decisión 2), ocultando los
campos de clasificación de incidente del Ticket (Decisión 1). Esta spec **reemplaza ambas
decisiones** tras una ronda de clarificación con el usuario:

- La Lista pasa de texto libre a una **entidad real**, administrable, con navegación tipo
  Teamwork/Asana (sidebar izquierdo), tal como se ve en `docs/mockup.html`, pantalla
  `Principal › Proyectos › Aris – Lower Mine › Lista` (id `s-lista`).
- La Tarea deja de tener una FSM propia separada: **reutiliza el mismo conjunto de 10
  estados/fases que el Ticket** (Nuevo, Pre-Análisis, Contacto, En Análisis, En Ejecución, En
  Pruebas, Pendiente de Usuario, Resuelto, Cerrado, Cancelado) y **los mismos campos de
  clasificación** (Tipo, Severidad, Herramienta, Proceso, Nivel de escalamiento) — visibles y
  editables, igual que en un Ticket. La diferencia no está en los datos que guarda sino en cómo
  se transiciona entre estados (ver Historia 2) y en que aparece en el tablero Kanban junto a los
  Tickets.

**Jerarquía de niveles** (ya documentada en `.specify/memory/constitution.md`, "Modelo de datos
- Jerarquía de 5 niveles", ahora activada por esta spec):

```
Cliente (Nivel 1) → Proyecto (Nivel 2) → Lista (Nivel 3) → Tarea (Nivel 4) → Subtarea (Nivel 5)
```

Mapeo del mockup a esta jerarquía: "Aris – Lower Mine" = Proyecto · "F1: Definiciones y
Alistamiento" = Lista · "Documentos de Diseño Activos y Proyecto" = Tarea (el mismo
`ticket`/`Tarea` de la spec `008`) · "Revisar módulos de Activos Fijos" = Subtarea.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar tiempo en cualquier Ticket o Tarea propios (Priority: P1) 🎯 Fix

Un Resolutor (o cualquier recurso interno) intenta registrar tiempo desde el detalle de una
Tarea que él mismo creó, o de un Ticket que tiene asignado, y la acción se rechaza con "El
recurso no participa de este ticket" aunque es evidentemente su propio trabajo.

**Why this priority**: es un defecto que bloquea una funcionalidad ya entregada (Fase 2) en el
escenario más común de uso de Tareas (Fase 3) — sin esto, "Registro de tiempo" es inutilizable
para el caso de uso central de una Tarea recién creada.

**Independent Test**: crear una Tarea, registrar tiempo sobre ella sin pasar por Triage/Panel de
Asignación, y confirmar que se guarda.

**Acceptance Scenarios**:

1. **Given** un recurso que creó una Tarea (auto-asignada a sí mismo desde la spec `008`),
   **When** intenta registrar tiempo sobre ella, **Then** el sistema lo permite.
2. **Given** un recurso que es el `assignee` formal de un Ticket (vía Triage) o aparece en su
   historial de asignaciones, **When** registra tiempo, **Then** sigue funcionando exactamente
   igual que hoy (sin regresión).
3. **Given** un recurso que NO creó ni tiene ninguna relación con una Tarea/Ticket ajeno,
   **When** intenta registrar tiempo sobre él, **Then** el sistema lo sigue rechazando (la
   corrección no abre la puerta a registrar tiempo en trabajo ajeno).

---

### User Story 2 - Ciclo de vida unificado con Ticket: mismos estados, mismos campos, visible en Kanban (Priority: P1)

Un usuario abre una Tarea y ve los mismos campos que vería en un Ticket (Tipo, Severidad,
Herramienta, Proceso, Nivel de escalamiento) y el mismo conjunto de 10 estados. A diferencia de
un Ticket — que solo transiciona de estado a través de comentarios tipificados que siguen una
secuencia fija — la Tarea puede cambiar a **cualquiera** de esos estados en **cualquier
momento**, sin una secuencia obligatoria ni pasos que saltarse: el único requisito es dejar un
comentario que documente el cambio. La Tarea también aparece en el tablero Kanban, en las mismas
columnas de estado que los Tickets.

**Why this priority**: es la base que hace que "las tareas son los mismos tickets, con una
interpretación diferente" sea literalmente cierto en los datos — sin esto, Historias como
Subtareas (3) o Listas (4) heredarían una FSM y un formulario recortados que ya no reflejan lo
que el usuario pidió.

**Independent Test**: en una Tarea recién creada (estado inicial "Nuevo"), cambiarla directamente
a "Cerrado" sin pasar por los estados intermedios, dejando un comentario, y confirmar que el
sistema lo permite; luego confirmar que aparece en la columna "Cerrado" del Kanban.

**Acceptance Scenarios**:

1. **Given** una Tarea en cualquier estado, **When** el usuario la cambia a cualquier otro
   estado del mismo catálogo de 10 (incluso salteando estados intermedios), **Then** el sistema
   lo permite, siempre que el usuario deje un comentario justificando el cambio.
2. **Given** un Ticket normal, **When** se intenta la misma transición libre, **Then** el sistema
   la sigue rechazando si no respeta la secuencia de la FSM — la Tarea es la única excepción a la
   secuencia estricta.
3. **Given** una Tarea, **When** el usuario abre su detalle, **Then** ve y puede editar Tipo,
   Severidad, Herramienta, Proceso y Nivel de escalamiento, igual que en un Ticket (el formulario
   de creación reducido de la spec `008` — sin pedir estos campos al crear — se mantiene; se
   vuelven editables después, desde el detalle).
4. **Given** el tablero Kanban, **When** el usuario lo abre, **Then** ve Tickets y Tareas
   mezclados en las mismas columnas de estado, distinguibles visualmente por tipo de registro.

---

### User Story 3 - Crear y administrar Listas de tareas dentro de un Proyecto (Priority: P1)

Un Coordinador o Resolutor abre un Proyecto y ve, en un panel izquierdo (igual al mockup
`Aris – Lower Mine › Lista`), las Listas de tareas de ese Proyecto ("F1: Definiciones y
Alistamiento", "F2: Diseño", etc.), cada una con su conteo de Tareas. Puede crear una Lista
nueva con un nombre, y al crear o editar una Tarea puede asociarla a una de esas Listas del
mismo Proyecto.

**Why this priority**: es la base estructural que reemplaza el campo de texto libre de la spec
`008` — sin la entidad real no hay nada que administrar ni asociar de forma consistente
(evita duplicados por error de tipeo, ya identificado como limitación conocida en `008`).

**Independent Test**: crear dos Listas nuevas en un Proyecto, crear una Tarea en cada una, y
confirmar que el panel izquierdo muestra el conteo correcto por Lista.

**Acceptance Scenarios**:

1. **Given** un Proyecto sin Listas todavía, **When** el usuario crea una Lista con un nombre,
   **Then** aparece en el panel izquierdo con conteo 0.
2. **Given** una Lista existente de un Proyecto, **When** el usuario crea una Tarea y la asocia a
   esa Lista, **Then** el conteo de la Lista aumenta y la Tarea aparece agrupada bajo ella.
3. **Given** dos Proyectos distintos, **When** el usuario crea una Tarea en el Proyecto A,
   **Then** solo puede asociarla a Listas del Proyecto A, nunca del Proyecto B.
4. **Given** las Tareas migradas desde la spec `008` (con `list_name` como texto libre),
   **When** se activa esta spec, **Then** cada valor de texto distinto se convierte en una Lista
   real del Proyecto correspondiente, sin perder la agrupación ya visible en "Mis Tareas".

---

### User Story 4 - Subtareas dentro de una Tarea, con su propio Encargado y Estado (Priority: P2)

Dentro de una Tarea (p. ej. "Documentos de Diseño Activos y Proyecto"), un usuario agrega una o
más Subtareas (p. ej. "Revisar módulos de Activos Fijos"), cada una con su propio título,
Encargado (persona asignada, distinta por subtarea), estado (mismo catálogo unificado de la
Historia 2) y comentarios — igual que se ve en el mockup (fila indentada con "└", avatar propio,
badge de estado propio).

**Why this priority**: es el nivel más profundo de la jerarquía y el que más valor visual aporta
respecto al mockup, pero el sistema ya es útil sin subtareas (Historias 1-3 entregan valor de
forma independiente).

**Independent Test**: crear una Tarea, agregarle dos Subtareas con Encargados distintos, cambiar
el estado de una de ellas, y confirmar que no afecta el estado de la Tarea padre ni de la otra
Subtarea.

**Acceptance Scenarios**:

1. **Given** una Tarea abierta, **When** el usuario agrega una Subtarea con título y Encargado,
   **Then** aparece anidada bajo la Tarea con su propio badge de estado ("Nuevo" por defecto).
2. **Given** una Subtarea con Encargado propio, **When** ese Encargado abre "Mis Tareas" o el
   Kanban, **Then** la Subtarea aparece igual que cualquier Tarea asignada a él.
3. **Given** una Tarea con Subtareas en distintos estados, **When** se completan todas las
   Subtareas, **Then** la Tarea padre NO cambia de estado automáticamente (el usuario la
   completa explícitamente) — evita sorpresas de un cierre automático no solicitado.
4. **Given** una Subtarea, **When** el usuario intenta agregarle una Subtarea propia (Nivel 6),
   **Then** el sistema lo rechaza — la jerarquía se detiene en 5 niveles (Cliente → Proyecto →
   Lista → Tarea → Subtarea).

---

### User Story 5 - Comentarios en Tareas y Subtareas (Priority: P2)

Un usuario dentro del detalle de una Tarea (o Subtarea) agrega un comentario — el mismo
comentario que documenta un cambio de estado (Historia 2) sirve también como comentario simple
sin cambio de estado — y otros usuarios lo ven en el historial, igual que el contador 💬 visible
por fila en el mockup.

**Why this priority**: complementa la Historia 4 (Subtareas) — depende de que exista el nivel de
Subtarea para tener sentido completo, aunque los comentarios en la Tarea misma ya aportan valor
solos.

**Independent Test**: agregar un comentario a una Tarea y a una de sus Subtareas sin cambiar su
estado, y confirmar que cada uno aparece en su propio historial, sin mezclarse.

**Acceptance Scenarios**:

1. **Given** una Tarea abierta, **When** el usuario escribe y envía un comentario simple (sin
   cambiar el estado), **Then** aparece en el historial de esa Tarea con autor y fecha.
2. **Given** una Subtarea abierta, **When** el usuario comenta, **Then** el comentario queda
   asociado únicamente a esa Subtarea (no a la Tarea padre).

---

### Edge Cases

- ¿Qué pasa si se intenta eliminar una Lista que todavía tiene Tareas? Se rechaza, o se exige
  mover/archivar las Tareas primero (mismo criterio ya usado para catálogos con
  `catalog_inactive`/bloqueo por uso).
- ¿Qué pasa si dos Listas de Proyectos distintos tienen el mismo nombre (p. ej. "F1" en dos
  proyectos)? Es válido — la Lista pertenece a un Proyecto, el nombre no es único globalmente.
- ¿Qué pasa con el "Registro de tiempo" de una Subtarea? Se registra igual que en una Tarea —
  Subtarea es un registro más de la misma tabla, con las mismas reglas de la Historia 1.
- ¿Qué pasa si el Encargado de una Subtarea no es el mismo que el de la Tarea padre? Es válido y
  esperado — el mockup muestra avatares distintos por fila.
- ¿Qué pasa si se cambia la Lista de una Tarea a una de otro Proyecto? Se rechaza — igual que
  "Registro relacionado" (spec `008`, FR-005), una Lista está acotada al Proyecto de la Tarea.
- ¿Qué pasa si un usuario intenta cambiar el estado de una Tarea sin dejar comentario? Se
  rechaza — el comentario es obligatorio en cada cambio de estado (Historia 2), aunque la
  transición en sí no tenga restricciones de secuencia.
- ¿Qué pasa con "Cerrado"/"Cancelado" en una Tarea? Son estados como cualquier otro dentro del
  catálogo unificado — a diferencia del Ticket, no son finales/bloqueantes para la Tarea: el
  usuario puede volver a cambiarla de estado libremente incluso después (ver Historia 2).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir registrar tiempo sobre una Tarea a su creador y a su
  encargado actual, sin exigir que aparezca en el historial formal de asignaciones de Triage
  (que solo aplica a Tickets) — corrige el defecto de la Historia 1.
- **FR-002**: El sistema DEBE seguir rechazando el registro de tiempo de un recurso que no creó
  ni tiene ninguna relación de asignación con el Ticket/Tarea/Subtarea (sin regresión de
  seguridad sobre la regla ya vigente para Tickets).
- **FR-003**: Una Tarea DEBE usar el mismo catálogo de 10 estados que un Ticket (Nuevo,
  Pre-Análisis, Contacto, En Análisis, En Ejecución, En Pruebas, Pendiente de Usuario, Resuelto,
  Cerrado, Cancelado) — reemplaza el catálogo propio de 4 estados de la spec `008`.
- **FR-004**: A diferencia de un Ticket (transiciones restringidas a una secuencia fija), una
  Tarea DEBE poder cambiar a cualquier estado del catálogo unificado desde cualquier estado
  actual, sin restricción de secuencia ni de estados intermedios obligatorios.
- **FR-005**: Todo cambio de estado de una Tarea DEBE requerir un comentario que documente el
  motivo — sin tipificación FSM como los comentarios de Ticket (un comentario simple basta).
- **FR-006**: El sistema DEBE mostrar y permitir editar en una Tarea los mismos campos de
  clasificación que un Ticket — Tipo, Severidad, Herramienta, Proceso, Nivel de escalamiento —
  desde su detalle. El formulario de creación reducido (spec `008`, sin pedir estos campos) se
  mantiene; quedan disponibles para completar/editar después de creada.
- **FR-007**: El sistema DEBE mostrar las Tareas en el tablero Kanban, usando las mismas columnas
  de estado que los Tickets, distinguibles visualmente por tipo de registro (Ticket/Tarea).
- **FR-008**: El sistema DEBE permitir crear una Lista de tareas dentro de un Proyecto, con un
  nombre.
- **FR-009**: El sistema DEBE mostrar las Listas de un Proyecto en un panel de navegación
  (sidebar), cada una con el conteo de Tareas que contiene, igual que
  `docs/mockup.html` → pantalla `s-lista`.
- **FR-010**: El sistema DEBE permitir asociar una Tarea a una Lista del mismo Proyecto al
  crearla o editarla; una Tarea sin Lista asignada cae en un grupo "Sin lista" (mismo criterio ya
  usado en "Mis Tareas" desde la spec `008`).
- **FR-011**: El sistema DEBE rechazar asociar una Tarea a una Lista que pertenezca a un Proyecto
  distinto del de la Tarea.
- **FR-012**: El sistema DEBE migrar los valores de texto libre `list_name` ya existentes
  (spec `008`) a Listas reales del Proyecto correspondiente, preservando la agrupación visible
  hoy en "Mis Tareas", sin intervención manual del usuario.
- **FR-013**: El sistema DEBE migrar el estado de las Tareas ya existentes (creadas bajo el
  catálogo de 4 estados de la spec `008`) al catálogo unificado de 10 estados, sin perder
  información de en qué punto del trabajo estaban (p. ej. "Pendiente" → "Nuevo", "En progreso" →
  "En Ejecución", "Hecha" → "Cerrado", "Cancelada" → "Cancelado").
- **FR-014**: El sistema DEBE permitir agregar una o más Subtareas dentro de una Tarea, cada una
  con su propio título, descripción, Encargado, estado (catálogo unificado) y comentarios —
  mismos campos base que una Tarea, sin heredar el estado de la Tarea padre.
- **FR-015**: El sistema DEBE permitir asignar una Subtarea a un recurso distinto del Encargado
  de la Tarea padre.
- **FR-016**: El sistema NO DEBE permitir crear una Subtarea dentro de otra Subtarea (la
  jerarquía se detiene en 5 niveles).
- **FR-017**: El sistema DEBE mostrar, para cada Tarea y Subtarea en la vista de Lista, un
  conteo de comentarios y de adjuntos, igual que el mockup (íconos 💬 y 📎).
- **FR-018**: El sistema DEBE permitir agregar comentarios simples (sin cambio de estado
  asociado) a una Tarea o Subtarea, visibles en su propio historial.

### Key Entities

- **Lista de tareas**: agrupación de Tareas dentro de un Proyecto (Nivel 3), con nombre y orden
  de aparición. Reemplaza el campo de texto libre `list_name` de la spec `008`.
- **Tarea**: mismo registro que un Ticket (`record_type_id = 'Tarea'`), ahora con el mismo
  catálogo de estados y los mismos campos de clasificación que un Ticket, transición de estado
  libre (no secuencial) con comentario obligatorio, y referencia a una Lista real en vez de un
  texto libre.
- **Subtarea**: mismo registro que una Tarea (Nivel 5), con una referencia a su Tarea padre
  (Nivel 4); comparte título, descripción, Encargado, estado, comentarios — no tiene Lista propia
  (hereda la de su Tarea padre) ni puede tener Subtareas propias.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los intentos de registrar tiempo sobre una Tarea propia (creada o
  asignada al usuario) se completan sin error de permisos.
- **SC-002**: Un usuario puede cambiar el estado de una Tarea a cualquiera de los 10 valores del
  catálogo unificado, en cualquier orden, dejando solo un comentario — sin encontrar ningún
  bloqueo de secuencia.
- **SC-003**: El 100% de las Tareas aparecen en el tablero Kanban, en la columna correspondiente
  a su estado actual, junto a los Tickets.
- **SC-004**: Un usuario puede crear una Lista nueva y asociarle una Tarea en menos de 30
  segundos, sin salir de la vista del Proyecto.
- **SC-005**: El 100% de los `list_name` de texto libre y los estados de 4 valores existentes al
  momento de activar esta spec se migran correctamente (Listas reales + catálogo unificado), sin
  Tareas huérfanas, duplicadas ni con estado ambiguo.
- **SC-006**: Un usuario puede agregar una Subtarea con su propio Encargado en menos de 20
  segundos desde el detalle de la Tarea padre.
- **SC-007**: El 100% de los intentos de asociar una Tarea a una Lista de otro Proyecto son
  rechazados por el sistema.

## Assumptions

- La navegación por Proyecto (`Cliente → Proyecto → Lista`) reutiliza las pantallas de Cliente/
  Proyecto ya existentes (Fase 0/1) como punto de entrada — esta spec no rediseña esas pantallas,
  solo agrega la vista "Lista" nueva colgando de un Proyecto, según `docs/mockup.html`.
- Las Subtareas participan del mismo sistema de "Mis Tareas", Kanban y "Registro de tiempo" que
  las Tareas (mismo registro de tabla, Nivel 5) — sin pantallas nuevas para ellas más allá de su
  anidamiento visual bajo la Tarea padre.
- El catálogo de 4 estados propio de la Tarea (Pendiente/En progreso/Hecha/Cancelada, spec `008`)
  y su FSM restringida (`task_fsm.py`) quedan **reemplazados**, no extendidos, por el catálogo
  unificado de 10 estados de esta spec — la única diferencia de comportamiento entre Ticket y
  Tarea pasa a ser exclusivamente la libertad de transición (Historia 2), no el catálogo de
  valores.
- "Aprobar" una Tarea no introduce un estado nuevo ("En revisión") ni un actor especial: al
  compartir el mismo catálogo que el Ticket, una Tarea en "Resuelto" ya hereda el mecanismo de
  aceptación/cierre que el Ticket tiene hoy — no se requiere un motor de aprobación adicional
  para cumplir con lo pedido, dado que el usuario priorizó la transición libre sin restricciones
  por sobre un gate formal de aprobación.
- Los comentarios de Tarea/Subtarea (Historia 5) son simples — no requieren la tipificación de 10
  tipos que usa el Ticket (asignado, pre_analisis, confirmación_atención, etc.), ya que las
  transiciones de la Tarea no están atadas a un tipo de comentario específico (Historia 2).
