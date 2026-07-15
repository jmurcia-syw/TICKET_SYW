# Feature Specification: Encargado (Usuario/cliente) en múltiples Proyectos

**Feature Branch**: `015-encargado-multiples-proyectos`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "un encargado puede estar en varios proyectos, no solo en uno"

**Contexto (estado actual)**: hoy la relación Usuario/cliente ↔ Proyecto ya es técnicamente
muchos-a-muchos en el modelo de datos (`project_members`, spec 010), y la lógica de tickets ya
filtra correctamente al "Encargado solicitante" por Proyecto. La restricción a **un solo
Proyecto** vive únicamente en el alta de Usuario/cliente: el modal "Nuevo Usuario/cliente" solo
permite elegir un Proyecto (selector simple, obligatorio) y el endpoint de creación solo acepta
un `project_id`, del cual además deriva el Cliente y crea una única membresía de Proyecto. No
existe hoy ninguna pantalla para agregar o quitar Proyectos a un Usuario/cliente ya creado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Asignar varios Proyectos al crear un Usuario/cliente (Priority: P1)

Un Admin/Coordinador da de alta un nuevo Usuario/cliente (Encargado) para una empresa Cliente
que tiene más de un Proyecto activo con SYW, y necesita que esa persona pueda ver y crear
tickets en todos esos Proyectos desde el primer momento, sin tener que repetir el alta ni pedir
soporte técnico para "agregar" los proyectos restantes.

**Why this priority**: es el caso de uso que motivó el pedido — hoy obliga a elegir un solo
Proyecto en el alta, lo cual es el bloqueo más directo y frecuente.

**Independent Test**: puede probarse completamente creando un Usuario/cliente y seleccionando 2
o más Proyectos del mismo Cliente en el formulario de alta; el Usuario/cliente resultante
aparece como solicitante seleccionable en tickets de cualquiera de esos Proyectos.

**Acceptance Scenarios**:

1. **Given** un Cliente con 2 Proyectos activos, **When** el Admin crea un Usuario/cliente y
   selecciona ambos Proyectos en el alta, **Then** el sistema crea la cuenta con membresía en
   ambos Proyectos y el Usuario/cliente puede ser seleccionado como solicitante en tickets de
   cualquiera de los dos.
2. **Given** el formulario de alta de Usuario/cliente, **When** el Admin intenta guardar sin
   seleccionar ningún Proyecto y sin usar la forma legada de Cliente directo, **Then** el
   sistema exige al menos una selección (Proyecto o Cliente directo), igual que hoy.
3. **Given** un Cliente con Proyectos, **When** el Admin selecciona el mismo Proyecto dos veces
   en el multi-selector, **Then** el sistema lo trata como una sola selección (sin error ni
   membresía duplicada).

---

### User Story 2 - Agregar o quitar Proyectos de un Usuario/cliente existente (Priority: P2)

Un Admin/Coordinador necesita que un Usuario/cliente que ya tiene cuenta y ya está en uno o más
Proyectos, empiece o deje de tener acceso a un Proyecto adicional (por ejemplo, porque la empresa
Cliente arrancó un nuevo Proyecto, o porque un Proyecto terminó), sin recrear la cuenta.

**Why this priority**: complementa la US1 dando paridad de gestión post-alta; es menos urgente
porque hoy existe un rodeo manual vía la pantalla genérica de "Asignar personal" del Proyecto,
pero no es una gestión pensada para Usuarios/cliente ni visible desde su pantalla de gestión.

**Independent Test**: puede probarse completamente abriendo el detalle/edición de un Usuario/
cliente existente, agregando un Proyecto nuevo y confirmando que aparece en su lista de
Proyectos; luego quitando un Proyecto y confirmando que desaparece de esa lista y deja de ser
seleccionable como solicitante en tickets nuevos de ese Proyecto.

**Acceptance Scenarios**:

1. **Given** un Usuario/cliente ya asignado al Proyecto A, **When** el Admin le agrega el
   Proyecto B (del mismo Cliente) desde su pantalla de gestión, **Then** el Usuario/cliente
   queda visible como solicitante seleccionable también en tickets del Proyecto B, sin perder su
   acceso al Proyecto A.
2. **Given** un Usuario/cliente asignado a los Proyectos A y B, **When** el Admin le quita el
   Proyecto B, **Then** el Usuario/cliente deja de aparecer como solicitante seleccionable en
   tickets nuevos del Proyecto B, pero conserva su acceso y visibilidad sobre tickets ya
   existentes donde figura como solicitante.
3. **Given** un Usuario/cliente asignado únicamente al Proyecto A, **When** el Admin intenta
   asignarle un Proyecto que pertenece a un Cliente distinto, **Then** el sistema rechaza la
   operación (un Usuario/cliente solo puede tener Proyectos del Cliente al que pertenece).

---

### Edge Cases

- ¿Qué pasa si se quitan todos los Proyectos de un Usuario/cliente? La cuenta sigue existiendo y
  conserva el acceso a tickets históricos, pero no puede ser elegido como solicitante en tickets
  nuevos hasta que se le asigne al menos un Proyecto de nuevo (mismo comportamiento que un
  contacto legado sin Proyecto).
- ¿Qué pasa con los tickets ya creados donde el Usuario/cliente removido de un Proyecto figura
  como `client_contact_id`? No se modifican: la relación histórica del ticket se conserva
  aunque la membresía activa al Proyecto se haya quitado.
- ¿Qué pasa si se intenta asignar un Proyecto inactivo? Se rechaza, igual que en el alta actual
  con un solo Proyecto.
- ¿Qué pasa si dos Admins intentan modificar en simultáneo los Proyectos del mismo Usuario/
  cliente? Última escritura gana, sin bloqueo optimista (consistente con el resto del sistema).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El formulario de alta de Usuario/cliente DEBE permitir seleccionar uno o varios
  Proyectos (en lugar de exactamente uno) al crear la cuenta.
- **FR-002**: El sistema DEBE crear una membresía de Proyecto (`project_members`) por cada
  Proyecto seleccionado en el alta, derivando el Cliente del Usuario/cliente a partir de esos
  Proyectos (todos deben pertenecer al mismo Cliente).
- **FR-003**: El sistema DEBE rechazar el alta o la asignación si los Proyectos seleccionados no
  pertenecen todos al mismo Cliente.
- **FR-004**: El sistema DEBE permitir a un usuario con permiso de gestión de Usuarios/cliente
  agregar Proyectos adicionales a un Usuario/cliente ya existente, sin recrear la cuenta.
- **FR-005**: El sistema DEBE permitir a un usuario con permiso de gestión de Usuarios/cliente
  quitar a un Usuario/cliente de un Proyecto, sin eliminar la cuenta ni sus tickets históricos.
- **FR-006**: El sistema DEBE seguir exigiendo al menos una asignación (Proyecto o Cliente
  directo legado) para crear la cuenta, igual que hoy.
- **FR-007**: El sistema DEBE seguir resolviendo el listado de "Encargado solicitante"
  seleccionable en un ticket en base a la membresía del Usuario/cliente en el Proyecto de ese
  ticket (comportamiento ya existente, sin cambios), ahora correctamente poblado para Usuarios/
  cliente con varios Proyectos.
- **FR-008**: La pantalla de gestión de Usuarios/cliente DEBE mostrar, para cada uno, la lista
  completa de Proyectos a los que está asignado actualmente.
- **FR-009**: El sistema DEBE evitar membresías duplicadas si el mismo Proyecto se selecciona o
  se intenta agregar más de una vez para el mismo Usuario/cliente.
- **FR-010**: El sistema DEBE rechazar la asignación de un Proyecto inactivo a un Usuario/
  cliente, tanto en el alta como en la gestión posterior.

### Key Entities

- **Usuario/cliente (Encargado)**: cuenta de acceso externa de una persona que representa a un
  Cliente; pertenece a un único Cliente pero ahora puede estar vinculada a varios de los
  Proyectos de ese Cliente.
- **Membresía de Proyecto**: vínculo entre un Usuario/cliente (o cualquier persona del sistema) y
  un Proyecto; ya existe como relación muchos-a-muchos y es la base sobre la que se habilita esta
  funcionalidad — no requiere cambios de esquema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un Admin puede dar de alta un Usuario/cliente asignado a 2 o más Proyectos en un
  único flujo, sin pasos adicionales ni intervención técnica.
- **SC-002**: El 100% de los Usuarios/cliente con más de un Proyecto asignado aparecen como
  solicitante seleccionable en tickets de cada uno de sus Proyectos.
- **SC-003**: Un Admin puede agregar o quitar un Proyecto de un Usuario/cliente existente en un
  único flujo de gestión, sin recrear la cuenta.
- **SC-004**: Quitar un Proyecto de un Usuario/cliente no afecta ningún ticket histórico ya
  vinculado a esa persona.

## Assumptions

- Un Usuario/cliente sigue perteneciendo a un único Cliente (empresa); lo que cambia es que
  puede tener varios Proyectos de ese mismo Cliente, no de Clientes distintos.
- No hay un límite máximo de Proyectos por Usuario/cliente.
- La forma legada de alta directa por Cliente (sin Proyecto) se mantiene sin cambios para
  compatibilidad.
- Quitar a un Usuario/cliente de un Proyecto es una operación reversible (se puede volver a
  agregar) y no requiere confirmación adicional más allá de la habitual en el sistema.
- No se requiere migración de datos: el modelo `project_members` ya soporta múltiples Proyectos
  por persona: esta funcionalidad solo relaja restricciones de UI/API existentes.
