# Feature Specification: Accesos y conexiones múltiples del Cliente

**Feature Branch**: `018-cliente-accesos-conexiones`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "Rediseñar la gestión de accesos/conexiones (VPN, URLs por ambiente, escritorio remoto) del Cliente en el módulo Maestros > Clientes, resolviendo OBS-0001 (ITER-001), OBS-0008 (ITER-002) y OBS-0017 (ITER-003) del framework UAT (`UAT/02_Backlog/BACKLOG.md`)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar múltiples accesos y conexiones de un cliente (Priority: P1)

Quien administra un cliente necesita dejar constancia de todos sus accesos técnicos reales: distintos usuarios VPN, URLs de sistema por ambiente (DEV/TEST/PROD) cada una con su propio usuario y contraseña, IP o nombre de escritorio remoto con sus propias credenciales, y en algunos casos un archivo con el instructivo de instalación/configuración. Hoy solo existen dos campos de texto simple que no alcanzan para representar esa realidad.

**Why this priority**: Es el corazón del rediseño (`OBS-0001`) — sin esto, el resto de la funcionalidad (aislamiento entre clientes, enmascarado) no tiene nada nuevo que proteger. Sin esta capacidad, el equipo sigue registrando esta información fuera del sistema (chats, documentos sueltos), con el riesgo de pérdida y desactualización que eso implica.

**Independent Test**: Puede probarse completamente creando un cliente y agregando tres registros de acceso de tipos distintos (VPN, URL de sistema en DEV, Escritorio remoto), cada uno con su propio usuario/contraseña, y verificando que los tres persisten de forma independiente al reabrir el cliente.

**Acceptance Scenarios**:

1. **Given** un cliente sin ningún acceso registrado, **When** el usuario agrega un registro de tipo "VPN" con usuario, contraseña, IP y notas, **Then** el registro queda guardado y visible al reabrir la edición del cliente.
2. **Given** un cliente con un registro de acceso ya guardado, **When** el usuario agrega un segundo registro de tipo "URL de sistema" con ambiente "TEST", **Then** ambos registros coexisten y se muestran por separado, sin que uno sobrescriba al otro.
3. **Given** un registro de acceso existente, **When** el usuario lo edita o lo elimina, **Then** el cambio afecta únicamente a ese registro y los demás registros del mismo cliente permanecen intactos.
4. **Given** un cliente con datos que antes vivían en los campos "IPs VPN" y "Credenciales VPN", **When** se despliega este cambio, **Then** esa información aparece migrada como un registro de acceso inicial (tipo VPN), sin que el cliente pierda lo que ya tenía cargado.
5. **Given** un registro de acceso, **When** el usuario adjunta uno o varios archivos (ej. instructivo de instalación), **Then** los archivos quedan asociados al cliente y pueden descargarse posteriormente desde la misma pantalla.
6. **Given** el usuario está viendo el detalle o edición de un cliente, **When** navega a la sección de accesos y conexiones, **Then** la encuentra en un espacio propio (pestaña separada) con una tabla amplia y horizontal — no un formulario angosto apilado junto a los demás campos del cliente.
7. **Given** un registro de acceso nuevo o modificado, **When** el usuario lo guarda, **Then** la operación se confirma de inmediato para ese registro, sin depender de que el usuario guarde también el resto de los datos del cliente (nombre, contacto, facturación) en la misma acción.

---

### User Story 2 - Ver únicamente los accesos del cliente que se está editando (Priority: P1)

Al editar un cliente y luego abrir la edición de otro cliente distinto, hoy los campos de VPN muestran información del cliente anterior (`OBS-0008`) — un defecto de aislamiento de datos que se debe evitar explícitamente al construir el nuevo modelo de accesos múltiples, no solo corregir en el campo simple actual.

**Why this priority**: Es un defecto de integridad de datos con impacto directo en confianza del usuario y riesgo de que alguien actúe sobre credenciales del cliente equivocado. Debe validarse como parte del mismo esfuerzo que introduce el nuevo modelo, para no reintroducirlo.

**Independent Test**: Puede probarse abriendo la edición del Cliente A (con accesos cargados), cerrando el formulario, y abriendo inmediatamente la edición del Cliente B (con accesos distintos o sin accesos) — B debe mostrar solo lo suyo.

**Acceptance Scenarios**:

1. **Given** el Cliente A tiene accesos cargados y se abrió su edición, **When** el usuario cierra esa edición y abre la edición del Cliente B, **Then** el formulario del Cliente B muestra únicamente los accesos propios de B (o ninguno, si no tiene).
2. **Given** una secuencia de ediciones consecutivas entre tres o más clientes distintos en la misma sesión de navegador, **When** se abre la edición de cada uno, **Then** en ningún momento se observan accesos de un cliente distinto al que se está editando.

---

### User Story 3 - Ocultar por defecto la información sensible de los accesos (Priority: P2)

En el formulario de creación/edición, los datos sensibles se muestran hoy en texto plano (`OBS-0017`), a la vista de cualquiera que mire la pantalla — inconsistente con el modal de Detalle del cliente, que ya enmascara esos mismos datos y exige una acción explícita para revelarlos.

**Why this priority**: Es una exposición de datos sensibles innecesaria (postura de seguridad), pero de menor severidad que perder datos (US1) o mezclarlos entre clientes (US2): aquí el dato es correcto, solo está expuesto de más.

**Independent Test**: Puede probarse abriendo el formulario de edición de un cliente con contraseñas cargadas en sus accesos y verificando que aparecen enmascaradas por defecto, con un control para revelarlas.

**Acceptance Scenarios**:

1. **Given** un registro de acceso con contraseña cargada, **When** el usuario abre el formulario de creación/edición del cliente, **Then** la contraseña se muestra enmascarada por defecto, igual que ya ocurre en el modal de Detalle.
2. **Given** una contraseña enmascarada en el formulario, **When** el usuario acciona el control de revelado, **Then** el valor real se muestra en texto claro mientras el control permanece activo.
3. **Given** un usuario sin permiso para ver datos sensibles del cliente, **When** abre el formulario de edición, **Then** puede ver que existen registros de acceso (tipo, ambiente) pero no puede revelar usuario/contraseña.

---

### Edge Cases

- ¿Qué pasa si un cliente no tiene ningún registro de acceso? Debe ser un estado válido (lista vacía), no un error ni un registro fantasma.
- ¿Qué pasa si un cliente tenía los campos "IPs VPN"/"Credenciales VPN" vacíos antes del cambio? No debe crearse un registro de acceso vacío al migrar.
- ¿Qué pasa si se intenta adjuntar un archivo de tipo o tamaño no permitido? El sistema debe rechazarlo con un mensaje claro, igual que ya ocurre con adjuntos en otras partes de la aplicación.
- ¿Qué pasa si se elimina el único registro de acceso de un cliente? El cliente debe quedar sin accesos (no es un estado bloqueado).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir registrar, para cada cliente, cero o más "accesos y conexiones", cada uno con: tipo de acceso (VPN / URL de sistema / Escritorio remoto), ambiente (DEV/TEST/PROD, aplicable cuando el tipo es "URL de sistema"), usuario, contraseña, IP/URL/host y notas.
- **FR-002**: El sistema MUST permitir crear, editar y eliminar cada registro de acceso de forma independiente, sin afectar a los demás registros del mismo cliente.
- **FR-003**: El sistema MUST permitir adjuntar uno o más archivos por cliente (ej. instructivos de instalación/configuración), asociados a su sección de accesos y conexiones.
- **FR-004**: El sistema MUST mostrar, al abrir la edición de un cliente, únicamente los registros de acceso pertenecientes a ese cliente — sin importar qué otro cliente se haya editado inmediatamente antes en la misma sesión de navegador.
- **FR-005**: El sistema MUST enmascarar por defecto el valor de "contraseña" de cada registro de acceso, tanto en el formulario de creación/edición como en el modal de Detalle, y MUST ofrecer un control explícito para revelarlo bajo demanda.
- **FR-006**: El control de revelado de datos sensibles MUST regirse por el mismo permiso que ya determina la visibilidad de datos sensibles del cliente (el que hoy habilita el "ojito" en el modal de Detalle) — no se introduce un permiso nuevo.
- **FR-007**: El sistema MUST migrar automáticamente, sin intervención manual del usuario, los valores ya cargados en "IPs VPN" y "Credenciales VPN" de cada cliente existente a un registro de acceso inicial de tipo "VPN", sin pérdida de la información previamente capturada.
- **FR-008**: El sistema MUST seguir permitiendo consultar, tras la migración, toda la información de VPN que ya era visible en el modal de Detalle antes del cambio.
- **FR-009**: El sistema MUST tratar "cliente sin ningún acceso registrado" como un estado válido, no como un error ni como un registro vacío implícito.
- **FR-010**: Un usuario sin permiso de datos sensibles MUST poder ver que existen registros de acceso (tipo, ambiente) sin poder revelar usuario/contraseña de ninguno de ellos.
- **FR-011**: La sección de accesos y conexiones MUST presentarse en un espacio propio (pestaña separada) dentro de la vista del cliente, con un área de listado más amplia y de disposición horizontal que las demás secciones del cliente (no un formulario angosto apilado).
- **FR-012**: Crear, editar o eliminar un registro de acceso MUST poder confirmarse de inmediato, sin exigir que el usuario guarde en la misma acción el resto de los datos del cliente (nombre, contacto, facturación).

### Key Entities

- **Acceso y conexión (de Cliente)**: representa una vía de conexión al ambiente técnico de un cliente. Atributos: tipo (VPN / URL de sistema / Escritorio remoto), ambiente (opcional, aplica a URL de sistema), usuario, contraseña, IP/URL/host, notas. Pertenece a exactamente un cliente; un cliente puede tener cero o más.
- **Adjunto de accesos**: archivo (ej. instructivo de instalación/configuración) asociado a la sección de accesos y conexiones de un cliente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede registrar accesos de un cliente de los tres tipos (VPN, URL de sistema, Escritorio remoto) y de múltiples ambientes en una misma sesión de edición, sin tope artificial de cantidad de registros.
- **SC-002**: En el 100% de las secuencias de edición consecutiva entre dos o más clientes distintos, cada formulario muestra únicamente los accesos propios del cliente que se está editando.
- **SC-003**: Las contraseñas de los accesos permanecen ocultas por defecto en el 100% de las pantallas donde se muestran (creación, edición y detalle), y solo se revelan tras una acción explícita de un usuario con permiso.
- **SC-004**: El 100% de los clientes que tenían datos en "IPs VPN"/"Credenciales VPN" antes del cambio conservan esa información accesible después de la migración.

## Assumptions

- El permiso que ya existe para ver datos sensibles del cliente (usado hoy en el "ojito" del modal de Detalle) es el que gobierna también el revelado en el formulario de creación/edición; no se crea un permiso nuevo.
- Los adjuntos de la sección de accesos y conexiones reutilizan los mismos límites de tipo y tamaño de archivo ya vigentes para adjuntos en otras partes de la aplicación, salvo que se decida lo contrario durante la planificación técnica.
- La migración de datos existentes crea, por cada cliente que tuviera algo cargado en "IPs VPN" y/o "Credenciales VPN", un único registro de acceso de tipo "VPN" con esos valores; si ambos campos estaban vacíos, no se crea ningún registro.
- Este cambio no introduce roles ni permisos nuevos: reutiliza el control de acceso por módulo "Clientes" ya existente.
- Queda fuera de alcance de este spec el mecanismo de cifrado en base de datos de estos campos (asunto de infraestructura ya existente, no introducido ni modificado por este cambio).
- La sección de accesos y conexiones no necesita compartir modal ni acción de guardado con el resto de los datos del cliente: puede vivir en su propia pestaña, con altas/ediciones/eliminaciones independientes de la operación "Guardar" del formulario principal del cliente.
