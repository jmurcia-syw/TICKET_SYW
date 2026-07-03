# Feature Specification: Fase 0 — Maestros

**Feature Branch**: `001-fase0-maestros`

**Created**: 2026-06-29

**Status**: Enriched — Ampliado 2026-07-02 con los campos de maestros de SDD V3 (`docs/SDD V3.docx`)

---

## User Scenarios & Testing

### User Story 1 — Gestión de Clientes (Priority: P1)

Un Administrador, Coordinador o QM necesita registrar y mantener los datos de los clientes de
SyWork, incluyendo información de contacto y datos sensibles de acceso (IPs, credenciales VPN)
que permiten a los consultores conectarse a los entornos del cliente para resolver tickets. Un
Resolutor solo necesita consultar el listado de clientes para dar contexto a su trabajo, sin
poder modificarlo ni ver los datos sensibles de conexión.

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

3. **Given** un Resolutor autenticado, **When** accede a la pantalla de Clientes, **Then** puede
   ver el listado (permiso `clients.view`) pero no ve los botones de crear/editar/desactivar, y
   los campos VPN sensibles no aparecen en absoluto en su vista ni en la respuesta de la API
   (reservados a Admin/Coordinador por FR-003).

4. **Given** un Admin, **When** desactiva un cliente, **Then** el cliente queda con estado Inactivo
   y no aparece en selectores de nuevos proyectos, pero su historial se conserva.

5. **Given** un QM autenticado en la pantalla de Clientes, **When** crea, edita o desactiva un
   cliente, **Then** la operación se completa igual que para Admin/Coordinador (mismo permiso de
   módulo `clients`), pero los campos VPN sensibles permanecen ocultos para su rol (FR-003).

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

4. **Given** un QM o un Resolutor autenticado, **When** accede a la pantalla de Proyectos,
   **Then** puede ver el listado y filtrarlo por cliente (permiso `projects.view`), pero no ve
   los botones de crear/editar/desactivar.

---

### User Story 3 — Gestión de Recursos y Skills (Priority: P2)

Un Administrador, Coordinador o QM necesita registrar a los miembros del equipo de SyWork
(consultores, coordinadores, QMs) con sus habilidades técnicas parametrizadas (skills), de modo
que el Coordinador pueda tomar decisiones de asignación de tickets basadas en capacidades reales
en Fase 1. Admin, Coordinador y QM comparten el mismo nivel de acceso sobre Recursos y sobre el
catálogo de Skills (crear, ver, editar, desactivar); un Resolutor solo puede ver y editar su
propio perfil.

**Why this priority**: Los recursos son necesarios para la asignación de tickets en Fase 1, pero
no bloquean la creación de clientes y proyectos. Se puede demostrar independientemente.

**Independent Test**: Se puede demostrar creando un recurso, asignándole skills de la lista
predefinida, y verificando que el perfil del recurso muestre correctamente sus habilidades.

**Acceptance Scenarios**:

1. **Given** un Admin, Coordinador o QM en la pantalla de Recursos, **When** crea un nuevo recurso
   y le asigna skills de una lista predefinida (ej. JDE_GL, API_REST, Oracle_Fusion), **Then** el
   recurso aparece en la lista con sus skills visibles.

2. **Given** un QM autenticado, **When** accede a la pantalla de Recursos, **Then** tiene el mismo
   nivel de acceso que Admin y Coordinador: puede ver, crear, editar y desactivar recursos y
   gestionar el catálogo de Skills (permiso de módulo `resources`/`skills` completo).

3. **Given** un Resolutor autenticado, **When** accede a la pantalla de Recursos, **Then** solo
   puede ver y editar su propio perfil (no el de otros recursos), independientemente de que su
   permiso de módulo sea de solo lectura.

4. **Given** un Coordinador, **When** busca recursos filtrando por skill "JDE_GL", **Then**
   solo ve los recursos que tienen ese skill asignado.

---

### User Story 4 — Gestión de Roles, Permisos y Seguridad (Priority: P2)

Un Administrador necesita crear y administrar roles dinámicos (no una lista fija de 4), asignar
permisos granulares (módulo + acción) a cada rol, y asignar roles a los usuarios del sistema para
controlar qué pantallas y acciones puede realizar cada persona. El sistema se siembra con 4 roles
iniciales (Admin, Coordinador, QM, Resolutor) pero Admin puede crear roles adicionales y ajustar
los permisos de cualquier rol (excepto el rol Admin, que conserva siempre acceso total).

Los módulos del catálogo de permisos son: `clients`, `projects`, `resources`, `skills`, `users`
y `roles`; las acciones son: `view`, `create`, `edit`, `deactivate` (24 combinaciones sembradas
inicialmente). El seed inicial asigna el siguiente nivel de acceso por rol y módulo:

| Módulo | Admin | Coordinador | QM | Resolutor |
|--------|-------|--------------|-----|-----------|
| clients | completo | completo | completo | solo ver |
| projects | completo | completo | solo ver | solo ver |
| resources | completo | completo | completo | solo ver (+ propio perfil editable) |
| skills | completo | completo | completo | solo ver |
| users | completo (incl. crear) | solo ver | solo ver | solo ver |
| roles | completo | sin acceso | sin acceso | sin acceso |

("completo" = ver + crear + editar + desactivar del módulo)

El login provisional por usuario/contraseña (FR-022b) deja de ser un mecanismo secundario de
prueba: es, junto con Google OAuth2, la única forma real de iniciar sesión en el frontend — no
existe ningún modo de "saltarse" la autenticación en ningún ambiente.

**Why this priority**: Los roles y permisos son necesarios para aplicar el modelo de seguridad
completo, pero el sistema puede operar inicialmente con los 4 roles semilla predefinidos.

**Independent Test**: Se puede demostrar asignando un rol diferente a un usuario, cerrando
sesión y verificando que los menús accesibles cambian según los permisos del nuevo rol. También
se puede demostrar creando un rol nuevo, asignándole permisos vía la pantalla de Roles y Permisos,
y verificando que un usuario con ese rol ve exactamente esos menús. También se puede demostrar
creando un usuario nuevo desde cero (email, username, rol) e iniciando sesión con la contraseña
provisional generada.

**Acceptance Scenarios**:

1. **Given** un Admin en la pantalla de Usuarios, **When** cambia el rol de un usuario de
   Resolutor a Coordinador y el usuario vuelve a iniciar sesión, **Then** el usuario puede
   acceder a las pantallas de Clientes y Proyectos.

2. **Given** un usuario autenticado, **When** su rol no tiene el permiso `view` de un módulo,
   **Then** el menú correspondiente no aparece en la navegación del frontend.

3. **Given** un Admin, **When** desactiva la cuenta de un usuario, **Then** ese usuario no
   puede iniciar sesión aunque sus credenciales sean válidas.

4. **Given** un Admin en la pantalla de Roles y Permisos, **When** crea un rol nuevo y le asigna
   permisos vía la matriz módulo × acción, **Then** el rol queda disponible para asignar a
   usuarios y sus permisos determinan los menús visibles.

5. **Given** un usuario con correo/usuario y contraseña provisional válidos, **When** inicia
   sesión desde la pantalla de login, **Then** obtiene acceso equivalente al login por Google
   OAuth (mismo token, mismo rol y permisos).

6. **Given** el sistema recién desplegado, **When** se ejecuta la migración inicial de roles y
   permisos, **Then** existen 4 usuarios de prueba (uno por rol semilla) con una contraseña
   provisional compartida, generada aleatoriamente y mostrada una única vez durante la migración
   (nunca almacenada en el repositorio en texto plano).

7. **Given** cualquier ambiente (desarrollo, pruebas o producción), **When** un usuario abre el
   frontend sin haber iniciado sesión, **Then** es dirigido a la pantalla de login sin ningún
   mecanismo de acceso que omita la autenticación.

8. **Given** un Admin en la pantalla de Usuarios, **When** crea un nuevo usuario indicando email
   `@sywork.net`, username y rol, **Then** el sistema genera y muestra una contraseña provisional
   una única vez, y esa persona puede iniciar sesión con esas credenciales inmediatamente.

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
- Migración inicial encuentra un usuario existente con un rol desconocido (fuera de los 4 roles
  semilla) → la migración DEBE fallar explícitamente en vez de asignar un rol por defecto en
  silencio.
- Renombrar el rol "Admin" a otro nombre → la protección de "no desactivar/degradar al último
  Admin" deja de aplicar (se basa en el nombre del rol); el sistema SOLO bloquea explícitamente
  el borrado/desactivación del rol cuyo nombre es "Admin" en el momento de la operación. Esta es
  una limitación conocida y aceptada para Fase 0.
- Admin crea un usuario con email fuera de `@sywork.net` → rechazar con el mismo mensaje de
  dominio inválido que usa el callback de Google OAuth2.
- Admin crea un usuario con email o username ya existente → rechazar; ambos son identificadores
  únicos.

---

## Requirements

### Functional Requirements

**Clientes**

- **FR-001**: El sistema DEBE permitir a Admin, Coordinador y QM crear, ver, editar, desactivar y
  reactivar clientes (toggle Activo/Inactivo desde la pantalla de detalle; mismo permiso de módulo
  `clients` para los tres roles). Un Resolutor DEBE tener acceso de solo lectura (`clients: view`):
  puede ver el listado pero no crear, editar ni desactivar. Ningún rol distinto de Admin/Coordinador
  puede ver los campos VPN sensibles (FR-003).
- **FR-002**: El sistema DEBE almacenar los datos sensibles de clientes (IPs, credenciales VPN)
  cifrados en reposo.
- **FR-003**: El sistema DEBE mostrar datos sensibles de clientes únicamente a usuarios con rol
  Admin o Coordinador, nunca a QM ni Resolutor. Los campos `vpn_ips` y `vpn_credentials` se
  presentan enmascarados por defecto (`••••••••`) con un botón de revelar (icono ojo) que
  muestra el valor descifrado sin requerir un endpoint adicional.
- **FR-004**: El sistema DEBE impedir la creación de dos clientes con el mismo nombre.
- **FR-005**: El sistema DEBE conservar el historial de tickets al desactivar un cliente.

**Proyectos**

- **FR-006**: El sistema DEBE permitir a Admin y Coordinador crear, ver, editar, desactivar y
  reactivar proyectos asociados a un cliente existente (toggle Activo/Inactivo).
- **FR-006b**: QM y Resolutor DEBEN tener acceso de solo lectura (`projects: view`) a Proyectos:
  pueden ver y filtrar el listado, pero no crear, editar ni desactivar.
- **FR-007**: El sistema DEBE filtrar la lista de proyectos por cliente.
- **FR-008**: Los proyectos inactivos NO DEBEN aparecer en selectores de creación de tickets.

**Recursos y Skills**

- **FR-009**: El sistema DEBE permitir a Admin, Coordinador y QM crear, editar, desactivar y
  reactivar recursos (miembros del equipo) mediante toggle Activo/Inactivo — mismo permiso de
  módulo `resources` para los tres roles.
- **FR-010**: Cada recurso DEBE tener uno o más skills asignados de una lista predefinida,
  gestionable por Admin, Coordinador y QM (mismo permiso de módulo `skills` para los tres roles).
- **FR-011**: El sistema DEBE permitir filtrar recursos por skill.
- **FR-012**: Un Resolutor DEBE poder ver y editar únicamente su propio perfil de recurso, sin
  importar que su permiso de módulo `resources` sea de solo lectura (la restricción de "propio
  perfil" se aplica por `user_id`, no por el catálogo de permisos).
- **FR-013**: Un QM DEBE tener el mismo nivel de acceso que Admin y Coordinador sobre Recursos:
  ver, crear, editar y desactivar (permiso de módulo `resources` completo).
- **FR-014**: La lista de skills predefinidos NO DEBE poder eliminar un skill que esté asignado
  a al menos un recurso.
- **FR-014b**: Un recurso sin skills asignados DEBE poder crearse, pero el sistema DEBE mostrar
  advertencia de que no aparecerá en sugerencias de asignación.
- **FR-014c**: Dos recursos NO PUEDEN compartir el mismo email; el email es identificador único.

**Roles y Seguridad**

- **FR-015**: El sistema DEBE implementar roles dinámicos gestionables por Admin (crear, editar,
  desactivar/activar), sembrados inicialmente con 4 roles: Admin, Coordinador, QM, Resolutor.
  El rol Admin no puede desactivarse ni eliminarse.
- **FR-015b**: El sistema DEBE implementar permisos granulares por módulo + acción, asignables a
  cualquier rol mediante una pantalla de Roles y Permisos accesible solo para Admin. Los módulos
  del catálogo inicial son `clients`, `projects`, `resources`, `skills`, `users` y `roles`; las
  acciones son `view`, `create`, `edit`, `deactivate` (24 combinaciones sembradas). Un permiso no
  puede eliminarse si está asignado a algún rol.
- **FR-016**: Cada usuario DEBE tener exactamente un rol asignado.
- **FR-017**: El sistema DEBE aplicar control de acceso basado en permisos en la navegación del
  frontend (menús visibles según los permisos `view` del rol del usuario). El enforcement de
  permisos a nivel de rutas de la API queda **fuera de alcance de Fase 0** y diferido a una fase
  posterior; las rutas de maestros no exigen JWT en esta fase.
- **FR-018**: Un Admin DEBE poder cambiar el rol de cualquier usuario a cualquier rol existente.
- **FR-018b**: Un Admin DEBE poder crear nuevos usuarios (email `@sywork.net`, username, rol)
  desde la pantalla de Usuarios. El sistema DEBE generar una contraseña provisional aleatoria al
  crear el usuario, mostrada una única vez a Admin para compartirla manualmente con la persona
  (mismo patrón que los 4 usuarios semilla, FR-022d). Email y username duplicados DEBEN
  rechazarse.
- **FR-019**: Un Admin DEBE poder desactivar la cuenta de un usuario impidiendo su acceso.
- **FR-020**: El sistema DEBE impedir que el último Admin activo sea desactivado o degradado a
  otro rol, garantizando al menos un Admin operativo en todo momento.
- **FR-021**: El middleware de autenticación DEBE verificar el estado activo del usuario en cada
  request a la API, rechazando con 401 si la cuenta fue desactivada tras emitir el JWT.
- **FR-022**: El sistema DEBE rechazar el login OAuth2 de emails con dominio distinto a
  @sywork.net sin crear ningún registro de usuario.
- **FR-022b**: El sistema DEBE ofrecer un login provisional adicional por usuario/contraseña
  (correo o nombre de usuario + contraseña), coexistiendo con el login de Google OAuth2 sin
  reemplazarlo. Las contraseñas se almacenan solo como hash (nunca en texto plano).
- **FR-023**: Las respuestas de error 403 y 401 NO DEBEN incluir en su payload detalles sobre
  qué campo o recurso fue solicitado.
- **FR-022c**: El frontend NO DEBE ofrecer ningún mecanismo que omita la autenticación (bypass de
  desarrollo o de cualquier otro tipo) en ningún ambiente; toda sesión DEBE originarse en un login
  real, ya sea Google OAuth2 (FR-022) o el login provisional usuario/contraseña (FR-022b).
- **FR-022d**: El sistema DEBE sembrar automáticamente, durante la migración inicial, los 4 roles
  base y 4 usuarios de prueba (uno por rol) con una contraseña provisional compartida generada
  aleatoriamente en el momento de la migración, mostrada una única vez y nunca almacenada en el
  repositorio en texto plano.

**Ampliación de Maestros — SDD V3 (2026-07-02)**

- **FR-028**: El maestro de Clientes DEBE registrar el volumen de facturación anual en dólares
  (USD) del cliente, editable por los roles con permiso `clients: edit`.
- **FR-029**: El maestro de Clientes DEBE registrar el portafolio de software del cliente:
  cero o más sistemas, cada uno con tipo (ERP, WMS, CRM, otro), marca y versión
  (ej. ERP / JD Edwards / 9.2). Gestionable desde el detalle del cliente.
- **FR-030**: El maestro de Proyectos DEBE registrar el overview del proyecto, los valores de
  venta desglosados (servicios, licencias, suscripciones, en USD) y los componentes vendidos,
  conformando el historial completo de proyectos por cliente.
- **FR-031**: El maestro de Recursos DEBE ampliarse con: identificación, nacionalidad, fecha de
  nacimiento, estado civil, tipo de contrato, país/calendario de trabajo (país base), nivel de
  estudios, especialidad (Desarrollador, Funcional, Infraestructura, etc.), seniority (Junior,
  Staff, Senior), certificaciones, equipo al que pertenece y jefe (referencia a otro recurso).
  Todos opcionales salvo los ya requeridos (nombre, email).
- **FR-032**: El sistema DEBE manejar un área protegida de compensación por recurso: salario
  base, salario total (con beneficios legales y extralegales), costos adicionales/overhead, y
  el costo hora calculado por el sistema a partir de esos valores. Estos datos DEBEN
  almacenarse cifrados en reposo (mismo mecanismo que los datos VPN de clientes).
- **FR-033**: El acceso al área de compensación DEBE controlarse con un nuevo módulo de permisos
  `compensation` (acciones `view`, `edit`), sembrado inicialmente solo para el rol Admin. Los
  campos de compensación NUNCA aparecen en el payload de la API para roles sin ese permiso
  (ausentes, no enmascarados), y nunca en logs.
- **FR-034**: El calendario detallado de trabajo por país (feriados, ausencias, vacaciones)
  queda fuera de alcance de esta fase (Fase 5 del roadmap SDD V3); en esta fase solo se registra
  el país base del calendario como atributo del recurso.

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
  datos de contacto, facturación anual USD (FR-028), datos sensibles de conexión (IPs,
  credenciales VPN cifradas). Es el nodo raíz del modelo de datos (RLS root).
- **ClientSystem**: Sistema de software que posee el cliente (FR-029). Atributos: tipo
  (ERP/WMS/CRM/otro), marca, versión, FK client_id. Relación 1..N desde Client.
- **Project**: Proyecto o contrato asociado a un cliente. Atributos: nombre, descripción,
  overview, estado, fecha de inicio, fecha de fin estimada, valores de venta (servicios,
  licencias, suscripciones en USD), componentes vendidos (FR-030), FK client_id.
- **Resource**: Miembro del equipo de SyWork. Atributos: nombre, email (@sywork.net),
  estado (activo/inactivo), lista de skills asignados; perfil extendido FR-031 (identificación,
  nacionalidad, fecha de nacimiento, estado civil, tipo de contrato, país de calendario, nivel
  de estudios, especialidad, seniority, certificaciones, equipo, jefe → FK autorreferencial a
  Resource). No tiene campo de rol propio; el rol de acceso (permisos) reside únicamente en el
  `User` vinculado (relación opcional, 0..1).
- **ResourceCompensation**: Área protegida de compensación 1..1 con Resource (FR-032/FR-033).
  Atributos cifrados: salario base, salario total con beneficios, overhead/costos adicionales,
  costo hora calculado. Visible solo con permiso `compensation`.
- **Skill**: Etiqueta de habilidad técnica predefinida. Ejemplos: JDE_GL, API_REST,
  Oracle_Fusion, JDE_AP, Oracle_CRM. Catálogo gestionable por Admin, Coordinador y QM (mismo
  permiso de módulo `skills`).
- **User**: Cuenta de acceso al sistema. Vinculada a un Resource. Atributos: email, username,
  password_hash (opcional, para login provisional), rol (FK dinámica), estado activo/inactivo,
  último acceso.
- **Role**: Rol dinámico gestionable por Admin. Atributos: nombre, descripción, estado
  activo/inactivo. Sembrado inicialmente con Admin, Coordinador, QM, Resolutor.
- **Permission**: Permiso granular módulo + acción. Módulos: `clients`, `projects`, `resources`,
  `skills`, `users`, `roles` y `compensation` (FR-033, agregado 2026-07-02). Acciones: `view`,
  `create`, `edit`, `deactivate` (24 combinaciones sembradas inicialmente + `compensation:
  view/edit` sembradas solo para Admin). Asignado a roles mediante una tabla puente many-to-many.

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
- Q: ¿Cómo deben mostrarse las credenciales VPN en el detalle del cliente para Admin/Coordinador? → A: Enmascaradas por defecto (`••••••••`), con botón de revelar (icono ojo) sin endpoint adicional.

### Session 2026-07-01

- Q: La sección Key Entities lista `rol` como atributo tanto de `Resource` como de `User`. ¿`Resource` debe tener su propio campo de rol independiente, o el rol de acceso vive únicamente en `User`? → A: Solo `User` tiene rol de acceso (FK dinámica a `Role`); `Resource` no tiene campo `rol` propio.
- Q: ¿Un cliente/proyecto/recurso inactivo puede reactivarse desde la UI, o la desactivación es unidireccional en Fase 0? → A: Sí, reactivable (toggle Activo/Inactivo desde la pantalla de detalle), igual que ya aplica para Roles (FR-015). *(Sin respuesta explícita del usuario; se adoptó la opción recomendada por inactividad — confirmar o corregir si no aplica.)*
- Q: ¿Qué nivel de acceso deben tener QM y Resolutor sobre Clientes, Proyectos, Recursos y Skills — el spec original solo mencionaba Admin/Coordinador para Clientes/Proyectos y "QM sin edición" para Recursos? → A: Se formaliza el modelo de permisos ya diseñado y aprobado fuera de este flujo (`docs/superpowers/specs/2026-07-01-roles-permissions-login-design.md`, implementado en la migración `009_roles_permissions_login.py`): QM tiene el mismo acceso completo que Admin/Coordinador sobre `clients`, `resources` y `skills` (pero nunca ve datos VPN sensibles); QM tiene solo lectura sobre `projects`; Resolutor tiene solo lectura sobre `clients`/`projects`/`skills`/`users`, y sobre `resources` solo lectura salvo su propio perfil (FR-012). Esto reemplaza la Acceptance Scenario 3 original de US1 ("Resolutor... acceso denegado") y el FR-013 original ("QM sin capacidad de edición").
- Q: ¿Debe eliminarse cualquier bypass de autenticación de desarrollo (`DEV_SKIP_AUTH`) ahora que existe login provisional real? → A: Sí — el login provisional (FR-022b) pasa a ser, junto con Google OAuth2, el único mecanismo real de acceso al frontend en todos los ambientes (FR-022c).
- Q: Ni el spec ni el código definen cómo se crea un `User` nuevo para un empleado que no sea uno de los 4 usuarios semilla (no hay `POST /api/users`, y el login de Google no auto-crea cuentas). ¿Cómo debe un Admin dar acceso a un empleado nuevo? → A: Admin crea el `User` manualmente desde la pantalla de Usuarios (email, username, rol); el sistema genera una contraseña provisional aleatoria mostrada una única vez para compartirla manualmente, igual que con los usuarios semilla (FR-022d).

### Session 2026-07-02 — Ampliación por SDD V3

- Q: ¿Los nuevos campos de maestros de SDD V3 (facturación de cliente, portafolio de software,
  financieros de proyecto, perfil extendido y compensación de recurso) se agregan a esta spec o
  a una nueva? → A: Se amplía esta spec (FR-028..FR-034); son extensiones de las mismas cuatro
  pantallas de maestros ya construidas y prerequisito para iniciar la fase de Tickets.
- Q: ¿Cómo se protege la compensación del recurso? → A: Tabla separada 1..1 cifrada con pgcrypto
  (mismo patrón que VPN de clientes) + nuevo módulo de permisos `compensation` sembrado solo
  para Admin; los campos están ausentes del payload para roles sin permiso.
- Q: ¿El calendario de trabajo del recurso? → A: Solo se guarda el país base del calendario
  (texto/código de país); la administración de calendarios, feriados y ausencias es Fase 5 del
  roadmap SDD V3 (FR-034).
- Q: Información familiar del recurso (hijos, EPS, etc.) mencionada como "más adelante" en el
  SDD → A: Fuera de alcance de esta fase.

---

## Assumptions

- El sistema de autenticación Google OAuth2 restringido a `@sywork.net` ya está operativo
  (configurado en Fase de infraestructura previa al desarrollo de Maestros). Coexiste con un
  login provisional adicional por usuario/contraseña (ver FR-022b), pensado como mecanismo
  temporal mientras se valida el flujo completo.
- El enforcement de permisos en Fase 0 es solo a nivel de frontend (menús visibles según
  permisos). Las rutas de la API de maestros no exigen JWT ni validan permisos por endpoint en
  esta fase; ese enforcement queda diferido a una fase posterior (ver FR-017).
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
- El diseño detallado de roles/permisos/login provisional (modelo de datos, migración, rutas,
  matriz de permisos por rol, datos semilla) fue elaborado y aprobado en
  `docs/superpowers/specs/2026-07-01-roles-permissions-login-design.md` y ejecutado según
  `docs/superpowers/plans/2026-07-01-roles-permissions-login-backend.md`, fuera del flujo
  speckit. Los FR-001, FR-006b, FR-009, FR-010, FR-013, FR-015b, FR-022c y FR-022d de esta spec
  formalizan esas decisiones ya implementadas; en caso de discrepancia futura, ese diseño y la
  migración `009_roles_permissions_login.py` son la fuente de verdad de lo ya construido.
- La contraseña provisional de los 4 usuarios semilla es compartida y de un solo uso informativo
  (se imprime una vez en el log de la migración); rotarla o individualizarla por usuario queda
  fuera de alcance de Fase 0.
