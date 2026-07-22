# Feature Specification: Actualización Integral del Manual de Usuario

**Feature Branch**: `025-manual-usuario-integral`

**Created**: 2026-07-21

**Status**: Draft (alcance ampliado el 2026-07-21, ver nota abajo)

> **Nota de ampliación de alcance (2026-07-21)**: a pedido explícito del usuario, tras la primera
> entrega (6 vistas: Panel General, Kanban, Mis Tareas, Detalle de Ticket, Vista del Cliente, RRHH),
> el alcance de FR-005/FR-006/SC-002 se amplía para cubrir **todas** las pantallas vigentes de la
> aplicación (Maestros completo, Panel de Asignación, Tickets, Registro/Reporte de Tiempos, Login,
> Reseteo de contraseña, Mi Perfil), reemplazando los marcadores `[INSERTAR CAPTURA: ...]` por
> **capturas reales** tomadas navegando la aplicación en el entorno Docker de desarrollo. Se confirmó
> con el usuario que "pruebas pertinentes" significa verificación manual/documental (navegar la app y
> contrastar los diagramas contra el código), **no** ejecutar la suite automatizada de pytest/vitest
> — se mantiene la restricción original de no ejecutar pruebas automatizadas.

**Input**: User description: "Actualización Integral del Manual de Usuario (Manual_de_Usuario.docx) — actualizar el documento para reflejar el estado actual del sistema tras las últimas fases desarrolladas (Fase 0 a Fase 5 SDD V3 + specs 001-024): resumen arquitectónico orientado a usabilidad, diagramas de flujo Mermaid (ciclo de vida de Ticket, aprobación de vacaciones/permisos, regla de pausa/reanudación de SLA), guía paso a paso de módulos con marcadores de posición para capturas de pantalla, lenguaje amigable con tablas de ayuda rápida y notas de error comunes. Sesión de solo documentación: no modificar código ni ejecutar pruebas."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
-->

### User Story 1 - Un nuevo Resolutor aprende el ciclo de vida del Ticket (Priority: P1)

Un Resolutor que se incorpora al equipo abre el Manual de Usuario para entender cómo se crea, asigna, atiende y cierra un Ticket, qué comentarios estructurados debe usar en cada paso y cómo el sistema calcula y pausa el SLA mientras espera respuesta del usuario.

**Why this priority**: El ciclo de vida del Ticket es el flujo central del sistema (Principio II y FSM de la Constitución) y el punto de entrada obligatorio para cualquier persona nueva en el equipo. Sin esta sección el manual no cumple su propósito básico.

**Independent Test**: Puede validarse entregando solo la sección "Ciclo de vida de un Ticket" (con su diagrama Mermaid y guía paso a paso) a un Resolutor nuevo y verificando que puede identificar, sin ayuda externa, qué comentario usar para pasar de CONTACTO a EN ANÁLISIS y cuándo se pausa el SLA.

**Acceptance Scenarios**:

1. **Given** el manual actualizado, **When** el lector busca "cómo se reasigna un ticket a otro resolutor", **Then** encuentra el paso a paso con capturas de referencia y el efecto en el historial ("resolutor anterior ➡️ nuevo resolutor").
2. **Given** el manual actualizado, **When** el lector revisa el diagrama Mermaid del ciclo de vida del Ticket, **Then** el diagrama incluye todos los estados vigentes (NUEVO, PRE-ANÁLISIS, CONTACTO, EN ANÁLISIS, EN EJECUCIÓN, PENDIENTE DE USUARIO, RESUELTO, CERRADO) y los triggers de comentario estructurado que disparan cada transición.

---

### User Story 2 - Un responsable de RRHH explica el flujo de vacaciones/permisos (Priority: P2)

Un usuario con rol RRHH o un Jefe directo usa el manual para entender el flujo de doble aprobación de una solicitud de vacaciones o permiso, y cómo esa ausencia afecta la disponibilidad mostrada en la asignación/reasignación de tickets.

**Why this priority**: El módulo de RRHH (Calendarios, Franjas Horarias, Ausencias) es una fase completa del roadmap y alimenta directamente la disponibilidad usada en Asignación y Reasignación (spec 024); sin documentarlo el manual deja un módulo completo sin explicación operativa.

**Independent Test**: Puede validarse entregando solo la sección de RRHH (con el diagrama de aprobación) a un Jefe directo y verificando que identifica correctamente quién debe aprobar primero y qué pasa si el segundo aprobador rechaza.

**Acceptance Scenarios**:

1. **Given** el manual actualizado, **When** el lector consulta el diagrama de aprobación de vacaciones, **Then** distingue claramente el paso de aprobación del Jefe directo del paso de aprobación de RRHH y el resultado de cada camino (aprobado / rechazado).
2. **Given** el manual actualizado, **When** el lector busca "por qué un resolutor aparece como no disponible al reasignar", **Then** encuentra la explicación de las etiquetas de no disponibilidad (fuera de horario, festivo, ausencia) y su origen en el calendario/RRHH.

---

### User Story 3 - Un Coordinador entiende la regla de SLA y sus pausas (Priority: P2)

Un Coordinador o QM consulta el manual para entender cómo se calcula el tiempo límite de un ticket, en qué momentos el contador de SLA se pausa (por ejemplo, en PENDIENTE DE USUARIO o fuera de horario laboral) y cómo interpretar los indicadores visuales (✅/⚠️/❌) del historial de estados.

**Why this priority**: El motor de SLA dinámico (spec 022) es una regla de negocio no trivial (Principio VI, Gold Standard Dataset) que genera dudas frecuentes; documentarla reduce tickets de soporte interno sobre "por qué el SLA no avanzó".

**Independent Test**: Puede validarse entregando solo la sección de SLA (con su diagrama Mermaid de pausa/reanudación) a un Coordinador y verificando que puede explicar correctamente por qué el SLA de un ticket en PENDIENTE DE USUARIO no avanza durante un fin de semana.

**Acceptance Scenarios**:

1. **Given** el manual actualizado, **When** el lector revisa el diagrama de SLA, **Then** ve representados los tres factores que afectan el contador: horario laboral del recurso (Franjas Horarias/país), festivos, y estados que pausan el SLA (PENDIENTE DE USUARIO).
2. **Given** el manual actualizado, **When** el lector consulta el historial de estados de un ticket de ejemplo, **Then** encuentra la explicación de qué significa cada ícono (✅ cumplido, ⚠️ en riesgo, ❌ incumplido) junto al marcador de captura correspondiente.

---

### User Story 4 - Un Coordinador o Cliente navega las vistas principales del sistema (Priority: P3)

Un usuario nuevo (Coordinador, Resolutor, Encargado/Cliente) recorre la guía paso a paso de cada pantalla (Dashboard, Kanban, Mis Tareas, Vista del Cliente, Módulo de RRHH) para ubicar botones y campos sin tener que preguntar a un compañero.

**Why this priority**: Complementa las secciones de flujo con referencia de pantalla completa; es de menor prioridad porque el usuario puede explorar la interfaz por sí mismo una vez entiende los flujos centrales (US1-US3).

**Independent Test**: Puede validarse entregando solo la guía de una pantalla (por ejemplo, Kanban) y verificando que el lector identifica la función de cada botón/campo descrito sin acceder al sistema real.

**Acceptance Scenarios**:

1. **Given** el manual actualizado, **When** el lector abre la sección "Kanban", **Then** encuentra el marcador `[INSERTAR CAPTURA: ...]` correspondiente junto a la descripción de qué representa cada columna y qué acción dispara el arrastre de una tarjeta.
2. **Given** el manual actualizado, **When** el lector abre la sección "Vista del Cliente", **Then** encuentra qué información puede ver y qué acciones puede realizar un Encargado/Cliente, diferenciándolas de las de un Coordinador.

### Edge Cases

- ¿Qué debe hacer el lector si en un ticket no ve la opción "Reasignar"? → El manual debe indicar que depende del rol/permiso del usuario y remitir a la tabla de roles y permisos.
- ¿Cómo se documenta una pantalla que aún no tiene todas sus reglas cerradas en el SDD (ejemplo: estado EN PRUEBAS, marcado como pendiente de definición en la Constitución)? → El manual debe señalar explícitamente que ese estado está pendiente de definición, sin inventar comportamiento.
- ¿Qué pasa si el lector abre el manual en una fase futura donde ya no existan capturas de pantalla insertadas? → Los marcadores de captura deben quedar identificables (formato uniforme) para que puedan completarse o actualizarse sin rehacer el texto.
- ¿Cómo se comunica al lector que un módulo mostrado (ej. Focus Room, Portal de clientes) todavía no está implementado? → El manual debe distinguir explícitamente funcionalidades vigentes (Fases 0-5 SDD V3) de funcionalidades futuras del roadmap, para no generar expectativas incorrectas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El manual DEBE incluir un resumen arquitectónico no técnico que explique cómo se relacionan los módulos Proyectos, Tickets/Tareas, Calendarios/RRHH, Registro de Tiempo y SLA, usando lenguaje orientado a usabilidad (sin jerga de código, sin nombres de archivos ni endpoints).
- **FR-002**: El manual DEBE incluir un diagrama de flujo en formato Mermaid del ciclo de vida completo de un Ticket, cubriendo creación, asignación, reasignación, registro de tiempo y cierre, con los estados y triggers de comentario vigentes según la Constitución del proyecto.
- **FR-003**: El manual DEBE incluir un diagrama de flujo en formato Mermaid del proceso de solicitud y aprobación de vacaciones/permisos, mostrando el paso de doble aprobación (Jefe directo + rol RRHH) y sus resultados posibles.
- **FR-004**: El manual DEBE incluir un diagrama de flujo en formato Mermaid de la regla de SLA, mostrando cuándo el contador corre, cuándo se pausa (estado PENDIENTE DE USUARIO, fuera de horario laboral, festivo) y cuándo se reanuda.
- **FR-005**: El manual DEBE incluir una guía paso a paso por cada vista principal del sistema vigente: Dashboard, Kanban, Mis Tareas, Detalle de Ticket (incluyendo historial de SLA y reasignación de resolutor), Vista del Cliente/Encargado y Módulo de RRHH (Calendarios, Ausencias, Franjas Horarias).
- **FR-006**: Cada vista documentada en la guía paso a paso DEBE incluir al menos un marcador explícito de captura de pantalla en el formato `[INSERTAR CAPTURA: descripción específica]`, acompañado de una descripción textual de qué debe verse y qué hace cada botón/campo relevante.
- **FR-007**: El manual DEBE usar lenguaje amigable y no técnico, estructurado con viñetas y encabezados claros, evitando términos de implementación (nombres de tablas, componentes, endpoints).
- **FR-008**: El manual DEBE incluir al menos una tabla de "ayuda rápida" (referencia corta de acciones frecuentes o de roles y permisos) que el lector pueda consultar sin leer el texto completo.
- **FR-009**: El manual DEBE incluir bloques de nota o advertencia (formato visualmente distinguible) para casos comunes de error o confusión del usuario (ejemplo: "no veo el botón Reasignar", "el SLA no avanza").
- **FR-010**: El manual DEBE reflejar únicamente funcionalidades ya implementadas hasta la fase más reciente completada (spec 024 — sugerencias de carga y disponibilidad en la reasignación) y distinguir explícitamente cualquier funcionalidad de fases futuras del roadmap que se mencione como contexto.
- **FR-011**: El contenido final DEBE producirse en un archivo `docs/Manual_de_Usuario.md` con estructura y formato lista para exportar a Word/PDF (encabezados jerárquicos, tablas en formato Markdown, bloques de diagrama Mermaid en fences ```mermaid), dado que la edición directa de un `.docx` binario no es una operación soportada en esta sesión.
- **FR-012**: El manual DEBE mantener consistencia terminológica con los documentos fuente del proyecto (Constitución, specs 001-024): mismos nombres de estado, mismos nombres de rol (Coordinador, Resolutor, QM, RRHH, Encargado/Cliente) y misma nomenclatura de campos visibles en pantalla.

### Key Entities

- **Sección del Manual**: Bloque de contenido documental (resumen arquitectónico, diagrama de flujo, guía de módulo) con un título, un propósito y, cuando aplica, un diagrama Mermaid asociado.
- **Marcador de Captura**: Referencia textual dentro de una guía de módulo que indica dónde debe insertarse una imagen real de pantalla, junto con la descripción de su contenido esperado.
- **Diagrama de Flujo**: Representación Mermaid de un proceso del negocio (ciclo de vida de Ticket, aprobación de ausencias, regla de SLA) construida a partir de las reglas vigentes documentadas en la Constitución y en las specs de fases relacionadas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un lector sin conocimiento previo del sistema puede identificar, leyendo solo el resumen arquitectónico, qué módulo alimenta a cuál (por ejemplo, que RRHH/Calendarios alimenta la disponibilidad de Asignación) en menos de 3 minutos.
- **SC-002**: El manual cubre el 100% de las vistas principales vigentes listadas en el alcance (Dashboard, Kanban, Mis Tareas, Detalle de Ticket, Vista del Cliente, Módulo de RRHH) con al menos un marcador de captura y su descripción cada una.
- **SC-003**: Los tres diagramas de flujo solicitados (Ticket, Vacaciones/Permisos, SLA) están presentes, son sintácticamente válidos en formato Mermaid y reflejan los mismos estados/roles definidos en la Constitución del proyecto, sin discrepancias.
- **SC-004**: Un lector que busca cómo resolver un caso de error común (ejemplo: "no veo el botón Reasignar") encuentra la respuesta en un bloque de nota/advertencia dedicado, sin necesidad de leer el manual completo.
- **SC-005**: El archivo de salida (`docs/Manual_de_Usuario.md`) se abre y renderiza correctamente (encabezados, tablas y diagramas) en un visor Markdown estándar, quedando listo para una conversión posterior a `.docx`/PDF sin reestructurar el contenido.

## Assumptions

- No es técnicamente posible en esta sesión editar directamente el binario `docs/Manual_de_Usuario.docx`; por lo tanto el entregable de esta especificación es el contenido estructurado en `docs/Manual_de_Usuario.md`, listo para exportar/pegar a Word o convertir a PDF. La conversión final al `.docx` queda como paso manual o de una sesión posterior con la skill de manejo de documentos Word.
- No se cuenta con acceso para tomar capturas de pantalla reales dentro de esta sesión de documentación; todas las referencias visuales se dejan como marcadores explícitos `[INSERTAR CAPTURA: ...]` con descripción detallada para que se completen posteriormente.
- El alcance del manual cubre las funcionalidades implementadas hasta la spec 024 (reasignación con sugerencias de carga y disponibilidad) inclusive; specs o fases futuras del roadmap (Focus Room, agente IA, Portal de clientes) se mencionan solo como contexto de evolución, no como funcionalidad actual.
- Los roles documentados (Coordinador, Resolutor, QM, RRHH, Encargado/Cliente, Administrador) y el catálogo de estados del ticket son los definidos en `.specify/memory/constitution.md`; cualquier cambio posterior a esos catálogos requerirá una actualización posterior del manual, fuera de esta especificación.
- El manual se redacta en español, consistente con el resto de la documentación del proyecto (specs, constitución).
