# Feature Specification: Usuario/cliente por Proyecto, Asignación de Personal y Estructura de Skills

**Feature Branch**: `010-proyecto-personal-skills`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Refactorización de Relaciones del Proyecto, Asignación de Personal
y Estructura de Skills — (1) Renombrar rol 'Encargado' a 'Usuario/cliente' en todo el sistema
(BD, modelos, UI) y cambiar su relación: ya no se asocia al Ticket de forma aislada sino
directamente al Proyecto. (2) Asignación de Personal en el Proyecto estilo Teamwork: sección
'Asignar Personal' en la vista de edición del Proyecto, listar/asignar cualquier usuario del
sistema, múltiples tipos de personal (Resolutores, Coordinadores, Usuario/cliente, etc.),
sección visual 'Equipo' para agrupar personal en subgrupos dentro del proyecto. (3) Estructura
de Skill con campos 'herramientas' (opcional), 'proceso' (opcional) y 'type' (obligatorio), con
seeders de ejemplos base. Directrices estrictas: modificar solo migraciones, modelos y
componentes UI directamente afectados; no refactorizar nada más; no ejecutar la suite completa
de tests, solo tests específicos de lo modificado."

**Contexto (estado actual, specs `005`/`007`)**: hoy el rol se llama **Encargado** y su perfil
(`ClientContact`) lo vincula únicamente a un **Cliente**. El Ticket guarda una referencia
directa al Encargado solicitante, y la lista de Encargados seleccionables al crear/editar un
ticket se filtra **por Cliente**. Esta spec renombra el rol a **"Usuario/cliente"** y mueve la
relación al nivel de **Proyecto**: el Usuario/cliente pasa a formar parte del personal asignado
a uno o más Proyectos, junto con el resto de roles internos (Resolutor, Coordinador, QM,
Admin), replicando el modelo de gestión de personas de Teamwork (pestañas "Personas" y
"Equipos" dentro del proyecto).

**Alcance estricto (directriz del solicitante)**: modificar únicamente las migraciones, modelos
y componentes de UI directamente afectados por los tres puntos. Nada de refactorizaciones
colaterales. La validación se hace con tests dirigidos a lo modificado — NO ejecutar la suite
completa de forma masiva durante el desarrollo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Renombrar "Encargado" a "Usuario/cliente" en todo el sistema (Priority: P1)

Cualquier usuario del sistema (Admin, Coordinador, Resolutor o el propio usuario externo) ve el
rol y el concepto "Usuario/cliente" en lugar de "Encargado" en todas las pantallas, menús,
etiquetas, mensajes y listados donde hoy aparece "Encargado". El nombre del rol almacenado
también cambia, de modo que reportes y administración de roles muestren el nuevo nombre.

**Why this priority**: es un cambio de nomenclatura transversal que condiciona el vocabulario
de las otras dos historias (la sección de personal del Proyecto lista "Usuario/cliente" como
tipo de personal); hacerlo primero evita introducir pantallas nuevas con el nombre viejo.

**Independent Test**: recorrer las pantallas que hoy muestran "Encargado" (alta de usuario
externo, detalle/creación de ticket, listado de contactos, roles y permisos) y confirmar que
todas muestran "Usuario/cliente"; iniciar sesión con un usuario de ese rol y confirmar que su
experiencia (crear tickets de autoservicio para su Cliente) sigue intacta.

**Acceptance Scenarios**:

1. **Given** el sistema con el rol hoy llamado "Encargado", **When** un Admin abre la pantalla
   de Roles y Permisos, **Then** el rol aparece como "Usuario/cliente" conservando exactamente
   los mismos permisos que tenía.
2. **Given** un usuario externo existente con el rol renombrado, **When** inicia sesión,
   **Then** conserva su acceso y restricciones actuales (autoservicio de tickets de su Cliente,
   sin acceso a Maestros/Catálogos/Panel de Asignación) — el renombre no altera comportamiento.
3. **Given** cualquier pantalla que hoy muestra la palabra "Encargado" (alta simplificada,
   detalle de ticket, selector de solicitante, listado de contactos), **When** se navega tras el
   cambio, **Then** el texto visible dice "Usuario/cliente" en todos los casos.

---

### User Story 2 - Usuario/cliente vinculado al Proyecto (Priority: P1)

Un Coordinador (o Admin) asocia a un Usuario/cliente con uno o más **Proyectos** de su Cliente.
A partir de ahí, la relación operativa del Usuario/cliente con el trabajo (tickets, tareas) se
deriva de su pertenencia al Proyecto: al crear o editar un ticket de un Proyecto, la lista de
Usuario/cliente seleccionables como solicitante son los vinculados a ese Proyecto. El Ticket
**conserva** su campo "solicitante" (spec `007`) — lo que cambia es la fuente de la lista: del
filtro por Cliente actual al personal del Proyecto (decisión de clarificación, 2026-07-09).

**Why this priority**: es el cambio de relación crítico solicitado — sin él, la sección de
personal del Proyecto (Historia 3) no tendría al Usuario/cliente como tipo de personal
asignable, y el vínculo seguiría siendo por Cliente de forma aislada.

**Independent Test**: vincular un Usuario/cliente a un Proyecto A (y no al Proyecto B del mismo
Cliente), crear un ticket en cada proyecto y verificar que el Usuario/cliente solo es
seleccionable/visible en el del Proyecto A.

**Acceptance Scenarios**:

1. **Given** un Usuario/cliente de un Cliente con dos Proyectos, **When** un Coordinador lo
   vincula solo al Proyecto A, **Then** en el Proyecto B ese Usuario/cliente no aparece como
   personal ni como solicitante seleccionable.
2. **Given** los tickets existentes que hoy referencian a un Encargado, **When** se aplica el
   cambio de relación, **Then** ningún ticket pierde la información de su solicitante actual
   (la migración conserva el dato histórico).
3. **Given** un Usuario/cliente vinculado a un Proyecto, **When** intenta crear un ticket de
   autoservicio, **Then** solo puede hacerlo sobre Proyectos a los que está vinculado (dentro
   de su Cliente fijo).
4. **Given** un Usuario/cliente cuyo vínculo con un Proyecto se retira, **When** se consultan
   los tickets históricos de ese Proyecto donde figura como solicitante, **Then** el histórico
   permanece intacto y legible.

---

### User Story 3 - Asignar Personal al Proyecto con sección "Equipo" (estilo Teamwork) (Priority: P1)

Un Coordinador (o Admin) abre la vista de edición de un Proyecto y encuentra una sección
"Asignar Personal": puede listar y asignar **cualquier usuario existente** del sistema al
proyecto (Resolutores, Coordinadores, QM, Usuario/cliente, etc.), viendo de cada persona su
nombre, correo y tipo/rol. Además, dentro del Proyecto existe un apartado visual "Equipo" que
permite agrupar el personal asignado en subgrupos con nombre (p. ej. "Infraestructura",
"Sywork LAB"), tal como las pestañas Personas/Equipos de Teamwork.

**Why this priority**: es la funcionalidad visible central de la spec — habilita la gestión de
personal por proyecto y es el mecanismo por el que el Usuario/cliente queda vinculado al
Proyecto (Historia 2).

**Independent Test**: en la edición de un Proyecto, asignar un Resolutor, un Coordinador y un
Usuario/cliente; crear un subgrupo "Equipo X" con dos de ellos; verificar el listado de
personas (con su tipo) y de equipos (con sus miembros y conteo).

**Acceptance Scenarios**:

1. **Given** un Proyecto sin personal asignado, **When** el Coordinador abre "Asignar
   Personal", **Then** puede buscar entre todos los usuarios activos del sistema y asignar a
   cualquiera, quedando visible en la lista de personas del proyecto con su rol/tipo.
2. **Given** un Proyecto con personal de varios roles asignado, **When** se consulta la sección
   de personas, **Then** se muestran todas las personas con nombre, correo y tipo, sin importar
   el rol (Resolutor, Coordinador, QM, Usuario/cliente, Admin).
3. **Given** personal asignado a un Proyecto, **When** el Coordinador crea un subgrupo en la
   sección "Equipo" y agrega miembros, **Then** el subgrupo muestra nombre y miembros, y una
   persona puede pertenecer a más de un subgrupo.
4. **Given** una persona asignada a un Proyecto y miembro de un subgrupo, **When** se elimina
   el subgrupo, **Then** la persona sigue asignada al Proyecto (el subgrupo es solo una
   agrupación visual, no la fuente de la asignación).
5. **Given** una persona asignada a un Proyecto, **When** el Coordinador la desasigna,
   **Then** desaparece de la lista de personas y de todos los subgrupos del proyecto, sin
   afectar los registros históricos (tickets, tiempos) donde participó.

---

### User Story 4 - Estructura de Skill con herramienta, proceso y tipo + semillas (Priority: P2)

Un Admin administra el catálogo de Skills y cada Skill ahora declara: una **herramienta**
(opcional, del catálogo de herramientas existente), un **proceso** (opcional, del catálogo de
procesos existente) y un **tipo** (obligatorio: **funcional** o **técnico**). El sistema
incluye por defecto un conjunto semilla de skills de ejemplo con estos tres campos poblados.

**Why this priority**: enriquece el maestro de Skills para el futuro Triage Agent (Principio
VI — skills parametrizados), pero no bloquea la operación diaria de proyectos ni tickets.

**Independent Test**: consultar el catálogo de Skills tras aplicar los cambios y verificar que
las semillas traen herramienta/proceso/tipo según la tabla de referencia; crear una skill nueva
sin tipo y confirmar el rechazo; crearla con tipo y sin herramienta/proceso y confirmar que se
acepta.

**Acceptance Scenarios**:

1. **Given** el catálogo de Skills tras la actualización, **When** se listan las skills,
   **Then** existen las semillas: JDE_GL (JDE · Finanzas · funcional), JDE_AP (JDE · Compras ·
   funcional), JDE_MTC (JDE · Mantenimiento · funcional), BSFN (JDE · — · técnico), SQL_JDE
   (JDE · — · técnico), OIC (Oracle Fusion · Integraciones · técnico), APEX (— · — · técnico),
   BI (— · — · técnico), JAVA / PYTHON / REACT (— · — · técnico), DBA (— · — · técnico).
2. **Given** el formulario de Skill, **When** se intenta guardar una skill sin tipo, **Then**
   el sistema la rechaza indicando que el tipo es obligatorio.
3. **Given** el formulario de Skill, **When** se guarda una skill con tipo pero sin herramienta
   ni proceso, **Then** se acepta (ambos son opcionales).
4. **Given** las skills preexistentes en el sistema (p. ej. JDE_AR, ORACLE_FUSION, API_REST),
   **When** se aplica el cambio, **Then** todas quedan con un tipo asignado (ninguna skill
   queda sin tipo) y conservan sus asociaciones con recursos.

---

### Edge Cases

- ¿Qué pasa con un Usuario/cliente vinculado a un Cliente que no tiene ningún Proyecto activo?
  Puede existir, pero no podrá crear tickets de autoservicio hasta ser vinculado a un Proyecto.
- ¿Qué pasa si se desactiva un usuario que está asignado a Proyectos? Deja de aparecer como
  asignable y como seleccionable, pero su participación histórica permanece visible.
- ¿Qué pasa con los tickets creados antes del cambio cuyo Encargado no quede vinculado al
  Proyecto del ticket? El dato histórico del solicitante se conserva; la migración vincula
  automáticamente a cada Usuario/cliente con los Proyectos donde ya figura como solicitante,
  para no dejar relaciones huérfanas.
- ¿Puede un mismo usuario asignarse dos veces al mismo Proyecto? No — la asignación es única
  por persona y proyecto; reintentarlo no duplica.
- ¿Un subgrupo "Equipo" puede quedar vacío? Sí — puede crearse antes de agregar miembros.
- ¿Los procesos "Compras" y "Mantenimiento" existen hoy en el catálogo de procesos? No — las
  semillas de skills los requieren, por lo que deben agregarse al catálogo como parte de las
  semillas (sin borrar los existentes).
- ¿Qué pasa al guardar una skill semilla que ya existe (JDE_GL, JDE_AP)? Se actualiza con los
  nuevos campos en lugar de duplicarse (el código de skill es único).

## Requirements *(mandatory)*

### Functional Requirements

**Renombre de rol (US1)**

- **FR-001**: El sistema DEBE mostrar "Usuario/cliente" en lugar de "Encargado" en todas las
  interfaces de usuario: menús, formularios de alta, listados, selector de solicitante en el
  ticket, pantalla de roles y permisos, y mensajes/validaciones.
- **FR-002**: El nombre del rol almacenado DEBE cambiar a "Usuario/cliente", conservando el
  mismo conjunto de permisos y las mismas asignaciones de usuarios existentes.
- **FR-003**: El renombre NO DEBE alterar el comportamiento existente del rol: autoservicio de
  tickets restringido a su Cliente, alta simplificada (email/usuario + contraseña provisional),
  sin acceso a Maestros/Catálogos/Panel de Asignación.

**Relación con el Proyecto (US2)**

- **FR-004**: El sistema DEBE permitir vincular un Usuario/cliente a uno o más Proyectos de su
  Cliente (no a Proyectos de otros Clientes).
- **FR-005**: El Ticket DEBE conservar su campo "solicitante" (Usuario/cliente); la lista de
  seleccionables al crear/editar un ticket DEBE derivarse del Proyecto del ticket (personal
  vinculado a ese Proyecto), en lugar del filtro por Cliente actual. Las reglas existentes de
  la spec `007` (limpieza al cambiar Cliente/Proyecto, bloqueo en autoservicio y estados
  finales) se mantienen, ajustadas a la nueva fuente.
- **FR-006**: La migración de datos DEBE conservar toda referencia histórica de tickets a su
  solicitante actual y vincular automáticamente a cada Usuario/cliente con los Proyectos donde
  ya figura como solicitante de tickets.
- **FR-007**: El autoservicio del Usuario/cliente DEBE quedar acotado a los Proyectos a los que
  está vinculado (dentro de su Cliente fijo).

**Personal del Proyecto (US3)**

- **FR-008**: La vista de edición del Proyecto DEBE incluir una sección "Asignar Personal" que
  permita buscar y asignar cualquier usuario activo del sistema, sin restricción de rol.
- **FR-009**: La asignación de personal DEBE ser única por persona y Proyecto, y removible sin
  afectar registros históricos (tickets, tiempos, comentarios).
- **FR-010**: La sección de personas del Proyecto DEBE listar el personal asignado mostrando al
  menos nombre, correo y tipo/rol de cada persona.
- **FR-011**: El Proyecto DEBE ofrecer un apartado "Equipo" para crear subgrupos con nombre y
  agrupar en ellos personal ya asignado al Proyecto; una persona puede pertenecer a varios
  subgrupos; eliminar un subgrupo no desasigna a sus miembros del Proyecto.
- **FR-012**: Solo roles con permiso de gestión (Coordinador, Admin) DEBEN poder asignar/
  desasignar personal y administrar subgrupos; los demás roles pueden consultar la sección.

**Estructura de Skills (US4)**

- **FR-013**: Cada Skill DEBE declarar un tipo obligatorio con valores "funcional" o "técnico";
  el sistema DEBE rechazar skills sin tipo.
- **FR-014**: Cada Skill PUEDE declarar una herramienta (del catálogo de herramientas) y un
  proceso (del catálogo de procesos); ambos opcionales.
- **FR-015**: El sistema DEBE incluir semillas con las 10 skills de referencia (JDE_GL, JDE_AP,
  JDE_MTC, BSFN, SQL_JDE, OIC, APEX, BI, JAVA / PYTHON / REACT, DBA) con su herramienta,
  proceso y tipo según la tabla de la Historia 4; las que ya existan por código se actualizan,
  no se duplican.
- **FR-016**: Las semillas DEBEN agregar al catálogo de procesos los valores requeridos que no
  existan ("Compras", "Mantenimiento") sin eliminar los existentes.
- **FR-017**: Toda skill preexistente DEBE quedar con un tipo asignado tras la migración
  (backfill), conservando sus asociaciones con recursos.
- **FR-018**: La pantalla de administración de Skills DEBE permitir ver y editar herramienta,
  proceso y tipo de cada skill.

**Alcance (transversal)**

- **FR-019**: Los cambios DEBEN limitarse a las migraciones, modelos/entidades, servicios y
  componentes de UI directamente afectados por FR-001..FR-018; queda fuera de alcance cualquier
  refactorización colateral.
- **FR-020**: La verificación durante el desarrollo DEBE hacerse con tests dirigidos a lo
  modificado; la suite completa NO se ejecuta de forma masiva como parte del ciclo de
  desarrollo de esta feature.

### Key Entities

- **Usuario/cliente** (antes "Encargado"): usuario externo de un Cliente; conserva su Cliente
  fijo y ahora se vincula a uno o más Proyectos de ese Cliente a través del personal del
  Proyecto.
- **Personal del Proyecto** (nueva relación): vínculo persona ↔ Proyecto, válido para
  cualquier usuario del sistema (interno o externo), único por par persona/proyecto, con fecha
  de asignación.
- **Subgrupo de Proyecto ("Equipo")** (nueva): agrupación con nombre dentro de un Proyecto que
  contiene personal ya asignado; relación muchos-a-muchos con las personas del proyecto.
- **Skill** (ampliada): además de código y etiqueta, declara tipo (obligatorio: funcional |
  técnico), herramienta (opcional, catálogo de herramientas) y proceso (opcional, catálogo de
  procesos).
- **Ticket** (afectada): conserva su campo de solicitante (Usuario/cliente), que pasa a
  alimentarse del personal vinculado al Proyecto del ticket.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% de las pantallas y textos que hoy muestran "Encargado" muestran
  "Usuario/cliente" tras el cambio (verificable recorriendo las pantallas afectadas).
- **SC-002**: Un Coordinador puede asignar una persona a un Proyecto y verla listada con su
  tipo en menos de 1 minuto desde la vista de edición del Proyecto.
- **SC-003**: 0 tickets pierden la referencia a su solicitante tras la migración (conteo de
  referencias antes y después idéntico).
- **SC-004**: Un Usuario/cliente vinculado a un solo Proyecto no aparece como seleccionable en
  ningún otro Proyecto (0 fugas de visibilidad entre proyectos).
- **SC-005**: El catálogo de Skills queda con las 10 semillas de referencia completas
  (herramienta/proceso/tipo) y 0 skills sin tipo en todo el sistema.
- **SC-006**: Los flujos existentes no cubiertos por esta spec (transiciones de ticket,
  registro de tiempos, Listas/Subtareas) siguen funcionando sin cambios (verificación dirigida,
  sin regresión).

## Assumptions

- El Usuario/cliente conserva su Cliente fijo (la vinculación a Proyectos es adicional y
  siempre dentro de ese Cliente); no se habilitan Usuario/cliente multi-Cliente.
- Los subgrupos "Equipo" son internos a cada Proyecto (no equipos globales de la empresa como
  en Teamwork corporativo); el nombre es libre y único dentro del Proyecto.
- La sección "Asignar Personal" vive en la vista de edición/detalle del Proyecto existente
  (pestañas o secciones dentro de la misma pantalla), replicando el patrón Personas/Equipos de
  Teamwork mostrado como referencia.
- La asignación de personal al Proyecto es informativa/organizativa en esta fase: no altera las
  reglas de asignación de tickets (Triage/Panel de Asignación) ni los permisos de los roles
  internos; el único efecto funcional nuevo es el vínculo Usuario/cliente ↔ Proyecto.
- Los valores de tipo de skill son exactamente dos: "funcional" y "técnico" (según la tabla de
  referencia aportada por el solicitante).
- Backfill de tipo para skills preexistentes no incluidas en la tabla de referencia: JDE_AR y
  ORACLE_CRM como "funcional"; ORACLE_FUSION, API_REST, SQL_ORACLE y ORCHESTRATOR como
  "técnico" (mejor esfuerzo, editable después desde la pantalla de Skills).
- "Herramienta" y "proceso" de la skill reutilizan los catálogos administrables existentes de
  herramientas y procesos (los mismos que clasifican tickets); no se crean catálogos nuevos.
- El renombre no requiere migrar credenciales ni sesiones: los usuarios existentes del rol
  siguen entrando con sus credenciales actuales.
