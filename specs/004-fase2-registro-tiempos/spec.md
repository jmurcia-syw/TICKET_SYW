# Feature Specification: Fase 2 — Registro diario de tiempos por recurso

**Feature Branch**: `004-fase2-registro-tiempos`

**Created**: 2026-07-07

**Status**: Draft

**Input**: User description: "Fase 2 — Registro diario de tiempos por recurso. Según el roadmap de la
constitución (.specify/memory/constitution.md), esta fase cubre el registro diario de tiempos
trabajados por cada recurso (empleado/consultor) sobre los tickets/tareas en los que participa.
Debe construir sobre la Fase 1 ya completada (001-fase0-maestros + 002-fase1-tickets: FSM de
tickets, maestros de clientes/proyectos/recursos, comentarios, adjuntos)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar horas trabajadas en un ticket (Priority: P1)

Un Resolutor (o cualquier recurso interno que participa en tickets) termina su jornada y registra
cuánto tiempo dedicó, en el día, a cada uno de los tickets en los que trabajó. Selecciona el
ticket, indica la fecha (por defecto hoy), la cantidad de horas/minutos y una nota corta opcional
sobre lo realizado.

**Why this priority**: Es el registro atómico del que dependen todos los reportes y, a futuro, la
facturación y el cálculo de disponibilidad (Fase 5). Sin esta captura no existe dato para ninguna
otra historia de esta fase.

**Independent Test**: Un Resolutor con al menos un ticket asignado abre el registro de tiempos,
carga una entrada de horas contra ese ticket y verifica que aparece guardada en su listado del día.

**Acceptance Scenarios**:

1. **Given** un Resolutor autenticado con un ticket asignado en un estado activo (no CERRADO),
   **When** registra una entrada de tiempo con horas > 0 para ese ticket en la fecha de hoy,
   **Then** la entrada queda guardada y visible en su listado de registros del día, asociada al
   ticket, al recurso y a la fecha.
2. **Given** un Resolutor con varios tickets asignados, **When** registra tiempo contra dos
   tickets distintos el mismo día, **Then** ambas entradas se guardan de forma independiente y la
   suma de horas del día se refleja en el resumen diario del recurso.
3. **Given** un ticket que no está asignado al Resolutor que intenta registrar tiempo, **When**
   intenta guardar la entrada, **Then** el sistema rechaza la operación e indica que el recurso no
   participa en ese ticket.

---

### User Story 2 - Corregir o eliminar un registro de tiempo (Priority: P2)

El recurso se equivoca al cargar una entrada (horas, ticket o fecha incorrectos) y necesita
corregirla o eliminarla mientras la ventana de edición sigue abierta.

**Why this priority**: La captura manual es propensa a errores; sin la posibilidad de corregir,
los datos de tiempo pierden confiabilidad para cualquier reporte posterior.

**Independent Test**: Con una entrada de tiempo ya guardada por el propio recurso, editar sus
horas o eliminarla y verificar que el resumen diario se recalcula de inmediato.

**Acceptance Scenarios**:

1. **Given** una entrada de tiempo registrada por el propio recurso dentro de la ventana de
   edición permitida, **When** modifica las horas o la nota y guarda, **Then** el registro se
   actualiza y el resumen diario refleja el nuevo total.
2. **Given** una entrada de tiempo propia dentro de la ventana de edición, **When** el recurso la
   elimina, **Then** la entrada desaparece del listado y del resumen diario.
3. **Given** una entrada de tiempo fuera de la ventana de edición permitida, **When** el recurso
   intenta modificarla o eliminarla, **Then** el sistema lo impide e indica que debe solicitar la
   corrección a su Coordinador o Admin.

---

### User Story 3 - Consultar tiempos registrados por recurso y período (Priority: P3)

Un Coordinador, QM o Admin necesita ver cuánto tiempo registró cada recurso en un rango de fechas,
para revisar carga de trabajo real y detectar días sin registro.

**Why this priority**: Es el primer consumo de los datos capturados en US1/US2; habilita el
seguimiento operativo, aunque el producto ya entrega valor solo con la captura (US1).

**Independent Test**: Con registros de tiempo cargados para varios recursos, un Coordinador abre
el reporte, filtra por recurso y rango de fechas, y verifica que el total coincide con la suma de
las entradas individuales.

**Acceptance Scenarios**:

1. **Given** varios recursos con entradas de tiempo cargadas en la última semana, **When** un
   Coordinador consulta el reporte filtrando por esa semana, **Then** ve el total de horas por
   recurso y por día, desglosable por ticket.
2. **Given** un recurso sin ninguna entrada de tiempo en un día laborable del rango consultado,
   **When** se genera el reporte, **Then** ese día se muestra explícitamente como "sin registro"
   en vez de omitirse.
3. **Given** un usuario sin rol de Coordinador, QM o Admin, **When** intenta acceder al reporte de
   tiempos de otros recursos, **Then** el sistema lo restringe a ver únicamente sus propios
   registros.

---

### Edge Cases

- ¿Qué pasa si un recurso intenta registrar más de 24 horas en un mismo día (sumando todas sus
  entradas)? El sistema debe rechazar el guardado y mostrar el total ya acumulado ese día.
- ¿Qué pasa si se registra tiempo contra un ticket que pasa a CERRADO después de la carga? El
  registro histórico se conserva; no se permiten nuevas entradas contra tickets ya CERRADOS salvo
  para Admin (corrección administrativa).
- ¿Qué pasa si dos recursos distintos registran tiempo el mismo día contra el mismo ticket? Ambas
  entradas se guardan de forma independiente; el tiempo total del ticket es la suma de todos los
  recursos que participaron.
- ¿Qué pasa si el recurso intenta cargar una entrada con fecha futura? El sistema la rechaza; solo
  se permite registrar tiempo en el día actual o en días pasados dentro de la ventana de edición.
- ¿Qué pasa si el recurso intenta cargar horas en cero o negativas? El sistema rechaza la entrada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a cualquier recurso interno registrar una entrada de tiempo
  (fecha, ticket, cantidad de horas/minutos, nota opcional) contra un ticket en el que participa.
- **FR-002**: El sistema DEBE impedir registrar tiempo contra un ticket en el que el recurso no
  figura como asignado o partícipe (excepto Admin, para corrección administrativa).
- **FR-003**: El sistema DEBE calcular y mostrar, para cada recurso y día, el total de horas
  registradas entre todas sus entradas.
- **FR-004**: El sistema DEBE rechazar una entrada que haga que el total diario del recurso supere
  24 horas.
- **FR-005**: El sistema DEBE rechazar entradas con horas/minutos en cero o negativos.
- **FR-006**: El sistema DEBE rechazar entradas con fecha futura.
- **FR-007**: El sistema DEBE permitir al propio recurso editar o eliminar sus entradas de tiempo
  únicamente dentro de una ventana de edición de 7 días corridos desde la fecha original del
  registro.
- **FR-008**: El sistema DEBE impedir la edición o eliminación de entradas fuera de la ventana de
  edición para todo rol salvo Admin.
- **FR-009**: El sistema DEBE permitir registrar tiempo contra tickets en cualquier estado activo
  del ciclo de vida (no CERRADO); solo Admin puede registrar tiempo contra un ticket CERRADO.
- **FR-010**: El sistema DEBE exponer un reporte de tiempos filtrable por recurso y por rango de
  fechas, visible para Coordinador, QM y Admin sobre cualquier recurso, y para cada recurso sobre
  sus propios registros.
- **FR-011**: El reporte de tiempos DEBE mostrar explícitamente los días sin ningún registro dentro
  del rango consultado, en lugar de omitirlos.
- **FR-012**: El sistema DEBE conservar el detalle de cada entrada de tiempo (recurso, ticket,
  fecha, horas, nota, quién y cuándo la cargó/editó) de forma auditable, sin sobrescribir el
  historial de ediciones.
- **FR-013**: Cada entrada de tiempo DEBE quedar asociada de forma inmutable al recurso que la
  registró originalmente, independientemente de futuras ediciones por Admin.

### Key Entities

- **WorkSession (Registro de tiempo)**: Entrada individual de tiempo trabajado por un recurso en
  una fecha determinada sobre un ticket específico. Atributos clave: recurso, ticket, fecha,
  cantidad de tiempo (horas/minutos), nota opcional, quién la creó/editó y cuándo. Se relaciona con
  `Ticket` (Fase 1) y con `User`/recurso (Fase 0 — maestros).
- **Resumen diario de recurso**: Vista derivada (no almacenada como entidad propia) que agrega las
  `WorkSession` de un recurso por día para mostrar el total y detectar excesos de 24 horas o días
  sin registro.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un recurso puede registrar el tiempo de un ticket en menos de 30 segundos desde que
  abre la pantalla de registro.
- **SC-002**: El 100% de las entradas de tiempo con horas en cero, negativas, fecha futura, o que
  excedan 24 horas diarias son rechazadas antes de guardarse.
- **SC-003**: Un Coordinador puede obtener el total de horas registradas por cualquier recurso en
  un rango de fechas arbitrario en menos de 10 segundos, sin necesidad de sumar manualmente.
- **SC-004**: El reporte de tiempos identifica el 100% de los días sin registro dentro de un rango
  consultado, sin omitir ninguno.
- **SC-005**: El historial de ediciones de una entrada de tiempo es auditable al 100%: toda
  modificación posterior a la carga original queda registrada con autor y fecha/hora.

## Assumptions

- El recurso que registra tiempo es un usuario interno ya dado de alta en los maestros de la Fase
  0 (empleado o consultor con cuenta en el sistema); no se contempla carga de tiempos por terceros
  externos.
- El tiempo se registra siempre contra un ticket existente de la Fase 1 (`tickets`); la jerarquía
  de tareas/subtareas (Fase 3) y el motor de SLA que pausa contadores (Fase 4) quedan fuera de
  alcance de esta fase.
- La ventana de edición de 7 días corridos es un valor por defecto razonable para permitir
  correcciones sin comprometer la integridad de reportes ya cerrados; puede ajustarse en
  planificación si el negocio define otro criterio.
- No se define en esta fase ninguna validación cruzada contra calendarios país/recurso ni contra
  excepciones de RRHH (eso corresponde a la Fase 5 del roadmap).
- El registro de tiempo es informativo/operativo en esta fase; no dispara facturación, no requiere
  aprobación de un superior, y no está integrado aún con el motor de SLA.
- Los roles Coordinador, QM y Admin ya existentes (Fase 0/1) son los únicos con visibilidad sobre
  los registros de tiempo de otros recursos; un recurso raso solo ve los suyos.
