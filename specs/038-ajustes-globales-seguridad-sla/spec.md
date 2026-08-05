# Feature Specification: Ajustes Globales — Seguridad/Permisos, Notificaciones, Motor de SLA, Bugs de UI y Rendimiento

**Feature Branch**: `038-ajustes-globales-seguridad-sla`

**Created**: 2026-08-05

**Status**: Draft

**Input**: User description: "Mapeo de Ajustes Globales: Seguridad/Permisos, Notificaciones, Motor de SLA, Corrección de Bugs de UI y Rendimiento — paquete de ajustes, correcciones de errores y optimizaciones: (1) filtro automático "Asignado a mí" para Resolutores en Kanban/Listas/Tareas, vista global de Tickets restringida a Coordinador/Admin, calendario y catálogos maestros acotados para Resolutores, menú lateral colapsable; (2) SLA de Contacto corre hasta "En Análisis", SLA de Resolución corre hasta "Cerrado" (no se detiene en "Resuelto"), historial de auditoría inicial al crear Ticket/Tarea, separación Resolutor/QM; (3) cascada Cliente→Proyecto en formularios, Solicitante obligatorio en Ticket/opcional en Tarea, Descripción obligatoria en Registro de Tiempo; (4) fix botón Copiar Contraseña, notificación/correo de bienvenida HTML con contraseña temporal y link de cambio de 30 minutos; (5) fix parpadeo global de UI, fix de credenciales cruzadas entre pestañas de Accesos y Conexiones del Cliente; (6) optimización de rendimiento del Detalle del Cliente."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vistas acotadas por rol para Resolutores (Priority: P1)

Un Resolutor inicia sesión y, sin configurar nada, ve únicamente los Tickets/Tareas que tiene asignados en Kanban, Listas y Mis Tareas. No puede acceder a la vista global de "Tickets" (reservada a Coordinador/Administrador), su Calendario muestra solo su propia disponibilidad/ausencias, y la aplicación no descarga catálogos maestros administrativos completos en su sesión.

**Why this priority**: Hoy un Resolutor ve datos de todos los clientes/tickets/recursos aunque no le correspondan, lo que expone información innecesaria (de otros clientes/resolutores) y degrada el rendimiento al cargar catálogos que no usa. Es un ajuste de exposición de datos y de carga inicial — la base de todo lo demás.

**Independent Test**: Login como un usuario con rol Resolutor con 2-3 tickets asignados (de un total mayor en el sistema) y verificar que Kanban/Listas/Mis Tareas muestran solo esos, que "Tickets" no aparece en el menú (o redirige), que el Calendario solo muestra su propio recurso, y que no se disparan peticiones de catálogos maestros completos al cargar la sesión.

**Acceptance Scenarios**:

1. **Given** un usuario con rol Resolutor con tickets asignados, **When** inicia sesión y abre Kanban, **Then** el tablero muestra por defecto solo los tickets/tareas asignados a él, sin que tenga que aplicar el filtro manualmente.
2. **Given** el mismo usuario, **When** abre "Mis Tareas"/Listas, **Then** ve el mismo criterio de "Asignado a mí" aplicado por defecto.
3. **Given** el mismo usuario, **When** intenta navegar a la vista global de "Tickets", **Then** el sistema le niega el acceso (opción no visible en el menú y ruta protegida).
4. **Given** un usuario con rol Coordinador o Administrador, **When** inicia sesión, **Then** conserva acceso a la vista global de "Tickets" sin ningún filtro aplicado por defecto (comportamiento actual sin cambios).
5. **Given** un usuario con rol Resolutor, **When** abre el Calendario, **Then** solo ve su propio calendario/franja laboral/ausencias, no las de otros recursos o equipos.
6. **Given** un usuario con rol Resolutor, **When** navega por la aplicación, **Then** el sistema no precarga los catálogos administrativos completos (Clientes, Herramientas, Procesos, Tipos de resolución, Equipos, Tipos de acceso) salvo que una pantalla puntual a la que sí tiene acceso los necesite de forma acotada (p. ej. el selector de Cliente/Proyecto al crear un ticket).
7. **Given** cualquier usuario, **When** hace clic en el control de colapsar del menú lateral, **Then** el menú se reduce a solo iconos y puede volver a expandirse al interactuar con él o seleccionar una opción.

---

### User Story 2 - Motor de SLA corregido y auditoría inicial (Priority: P1)

Coordinador/Admin/QM necesitan que los tiempos de SLA mostrados reflejen la realidad operativa: el SLA de Contacto debe reflejar cuánto tarda el equipo en empezar a analizar el caso (no solo en asignarlo), y el SLA de Resolución/Cierre debe seguir corriendo mientras el ticket espera confirmación del cliente en estado "Resuelto", deteniéndose solo cuando se cierra formalmente. Además, todo Ticket/Tarea debe dejar un rastro de auditoría desde el instante en que se crea.

**Why this priority**: El cómputo de SLA es la base de los compromisos contractuales con clientes (specs `014`/`019`/`022`/`023`); un cómputo incorrecto genera reportes de cumplimiento falsos. La falta de una entrada inicial en el historial rompe la trazabilidad completa de un ticket desde su origen.

**Independent Test**: Crear un ticket de prueba, asignarlo, y verificar en su Historial de Estados que (a) existe una entrada inicial de creación, (b) el contador de SLA de Contacto sigue corriendo mientras el ticket está en estado "Contacto" (ya asignado, aún sin iniciar el análisis) y se congela justo al pasar a "En Análisis", y (c) al llevarlo a "Resuelto" el contador de SLA de Resolución sigue activo (no aparece como "detenido") hasta que se marca "Cerrado".

**Acceptance Scenarios**:

1. **Given** un Ticket recién creado, **When** se consulta su Historial de Estados, **Then** existe una primera entrada que indica la creación del Ticket en su estado inicial ("Nuevo"), con fecha/hora y usuario creador.
2. **Given** una Tarea recién creada, **When** se consulta su Historial de Estados, **Then** existe la misma entrada inicial de auditoría.
3. **Given** un Ticket que acaba de ser asignado (pasa a "Contacto") pero el resolutor aún no ha iniciado el análisis, **When** se consulta el estado de su SLA de Contacto, **Then** el contador sigue corriendo (no está congelado).
4. **Given** ese mismo Ticket, **When** el resolutor lo transiciona a "En Análisis", **Then** el SLA de Contacto se congela en ese instante y su resultado (cumplido/vencido) queda fijo a partir de ahí.
5. **Given** un Ticket con SLA de Resolución activo, **When** pasa a estado "Resuelto", **Then** el contador de SLA de Resolución continúa corriendo (respetando horario hábil/disponibilidad), sin mostrarse como "detenido".
6. **Given** ese mismo Ticket, **When** pasa a estado "Cerrado", **Then** el contador de SLA de Resolución se congela definitivamente en ese instante y su resultado queda fijo.
7. **Given** un Ticket "Resuelto" que es rechazado y vuelve a "En Ejecución" (`reject_resolution`), **When** se consulta su SLA de Resolución, **Then** el contador retoma sin reiniciarse ni perder el tiempo ya consumido.
8. **Given** los roles Resolutor y QM, **When** se revisan sus permisos, **Then** el Resolutor puede ejecutar/actualizar tickets asignados y el QM puede evaluarlos/aprobarlos, sin que ninguno de los dos herede automáticamente las capacidades del otro.

---

### User Story 3 - Corrección de bugs críticos de UI (Priority: P1)

Los usuarios reportan dos problemas que afectan la confiabilidad de la interfaz: (a) un parpadeo (flickering) que ahora afecta también al menú lateral y a componentes principales, no solo al detalle de Ticket/Tarea; y (b) al editar varios tipos de acceso/credencial en la pestaña "Accesos y conexiones" del detalle de un Cliente, los datos escritos en un tipo de acceso terminan guardándose sobre otro tipo distinto.

**Why this priority**: El bug de credenciales cruzadas es un problema de integridad de datos (se puede sobrescribir sin querer la contraseña de un acceso VPN con la de un acceso a base de datos, por ejemplo) — el de mayor riesgo de todo el paquete. El parpadeo generalizado degrada la percepción de estabilidad de toda la aplicación.

**Independent Test**: (a) Reproducir el flujo ya conocido de scroll/interacción que antes causaba parpadeo en Ticket/Tarea y confirmar que el menú lateral y los componentes principales permanecen estables. (b) Abrir el detalle de un Cliente con 2+ tipos de acceso distintos, editar las credenciales de uno, cambiar a otro tipo y editar sus credenciales, guardar, y confirmar que cada tipo conserva sus propios datos sin mezclarse.

**Acceptance Scenarios**:

1. **Given** el detalle de un Ticket/Tarea abierto, **When** el usuario hace scroll o interactúa con la pantalla, **Then** el menú lateral y los componentes principales de la interfaz no parpadean ni cambian de tamaño de forma errática.
2. **Given** un Cliente con 2 o más tipos de acceso configurados (p. ej. VPN y Base de datos), **When** el usuario edita las credenciales del primer tipo y luego abre y edita las del segundo tipo, **Then** al guardar, cada tipo de acceso conserva únicamente los datos que le corresponden.
3. **Given** el mismo escenario, **When** el usuario vuelve a abrir el primer tipo de acceso tras haber editado el segundo, **Then** sus datos originales (no modificados) siguen intactos.

---

### User Story 4 - Cascada y campos obligatorios en formularios (Priority: P2)

Al elegir un Cliente en cualquier formulario que dependa de esa relación, el selector de Proyecto debe limitarse a los proyectos de ese Cliente. Además, se refuerzan dos campos que hoy pueden quedar vacíos por error: el Usuario/cliente solicitante en un Ticket (obligatorio, no así en una Tarea) y la Descripción de la actividad en un Registro de tiempo (obligatoria siempre).

**Why this priority**: Reduce errores de captura (proyectos de otro cliente, tickets sin solicitante, tiempos sin descripción que luego no se pueden auditar), pero no bloquea operación crítica del día a día como sí lo hacen las US1-3.

**Independent Test**: En cualquier formulario con selección de Cliente y Proyecto, cambiar el Cliente y verificar que el listado de Proyecto se acota; intentar guardar un Ticket sin solicitante y una Tarea sin solicitante (el primero debe bloquear, el segundo no); intentar guardar un Registro de tiempo sin descripción y verificar que se bloquea.

**Acceptance Scenarios**:

1. **Given** un formulario con selección de Cliente y Proyecto, **When** el usuario selecciona un Cliente, **Then** el selector de Proyecto solo ofrece los proyectos de ese Cliente.
2. **Given** ese mismo formulario, **When** el usuario cambia de Cliente habiendo ya elegido un Proyecto de otro Cliente, **Then** la selección de Proyecto se limpia.
3. **Given** el formulario de creación de Ticket, **When** el usuario intenta guardar sin elegir Usuario/cliente solicitante, **Then** el sistema bloquea el guardado y señala el campo como requerido.
4. **Given** el formulario de creación de Tarea, **When** el usuario guarda sin elegir Usuario/cliente solicitante, **Then** el sistema permite guardar sin error.
5. **Given** el modal/pantalla de Registro de Tiempo, **When** el usuario intenta guardar sin escribir una Descripción, **Then** el sistema bloquea el guardado y señala el campo como requerido.

---

### User Story 5 - Gestión de usuarios: copiar contraseña y correo de bienvenida (Priority: P2)

Al crear o resetear la cuenta de un usuario, quien administra el sistema puede copiar la contraseña provisional al portapapeles de forma confiable, y opcionalmente notificar al usuario por correo institucional con un mensaje de bienvenida, la URL de acceso, su contraseña temporal y un enlace para cambiarla, válido solo por 30 minutos.

**Why this priority**: Es una mejora operativa de onboarding, valiosa pero no bloqueante — hoy existe una vía alterna (compartir la contraseña visible en pantalla manualmente y el flujo ya existente de "¿Olvidaste tu contraseña?").

**Independent Test**: Crear un usuario de prueba marcando "Notificar al Usuario", confirmar que llega un correo HTML con logo, aviso de mensaje automatizado, aviso de tratamiento de datos, URL de login, contraseña temporal y enlace de cambio; confirmar que ese enlace deja de funcionar pasados 30 minutos. Por separado, usar el botón "Copiar Contraseña" y pegar el contenido del portapapeles para confirmar que coincide.

**Acceptance Scenarios**:

1. **Given** la pantalla de creación/gestión de usuarios con una contraseña provisional visible, **When** el administrador hace clic en "Copiar Contraseña", **Then** el valor exacto queda disponible en el portapapeles del sistema operativo.
2. **Given** un fallo al copiar (p. ej. navegador sin permiso de portapapeles), **When** ocurre el fallo, **Then** el sistema informa claramente que no se pudo copiar (no muestra un mensaje de éxito falso).
3. **Given** el formulario de creación de un usuario nuevo, **When** el administrador marca la opción "Notificar al Usuario" y guarda, **Then** se envía un correo institucional en HTML al correo del nuevo usuario con: mensaje de bienvenida, URL de login, contraseña temporal y enlace de cambio de contraseña.
4. **Given** ese correo enviado, **When** el usuario abre el enlace de cambio de contraseña dentro de los 30 minutos, **Then** puede definir su contraseña normalmente.
5. **Given** ese mismo correo, **When** el usuario abre el enlace después de 30 minutos, **Then** el sistema rechaza el enlace con un mensaje claro de expiración (sin exponer la contraseña temporal ni datos sensibles).
6. **Given** el formulario de creación de un usuario nuevo, **When** el administrador NO marca "Notificar al Usuario", **Then** la cuenta se crea igual, sin enviar correo (comportamiento actual).
7. **Given** un fallo del servidor de correo al intentar notificar, **When** ocurre, **Then** la cuenta del usuario queda creada igualmente y el administrador recibe aviso de que el correo no pudo enviarse.

---

### User Story 6 - Rendimiento del Detalle del Cliente (Priority: P3)

Al abrir "Ver detalle de cliente", la pantalla carga de forma notablemente más rápida, sin peticiones redundantes ni recálculos de interfaz innecesarios, incluso para clientes con historial extenso de accesos/proyectos/contactos.

**Why this priority**: Es una mejora de percepción y productividad, no corrige un error funcional ni de seguridad — se aborda al final del paquete.

**Independent Test**: Abrir el detalle de un cliente con datos abundantes (varios accesos, proyectos, contactos) antes y después del cambio, comparando el tiempo hasta que la pantalla es interactiva y el número de peticiones de red disparadas.

**Acceptance Scenarios**:

1. **Given** un Cliente con historial extenso (accesos, proyectos, contactos), **When** el usuario abre su detalle, **Then** el contenido principal se muestra de forma notablemente más rápida que antes del cambio.
2. **Given** el detalle de un Cliente ya abierto, **When** el usuario cambia entre sus pestañas internas, **Then** los datos de una pestaña pesada no se cargan hasta que el usuario la visita.
3. **Given** el detalle de un Cliente abierto, **When** se inspecciona la actividad de red, **Then** no se repiten peticiones idénticas innecesarias durante la misma sesión de vista.

---

### Edge Cases

- Un Resolutor sin ningún ticket/tarea asignado ve Kanban/Listas/Mis Tareas vacíos (no un error ni un listado completo por defecto).
- Un usuario cambia de rol (p. ej. de Resolutor a Coordinador): el nuevo nivel de acceso a la vista global de Tickets debe reflejarse en su siguiente sesión/carga de permisos, sin requerir intervención manual en base de datos.
- Un Ticket es cancelado (`cancelado`) en vez de resuelto/cerrado: el SLA de Resolución se congela igual que hoy, sin cambios respecto al comportamiento de las specs `014`/`023`/`033`.
- Un correo de bienvenida no puede enviarse por configuración SMTP ausente/incorrecta: el alta del usuario no debe fallar por esto.
- El enlace de cambio de contraseña del correo de bienvenida se reutiliza dos veces dentro de la ventana de 30 minutos: la segunda vez, si la contraseña ya fue cambiada, el sistema lo rechaza igual que cualquier token ya consumido (mismo patrón que el flujo existente de "¿Olvidaste tu contraseña?").
- Un formulario con Cliente y Proyecto donde el Cliente aún no fue elegido: el selector de Proyecto aparece vacío o deshabilitado, no con la lista completa.
- Un Ticket que nunca pasa por "En Análisis" y se cancela directamente desde "Contacto": el SLA de Contacto se congela igual como "vencido" o "cumplido" según corresponda al momento de la cancelación, sin quedar corriendo indefinidamente.
- Un usuario con permisos de administración (Admin/Coordinador) revisa el calendario de un Resolutor: sigue viendo el calendario de equipo/superpuesto existente sin restricciones (la restricción de "solo mi calendario" aplica al propio Resolutor consultando su sesión, no a quien administra).

## Requirements *(mandatory)*

### Functional Requirements

**Vistas y accesos por rol**

- **FR-001**: El sistema DEBE aplicar por defecto el filtro "Asignado a mí" en Kanban, Listas de tareas y Mis Tareas cuando el usuario autenticado tiene rol Resolutor, sin exigir que lo configure manualmente.
- **FR-002**: El sistema DEBE permitir que Coordinador y Administrador continúen viendo Kanban/Listas/Mis Tareas sin ningún filtro de asignación aplicado por defecto (sin cambios respecto al comportamiento actual).
- **FR-003**: El sistema DEBE restringir el acceso a la vista global de "Tickets" (listado completo, sin acotar a un ticket o tarea puntual) únicamente a usuarios con rol Coordinador o Administrador.
- **FR-004**: El sistema DEBE ocultar la opción de menú hacia la vista global de "Tickets" para cualquier usuario que no tenga rol Coordinador o Administrador, y bloquear el acceso directo por URL para esos usuarios.
- **FR-005**: El sistema DEBE limitar la vista de Calendario de un usuario con rol Resolutor a su propio calendario/franja laboral/ausencias, sin exponer el calendario de otros recursos o el calendario de equipo superpuesto.
- **FR-006**: El sistema DEBE evitar cargar catálogos maestros administrativos completos (Clientes, Herramientas, Procesos, Tipos de resolución, Equipos, Tipos de acceso, y equivalentes) en la sesión de un usuario que no tenga permisos de administración sobre esos catálogos.
- **FR-007**: El sistema DEBE ofrecer un modo colapsado del menú lateral (solo iconos) disponible para todos los usuarios, activable/desactivable mediante un control visible.
- **FR-008**: El sistema DEBE expandir el menú lateral colapsado al interactuar con él (pasar el cursor, hacer clic) o al seleccionar una opción de navegación.

**Motor de SLA y auditoría**

- **FR-009**: El sistema DEBE mantener el contador de SLA de Contacto corriendo desde la creación/asignación del Ticket hasta que este pasa al estado "En Análisis" (incluyendo el tiempo en que el ticket ya fue asignado pero el resolutor aún no inició el análisis).
- **FR-010**: El sistema DEBE congelar el resultado del SLA de Contacto (cumplido/vencido) en el instante en que el Ticket pasa a "En Análisis", y no antes.
- **FR-011**: El sistema DEBE mantener el contador de SLA de Resolución activo (respetando horario hábil/disponibilidad del recurso) mientras el Ticket permanece en estado "Resuelto", sin mostrarlo como detenido.
- **FR-012**: El sistema DEBE congelar el resultado del SLA de Resolución únicamente cuando el Ticket pasa a estado "Cerrado" (o a un estado final equivalente ya congelado hoy, como "Cancelado").
- **FR-013**: El sistema DEBE, si un Ticket "Resuelto" es rechazado y regresa a un estado de ejecución, seguir acumulando el tiempo de SLA de Resolución sin reiniciar ni perder el tiempo ya consumido antes del rechazo.
- **FR-014**: El sistema DEBE registrar automáticamente, al crear un Ticket o una Tarea, una primera entrada en su Historial de Estados que indique el evento de creación y el estado inicial asignado.
- **FR-015**: El sistema DEBE mantener las capacidades de los roles Resolutor (ejecución de tickets asignados) y QM (evaluación de calidad) diferenciadas, sin que este paquete de cambios fusione o amplíe implícitamente los permisos de uno sobre el otro.

**Formularios y validaciones**

- **FR-016**: El sistema DEBE, en todo formulario donde se seleccione Cliente y Proyecto, acotar las opciones del selector de Proyecto a los proyectos que pertenecen al Cliente ya seleccionado.
- **FR-017**: El sistema DEBE limpiar la selección de Proyecto vigente cuando el usuario cambia de Cliente y el Proyecto previamente elegido ya no pertenece al nuevo Cliente.
- **FR-018**: El sistema DEBE exigir la selección de un Usuario/cliente solicitante al crear un Ticket, bloqueando el guardado si se omite.
- **FR-019**: El sistema DEBE permitir crear una Tarea sin Usuario/cliente solicitante (campo opcional).
- **FR-020**: El sistema DEBE exigir una Descripción no vacía al registrar tiempo (Registro de Tiempo), bloqueando el guardado si se omite.

**Gestión de usuarios y notificaciones**

- **FR-021**: El sistema DEBE copiar el valor exacto de la contraseña provisional mostrada al portapapeles del sistema operativo cuando el administrador usa el botón "Copiar Contraseña".
- **FR-022**: El sistema DEBE informar al administrador de forma explícita cuando la operación de copiar al portapapeles no pudo completarse, sin mostrar una confirmación de éxito falsa.
- **FR-023**: El sistema DEBE ofrecer, al crear una cuenta de usuario nueva, la opción "Notificar al Usuario" para enviarle un correo de bienvenida.
- **FR-024**: El sistema DEBE, cuando se activa "Notificar al Usuario", enviar un correo electrónico en formato HTML que incluya: logo institucional, mensaje de bienvenida, URL de inicio de sesión, contraseña temporal, un enlace para cambiar la contraseña, aviso de que es un mensaje automatizado y una nota sobre las políticas de tratamiento de datos.
- **FR-025**: El sistema DEBE limitar la validez del enlace de cambio de contraseña del correo de bienvenida a 30 minutos desde su envío, rechazando su uso posterior con un mensaje claro.
- **FR-026**: El sistema DEBE crear la cuenta de usuario correctamente incluso si el envío del correo de bienvenida falla, informando del fallo de envío sin bloquear el alta.

**Corrección de bugs de UI**

- **FR-027**: El sistema DEBE evitar el parpadeo (cambios de tamaño/posición erráticos) del menú lateral y de los componentes principales de la interfaz durante el scroll o la interacción normal en las vistas de Ticket/Tarea.
- **FR-028**: El sistema DEBE mantener aislados entre sí los datos capturados para cada tipo de acceso/credencial en la pestaña "Accesos y conexiones" del detalle de un Cliente, de forma que editar un tipo no sobrescriba ni mezcle los datos de otro tipo ya guardado.

**Rendimiento**

- **FR-029**: El sistema DEBE reducir el tiempo de carga percibido de la pantalla "Ver detalle de cliente" para clientes con historial extenso de accesos/proyectos/contactos, respecto al comportamiento actual.
- **FR-030**: El sistema DEBE evitar peticiones de red redundantes o recálculos de interfaz innecesarios mientras la pantalla "Ver detalle de cliente" permanece abierta en la misma sesión de vista.

### Key Entities

- **Entrada de auditoría inicial**: primer registro del Historial de Estados de un Ticket/Tarea, generado automáticamente en el momento de su creación; documenta el estado inicial y quién lo creó.
- **Correo de bienvenida**: comunicación institucional enviada opcionalmente al crear un usuario; contiene mensaje de bienvenida, URL de acceso, contraseña temporal y un enlace de cambio de contraseña con vigencia de 30 minutos.
- **Preferencia de menú colapsado**: estado de presentación del menú lateral (expandido/colapsado) por sesión de usuario.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los usuarios con rol Resolutor ven, al iniciar sesión, únicamente los tickets/tareas asignados a ellos en Kanban/Listas/Mis Tareas sin configurar ningún filtro manualmente.
- **SC-002**: El 100% de los intentos de un usuario sin rol Coordinador/Administrador de acceder a la vista global de "Tickets" (por menú o por URL directa) son bloqueados.
- **SC-003**: El tiempo de SLA de Contacto reportado para un ticket de prueba coincide, con un margen menor a 1 minuto, con el intervalo real entre su asignación y su paso a "En Análisis".
- **SC-004**: El 100% de los tickets llevados a "Resuelto" en una prueba muestran su SLA de Resolución como "corriendo" (no "detenido") mientras están en ese estado, y como "congelado" solo tras pasar a "Cerrado".
- **SC-005**: El 100% de los Tickets/Tareas creados en una prueba muestran al menos una entrada en su Historial de Estados inmediatamente después de guardarse.
- **SC-006**: El botón "Copiar Contraseña" deposita el valor correcto en el portapapeles en el 100% de los intentos realizados en un navegador soportado.
- **SC-007**: El 100% de los correos de bienvenida enviados en una prueba llegan con formato HTML, logo, y un enlace de cambio de contraseña que deja de funcionar después de 30 minutos.
- **SC-008**: Editar y guardar 2 tipos de acceso distintos de un mismo Cliente en una prueba no produce ninguna mezcla de datos entre ellos, verificado releyendo ambos tipos tras guardar.
- **SC-009**: Una prueba de scroll/interacción continua de 10 segundos en el detalle de un Ticket/Tarea no produce parpadeo visible del menú lateral ni de los componentes principales.
- **SC-010**: El tiempo hasta que "Ver detalle de cliente" es interactivo para un cliente con historial extenso se reduce de forma perceptible (evaluado antes/después con el mismo cliente de prueba).
- **SC-011**: El 100% de los formularios con selección de Cliente y Proyecto acotan el selector de Proyecto a los proyectos del Cliente elegido.
- **SC-012**: El 100% de los intentos de guardar un Registro de Tiempo sin Descripción son bloqueados por el sistema.

## Assumptions

- El rol QM queda fuera de la vista global de "Tickets" bajo la misma restricción que aplica a Resolutor (la instrucción original solo exceptúa explícitamente a Coordinador y Administrador); sus pantallas dedicadas ya existentes (Panel de Asignación/Pre-Análisis, Reportes) no se ven afectadas por este cambio, ya que son rutas y permisos independientes.
- El nuevo comportamiento del SLA de Resolución (correr hasta "Cerrado" en vez de congelarse en "Resuelto") reemplaza específicamente el congelamiento que hoy ocurre al entrar a "Resuelto" (specs `014`/`023`/`033`); el congelamiento al entrar a "Cancelado" se mantiene sin cambios, ya que ese estado sigue siendo final e irreversible.
- La opción "Notificar al Usuario" es un checkbox opcional en el formulario de alta de usuario, con valor por defecto desactivado, para no cambiar el comportamiento actual de quienes no la usen.
- El envío de correo reutiliza el mecanismo institucional de correo ya existente (usado hoy para el reseteo de contraseña), extendido con una plantilla HTML de bienvenida; no se introduce un proveedor de correo nuevo.
- "No cargar catálogos maestros globales en la sesión de usuarios sin permisos de administración" se refiere a listados administrativos completos (pantallas de Maestros/Catálogos); los datos acotados que un Resolutor sí necesita para trabajar (p. ej. el Cliente/Proyecto de sus propios tickets) siguen disponibles de forma puntual y filtrada.
- El modo colapsado del menú lateral es una preferencia de presentación por sesión de navegador (no requiere persistirse en el servidor ni sincronizarse entre dispositivos).
- La restricción del calendario de un Resolutor a "solo el propio" aplica a lo que el Resolutor ve de sí mismo; los roles con permisos de administración (Admin/Coordinador/RRHH) conservan el calendario de equipo superpuesto ya existente (specs `020`-`022`) sin cambios.
- Los formularios afectados por la cascada Cliente→Proyecto son todos los que hoy permiten elegir ambos campos en la aplicación (Ticket/Tarea ya migrado en spec `035`; se extiende el mismo criterio a cualquier otro formulario existente con esa combinación, p. ej. filtros de SLA Configurable o Reportes).
