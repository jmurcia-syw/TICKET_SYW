# Feature Specification: Selección manual del Encargado solicitante en el Ticket

**Feature Branch**: `007-ticket-encargado-cliente`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "el Ticket debe tener el campo para asignar un encargado según el
cliente seleccionado, para saber quien lo solicitó o responsable de ese ticket por parte del
cliente, quien fue que lo solicitó, eso es un 'encargado'."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar quién del cliente solicitó el ticket (Priority: P1)

Un Coordinador o Resolutor crea un ticket para un Cliente. Además de elegir el Cliente, quiere
dejar constancia de qué persona específica de ese cliente (el "Encargado") solicitó o es
responsable del ticket — la misma noción de "Encargado" ya usada en el producto (usuarios
externos vinculados a un cliente fijo), pero ahora elegible manualmente por el personal interno en
vez de derivarse solo automáticamente cuando el propio Encargado crea su ticket.

**Why this priority**: Hoy el "Encargado solicitante" de un ticket solo queda registrado cuando el
Encargado crea su propio ticket (autoservicio). La mayoría de los tickets los crea personal
interno en nombre del cliente, y en esos casos no hay forma de indicar quién del cliente lo pidió
— se pierde trazabilidad de negocio.

**Independent Test**: Crear un ticket seleccionando un Cliente que ya tiene Encargados
registrados, elegir uno en el nuevo campo, guardar el ticket, y verificar que el detalle del
ticket muestra a esa persona como "Encargado solicitante".

**Acceptance Scenarios**:

1. **Given** un Coordinador creando un ticket, **When** selecciona un Cliente que tiene Encargados
   registrados, **Then** aparece un campo para elegir cuál de esos Encargados solicitó el ticket.
2. **Given** el campo de Encargado con una selección hecha, **When** el ticket se guarda, **Then**
   el detalle del ticket muestra a esa persona como "Encargado solicitante".
3. **Given** un Cliente sin ningún Encargado registrado, **When** se selecciona ese Cliente,
   **Then** el campo de Encargado se muestra vacío con una indicación clara de que el cliente no
   tiene encargados registrados, sin impedir crear el ticket.
4. **Given** un ticket creado por un usuario con rol Encargado (alta simplificada ya existente),
   **When** se revisa su detalle, **Then** sigue mostrando automáticamente a ese mismo usuario
   como "Encargado solicitante", sin necesidad de selección manual y sin mostrarle el selector.

---

### User Story 2 - Corregir o completar el Encargado después de creado el ticket (Priority: P2)

Un Coordinador que no tenía el dato al crear el ticket, o que se equivocó de persona, quiere poder
asignar o corregir el Encargado solicitante desde el detalle del ticket más adelante.

**Why this priority**: Cubre el caso real de que la información no siempre está disponible en el
momento de creación; es una extensión natural de la Historia 1 pero no bloquea su valor principal.

**Independent Test**: Abrir el detalle de un ticket sin Encargado asignado (o con uno incorrecto),
cambiarlo desde el detalle, y verificar que el cambio se refleja de inmediato.

**Acceptance Scenarios**:

1. **Given** un ticket sin Encargado asignado, **When** un Coordinador lo edita desde el detalle
   del ticket, **Then** puede elegir un Encargado del Cliente del ticket.
2. **Given** un ticket con un Encargado ya asignado, **When** un Coordinador lo cambia por otro
   Encargado del mismo Cliente, **Then** el detalle refleja el nuevo Encargado.
3. **Given** un ticket creado por un usuario con rol Encargado (Historia 1, escenario 4), **When**
   se intenta editar el Encargado solicitante manualmente, **Then** el sistema no lo permite —ese
   valor sigue derivado automáticamente de quién lo creó.

---

### Edge Cases

- ¿Qué pasa si se cambia el Cliente de un ticket que ya tenía un Encargado asignado? El Encargado
  previamente elegido pertenece al cliente anterior, así que debe limpiarse (dejar de mostrarse
  como válido) al cambiar de Cliente, para no mostrar un Encargado de un cliente distinto.
- ¿Qué pasa si el Encargado seleccionado es dado de baja después de asignarse a un ticket? El
  ticket conserva la referencia; el detalle debe seguir mostrando su nombre aunque ya no esté
  activo, sin romper la pantalla.
- ¿Qué pasa con tickets creados antes de esta funcionalidad? Deben seguir funcionando sin error,
  mostrando "Sin encargado asignado" en el detalle hasta que alguien lo complete.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Al crear un ticket, el sistema DEBE permitir seleccionar un Encargado de entre los
  registrados para el Cliente elegido, como un campo nuevo y adicional — sin reemplazar, ocultar
  ni modificar los campos ya existentes de Cliente ni Proyecto, que siguen funcionando igual que
  hoy.
- **FR-002**: El sistema DEBE limitar la lista de Encargados seleccionables a los que pertenecen
  al Cliente del ticket — nunca mostrar Encargados de otro cliente.
- **FR-003**: El sistema DEBE permitir como máximo un Encargado solicitante por ticket.
- **FR-004**: Si el Cliente seleccionado no tiene Encargados registrados, el sistema DEBE
  mostrarlo claramente y permitir crear el ticket igualmente sin ese dato (FR-007 define si es
  obligatorio cuando sí existen encargados).
- **FR-005**: Si se cambia el Cliente de un ticket (al crear o editar), el sistema DEBE limpiar la
  selección de Encargado si ese Encargado no pertenece al nuevo Cliente.
- **FR-006**: El detalle del ticket DEBE mostrar el Encargado solicitante (manual o automático)
  con el mismo tratamiento visual ya usado hoy para "Encargado solicitante", sin duplicar la
  sección para los dos orígenes posibles.
- **FR-007**: Seleccionar un Encargado al crear un ticket para un Cliente con encargados
  registrados es **opcional** — el sistema no debe bloquear la creación del ticket por no tener
  este dato.
- **FR-008**: El sistema DEBE permitir asignar o corregir el Encargado solicitante desde el
  detalle del ticket después de creado, en cualquier momento del ciclo de vida salvo que el ticket
  esté Cerrado o Cancelado.
- **FR-009**: Cuando el ticket fue creado por un usuario con rol Encargado (alta simplificada ya
  existente), el sistema DEBE seguir resolviendo el Encargado solicitante automáticamente a partir
  de quien lo creó, y DEBE impedir su edición manual (FR-008 no aplica a este caso).
- **FR-010**: Los tickets existentes sin Encargado asignado DEBEN mostrar "Sin encargado asignado"
  en el detalle, sin error.

### Key Entities

- **Ticket**: gana una referencia opcional adicional a un Encargado (Encargado solicitante),
  acotada al Cliente del ticket — un campo más, igual que Cliente o Proyecto, sin reemplazar ni
  alterar ninguno de los dos. Coexiste con la resolución automática ya existente (Fase 2.1) para
  tickets creados por un usuario con rol Encargado — un ticket nunca tiene ambos orígenes a la
  vez.
- **Encargado (Client Contact)**: entidad ya existente (Fase 2.1) — usuario externo vinculado a un
  Cliente fijo; esta funcionalidad solo agrega una forma más de referenciarlo desde el ticket, sin
  cambiar su estructura.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un Coordinador puede registrar quién del cliente solicitó un ticket en el mismo
  formulario de creación, sin salir de esa pantalla ni consultar otra fuente.
- **SC-002**: El 100% de los tickets con Cliente y al menos un Encargado registrado permiten
  quedar con un Encargado solicitante asignado, ya sea al crearse o corregido después.
- **SC-003**: El detalle de cualquier ticket muestra de forma inequívoca quién es el Encargado
  solicitante (manual o automático) o indica claramente que no hay ninguno asignado — sin
  ambigüedad entre los dos orígenes posibles.
- **SC-004**: Cambiar el Cliente de un ticket nunca deja visible un Encargado que no pertenece a
  ese Cliente.

## Assumptions

- Esta funcionalidad no aplica a los tickets creados por un usuario con rol Encargado (alta
  simplificada de Fase 2.1): ese flujo sigue derivando el solicitante automáticamente de quien lo
  creó, sin selector manual ni edición posterior (ver FR-009).
- La lista de Encargados seleccionables reutiliza el catálogo ya existente de Encargados por
  Cliente (Fase 2.1); esta funcionalidad no agrega, edita ni elimina Encargados, solo los
  referencia desde el ticket.
- No se requiere aprobación ni flujo adicional para reasignar el Encargado solicitante — cualquier
  usuario con permiso de editar el ticket puede hacerlo (mismo permiso ya usado para editar otros
  campos de clasificación del ticket).
- El alcance de implementación se limita a los archivos estrictamente necesarios para cumplir
  estos requerimientos (sin refactors ni funcionalidad adicional no solicitada), y su validación
  se hará con los tests dirigidos a los archivos modificados, no con la suite completa del
  proyecto — restricción explícita del solicitante para esta funcionalidad, a respetar durante la
  implementación.
