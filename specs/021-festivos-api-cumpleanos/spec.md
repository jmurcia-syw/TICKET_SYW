# Feature Specification: Festivos sincronizados por API, categorización visual y cumpleaños en el Calendario

**Feature Branch**: `021-festivos-api-cumpleanos`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Ampliar el módulo de Calendarios (spec 020) con: (1) sincronización automática de festivos oficiales por país desde una API pública de festivos (ej. Nager.Date), en vez de mantenerlos manualmente en Catálogos, con reintento/actualización periódica y sin bloquear el sistema si el servicio externo falla; (2) categorización visual de los festivos en el calendario en dos niveles — festivo Oficial (nacional, viene de la API) vs. festivo Regional/Religioso no oficial (ej. 'Día de la Virgen del Rosario de Chiquinquirá' en Colombia, que no es festivo nacional pero es una celebración local relevante para el negocio) — cada categoría con su propio color/etiqueta distintivo en el calendario; y (3) mostrar automáticamente los cumpleaños de cada Recurso como evento anual recurrente en la pestaña 'Equipo' del calendario, derivado del campo birth_date ya existente en el perfil del Recurso, distinguido visualmente de los festivos. Corrige además el dato incompleto actual: el calendario de Colombia sembrado como prueba solo tiene 3 festivos (Año Nuevo, Día de la Raza, Navidad) y le falta el 20 de julio (Día de la Independencia) y el resto del calendario oficial colombiano (incluye festivos móviles trasladados a lunes por la Ley Emiliani)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Festivos oficiales siempre completos y actualizados (Priority: P1)

Como Admin o Coordinador, cuando abro el calendario de un Cliente o Recurso configurado en un país determinado, quiero ver la lista completa y correcta de festivos oficiales de ese país para el año en curso (y el siguiente), sin tener que cargarlos manualmente uno por uno ni preocuparme de que se me olvide alguno (como pasó con el 20 de julio en Colombia).

**Why this priority**: Es el problema concreto que motivó esta funcionalidad — los datos manuales quedaron incompletos y desactualizados. Sin esto, el calendario sigue siendo poco confiable para decisiones de disponibilidad y planificación.

**Independent Test**: Se puede probar seleccionando un país nuevo (sin festivos cargados manualmente) y verificando que el calendario se llena automáticamente con el listado oficial completo de ese país, incluyendo el 20 de julio para Colombia.

**Acceptance Scenarios**:

1. **Given** un país sin festivos cargados aún, **When** un usuario abre por primera vez el calendario de un Cliente/Recurso de ese país, **Then** el sistema obtiene y guarda el listado oficial de festivos del año en curso y del siguiente desde la fuente externa, y los muestra en el calendario.
2. **Given** un país cuyos festivos ya fueron sincronizados anteriormente, **When** pasa el tiempo (ej. cambia de año) o se ejecuta la sincronización periódica, **Then** el sistema actualiza automáticamente el listado sin intervención manual.
3. **Given** que la fuente externa de festivos no está disponible en el momento de la sincronización, **When** el sistema intenta actualizar, **Then** reintenta más adelante automáticamente y mientras tanto sigue mostrando el último listado guardado exitosamente (si existe) sin bloquear ninguna otra funcionalidad del sistema (asignación de tickets, aprobación de ausencias, etc.).
4. **Given** un festivo oficial que la fuente externa reporta incorrectamente o que un Admin necesita corregir, **When** el Admin edita o desactiva ese festivo específico desde Maestros, **Then** el cambio manual se respeta y no es sobrescrito por la siguiente sincronización automática.

---

### User Story 2 - Distinguir festivos oficiales de celebraciones regionales/religiosas (Priority: P2)

Como Admin o Coordinador, quiero que el calendario muestre con un color/etiqueta distinto los festivos oficiales (de cumplimiento obligatorio a nivel nacional) frente a celebraciones regionales o religiosas relevantes para el negocio pero que no son festivo nacional (ej. la fiesta patronal de una ciudad), para no confundir un día no laboral real con una fecha simplemente informativa.

**Why this priority**: Evita errores de interpretación al planificar disponibilidad — un festivo oficial afecta la disponibilidad de los recursos (FR existente de spec 020), mientras que una celebración regional/religiosa es solo informativa y no debería tratarse igual.

**Independent Test**: Se puede probar cargando un festivo oficial (ej. Navidad) y uno regional/religioso (ej. la fiesta de Chiquinquirá) para el mismo país y verificando que aparecen con colores/etiquetas distintos en el calendario, y que solo el oficial afecta el cálculo de disponibilidad de un recurso.

**Acceptance Scenarios**:

1. **Given** un festivo con categoría "Oficial", **When** se muestra en el calendario, **Then** aparece con el color/etiqueta de festivo oficial y sigue afectando la disponibilidad del recurso (como ya definía spec 020).
2. **Given** una fecha con categoría "Regional/Religioso" agregada manualmente por un Admin, **When** se muestra en el calendario, **Then** aparece con un color/etiqueta distinto al oficial, identificándose claramente como no oficial, y **no** afecta el cálculo de disponibilidad del recurso al asignar tickets.
3. **Given** un Admin que quiere agregar una celebración regional/religiosa (ej. "Día de la Virgen del Rosario de Chiquinquirá"), **When** la registra manualmente en Maestros, **Then** queda guardada con categoría "Regional/Religioso" y país asociado, disponible para todos los Clientes/Recursos de ese país.

---

### User Story 3 - Cumpleaños del equipo visibles en el calendario (Priority: P3)

Como Admin, Coordinador o miembro del equipo, quiero ver los cumpleaños de mis compañeros en la pestaña "Equipo" del calendario, para tener presente estas fechas sin necesidad de mantenerlas por separado.

**Why this priority**: Es un valor agregado claro pero no crítico para la operación (a diferencia de los festivos oficiales, que sí afectan disponibilidad); por eso queda en tercera prioridad.

**Independent Test**: Se puede probar seleccionando en la pestaña "Equipo" un Recurso con `birth_date` configurado y verificando que aparece un evento anual en esa fecha, distinguible visualmente de los festivos.

**Acceptance Scenarios**:

1. **Given** un Recurso con `birth_date` configurado en su perfil, **When** se selecciona ese Recurso en la pestaña "Equipo" del calendario, **Then** aparece un evento anual recurrente en el día y mes de su cumpleaños (sin importar el año de nacimiento), con un color/ícono distinto al de los festivos.
2. **Given** un Recurso sin `birth_date` configurado, **When** se selecciona en la pestaña "Equipo", **Then** simplemente no aparece ningún evento de cumpleaños para ese recurso, sin error.
3. **Given** un cumpleaños mostrado en el calendario, **When** un usuario lo observa, **Then** puede distinguirlo claramente de un festivo oficial o regional (no debe confundirse con un día no laboral).

---

### Edge Cases

- ¿Qué pasa si la fuente externa de festivos no reconoce el código de país configurado (ej. un país sin cobertura en el servicio)? → El sistema no bloquea nada; el país simplemente queda sin festivos oficiales automáticos, pero un Admin puede seguir agregando festivos oficiales o regionales manualmente para ese país (mismo comportamiento de "país sin festivos" ya tolerado en spec 020).
- ¿Qué pasa si un mismo país tiene un festivo oficial y una celebración regional el mismo día? → Ambos se muestran como eventos independientes en el calendario, cada uno con su propio color/etiqueta.
- ¿Qué pasa si dos Recursos del mismo equipo cumplen años el mismo día? → Ambos eventos se muestran, uno por cada Recurso seleccionado.
- ¿Qué pasa si se corrige manualmente un festivo oficial y luego la fuente externa cambia ese mismo dato en una sincronización futura? → Prevalece la corrección manual (ver Escenario 4 de US1); el sistema no vuelve a sobrescribir un registro editado manualmente.
- ¿Qué pasa si la sincronización automática nunca ha corrido para un país (recién configurado, primer uso)? → Se dispara la sincronización inicial en el momento en que un usuario visualiza el calendario de ese país por primera vez, sin que el usuario tenga que esperar una tarea programada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE obtener automáticamente el listado de festivos oficiales de un país desde una fuente pública externa de festivos, para el año en curso y el siguiente, la primera vez que se necesite el calendario de ese país.
- **FR-002**: El sistema DEBE actualizar periódicamente (de forma automática, sin intervención manual) los festivos oficiales ya sincronizados de los países en uso, para mantenerlos vigentes año a año.
- **FR-003**: El sistema DEBE seguir funcionando con normalidad (asignación de tickets, aprobación de ausencias, visualización de calendarios ya sincronizados) si la fuente externa de festivos no está disponible; el fallo de sincronización NUNCA debe bloquear otra funcionalidad.
- **FR-004**: El sistema DEBE reintentar automáticamente una sincronización fallida en una ejecución posterior, sin requerir que un usuario la dispare manualmente.
- **FR-005**: Cada festivo DEBE tener una categoría: "Oficial" (de cumplimiento nacional, normalmente proveniente de la fuente externa) o "Regional/Religioso" (celebración local o religiosa relevante para el negocio pero sin efecto de día no laboral nacional).
- **FR-006**: El calendario DEBE mostrar cada categoría de festivo con un color/etiqueta visualmente distinto, y esa distinción DEBE ser consistente en todas las vistas del calendario (pestaña Cliente y pestaña Equipo).
- **FR-007**: Solo los festivos de categoría "Oficial" DEBEN afectar el cálculo de disponibilidad de un Recurso al asignar tickets (FR-013 a FR-016 de spec 020); los de categoría "Regional/Religioso" son puramente informativos y no bloquean ni alertan sobre disponibilidad.
- **FR-008**: Un Admin DEBE poder agregar, editar o desactivar manualmente cualquier festivo (Oficial o Regional/Religioso) desde Maestros, igual que hoy.
- **FR-009**: Un festivo Oficial editado o desactivado manualmente por un Admin DEBE conservar ese cambio de forma permanente — la sincronización automática NUNCA debe sobrescribir un registro que ya fue modificado manualmente.
- **FR-010**: Los festivos de categoría "Regional/Religioso" DEBEN crearse siempre de forma manual (la fuente externa solo provee festivos oficiales nacionales).
- **FR-011**: El sistema DEBE mostrar, en la pestaña "Equipo" del calendario, un evento anual recurrente en la fecha de cumpleaños de cada Recurso seleccionado que tenga `birth_date` configurado en su perfil.
- **FR-012**: El evento de cumpleaños DEBE mostrarse cada año en la misma fecha (día y mes), independientemente del año en que se visualice el calendario, y sin exponer ni depender del año de nacimiento para su cálculo.
- **FR-013**: El evento de cumpleaños DEBE distinguirse visualmente (color/etiqueta) tanto de los festivos oficiales como de los regionales/religiosos.
- **FR-014**: Un Recurso sin `birth_date` configurado NO DEBE generar ningún evento de cumpleaños ni error visible en el calendario.
- **FR-015**: El sistema DEBE completar el listado de festivos oficiales de Colombia con el calendario oficial vigente (incluyendo el 20 de julio y los demás festivos de la Ley Emiliani) como parte de esta funcionalidad, ya sea vía la primera sincronización automática o como corrección de datos.

### Key Entities *(include if feature involves data)*

- **Festivo (Holiday, existente — se extiende)**: agrega una categoría (Oficial | Regional/Religioso) y un origen (sincronizado automáticamente | ingresado manualmente), además de los campos ya existentes (país, fecha, nombre, activo).
- **Estado de sincronización por país**: registro interno (por país y año) de la última sincronización exitosa con la fuente externa, usado para decidir cuándo volver a sincronizar y para no bloquear la experiencia del usuario mientras se reintenta.
- **Cumpleaños**: no es una entidad nueva — es un evento de calendario derivado del campo `birth_date` ya existente en el Recurso; no se persiste como registro independiente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al configurar el país de un Cliente o Recurso por primera vez, el calendario de festivos oficiales de ese país aparece completo (sin festivos nacionales faltantes) sin que ningún usuario tenga que cargarlos manualmente uno por uno.
- **SC-002**: El calendario de Colombia incluye el 20 de julio (Día de la Independencia) y el resto del calendario oficial vigente, verificable de inmediato tras desplegar esta funcionalidad.
- **SC-003**: Un usuario puede distinguir a simple vista, sin leer el detalle de cada evento, si una fecha marcada en el calendario es un festivo oficial, una celebración regional/religiosa o un cumpleaños.
- **SC-004**: Una caída o error de la fuente externa de festivos no genera ninguna interrupción visible en la asignación de tickets, aprobación de ausencias u otras funciones del sistema — como máximo, el calendario de festivos de un país recién agregado queda temporalmente vacío hasta el siguiente reintento exitoso.
- **SC-005**: Una corrección manual de un festivo oficial permanece vigente indefinidamente, incluso después de múltiples sincronizaciones automáticas posteriores.
- **SC-006**: Los cumpleaños de los Recursos con `birth_date` configurado son visibles en la pestaña Equipo del calendario sin ninguna configuración adicional por parte del usuario.

## Assumptions

- La fuente pública de festivos (ej. Nager.Date u otra equivalente) cubre al menos los países actualmente en uso en el sistema (Colombia, México) y es de acceso gratuito/sin credenciales, dado que este proyecto no maneja actualmente secretos de integraciones de terceros para este módulo.
- La sincronización periódica reutiliza la infraestructura de tareas en segundo plano ya existente en el proyecto (worker con tareas programadas), sin introducir un mecanismo de scheduling nuevo.
- El alcance de la sincronización automática son los festivos del año en curso y el siguiente; años anteriores no se sincronizan automáticamente (si se necesitan históricamente, se agregan manualmente).
- Un festivo se considera "editado manualmente" desde el momento en que un Admin lo crea a mano o modifica cualquier campo de un festivo previamente sincronizado; a partir de ahí queda excluido de futuras sobrescrituras automáticas.
- La categorización "Regional/Religioso" es de alcance abierto (cualquier fecha relevante para el negocio que un Admin quiera resaltar, no limitada a festividades religiosas), pero nunca se sincroniza automáticamente ni afecta el cálculo de disponibilidad.
- El cumpleaños solo se muestra en la pestaña "Equipo" (por Recurso); no aplica a Clientes, que no tienen `birth_date`.
- Esta funcionalidad depende de que exista conectividad saliente desde el backend hacia la fuente externa de festivos; en entornos sin acceso a internet, el sistema sigue funcionando solo con los festivos ya sincronizados o cargados manualmente (degradación aceptable, ver FR-003).
