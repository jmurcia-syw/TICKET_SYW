# Feature Specification: Corregir el Cliente de un Usuario/cliente y desambiguar Proyectos homónimos

**Feature Branch**: `016-corregir-cliente-encargado`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "tiene multiples proyecto, pero cuando quito todos, solo me deje
asignarle los proyecto que ya tenia asignado, no los de otro cliente, despues de cometer un
error en de un proyecto de un cliente incorrecto, no se puede corregir, y tambien debe mostrar
la opcion de que cliente pertenece el proyecto, ya que puede existir un proyecto con el mismo
nombre en diferente cliente como "SOPORTE", "EVOLUTIVO" para 2 clientes diferente"

**Contexto (bug reportado sobre spec 015)**: la feature "Encargado en múltiples Proyectos" (spec
015) permite agregar y quitar Proyectos de un Usuario/cliente, pero el Cliente del contacto
(`client_id`) se fija en el alta y nunca se corrige después. Si un Admin se equivoca y vincula al
Usuario/cliente con un Proyecto del Cliente incorrecto, quitar todos los Proyectos asignados
**no** libera esa restricción: el selector de "agregar Proyecto" sigue ofreciendo únicamente
Proyectos del Cliente original (el incorrecto), dejando el error sin forma de corrección salvo
eliminar la cuenta y crearla de nuevo. Además, el selector de "agregar Proyecto" solo muestra el
nombre del Proyecto sin indicar su Cliente, lo cual es ambiguo cuando dos Clientes distintos
tienen Proyectos con el mismo nombre (ej. "SOPORTE", "EVOLUTIVO").

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Corregir el Cliente de un Usuario/cliente sin Proyectos asignados (Priority: P1)

Un Admin se da cuenta de que vinculó por error a un Usuario/cliente con Proyectos del Cliente
equivocado. Quita todos los Proyectos mal asignados y necesita poder asignarle en su lugar un
Proyecto del Cliente correcto, sin tener que eliminar la cuenta y volver a crearla desde cero.

**Why this priority**: es el bloqueo reportado — hoy un error de Cliente en el alta es
irrecuperable por la UI, obligando a recrear la cuenta (con nueva contraseña provisional y
pérdida de la cuenta original).

**Independent Test**: puede probarse completamente creando un Usuario/cliente con un Proyecto del
Cliente A, quitando ese Proyecto (queda en 0 Proyectos), y luego agregándole un Proyecto del
Cliente B — el Usuario/cliente debe quedar asociado al Cliente B.

**Acceptance Scenarios**:

1. **Given** un Usuario/cliente creado por error con un Proyecto del Cliente A y sin ningún otro
   Proyecto asignado, **When** el Admin quita ese Proyecto, **Then** el selector de "agregar
   Proyecto" para ese Usuario/cliente ofrece Proyectos de **cualquier** Cliente, no solo del
   Cliente A.
2. **Given** un Usuario/cliente sin Proyectos asignados, **When** el Admin le agrega un Proyecto
   del Cliente B, **Then** el Cliente del Usuario/cliente pasa a ser el Cliente B (se corrige),
   y así se refleja en su listado y en los filtros por Cliente.
3. **Given** un Usuario/cliente que ya tiene al menos un Proyecto asignado (Cliente B, ya
   corregido), **When** el Admin intenta agregarle un Proyecto de un Cliente distinto (Cliente
   C), **Then** el sistema rechaza la operación — igual que hoy, todos los Proyectos de un
   Usuario/cliente deben ser del mismo Cliente mientras tenga al menos uno asignado.
4. **Given** un Usuario/cliente creado por la forma legada (Cliente directo, sin Proyecto,
   spec 007), **When** el Admin le agrega su primer Proyecto, **Then** el Cliente del contacto se
   ajusta al Cliente de ese Proyecto (mismo comportamiento de corrección que en el escenario 2).

---

### User Story 2 - Ver a qué Cliente pertenece cada Proyecto en los selectores (Priority: P1)

Un Admin necesita distinguir Proyectos con el mismo nombre que pertenecen a Clientes distintos
(por ejemplo, dos Clientes que tienen cada uno un Proyecto llamado "SOPORTE") al elegir qué
Proyecto agregar a un Usuario/cliente, para no vincularlo por error al Proyecto equivocado.

**Why this priority**: sin esta información, la corrección de la US1 es propensa a repetir el
mismo tipo de error — el Admin no puede distinguir entre dos Proyectos homónimos de Clientes
diferentes.

**Independent Test**: puede probarse completamente teniendo dos Clientes con un Proyecto del
mismo nombre cada uno, y verificando que el selector de "agregar Proyecto" muestra ambos
diferenciados por su Cliente.

**Acceptance Scenarios**:

1. **Given** dos Clientes distintos que tienen cada uno un Proyecto llamado "SOPORTE", **When**
   el Admin abre el selector de "agregar Proyecto" de un Usuario/cliente sin Proyectos
   asignados, **Then** ambos Proyectos "SOPORTE" aparecen listados de forma distinguible por su
   Cliente (ej. "Cliente A — SOPORTE" y "Cliente B — SOPORTE").
2. **Given** el mismo selector, **When** el Usuario/cliente ya tiene Proyectos asignados de un
   Cliente específico (selector acotado a ese Cliente), **Then** el nombre del Cliente se sigue
   mostrando junto a cada Proyecto, por consistencia, aunque en ese caso todos compartan el mismo
   Cliente.

---

### Edge Cases

- ¿Qué pasa si el Admin quita todos los Proyectos y luego no agrega ninguno nuevo? El Usuario/
  cliente conserva su Cliente actual (el último correcto o el original si nunca se corrigió) y su
  acceso a tickets históricos; simplemente no puede ser elegido como solicitante en tickets
  nuevos hasta que se le asigne un Proyecto (comportamiento ya definido en spec 015).
- ¿Qué pasa con tickets históricos que ya referencian al Usuario/cliente bajo el Cliente
  incorrecto? No se modifican — la corrección de Cliente solo aplica hacia adelante, sobre la
  cuenta del Usuario/cliente y las membresías de Proyecto activas.
- ¿Qué pasa si dos Admins corrigen el Cliente del mismo Usuario/cliente en simultáneo? Última
  escritura gana, sin bloqueo optimista (consistente con el resto del sistema, spec 015).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir agregar a un Usuario/cliente sin ningún Proyecto
  actualmente asignado un Proyecto de **cualquier** Cliente (no solo el Cliente originalmente
  asociado a la cuenta).
- **FR-002**: Cuando se agrega el primer Proyecto a un Usuario/cliente que no tenía ninguno, el
  sistema DEBE actualizar el Cliente de la cuenta para que coincida con el Cliente de ese
  Proyecto.
- **FR-003**: El sistema DEBE seguir exigiendo que todos los Proyectos de un Usuario/cliente que
  ya tiene al menos uno asignado pertenezcan al mismo Cliente (comportamiento de spec 015, sin
  cambios) — la corrección de Cliente solo es posible partiendo de cero Proyectos.
- **FR-004**: El selector para agregar un Proyecto a un Usuario/cliente DEBE mostrar, junto al
  nombre de cada Proyecto, el nombre del Cliente al que pertenece, para distinguir Proyectos con
  el mismo nombre en Clientes distintos.
- **FR-005**: El listado y los filtros por Cliente de Usuarios/cliente DEBEN reflejar el Cliente
  corregido inmediatamente después de agregar el primer Proyecto tras haber quedado en cero.

### Key Entities

- **Usuario/cliente (Encargado)**: su Cliente asociado deja de ser estrictamente inmutable — se
  puede corregir una vez que la cuenta queda sin ningún Proyecto asignado, derivándolo del
  siguiente Proyecto que se le agregue.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un Admin puede corregir el Cliente de un Usuario/cliente mal asignado en un único
  flujo (quitar Proyectos → agregar el Proyecto correcto), sin eliminar ni recrear la cuenta.
- **SC-002**: El 100% de los Proyectos con nombres duplicados entre Clientes distintos se
  muestran diferenciables por Cliente en el selector de asignación.
- **SC-003**: 0 tickets históricos se ven afectados por una corrección de Cliente en un Usuario/
  cliente.

## Assumptions

- La corrección de Cliente solo se habilita cuando el Usuario/cliente tiene cero Proyectos
  asignados; no se ofrece una forma de "forzar" el cambio de Cliente teniendo Proyectos activos
  de otro Cliente (evita vínculos inconsistentes a mitad de camino).
- No se requiere una pantalla o campo separado para editar el Cliente directamente: se sigue
  derivando siempre de los Proyectos asignados, igual que en spec 010/015.
- No aplica a la forma legada de alta directa por Cliente (sin Proyecto): si nunca se le asigna
  un Proyecto, el Cliente asignado en el alta permanece sin cambios.
