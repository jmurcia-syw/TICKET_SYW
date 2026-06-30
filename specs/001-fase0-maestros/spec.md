# Feature Specification: Fase 0 — Maestros

**Feature Branch**: `001-fase0-maestros`

**Created**: 2026-06-29

**Status**: Enriched

---

## User Scenarios & Testing

### User Story 1 — Gestión de Clientes (Priority: P1)

Un Administrador o Coordinador necesita registrar y mantener los datos de los clientes de SyWork,
incluyendo información de contacto y datos sensibles de acceso (IPs, credenciales VPN) que permiten
a los consultores conectarse a los entornos del cliente para resolver tickets.

**Why this priority**: Sin clientes no existe la estructura base. Tickets y proyectos dependen de
que los clientes estén registrados. Es el nodo raíz del modelo de datos (RLS root).

**Independent Test**: Se puede demostrar independientemente creando un cliente, editándolo,
viendo sus datos (con datos sensibles visibles solo para Admin/Coordinador) y desactivándolo.

**Acceptance Scenarios**:

1. **Given** un Admin autenticado en la pantalla de Clientes, **When** completa el formulario de
   nuevo cliente y confirma, **Then** el cliente aparece en la lista con estado Activo y sus datos
   sensibles almacenados de forma cifrada.

2. **Given** un Coordinador en la pantalla de Clientes, **When** abre el detalle de un cliente,
   **Then** puede ver las IPs y credenciales VPN del cliente pero no puede exportarlas en texto plano.

3. **Given** un Resolutor autenticado, **When** intenta acceder a la pantalla de Clientes,
   **Then** recibe un mensaje de acceso denegado y es redirigido al dashboard.

4. **Given** un Admin, **When** desactiva un cliente, **Then** el cliente queda con estado Inactivo
   y no aparece en selectores de nuevos proyectos, pero su historial se conserva.

---

### User Story 2 — Gestión de Proyectos (Priority: P1)

Un Administrador o Coordinador necesita registrar los proyectos activos de cada cliente, dado que
los tickets y tareas futuras se asociarán a un proyecto específico para dar contexto y visibilidad.

**Why this priority**: Los proyectos son el segundo nivel de la jerarquía de datos y son necesarios
antes de que los tickets puedan clasificarse correctamente en Fase 1.

**Independent Test**: Se puede demostrar creando un proyecto asociado a un cliente existente,
editando sus datos y desactivándolo. No depende de recursos ni roles más allá del cliente.

**Acceptance Scenarios**:

1. **Given** un Coordinador en la pantalla de Proyectos, **When** crea un nuevo proyecto
   seleccionando un cliente existente y completando el formulario, **Then** el proyecto aparece
   listado bajo ese cliente con estado Activo.

2. **Given** un Coordinador, **When** filtra la lista de proyectos por cliente, **Then** solo
   ve los proyectos de ese cliente.

3. **Given** un Admin, **When** desactiva un proyecto, **Then** el proyecto queda Inactivo
   y no aparece en la creación de nuevos tickets, pero los tickets existentes mantienen la
   referencia al proyecto.

---

### User Story 3 — Gestión de Recursos y Skills (Priority: P2)

Un Administrador necesita registrar a los miembros del equipo de SyWork (consultores, coordinadores,
QMs) con sus habilidades técnicas parametrizadas (skills), de modo que el Coordinador pueda tomar
decisiones de asignación de tickets basadas en capacidades reales en Fase 1.

**Why this priority**: Los recursos son necesarios para la asignación de tickets en Fase 1, pero
no bloquean la creación de clientes y proyectos. Se puede demostrar independientemente.

**Independent Test**: Se puede demostrar creando un recurso, asignándole skills de la lista
predefinida, y verificando que el perfil del recurso muestre correctamente sus habilidades.

**Acceptance Scenarios**:

1. **Given** un Admin en la pantalla de Recursos, **When** crea un nuevo recurso y le asigna
   skills de una lista predefinida (ej. JDE_GL, API_REST, Oracle_Fusion), **Then** el recurso
   aparece en la lista con sus skills visibles.

2. **Given** un QM autenticado, **When** accede a la pantalla de Recursos, **Then** puede ver
   la lista completa de recursos y sus skills, pero no puede crear, editar ni eliminar recursos.

3. **Given** un Resolutor autenticado, **When** accede a la pantalla de Recursos, **Then** solo
   puede ver y editar su propio perfil (no el de otros recursos).

4. **Given** un Coordinador, **When** busca recursos filtrando por skill "JDE_GL", **Then**
   solo ve los recursos que tienen ese skill asignado.

---

### User Story 4 — Gestión de Roles y Seguridad (Priority: P2)

Un Administrador necesita asignar roles a los usuarios del sistema para controlar qué acciones
puede realizar cada persona. Los roles son: Admin, Coordinador, QM y Resolutor/Consultor.

**Why this priority**: Los roles son necesarios para aplicar el modelo de seguridad completo,
pero el sistema puede operar inicialmente con roles predefinidos en la base de datos.

**Independent Test**: Se puede demostrar asignando un rol diferente a un usuario, cerrando
sesión y verificando que las pantallas accesibles cambian según el nuevo rol.

**Acceptance Scenarios**:

1. **Given** un Admin en la pantalla de Usuarios, **When** cambia el rol de un usuario de
   Resolutor a Coordinador y el usuario vuelve a iniciar sesión, **Then** el usuario puede
   acceder a las pantallas de Clientes y Proyectos.

2. **Given** el sistema con los 4 roles definidos, **When** un usuario intenta acceder a una
   pantalla fuera de sus permisos, **Then** recibe un error 403 y es redirigido al dashboard.

3. **Given** un Admin, **When** desactiva la cuenta de un usuario, **Then** ese usuario no
   puede iniciar sesión aunque sus credenciales sean válidas.

---

### Edge Cases

**Clientes**
- Cliente con nombre duplicado → rechazar con mensaje claro; no crear registro parcial.
- Desactivar cliente con proyectos activos → advertencia con lista de proyectos afectados +
  confirmación explícita requerida.
- Desactivar cliente con proyectos activos que tienen tickets abiertos → el sistema DEBE mostrar
  también la cantidad de tickets abiertos impactados.
- Acceso a datos sensibles sin JWT válido → respuesta 401 sin exponer ningún dato, sin mensaje
  descriptivo del campo solicitado.
- Acceso a datos sensibles con JWT válido pero rol insuficiente (QM/Resolutor) → respuesta 403,
  el campo sensible NO aparece en el payload de respuesta (no "***", directamente ausente).
- Nombre de cliente con caracteres especiales (comillas, barras, HTML) → el sistema DEBE
  sanitizar y almacenar correctamente sin riesgo de inyección.

**Proyectos**
- Crear proyecto para un cliente inactivo → el sistema DEBE impedirlo con mensaje explicativo.
- Proyecto con nombre duplicado dentro del mismo cliente → rechazar; permitir mismo nombre en
  clientes distintos.
- Fecha de fin anterior a fecha de inicio → validación en frontend y backend; rechazar con
  mensaje específico.

**Recursos y Skills**
- Eliminar skill en uso por uno o más recursos → bloqueado con listado de recursos afectados.
- Recurso sin ningún skill asignado → permitido en creación, pero el sistema DEBE advertir
  que sin skills no aparecerá en sugerencias de asignación de tickets.
- Recurso intenta editar perfil de otro recurso por URL directa → 403 en API,
  independientemente de la UI.
- Dos recursos con el mismo email → rechazar; el email es identificador único.
- Admin desactiva su propio usuario → el sistema DEBE impedirlo para evitar quedarse sin Admin.

**Roles y Seguridad**
- Intentar dejar el sistema sin ningún Admin (desactivar o cambiar rol del último Admin) →
  el sistema DEBE bloquearlo con mensaje explicativo.
- Token JWT expirado → respuesta 401, el frontend redirige al login sin exponer detalles.
- Usuario de Google válido pero dominio distinto a @sywork.net intenta autenticarse → acceso
  denegado en el callback OAuth, sin crear registro de usuario.
- Sesión activa de un usuario cuya cuenta es desactivada por Admin → la sesión actual
  DEBE invalidarse en la próxima llamada a la API (el JWT no se revoca pero el middleware
  DEBE verificar estado activo del usuario en cada request).

---

## Requirements

### Functional Requirements

**Clientes**

- **FR-001**: El sistema DEBE permitir a Admin y Coordinador crear, ver, editar y desactivar
  clientes.
- **FR-002**: El sistema DEBE almacenar los datos sensibles de clientes (IPs, credenciales VPN)
  cifrados en reposo.
- **FR-003**: El sistema DEBE mostrar datos sensibles de clientes únicamente a usuarios con rol
  Admin o Coordinador, nunca a QM ni Resolutor. Los campos `vpn_ips` y `vpn_credentials` se
  presentan enmascarados por defecto (`••••••••`) con un botón de revelar (icono ojo) que
  muestra el valor descifrado sin requerir un endpoint adicional.
- **FR-004**: El sistema DEBE impedir la creación de dos clientes con el mismo nombre.
- **FR-005**: El sistema DEBE conservar el historial de tickets al desactivar un cliente.

**Proyectos**

- **FR-006**: El sistema DEBE permitir a Admin y Coordinador crear, ver, editar y desactivar
  proyectos asociados a un cliente existente.
- **FR-007**: El sistema DEBE filtrar la lista de proyectos por cliente.
- **FR-008**: Los proyectos inactivos NO DEBEN aparecer en selectores de creación de tickets.

**Recursos y Skills**

- **FR-009**: El sistema DEBE permitir a Admin crear, editar y desactivar recursos (miembros
  del equipo).
- **FR-010**: Cada recurso DEBE tener uno o más skills asignados de una lista predefinida y
  controlada por Admin.
- **FR-011**: El sistema DEBE permitir filtrar recursos por skill.
- **FR-012**: Un Resolutor DEBE poder ver y editar únicamente su propio perfil de recurso.
- **FR-013**: Un QM DEBE poder ver todos los recursos y sus skills, sin capacidad de edición.
- **FR-014**: La lista de skills predefinidos NO DEBE poder eliminar un skill que esté asignado
  a al menos un recurso.
- **FR-014b**: Un recurso sin skills asignados DEBE poder crearse, pero el sistema DEBE mostrar
  advertencia de que no aparecerá en sugerencias de asignación.
- **FR-014c**: Dos recursos NO PUEDEN compartir el mismo email; el email es identificador único.

**Roles y Seguridad**

- **FR-015**: El sistema DEBE implementar cuatro roles: Admin, Coordinador, QM, Resolutor.
- **FR-016**: Cada usuario DEBE tener exactamente un rol asignado.
- **FR-017**: El sistema DEBE aplicar control de acceso basado en roles en todas las rutas de
  la API y en la navegación del frontend.
- **FR-018**: Un Admin DEBE poder cambiar el rol de cualquier usuario.
- **FR-019**: Un Admin DEBE poder desactivar la cuenta de un usuario impidiendo su acceso.
- **FR-020**: El sistema DEBE impedir que el último Admin activo sea desactivado o degradado a
  otro rol, garantizando al menos un Admin operativo en todo momento.
- **FR-021**: El middleware de autenticación DEBE verificar el estado activo del usuario en cada
  request a la API, rechazando con 401 si la cuenta fue desactivada tras emitir el JWT.
- **FR-022**: El sistema DEBE rechazar el login OAuth2 de emails con dominio distinto a
  @sywork.net sin crear ningún registro de usuario.
- **FR-023**: Las respuestas de error 403 y 401 NO DEBEN incluir en su payload detalles sobre
  qué campo o recurso fue solicitado.

**UX y Formularios**

- **FR-024**: Todos los formularios de creación/edición DEBEN validar campos requeridos en el
  frontend antes de enviar al servidor, mostrando mensajes en español junto al campo afectado.
- **FR-025**: Las listas de Clientes, Proyectos y Recursos DEBEN soportar búsqueda por texto
  libre y ordenamiento por columna.
- **FR-026**: Las acciones destructivas (desactivar cliente/proyecto/recurso, cambiar rol) DEBEN
  requerir un diálogo de confirmación con descripción del impacto antes de ejecutarse.
- **FR-027**: Las pantallas de listado DEBEN mostrar un indicador visual claro de estado
  (Activo/Inactivo) para cada registro.

### Key Entities

- **Client**: Organización cliente de SyWork. Atributos: nombre, slug, estado (activo/inactivo),
  datos de contacto, datos sensibles de conexión (IPs, credenciales VPN cifradas). Es el nodo
  raíz del modelo de datos (RLS root).
- **Project**: Proyecto o contrato asociado a un cliente. Atributos: nombre, descripción, estado,
  fecha de inicio, fecha de fin estimada, FK client_id.
- **Resource**: Miembro del equipo de SyWork. Atributos: nombre, email (@sywork.net), rol,
  estado (activo/inactivo), lista de skills asignados.
- **Skill**: Etiqueta de habilidad técnica predefinida. Ejemplos: JDE_GL, API_REST,
  Oracle_Fusion, JDE_AP, Oracle_CRM. Controlada por Admin.
- **User**: Cuenta de acceso al sistema. Vinculada a un Resource. Atributos: email Google,
  rol, estado activo/inactivo, último acceso.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Un Admin puede completar el registro de un nuevo cliente (incluyendo datos sensibles)
  en menos de 3 minutos.
- **SC-002**: Un Resolutor que intenta acceder a datos de otro recurso recibe rechazo en el 100%
  de los intentos, tanto desde la UI como accediendo directamente a la URL o endpoint de API.
- **SC-003**: Los datos sensibles de clientes (IPs, credenciales VPN) nunca aparecen en texto
  plano en logs, respuestas de error ni en el frontend para roles no autorizados.
- **SC-004**: Un Coordinador puede encontrar todos los recursos con un skill específico
  en menos de 30 segundos usando el filtro de la pantalla de Recursos.
- **SC-005**: El cambio de rol de un usuario se refleja en sus permisos en el siguiente inicio
  de sesión sin requerir intervención técnica adicional.
- **SC-006**: Las cuatro pantallas de maestros (Clientes, Proyectos, Recursos, Roles) son
  accesibles y funcionales con datos reales antes de iniciar Fase 1 (Tickets).
- **SC-007**: Ningún intento de acceso no autorizado a datos sensibles (IPs, credenciales VPN)
  tiene éxito en pruebas de penetración básicas: acceso sin token, con token de rol insuficiente,
  o por URL directa.
- **SC-008**: El sistema rechaza el 100% de los intentos de login desde cuentas fuera del dominio
  @sywork.net.
- **SC-009**: Todas las validaciones de formulario (campos requeridos, duplicados, fechas) son
  comunicadas al usuario con mensajes en español sin necesidad de recargar la página.

---

## Clarifications

### Session 2026-06-29

- Q: ¿Qué comportamiento debe tener el sistema cuando dos Admins editan el mismo registro simultáneamente? → A: Last-write-wins — el último en guardar sobreescribe sin error; no se requiere campo `version` ni control de concurrencia optimista.
- Q: ¿Debe el sistema registrar un trail de auditoría de acciones Admin (cambios de rol, desactivaciones, ediciones de clientes)? → A: No en esta fase — solo `updated_at` por tabla; trail de auditoría diferido a fase futura de Seguridad/Compliance.
- Q: ¿Cómo deben mostrarse las credenciales VPN en el detalle del cliente para Admin/Coordinator? → A: Enmascaradas por defecto (`••••••••`), con botón de revelar (icono ojo) sin endpoint adicional.

---

## Assumptions

- El sistema de autenticación Google OAuth2 restringido a `@sywork.net` ya está operativo
  (configurado en Fase de infraestructura previa al desarrollo de Maestros).
- Los skills predefinidos iniciales serán definidos por el equipo de SyWork antes del lanzamiento;
  el sistema solo necesita un mecanismo para administrarlos, no viene con una lista fija hardcodeada.
- La encriptación de datos sensibles de clientes se implementará a nivel de columna en PostgreSQL
  (ej. `pgcrypto`) o a nivel de aplicación en la Capa 2 (Infraestructura); la decisión técnica
  exacta se resolverá en la fase de planificación.
- El calendario de disponibilidad de recursos (vacaciones, permisos) está marcado como "Evolutivo"
  en el roadmap y queda **fuera del alcance de esta fase**. Esta spec cubre solo el perfil base
  del recurso con skills.
- Un usuario del sistema siempre corresponde a exactamente un recurso interno (no hay usuarios
  externos en esta fase).
- Las pantallas de maestros seguirán el diseño de la maqueta UI existente en `docs/mockup.html`
  como referencia visual.
- El middleware de verificación de estado activo del usuario agrega latencia mínima aceptable
  (consulta por user_id ya presente en el JWT; se puede cachear a nivel de request).
- Los datos sensibles de clientes nunca se serializan en logs de aplicación (ni en modo debug).
- La paginación de listas es necesaria pero el tamaño de página por defecto queda a criterio
  del plan técnico (sugerido: 20-50 registros).
- Las ediciones concurrentes al mismo registro se resuelven con last-write-wins: el último PATCH
  en guardar sobreescribe sin notificación de conflicto. No se requiere campo `version` ni
  control de concurrencia optimista dado el volumen de usuarios (~10-30 internos).
- No se implementa trail de auditoría en esta fase. Solo `updated_at` en cada tabla como
  trazabilidad mínima. Un sistema de auditoría completo queda diferido a una fase futura
  de Seguridad/Compliance.
