# Feature Specification: Fase 3 — Manejo de Tareas

**Feature Branch**: `008-fase3-tareas`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "empieza la fase 3"

**Contexto (roadmap SDD V3)**: según `.specify/memory/constitution.md` (Roadmap de Fases) y el
`README.md`, la Fase 3 es "Manejo de Tareas (misma tabla que tickets, campo 'Tipo de registro' +
'Registro relacionado')". Gran parte de la infraestructura de esquema ya existe desde fases
anteriores mientras estaba reservada para esta fase:
- `catalog_record_types` ya tiene sembrados `Ticket` y `Tarea` (migración `013`), pero
  `TicketsPage.tsx` hoy solo permite crear `Ticket` — "'Tarea' queda reservado para Fase 3".
- La columna `related_ticket_id` ("Registro relacionado") ya existe en `tickets` desde la
  migración `011` y es un campo PATCHable, pero no se expone aún en ningún formulario.
- `MyTasksPage.tsx` ("Mis Tareas", Fase 2.2) ya anuncia explícitamente: "el agrupamiento por
  listas llega en Fase 3".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Crear una Tarea para organizar el propio trabajo (Priority: P1)

Un Resolutor (o cualquier recurso interno) necesita registrar una unidad de trabajo propia que no
es un incidente de cliente (p. ej. "Preparar demo para el cliente", "Revisar documentación de
proyecto") sin forzarla a pasar por los campos de clasificación de un Ticket (tipo de incidente,
severidad, herramienta, proceso, escalamiento) que no le aplican. Crea una Tarea desde un
formulario reducido, asociada al Cliente y Proyecto en los que trabaja, y la ve aparecer de
inmediato en "Mis Tareas" junto a sus Tickets asignados, distinguible como Tarea.

**Why this priority**: Es el requisito mínimo que le da sentido a la Fase 3 — sin poder crear una
Tarea, ninguna otra historia de esta fase es alcanzable. Reutiliza el catálogo `record_type_id`
ya sembrado en la migración `013`.

**Independent Test**: Crear una Tarea vía el nuevo formulario reducido y confirmar que aparece en
"Mis Tareas" con una marca visual de "Tarea" (no "Ticket"), sin haber tenido que completar
severidad/herramienta/proceso.

**Acceptance Scenarios**:

1. **Given** un Resolutor autenticado con al menos un Cliente/Proyecto asignado, **When** crea un
   nuevo registro eligiendo "Tarea" como tipo de registro con título, descripción, Cliente y
   Proyecto, **Then** el sistema crea el registro sin exigir tipo de incidente, severidad,
   herramienta ni proceso.
2. **Given** una Tarea recién creada, **When** el Resolutor abre "Mis Tareas", **Then** la Tarea
   aparece en el listado con una etiqueta o columna que la distingue de los Tickets.
3. **Given** un usuario con rol Encargado, **When** usa el flujo de creación simplificado
   (autoservicio), **Then** no puede elegir "Tarea" como tipo de registro — su flujo sigue
   creando únicamente Tickets, igual que antes de esta fase.

---

### User Story 2 - Vincular una Tarea a un Registro relacionado (Priority: P2)

Al crear o editar una Tarea, el usuario quiere dejar constancia de que esa Tarea surge de (o está
asociada a) un Ticket u otra Tarea ya existente del mismo Cliente — por ejemplo, una Tarea de
seguimiento interno que nace de un Ticket resuelto. Selecciona ese "Registro relacionado" desde
una lista acotada al Cliente de la Tarea, y desde el detalle de cualquiera de los dos registros
puede navegar al otro.

**Why this priority**: Da valor real al campo `related_ticket_id` que ya existe en el esquema
desde la Fase 1 pero nunca se expuso en la UI; depende de que la Historia 1 ya permita crear
Tareas.

**Independent Test**: Crear una Tarea con "Registro relacionado" apuntando a un Ticket existente
del mismo Cliente; confirmar que el detalle de la Tarea muestra el enlace al Ticket y que el
detalle del Ticket lista la Tarea que lo referencia.

**Acceptance Scenarios**:

1. **Given** una Tarea en edición y un Ticket existente del mismo Cliente, **When** el usuario
   selecciona ese Ticket como "Registro relacionado" y guarda, **Then** el detalle de la Tarea
   muestra un enlace de navegación directo a ese Ticket.
2. **Given** un Ticket que es el "Registro relacionado" de una o más Tareas, **When** se abre su
   detalle, **Then** se listan las Tareas que lo referencian.
3. **Given** una Tarea de un Cliente A, **When** el usuario intenta seleccionar como "Registro
   relacionado" un Ticket de un Cliente B, **Then** el sistema lo rechaza (409), mismo criterio
   ya usado para el Encargado por Cliente de la Fase 2.2 (spec `007`, FR-008).

---

### User Story 3 - Agrupar Tareas en Listas dentro de "Mis Tareas" (Priority: P3)

El usuario organiza sus Tareas en listas con nombre propio (p. ej. "Esta semana", "Backlog") en
vez de verlas todas mezcladas en una sola tabla plana, como anuncia hoy el texto de "Mis Tareas"
("el agrupamiento por listas llega en Fase 3").

**Why this priority**: Es una mejora de organización visual sobre las Historias 1 y 2 — el
sistema ya es útil sin ella (una Tarea sin lista queda en un grupo "Sin lista" por defecto), por
lo que puede entregarse después.

**Independent Test**: Crear dos listas con al menos una Tarea cada una y confirmar que "Mis
Tareas" las agrupa visualmente por lista en vez de mostrar una tabla única.

**Acceptance Scenarios**:

1. **Given** un usuario con Tareas sin lista asignada, **When** abre "Mis Tareas", **Then** ve
   esas Tareas agrupadas bajo una sección "Sin lista" (comportamiento por defecto, sin romper el
   estado actual).
2. **Given** un usuario que escribe un nombre de lista nuevo (p. ej. "Esta semana") al crear o
   editar una Tarea, **When** abre "Mis Tareas", **Then** ve esa Tarea agrupada bajo el nombre de
   esa lista, junto a cualquier otra Tarea con el mismo nombre de lista.

---

### Edge Cases

- ¿Qué pasa si el Ticket/Tarea usado como "Registro relacionado" se cancela o cierra después de
  vincularse? El vínculo se conserva (es solo trazabilidad histórica); la Tarea no se bloquea.
- ¿Qué pasa si se intenta vincular una Tarea a un Ticket de otro Cliente? Se rechaza (ver US2,
  escenario 3).
- ¿Qué pasa si se intenta vincular una Tarea a sí misma como "Registro relacionado"? Se rechaza.
- ¿Qué pasa si dos Tareas usan nombres de lista casi idénticos por error de tipeo (p. ej. "Esta
  semana" vs. "esta semana ")? Al ser texto libre, se agrupan como listas distintas — no hay
  normalización ni autocompletado en esta fase.
- ¿Qué pasa si un Encargado (cliente externo) intenta acceder por API directa a la creación de
  una Tarea? Debe rechazarse igual que cualquier otro campo fuera de su flujo de autoservicio.
- ¿Puede reabrirse una Tarea en estado Hecha o Cancelada? Sí — a diferencia del Ticket (que exige
  tipo de resolución para Cerrar), la Tarea es de uso interno y su dueño puede devolverla a
  "En progreso" en cualquier momento.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir crear un registro con tipo de registro "Tarea" (catálogo
  `record_type_id`, ya sembrado desde la migración `013`) desde un formulario dedicado, distinto
  del de "Ticket".
- **FR-002**: El formulario de creación de Tarea NO DEBE exigir tipo de incidente, severidad,
  herramienta ni proceso — campos propios de la clasificación de un Ticket que no aplican a una
  Tarea.
- **FR-003**: Una Tarea DEBE requerir Cliente y Proyecto, igual que un Ticket, respetando el
  mismo modelo jerárquico Cliente → Proyecto ya vigente.
- **FR-004**: El sistema DEBE permitir seleccionar un "Registro relacionado" (`related_ticket_id`,
  ya existente en el esquema desde la migración `011`) al crear o editar una Tarea, acotado a
  Tickets/Tareas del mismo Cliente.
- **FR-005**: El sistema DEBE rechazar (409) un "Registro relacionado" que pertenezca a un
  Cliente distinto del de la Tarea, o que sea la propia Tarea.
- **FR-006**: El detalle de un Ticket o Tarea DEBE mostrar la lista de Tareas que lo referencian
  como "Registro relacionado" (relación inversa).
- **FR-007**: El listado "Mis Tareas" y el listado general de Tickets DEBEN distinguir
  visualmente los registros de tipo Tarea de los de tipo Ticket.
- **FR-008**: El flujo de creación simplificado de un usuario con rol Encargado NO DEBE ofrecer
  "Tarea" como tipo de registro — el autoservicio de Encargados permanece limitado a Tickets,
  igual que antes de esta fase (FR-030 de la Fase 1 sigue vigente para ese rol).
- **FR-009**: Una Tarea DEBE seguir un ciclo de vida propio y simplificado, independiente de la
  FSM de 10 estados del Ticket: **Pendiente → En progreso → Hecha**, con **Cancelada** alcanzable
  desde Pendiente o En progreso. No hereda estados orientados a cliente del Ticket (p. ej.
  "Pendiente de usuario", "Pre-Análisis/Contacto") por no tener sentido en trabajo interno sin un
  cliente esperando respuesta.
- **FR-010**: Las listas de agrupación de Tareas (User Story 3) DEBEN implementarse como un campo
  simple de agrupación (nombre de lista en texto libre) en la propia Tarea — sin tabla ni CRUD
  dedicado. Una Tarea sin lista asignada cae en el grupo "Sin lista" (comportamiento por defecto,
  ver Edge Cases).
- **FR-011**: Cualquier recurso interno (Admin, Coordinador, QM o Resolutor) DEBE poder crear
  Tareas para sí mismo sin necesitar un permiso nuevo — autoservicio interno de organización del
  propio trabajo, reutilizando el permiso `tickets:create` ya existente (una Tarea es, a nivel de
  permisos, un registro más de la misma tabla `tickets`).

### Key Entities

- **Tarea**: mismo registro físico que un Ticket (tabla `tickets`), distinguido por
  `record_type_id = 'Tarea'`. Comparte Cliente, Proyecto, título, descripción, prioridad,
  asignación y comentarios con el Ticket; no completa los campos de clasificación de incidente
  (severidad, herramienta, proceso, escalamiento), que seguirán existiendo en el esquema pero
  quedan sin uso para este tipo de registro. Sigue un ciclo de vida propio de 4 estados
  (Pendiente, En progreso, Hecha, Cancelada) independiente de la FSM de 10 estados del Ticket.
- **Registro relacionado**: referencia opcional (`related_ticket_id`, ya existente) de una Tarea
  hacia un Ticket u otra Tarea del mismo Cliente, para dar trazabilidad sin duplicar información.
- **Lista de Tareas**: nombre de agrupación en texto libre almacenado en la propia Tarea (no es
  una entidad ni tabla independiente); una Tarea sin ese campo cae en el grupo "Sin lista".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un Resolutor puede crear una Tarea en menos de 30 segundos, sin tener que completar
  ningún campo de clasificación de incidente que no le aplica.
- **SC-002**: El 100% de los intentos de vincular una Tarea a un "Registro relacionado" de un
  Cliente distinto son rechazados por el sistema.
- **SC-003**: "Mis Tareas" distingue visualmente el 100% de las Tareas frente a los Tickets
  mostrados, sin ambigüedad reportada en pruebas de usuario.
- **SC-004**: Un usuario con rol Encargado no puede, en ningún escenario probado, crear un
  registro de tipo Tarea desde su flujo de autoservicio.
- **SC-005**: El 100% de las Tareas sin lista asignada aparecen agrupadas bajo "Sin lista" en
  "Mis Tareas", sin registros que desaparezcan del listado por falta de lista.
- **SC-006**: Un recurso interno puede mover una Tarea entre Pendiente, En progreso y Hecha (o
  Cancelarla) sin ningún paso intermedio obligatorio de tipo Ticket (p. ej. sin necesitar un
  comentario tipificado ni un tipo de resolución).

## Assumptions

- Se reutiliza el catálogo `record_type_id` ya sembrado (`Ticket`, `Tarea`) desde la migración
  `013` — no se requiere una nueva migración de catálogo para esto.
- Se reutiliza la columna `related_ticket_id` ya existente desde la migración `011` para
  "Registro relacionado" — no se requiere una nueva columna de esquema para esto.
- Las Tareas participan del mismo sistema de comentarios, adjuntos, notificaciones y registro de
  tiempos (Fase 2) que los Tickets.
- El rol Encargado permanece sin acceso a Tareas en esta fase — su autoservicio sigue acotado a
  Tickets (consistente con FR-030 y con el resto del sistema de permisos ya construido).
- Los usuarios objetivo de "Mis Tareas" con Tareas son los mismos roles internos que ya acceden
  hoy a esa pantalla (Admin, Coordinador, QM, Resolutor) — Fase 3 no introduce un rol nuevo.
- El ciclo de vida de la Tarea (Pendiente/En progreso/Hecha/Cancelada) requiere una FSM nueva y
  simple en el dominio, separada de `ticket_fsm.py` (que sigue rigiendo solo a los registros de
  tipo Ticket).
- La agrupación por "lista" es texto libre sin normalización (sensible a mayúsculas/espacios) —
  no hay gestión, renombrado masivo ni CRUD de listas en esta fase; queda abierto como posible
  mejora futura si el uso real lo justifica.
- Cualquier recurso interno puede crear Tareas para sí mismo reutilizando el permiso
  `tickets:create` ya existente; no se introduce un permiso `tasks:create` separado en esta fase.
