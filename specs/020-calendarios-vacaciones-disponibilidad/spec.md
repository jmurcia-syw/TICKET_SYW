# Feature Specification: Calendarios Multi-Zona Horaria, Festivos, Vacaciones (RRHH) y Disponibilidad

**Feature Branch**: `[020-calendarios-vacaciones-disponibilidad]`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Fase 5: Sistema de Calendarios Multi-Zona Horaria con Festivos, Gestión de Vacaciones (RRHH) y Disponibilidad. Calendarios del Cliente (configurable desde la vista Cliente: huso horario y país) y del Equipo de Trabajo (zonas horarias por miembro), con días festivos por país visibles en ambos. Horario laboral semanal por defecto por usuario. Rol RRHH con solicitudes de vacaciones/permisos por rango de fechas y panel de aprobación/rechazo. Al asignar un ticket, si el resolutor no está disponible (fuera de horario, festivo en su país, o vacaciones aprobadas) la interfaz debe mostrar una alerta visual clara, sin bloquear la asignación."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Alerta de disponibilidad al asignar un ticket (Priority: P1)

Como Coordinador o QM que asigna un ticket a un Resolutor, quiero ver de inmediato si esa persona
está disponible en este momento (dentro de su horario laboral, sin ser día festivo en su país, y
sin tener vacaciones/permiso aprobado) para poder decidir con información completa sin que el
sistema me impida asignar igualmente si es necesario.

**Why this priority**: Es el valor de negocio central pedido para la Fase 5 — evita asignaciones
"a ciegas" a personas fuera de línea, reduciendo tiempos de primera respuesta fallidos y SLAs
incumplidos por desconocimiento de la disponibilidad real del equipo.

**Independent Test**: Con datos de horario laboral, festivos y vacaciones aprobadas ya cargados
para un Resolutor (aunque sea por carga directa de datos de prueba), abrir el panel de asignación
de un ticket y verificar que se muestra un indicador de "No disponible" con el motivo cuando
corresponde, y ningún indicador cuando el Resolutor sí está disponible. La asignación se completa
en ambos casos.

**Acceptance Scenarios**:

1. **Given** un Resolutor con horario laboral configurado y la hora actual está fuera de ese
   horario, **When** el Coordinador abre el selector de resolutor para asignar un ticket, **Then**
   el sistema muestra un indicador visual claro (ícono/color de advertencia + tooltip) de "No
   disponible: fuera de horario laboral" junto a su nombre, y permite completar la asignación de
   todas formas.
2. **Given** la fecha actual es un día festivo del país configurado para ese Resolutor, **When**
   el Coordinador visualiza al Resolutor en el selector de asignación, **Then** se muestra el
   indicador de "No disponible: día festivo" con el nombre del festivo.
3. **Given** el Resolutor tiene una solicitud de vacaciones/permiso con estado Aprobado que cubre
   la fecha actual, **When** el Coordinador visualiza al Resolutor en el selector de asignación,
   **Then** se muestra el indicador de "No disponible: vacaciones/permiso aprobado" con el rango
   de fechas.
4. **Given** el Resolutor está dentro de su horario laboral, no es festivo y no tiene
   ausencia aprobada vigente, **When** se abre el selector de asignación, **Then** no se muestra
   ningún indicador de no disponibilidad.
5. **Given** el Resolutor no tiene horario laboral, país o calendario configurado, **When** se
   abre el selector de asignación, **Then** el sistema lo trata como disponible por defecto y no
   muestra ningún indicador de advertencia (ausencia de datos no bloquea ni penaliza).

---

### User Story 2 - Solicitud y aprobación en cadena de ausencias (Jefe directo + RRHH) (Priority: P2)

Como miembro del equipo de trabajo quiero enviar una solicitud de ausencia (vacaciones,
incapacidad médica, permiso personal u otro tipo) indicando un rango de fechas y, cuando
corresponda, adjuntando un documento de soporte (por ejemplo una incapacidad médica); y como
Jefe directo del solicitante o como usuario con el rol RRHH quiero revisar y aprobar o rechazar
esa solicitud, para llevar un control formal de las ausencias del equipo con doble validación
(negocio + RRHH).

**Why this priority**: Es el flujo administrativo que alimenta de datos a la alerta de
disponibilidad (Historia 1) y es, además, un proceso de negocio con valor propio (control de
ausencias) que puede usarse y probarse de forma independiente. La doble aprobación asegura que
tanto el responsable directo del recurso (impacto operativo) como RRHH (cumplimiento formal)
den su visto bueno.

**Independent Test**: Un usuario del equipo crea una solicitud de ausencia de tipo "Incapacidad
médica" con fecha de inicio, fin y un documento adjunto; su Jefe directo la aprueba; luego un
usuario con rol RRHH la aprueba; el estado general pasa a "Aprobado" solo cuando ambas
aprobaciones existen. Si cualquiera de los dos rechaza, el estado general queda "Rechazado".

**Acceptance Scenarios**:

1. **Given** un usuario autenticado del equipo de trabajo, **When** completa el formulario de
   solicitud de ausencia eligiendo un tipo (Vacaciones, Incapacidad médica, Permiso personal,
   Otro), fecha de inicio y fecha de fin válidas, y opcionalmente adjunta un documento de
   soporte, **Then** la solicitud se crea con estado general "Pendiente" (aprobación de Jefe
   pendiente y aprobación de RRHH pendiente) y queda visible tanto para el Jefe directo como en
   el panel de RRHH.
2. **Given** una solicitud con ambas aprobaciones en estado "Pendiente", **When** el Jefe directo
   del solicitante la aprueba, **Then** su aprobación queda registrada como "Aprobado" pero el
   estado general permanece "Pendiente" hasta que RRHH también decida.
3. **Given** una solicitud ya aprobada por el Jefe directo, **When** un usuario con rol RRHH
   también la aprueba, **Then** el estado general cambia a "Aprobado" y esas fechas quedan
   disponibles para la lógica de disponibilidad de la Historia 1.
4. **Given** una solicitud en cualquier estado de aprobación parcial, **When** el Jefe directo o
   RRHH la rechaza, **Then** el estado general cambia inmediatamente a "Rechazado" (un solo
   rechazo es suficiente, sin esperar la otra aprobación) y no afecta la disponibilidad del
   usuario.
5. **Given** un solicitante sin Jefe directo asignado en su ficha de Recurso, **When** envía una
   solicitud de ausencia, **Then** el sistema solo requiere la aprobación de RRHH para que el
   estado general pase a "Aprobado".
6. **Given** un usuario que no es el Jefe directo del solicitante ni tiene el rol RRHH, **When**
   intenta acceder a la aprobación de esa solicitud, **Then** el sistema deniega el acceso.
7. **Given** una fecha de fin anterior a la fecha de inicio, **When** el usuario intenta enviar la
   solicitud, **Then** el sistema rechaza el envío con un mensaje de validación.
8. **Given** un usuario que es a la vez Jefe directo y tiene rol RRHH sobre su propia solicitud
   (o la de un subordinado que es él mismo), **When** intenta aprobar/rechazar su propia
   solicitud, **Then** el sistema lo impide.

---

### User Story 3 - Calendario con festivos por país (Cliente y Equipo) (Priority: P3)

Como Coordinador quiero ver, en el calendario del Cliente y en el calendario del Equipo de
Trabajo, los días festivos correspondientes al país configurado de cada uno, para planificar
trabajo y comunicación sin sorpresas por feriados locales.

**Why this priority**: Es la capa visual (estilo Google Calendar) sobre la que se apoyan las
Historias 1 y 2; sin embargo, puede construirse y validarse de forma independiente mostrando los
festivos ya cargados en el catálogo.

**Independent Test**: Configurar el país de un Cliente y el país de un miembro del equipo desde
sus respectivas vistas, y verificar que el calendario correspondiente muestra los festivos de ese
país en las fechas correctas, distinguibles visualmente de otros eventos.

**Acceptance Scenarios**:

1. **Given** un usuario con permisos sobre la vista "Cliente", **When** configura el huso horario
   y el país de residencia del Cliente, **Then** el calendario del Cliente muestra sus horas en
   ese huso horario y resalta los festivos del país configurado.
2. **Given** un miembro del equipo con su país configurado, **When** se visualiza el calendario
   del Equipo de Trabajo, **Then** los festivos de su país aparecen resaltados en su franja de
   calendario, ajustados a su zona horaria.
3. **Given** dos miembros del equipo con países distintos, **When** se visualiza el calendario del
   Equipo, **Then** cada miembro muestra únicamente los festivos de su propio país, sin mezclarlos.
4. **Given** un país sin festivos cargados en el catálogo, **When** se visualiza su calendario,
   **Then** el calendario se muestra normalmente sin festivos marcados (sin error).

---

### User Story 4 - Horario laboral semanal por defecto (Priority: P4)

Como usuario del equipo de trabajo quiero que se configure un horario de oficina semanal por
defecto en mi zona horaria local, para que el sistema sepa en qué franjas horarias se me considera
disponible.

**Why this priority**: Complementa a la Historia 1 (define qué es "fuera de horario"); tiene
menor prioridad porque puede operar con un horario por defecto razonable mientras no se
personalice.

**Independent Test**: Configurar un horario laboral semanal (días y horas) para un usuario y
verificar que las horas dentro de ese rango se consideran horario laboral y las horas fuera del
rango no, respetando la zona horaria del usuario.

**Acceptance Scenarios**:

1. **Given** un usuario del equipo, **When** un administrador configura su horario laboral semanal
   (por ejemplo lunes a viernes, 08:00–17:00 en su zona horaria), **Then** el sistema guarda ese
   horario asociado al usuario.
2. **Given** un usuario sin horario laboral configurado explícitamente, **When** se evalúa su
   disponibilidad, **Then** el sistema aplica un horario por defecto razonable documentado en la
   configuración del sistema.
3. **Given** la hora actual convertida a la zona horaria local del usuario cae dentro de su
   horario laboral configurado, **When** se evalúa su disponibilidad, **Then** el sistema lo
   considera "dentro de horario".

---

### Edge Cases

- ¿Qué ocurre si el país del Cliente o del Recurso se cambia después de tener festivos ya
  visualizados? El calendario debe recalcular los festivos mostrados según el país vigente.
- ¿Qué ocurre si una solicitud de vacaciones aprobada se solapa parcialmente con el momento de
  asignación (por ejemplo, empieza mañana)? Solo las fechas dentro del rango aprobado cuentan como
  "no disponible"; fuera del rango, el usuario es evaluado por horario laboral y festivos.
- ¿Qué ocurre si el mismo usuario tiene rol RRHH y además envía su propia solicitud de ausencia?
  No puede aprobar ni rechazar su propia solicitud (ni como RRHH ni como Jefe directo).
- ¿Qué ocurre con solicitudes ya aprobadas si se intenta cambiar sus fechas? Se trata como una
  nueva solicitud (edición no permitida sobre una aprobada; debe cancelarse y crear una nueva).
- ¿Qué ocurre si dos solicitudes de ausencia del mismo usuario se solapan en fechas? El sistema
  debe impedir el envío de una solicitud que se solape con otra ya Pendiente o Aprobada del mismo
  usuario.
- ¿Qué ocurre si el Jefe directo aprueba y luego RRHH rechaza (o viceversa)? El rechazo de
  cualquiera de las dos partes deja el estado general en "Rechazado" de forma definitiva; la
  solicitud no puede reabrirse, el solicitante debe crear una nueva.
- ¿Qué ocurre si el tipo de ausencia requiere documento de soporte (por ejemplo Incapacidad
  médica) y el usuario no adjunta nada? El adjunto es opcional a nivel de sistema en esta fase;
  Jefe y RRHH pueden rechazar la solicitud si consideran que falta el soporte, pero el envío no
  se bloquea por ausencia de archivo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir configurar, desde la vista "Cliente", el huso horario y el
  país de residencia de cada cliente.
- **FR-002**: El sistema DEBE permitir configurar el país (y por lo tanto huso horario y
  calendario de festivos) de cada miembro del equipo de trabajo (Recurso).
- **FR-003**: El sistema DEBE mantener un catálogo de días festivos por país, consultable para
  cualquier país configurado en un Cliente o Recurso.
- **FR-004**: El sistema DEBE mostrar, en el calendario del Cliente, los días festivos del país
  configurado para ese cliente, distinguibles visualmente de otros eventos.
- **FR-005**: El sistema DEBE mostrar, en el calendario del Equipo de Trabajo, los días festivos
  del país correspondiente a cada miembro, ajustados a la zona horaria de cada uno.
- **FR-006**: El sistema DEBE permitir configurar un horario laboral semanal (días de la semana y
  franjas horarias) por defecto para cada usuario del equipo, expresado en su zona horaria local.
- **FR-007**: El sistema DEBE habilitar un rol "RRHH" que pueda asignarse a cualquier usuario del
  sistema mediante el mecanismo existente de gestión de roles y permisos.
- **FR-008**: El sistema DEBE permitir que un usuario del equipo de trabajo envíe una solicitud de
  ausencia especificando un tipo (por ejemplo: Vacaciones, Incapacidad médica, Permiso personal,
  Otro), fecha de inicio y fecha de fin.
- **FR-008a**: El sistema DEBE permitir adjuntar opcionalmente uno o más documentos de soporte
  (por ejemplo un certificado de incapacidad médica) a una solicitud de ausencia, reutilizando el
  mecanismo de adjuntos ya existente en el sistema.
- **FR-009**: El sistema DEBE rechazar el envío de una solicitud de ausencia cuando la fecha de
  fin es anterior a la fecha de inicio, o cuando se solapa con otra solicitud propia en estado
  Pendiente o Aprobada.
- **FR-010**: El sistema DEBE exponer un panel, accesible únicamente a usuarios con el rol RRHH,
  donde se listan todas las solicitudes de ausencia de todo el equipo con su tipo, adjuntos y
  estado (general, de Jefe directo y de RRHH).
- **FR-010a**: El sistema DEBE permitir al Jefe directo de un solicitante (según el campo "jefe"
  ya existente en la ficha de Recurso) ver y decidir sobre las solicitudes de ausencia de sus
  subordinados directos, en una vista propia o dentro del mismo panel de aprobación.
- **FR-011**: El sistema DEBE requerir dos aprobaciones independientes para que una solicitud de
  ausencia quede en estado general "Aprobado": la del Jefe directo del solicitante y la de un
  usuario con rol RRHH, registrando quién y cuándo tomó cada decisión.
- **FR-011a**: El sistema DEBE cambiar el estado general de una solicitud a "Rechazado" en cuanto
  el Jefe directo o RRHH la rechace, sin requerir que la otra parte se pronuncie.
- **FR-011b**: El sistema DEBE requerir únicamente la aprobación de RRHH (omitiendo la del Jefe
  directo) cuando el solicitante no tiene un Jefe directo asignado en su ficha de Recurso.
- **FR-012**: El sistema DEBE impedir que un usuario apruebe o rechace su propia solicitud de
  ausencia, incluso si esa persona tiene el rol RRHH o es su propio Jefe directo en la jerarquía.
- **FR-013**: El sistema DEBE, al momento de mostrar candidatos para asignar un ticket, calcular la
  disponibilidad de cada Resolutor evaluando en este orden: solicitud de ausencia con estado
  general Aprobado vigente, día festivo en su país, y horario laboral configurado.
- **FR-014**: El sistema DEBE mostrar un indicador visual claro (ícono o color de advertencia con
  texto/tooltip explicando el motivo) cuando un Resolutor no está disponible en el momento de la
  asignación.
- **FR-015**: El sistema NUNCA DEBE bloquear la asignación de un ticket por motivos de
  disponibilidad; la alerta es siempre informativa y la asignación se permite en cualquier caso.
- **FR-016**: El sistema DEBE tratar como "disponible" (sin advertencia) a cualquier Resolutor que
  no tenga país, horario laboral o calendario configurado, para no bloquear el flujo de trabajo
  por falta de datos.
- **FR-017**: El sistema DEBE recalcular los festivos visualizados en un calendario cuando cambia
  el país configurado del Cliente o Recurso asociado.

### Key Entities

- **Calendario/Huso horario de Cliente**: huso horario y país de residencia asociados a un
  Cliente existente; determina qué festivos se muestran en su calendario.
- **Calendario/Huso horario de Recurso**: país y huso horario asociados a un miembro del equipo
  (Recurso) existente; determina festivos y conversión de horario laboral.
- **Día Festivo**: fecha, país, nombre del festivo; catálogo consultado por los calendarios de
  Cliente y Equipo.
- **Horario Laboral**: por usuario, conjunto de franjas (día de semana, hora de inicio, hora de
  fin) en su zona horaria local; define cuándo se considera "en horario".
- **Tipo de Ausencia**: catálogo (Vacaciones, Incapacidad médica, Permiso personal, Otro) que
  clasifica una solicitud.
- **Solicitud de Ausencia**: usuario solicitante, tipo de ausencia, fecha de inicio, fecha de fin,
  documento(s) adjunto(s) opcionales, estado de aprobación del Jefe directo
  (Pendiente/Aprobado/Rechazado), estado de aprobación de RRHH (Pendiente/Aprobado/Rechazado),
  estado general derivado (Pendiente/Aprobado/Rechazado), usuario y fecha de cada decisión.
- **Rol RRHH**: rol del sistema de roles/permisos existente con acceso al panel de aprobación de
  solicitudes de todo el equipo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al abrir el panel de asignación de un ticket, el Coordinador ve el estado de
  disponibilidad de cada Resolutor candidato en menos de 2 segundos, sin recargar la página.
- **SC-002**: El 100% de las solicitudes de ausencia con estado general "Aprobado" (ambas partes,
  Jefe directo y RRHH, o solo RRHH cuando no hay Jefe asignado) se reflejan en la lógica de
  disponibilidad de asignación sin intervención manual adicional.
- **SC-003**: Una solicitud de ausencia puede enviarse, y cada una de sus dos aprobaciones
  (Jefe directo, RRHH) puede resolverse, en menos de 1 minuto de interacción, sin necesidad de
  soporte técnico.
- **SC-004**: El 100% de los días festivos configurados para un país se visualizan correctamente
  en el calendario correspondiente (Cliente o Equipo) sin desfase de fecha por huso horario.
- **SC-005**: Ninguna asignación de ticket es bloqueada por el sistema debido a disponibilidad;
  la tasa de asignaciones completadas con y sin advertencia de disponibilidad es la misma (100%
  de intentos de asignación se completan).

## Assumptions

- El catálogo de días festivos por país se mantiene internamente (carga/edición manual por un
  administrador), sin integrar un servicio o librería externa de terceros, en línea con la
  gobernanza de dependencias del proyecto (Principio V de la constitución) que exige aprobación
  previa documentada para nuevas dependencias.
- El rol "RRHH" se crea usando el sistema de roles y permisos ya existente (tablas `roles` /
  `permissions`), sin requerir un mecanismo de roles paralelo.
- Las solicitudes de ausencia son por día completo (no por franja horaria parcial dentro de un
  día), salvo que se indique lo contrario en una futura clarificación.
- El "Jefe directo" de la cadena de aprobación es el campo `jefe` (FK autorreferencial) ya
  existente en la ficha del Recurso (mencionado en la constitución del proyecto); no se introduce
  una jerarquía de aprobación paralela.
- Los documentos adjuntos a una solicitud de ausencia reutilizan el mecanismo de adjuntos ya
  implementado en el sistema (spec `017-contenido-enriquecido-ticket`), sin crear un subsistema de
  almacenamiento de archivos nuevo.
- El horario laboral por defecto para usuarios sin configuración explícita es lunes a viernes,
  jornada estándar de oficina, en la zona horaria del propio usuario.
- La "disponibilidad" es informativa únicamente para el Coordinador/QM al asignar; no se usa (en
  esta fase) para impedir ni para sugerir automáticamente un resolutor alternativo.
- El campo país de Cliente/Recurso reutiliza el mismo catálogo de países ya usado en otras partes
  del sistema (por ejemplo, el selector de teléfono internacional), evitando duplicar catálogos.
