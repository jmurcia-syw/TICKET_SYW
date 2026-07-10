# Feature Specification: Manejo Global de Errores y Notificaciones (API a Frontend)

**Feature Branch**: `013-manejo-errores-notificaciones`

**Created**: 2026-07-10

**Status**: Draft

**Input**: User description: "Implementación de Manejo Global de Errores y Notificaciones (API a Frontend). Actualmente, cuando la API del Backend devuelve un error, el Frontend no muestra ninguna alerta visual al usuario (la aplicación simplemente 'no funciona' o se congela sin dar feedback). Necesito estandarizar las respuestas de error y notificarlas correctamente en la interfaz."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El usuario ve una alerta visual inmediata cuando una operación falla (Priority: P1)

Un usuario (Coordinador, Resolutor, Encargado, etc.) realiza una acción en la aplicación
(guardar un ticket, asignar personal, cambiar un estado) y la operación falla en el servidor.
Hoy la aplicación no reacciona: no aparece ningún mensaje y el usuario no sabe si su acción
se aplicó o no. Con esta feature, ante cualquier error del servidor aparece de inmediato una
notificación visual (toast/alerta) con el motivo del fallo.

**Why this priority**: Es el dolor principal reportado — la app "se congela" sin feedback.
Aunque el backend aún devuelva errores con formatos heterogéneos, capturar todo error HTTP y
mostrarlo ya elimina la sensación de aplicación rota.

**Independent Test**: Provocar cualquier error de API (p. ej. intentar una acción sin permisos)
y verificar que aparece una notificación visual en pantalla en el momento del fallo, sin
necesidad de abrir la consola del navegador.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado en cualquier pantalla, **When** una llamada a la API responde
   con un error (4xx o 5xx), **Then** aparece inmediatamente una notificación visual con el
   mensaje del error y la pantalla no queda congelada ni en estado de carga indefinida.
2. **Given** una respuesta de error que incluye un mensaje descriptivo del servidor, **When** se
   muestra la notificación, **Then** el texto mostrado es exactamente el mensaje enviado por el
   servidor (p. ej. "El ticket no está asignado a este proyecto").
3. **Given** una respuesta de error sin mensaje interpretable (error de red, respuesta no JSON,
   error 500 sin cuerpo), **When** se muestra la notificación, **Then** el texto es un mensaje
   genérico amigable: "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo".

---

### User Story 2 - Las respuestas de error de la API tienen una estructura estándar (Priority: P2)

Quien consume la API (el frontend hoy; integraciones o agentes IA mañana) recibe siempre la
misma estructura de error cuando algo falla en **cualquier endpoint de la API** (Tickets,
Proyectos, Asignaciones, Maestros, Personal/Skills, Tiempos, Autenticación, etc.): un indicador
de fallo, un mensaje legible para el usuario final y un código de error identificable, junto
con el código de estado HTTP correcto.

**Why this priority**: Sin estructura estándar, el frontend solo puede mostrar mensajes
genéricos. La estandarización habilita que el mensaje exacto del negocio llegue al usuario y
que los errores sean identificables por código. La revisión y ajuste debe realizarse en todos
los endpoints, priorizando en la verificación los de Tickets, Proyectos y Asignaciones.

**Independent Test**: Invocar directamente endpoints de cada módulo de la API provocando
errores conocidos (recurso inexistente, sin permisos, datos inválidos) y verificar
que cada respuesta contiene `success: false`, `message` y `code`, con el estado HTTP apropiado
(400, 403, 404, etc.).

**Acceptance Scenarios**:

1. **Given** cualquier endpoint de la API, **When** falla una validación de negocio, **Then** la
   respuesta tiene estado HTTP 400 y cuerpo `{ "success": false, "message": "<motivo>", "code": "<CÓDIGO>" }`.
2. **Given** un usuario sin el permiso requerido, **When** invoca un endpoint protegido, **Then**
   la respuesta tiene estado HTTP 403 con la misma estructura estándar y un mensaje entendible.
3. **Given** un identificador de recurso inexistente (ticket, proyecto), **When** se consulta o
   modifica, **Then** la respuesta tiene estado HTTP 404 con la estructura estándar.
4. **Given** un error interno no controlado en el servidor, **When** ocurre, **Then** la
   respuesta tiene estado HTTP 500 con la estructura estándar y un mensaje genérico, sin exponer
   detalles internos (stack traces, consultas SQL) — conforme al Principio IV de la constitución.

---

### User Story 3 - Los casos críticos del negocio muestran su mensaje específico (Priority: P3)

Un usuario que dispara uno de los errores de negocio conocidos — "Ticket no asignado a este
proyecto", "Usuario sin permisos", "Proyecto no encontrado" — ve en pantalla el mensaje
específico de ese error, no uno genérico.

**Why this priority**: Es la validación de punta a punta de las dos historias anteriores sobre
los flujos que más confusión generan hoy. Depende de que P1 y P2 estén implementadas.

**Independent Test**: Reproducir cada uno de los tres casos críticos desde la interfaz y
comprobar que la alerta visual aparece inmediatamente con el texto específico del error.

**Acceptance Scenarios**:

1. **Given** un ticket no asociado al proyecto seleccionado, **When** el usuario intenta la
   operación que los relaciona, **Then** aparece la notificación "El ticket no está asignado a
   este proyecto" (o el mensaje exacto que devuelva el servidor para ese caso).
2. **Given** un usuario sin permisos para una acción, **When** la intenta desde la interfaz,
   **Then** aparece una notificación indicando que no tiene permisos para esa acción.
3. **Given** un proyecto eliminado o inexistente, **When** el usuario intenta acceder a él,
   **Then** aparece una notificación indicando que el proyecto no fue encontrado.

---

### Edge Cases

- ¿Qué pasa si el servidor no responde (caída de red, timeout)? → Notificación con el mensaje
  genérico amigable; la interfaz no queda en estado de carga indefinida.
- ¿Qué pasa con respuestas de error que no siguen la estructura estándar (algún endpoint que
  escape a la revisión)? → El frontend intenta extraer un mensaje razonable; si no puede, usa
  el genérico. Esto es una red de seguridad, no una excepción permitida: la revisión debe
  cubrir todos los endpoints.
- ¿Qué pasa con el error 401 (sesión expirada)? → Se conserva el comportamiento actual de
  redirección al login; no debe duplicarse con una notificación adicional confusa.
- ¿Qué pasa si varias llamadas fallan a la vez (p. ej. al cargar un dashboard)? → El usuario no
  debe ser inundado: notificaciones duplicadas con el mismo mensaje en una ventana corta de
  tiempo se muestran una sola vez.
- ¿Qué pasa con errores de validación de formularios que la pantalla ya maneja localmente? → La
  notificación global no debe duplicar mensajes que el formulario ya muestra en línea.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: TODOS los endpoints de la API DEBEN devolver, ante cualquier fallo, una
  estructura JSON consistente con tres campos: `success` (false), `message` (texto legible para
  el usuario final, en español) y `code` (identificador estable del error en UPPER_SNAKE_CASE,
  p. ej. `TICKET_NOT_ASSIGNED`). La revisión y ajuste cubre todos los módulos de la API;
  la verificación prioriza Tickets, Proyectos y Asignaciones.
- **FR-002**: Cada respuesta de error DEBE usar el código de estado HTTP semánticamente
  correcto: 400 para validaciones de negocio/datos inválidos, 403 para falta de permisos,
  404 para recursos inexistentes, 500 para errores internos no controlados.
- **FR-003**: Los errores internos no controlados (500) NO DEBEN exponer detalles de
  implementación (stack traces, consultas, rutas internas) en el cuerpo de la respuesta.
- **FR-004**: El frontend DEBE capturar de forma centralizada (en un único punto del cliente
  HTTP) todas las respuestas de error de la API, sin requerir cambios pantalla por pantalla.
- **FR-005**: Ante un error capturado con `message` interpretable, el frontend DEBE mostrar una
  notificación visual inmediata con ese texto exacto.
- **FR-006**: Ante un error sin mensaje interpretable (error de red, cuerpo no JSON, estructura
  desconocida), el frontend DEBE mostrar el mensaje genérico "Ha ocurrido un error inesperado.
  Por favor, inténtalo de nuevo".
- **FR-007**: El manejo actual del error 401 (redirección al login) DEBE conservarse sin
  mostrar notificación de error adicional.
- **FR-008**: Las notificaciones de error duplicadas (mismo mensaje) generadas en una ventana
  corta de tiempo DEBEN colapsarse en una sola para no saturar al usuario.
- **FR-009**: Los tres casos críticos — ticket no asignado al proyecto, usuario sin permisos,
  proyecto no encontrado — DEBEN quedar verificados de punta a punta: el error del servidor
  llega con su estructura estándar y la notificación visual aparece con el mensaje específico.

### Key Entities

- **Respuesta de error estándar**: contrato de fallo de la API; atributos: indicador de éxito
  (siempre falso), mensaje legible para el usuario, código estable del error, estado HTTP.
  No se persiste; es un contrato de comunicación.
- **Notificación visual de error**: aviso efímero en la interfaz; atributos: texto del mensaje,
  severidad (error), duración de exhibición. No se persiste.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los fallos de API en cualquier flujo de la aplicación produce una
  notificación visual visible para el usuario en el momento del fallo (hoy: 0%).
- **SC-002**: Los tres casos críticos (ticket no asignado, sin permisos, proyecto no encontrado)
  muestran su mensaje específico — no el genérico — al reproducirlos desde la interfaz.
- **SC-003**: Ninguna pantalla queda en estado de carga indefinida o "congelada" tras un fallo
  de API en los flujos cubiertos.
- **SC-004**: Ninguna respuesta de error de ningún endpoint de la API expone detalles internos
  del servidor.

## Assumptions

- Ya existe un cliente HTTP centralizado en el frontend con un interceptor de respuestas que
  maneja el caso 401 (redirección al login); esta feature lo extiende, no lo reemplaza.
- Ya existe una librería de componentes visuales aprobada en el proyecto con sistema de
  notificaciones tipo toast; se reutiliza ese sistema, no se crea uno nuevo (Principio V).
- El alcance de la estandarización de errores es TODA la API (todos los módulos/endpoints
  existentes), preferiblemente mediante un manejador de errores global/centralizado en lugar de
  editar endpoint por endpoint, para mantener el esfuerzo acotado. La verificación manual
  end-to-end prioriza Tickets, Proyectos y Asignaciones (los 3 casos críticos).
- Los mensajes de error del servidor están escritos en español y son aptos para mostrarse
  directamente al usuario final.
- **Restricción de alcance (Principio VII, constitución v1.2.0)**: NO se refactoriza la lógica
  interna de los controladores del backend. El trabajo se limita a envolver las respuestas de
  error existentes (manejadores de error/try-catch) y a configurar el interceptor y el
  notificador en el frontend.
- **Restricción de pruebas (Principio VII)**: no se ejecuta la suite de pruebas de forma masiva;
  solo los tests específicos de lo modificado. Los tests nuevos del interceptor o del manejador
  de errores usan como máximo 5-10 registros/mocks simulados por test.
