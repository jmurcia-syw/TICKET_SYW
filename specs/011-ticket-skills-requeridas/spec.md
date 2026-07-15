# Feature Specification: Skills Requeridas en el Ticket

**Feature Branch**: `011-ticket-skills-requeridas`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "agrega en el ticket la de forma opcionar, colocar varias skills
para identificar la habilidades necesaria para resolverlo, es opcional y se puede cambiar en
cualquier fase del proceso"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Asignar Skills requeridas al ticket (Priority: P1)

Un Coordinador, QM o Admin, al crear o editar un Ticket (o Tarea/Subtarea), selecciona de forma
**opcional** una o varias Skills del catálogo existente que identifican las habilidades técnicas
o funcionales necesarias para resolverlo. El campo queda vacío por defecto si no se selecciona
ninguna.

**Why this priority**: es el núcleo de lo solicitado — sin la posibilidad de asociar Skills al
ticket no existe funcionalidad que entregar.

**Independent Test**: crear un ticket sin seleccionar ninguna Skill (se guarda vacío), luego
editarlo y agregar dos Skills del catálogo; verificar que ambas quedan listadas en el ticket.

**Acceptance Scenarios**:

1. **Given** un ticket nuevo, **When** el Coordinador lo crea sin seleccionar ninguna Skill,
   **Then** el ticket se guarda sin Skills requeridas asociadas (el campo es opcional).
2. **Given** un ticket existente sin Skills requeridas, **When** el Coordinador (u otro rol con
   permiso de edición del ticket) lo edita y selecciona dos Skills del catálogo, **Then** el ticket queda asociado a esas dos
   Skills y ambas se listan en su detalle.
3. **Given** un ticket con tres Skills requeridas asociadas, **When** se quita una y se agrega
   otra distinta, **Then** el ticket queda con las dos restantes originales más la nueva (total
   tres), reflejado de inmediato.

---

### User Story 2 - Cambiar las Skills requeridas en cualquier fase del ticket (Priority: P1)

Independientemente del estado actual del ticket (Nuevo, En análisis, En ejecución, Resuelto,
Cerrado, Cancelado, etc.), un usuario con permiso de edición del ticket (Coordinador, QM o Admin)
puede modificar el conjunto de Skills requeridas en cualquier momento, sin que el estado del
ticket bloquee el cambio ni exija una transición o comentario tipificado.

**Why this priority**: es el requisito explícito del solicitante ("se puede cambiar en cualquier
fase del proceso"); sin esto, la clasificación técnica no puede refinarse a medida que avanza el
análisis o la resolución del ticket.

**Independent Test**: llevar un ticket a estado "Cerrado" y verificar que igual se pueden
agregar o quitar Skills requeridas, sin reabrir el ticket ni registrar un comentario.

**Acceptance Scenarios**:

1. **Given** un ticket en estado "En análisis", **When** el QM agrega una Skill
   requerida, **Then** el cambio se guarda sin alterar el estado del ticket.
2. **Given** un ticket en estado "Cerrado", **When** el Coordinador quita una Skill previamente
   asignada, **Then** el cambio se guarda sin requerir reabrir el ticket ni comentario asociado.
3. **Given** un ticket en estado "Cancelado", **When** se intenta modificar sus Skills
   requeridas, **Then** el sistema permite el cambio igual que en cualquier otro estado.

---

### User Story 3 - Visualizar las Skills requeridas del ticket (Priority: P2)

Cualquier usuario con acceso al ticket puede ver, en su detalle, qué Skills fueron marcadas como
necesarias para resolverlo, para entender rápidamente el perfil técnico/funcional requerido
antes de tomar o revisar el caso.

**Why this priority**: sin visibilidad, la información capturada en las Historias 1 y 2 no
aporta valor operativo inmediato (aunque sí queda disponible para un futuro Triage Agent);
prioridad P2 porque el valor principal ya se logra con la sola captura del dato.

**Independent Test**: abrir el detalle de un ticket con dos Skills requeridas asignadas y
confirmar que ambas se muestran con su nombre/etiqueta.

**Acceptance Scenarios**:

1. **Given** un ticket con Skills requeridas asignadas, **When** cualquier usuario con acceso al
   ticket abre su detalle, **Then** ve la lista de Skills requeridas junto al resto de la
   clasificación del ticket.
2. **Given** un ticket sin Skills requeridas, **When** se abre su detalle, **Then** la sección se
   muestra vacía (o con una indicación de "sin Skills requeridas") sin errores.

---

### Edge Cases

- ¿Qué pasa si se intenta eliminar del catálogo una Skill usada como requerida en algún ticket?
  El catálogo de Skills (spec `010`) no tiene "desactivar", solo eliminar (`DELETE
  /api/skills/{id}`, permiso `skills:deactivate`) — igual que ya ocurre si está asignada a algún
  Recurso, el sistema lo bloquea con `409 skill_in_use` para que ningún ticket pierda su
  referencia. Solo se puede eliminar una Skill que no esté en uso por ningún ticket ni recurso.
- ¿Puede repetirse la misma Skill dos veces en el mismo ticket? No — la asociación es única por
  par ticket/Skill; reintentar agregarla no la duplica.
- ¿Aplica también a Tareas y Subtareas, no solo a Tickets? Sí — Tarea y Subtarea comparten la
  misma tabla/entidad que Ticket y el mismo patrón de campos de clasificación editables (Tipo,
  Severidad, Herramienta, Proceso), por lo que las Skills requeridas siguen el mismo criterio.
- ¿Qué pasa si el ticket no tiene ninguna Skill requerida asociada? Es el estado por defecto
  (campo opcional); no bloquea ninguna otra acción del ticket (asignación, transición, cierre).
- ¿El Usuario/cliente (autoservicio) puede definir las Skills requeridas de su propio ticket? No
  — queda fuera del formulario simplificado de autoservicio, igual que el resto de la
  clasificación técnica del ticket (ver Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir asociar cero, una o varias Skills (del catálogo de Skills
  existente) a un Ticket/Tarea/Subtarea como "Skills requeridas para resolverlo"; el campo es
  opcional y queda vacío por defecto.
- **FR-002**: El sistema DEBE permitir agregar o quitar Skills requeridas en cualquier momento
  del ciclo de vida del ticket, sin importar su estado actual, y sin exigir una transición de
  estado ni un comentario tipificado para hacerlo.
- **FR-003**: El sistema DEBE impedir que una misma Skill quede asociada más de una vez al mismo
  ticket.
- **FR-004**: El detalle del ticket DEBE mostrar las Skills requeridas asociadas junto al resto
  de su clasificación (Tipo, Severidad, Herramienta, Proceso).
- **FR-005**: Solo los roles con permiso de edición del ticket (`tickets:edit` — Admin,
  Coordinador y QM en este sistema; el Resolutor no lo tiene, igual que para el resto de la
  clasificación del ticket como Herramienta/Proceso) DEBEN poder agregar o quitar Skills
  requeridas; la visibilidad sigue las mismas reglas que el resto de la clasificación del ticket.
- **FR-006**: Cambiar las Skills requeridas de un ticket NO DEBE disparar notificaciones,
  transiciones de estado, ni requerir un comentario tipificado.
- **FR-007**: El sistema DEBE impedir eliminar del catálogo una Skill que esté asignada como
  requerida a cualquier ticket (`409 skill_in_use`), extendiendo el mismo chequeo que ya existe
  para Skills asignadas a Recursos — así ningún ticket pierde la referencia a sus Skills
  requeridas.
- **FR-008**: El selector de Skills requeridas DEBE tomar sus opciones del catálogo de Skills
  administrable ya existente, sin introducir un catálogo separado.

### Key Entities

- **Skills requeridas del Ticket** (nueva relación): vínculo muchos-a-muchos, opcional, entre el
  Ticket (o Tarea/Subtarea, misma entidad) y la Skill; único por par ticket/Skill; editable en
  cualquier estado del ticket.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un Coordinador (u otro rol con permiso de edición del ticket) puede agregar o
  quitar una Skill requerida de un ticket en menos de 15 segundos desde el detalle del ticket.
- **SC-002**: El 100% de los tickets existentes antes del cambio siguen funcionando sin errores,
  con cero Skills requeridas asociadas por defecto.
- **SC-003**: En el 100% de los casos probados, un usuario autorizado puede cambiar las Skills
  requeridas de un ticket en cualquiera de sus estados (incluidos Cerrado y Cancelado) sin
  encontrar bloqueos.
- **SC-004**: El detalle de cualquier ticket con Skills requeridas muestra el 100% de las Skills
  asignadas sin necesidad de navegar a otra pantalla.

## Assumptions

- El campo reutiliza el catálogo de Skills ya existente y administrable (spec `010`, con tipo,
  herramienta y proceso); no se crea un catálogo nuevo ni una lista paralela.
- Aplica de igual forma a Ticket, Tarea y Subtarea porque comparten la misma tabla/entidad y el
  mismo patrón de campos de clasificación editables en cualquier estado.
- Solo roles con permiso `tickets:edit` (Admin, Coordinador, QM — el Resolutor no lo tiene en
  este sistema, tal como descubierto al reutilizar el permiso ya existente en vez de crear uno
  nuevo) pueden definir o modificar las Skills requeridas; el Usuario/cliente (autoservicio) no
  las ve ni las edita, igual que el resto de la clasificación técnica del ticket (Tipo, Severidad,
  Herramienta, Proceso), que ya queda fuera de su formulario simplificado.
- En esta fase, las Skills requeridas son puramente informativas/de clasificación: no alteran
  automáticamente el Panel de Asignación, el Triage Push ni el Gold Standard Dataset existentes;
  quedan disponibles como dato base para un futuro Triage Agent (Principio VI, Fase 7 del
  roadmap SDD V3).
- Modificar las Skills requeridas no genera notificación ni requiere comentario tipificado, a
  diferencia de las transiciones de estado del ticket.
- No hay un límite máximo de Skills seleccionables por ticket.
