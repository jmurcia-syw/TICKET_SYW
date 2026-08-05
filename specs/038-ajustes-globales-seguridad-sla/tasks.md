# Tasks: Ajustes Globales — Seguridad/Permisos, Notificaciones, Motor de SLA, Bugs de UI y Rendimiento

**Input**: Design documents from `/specs/038-ajustes-globales-seguridad-sla/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-changes.md, quickstart.md

**Tests**: Se incluyen tareas de test dirigido por historia (patrón ya usado en specs previas de
este repo). Por Principio VII (constitution.md): ningún test nuevo debe insertar más de 5-10
registros mock, y está prohibido correr la suite completa de pytest — solo los archivos tocados.

**Organization**: Tareas agrupadas por User Story (P1-P3, ver spec.md) para permitir
implementación y prueba independiente de cada una. Las 6 historias son independientes entre sí —
no hay una fase "Foundational" bloqueante compartida más allá de verificar el entorno.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: A qué User Story pertenece (US1-US6)
- Rutas de archivo exactas ya verificadas contra el código real durante research.md

---

## Phase 1: Setup

**Purpose**: Confirmar el punto de partida antes de tocar código.

- [ ] T001 Verificar Docker stack arriba (`docker compose ps`) y Alembic en revisión `051`
      (`docker exec sywork_backend alembic current`) antes de agregar la migración `052`

---

## Phase 2: Foundational

**Purpose**: Las 6 User Stories de este paquete son independientes entre sí (distintos módulos,
sin entidad compartida nueva) — no existe un bloqueante común más allá del Setup de Phase 1. Esta
fase queda vacía deliberadamente; cada historia puede empezar apenas termine Phase 1.

**Checkpoint**: Foundation lista — cualquier User Story puede comenzar, en paralelo o en el orden
de prioridad P1→P2→P3.

---

## Phase 3: User Story 1 - Vistas acotadas por rol para Resolutores (Priority: P1)

**Goal**: Un Resolutor ve por defecto solo lo asignado a él en Kanban/Listas/Mis Tareas, pierde
acceso a la vista global de "Tickets" (reservada a Coordinador/Admin), su Calendario se acota a sí
mismo, no se precargan catálogos maestros completos en su sesión, y cualquier usuario puede
colapsar el menú lateral a solo iconos.

**Independent Test**: Login como Resolutor con 2 tickets asignados de un total de 3+ en el
sistema → Kanban/Listas muestran solo esos 2 por defecto → `/tickets` (global) no es accesible →
Calendario muestra solo su propio recurso → no se disparan peticiones de catálogos completos →
el control de colapsar el menú funciona.

### Implementación

- [ ] T002 [US1] Migración `backend/infra/migrations/versions/052_tickets_view_assigned.py`:
      agregar permiso `(module='tickets', action='view_assigned')` asignado al rol Resolutor;
      quitar el vínculo `Resolutor` → `tickets:view` si existe (downgrade restaura ambos estados)
- [ ] T003 [US1] `backend/infra/repositories/ticket_repo.py`: en `list()` (y el método que usa el
      Kanban/listado paginado), forzar `assignee_id = <resource_id del actor>` cuando el actor
      solo tiene `tickets:view_assigned` (sin `tickets:view`) — mismo patrón que el scoping ya
      existente por `client_contact_id` para `tickets:view_own`
- [ ] T004 [US1] `backend/api/routes/tickets.py` (`GET /api/tickets`): resolver el permiso del
      actor (`view` > `view_own` > `view_assigned`) y pasar el scope forzado correspondiente al
      repositorio; documentar el nuevo caso en el docstring del endpoint (Swagger, Principio I)
- [ ] T005 [US1] `backend/api/routes/calendar.py`: acotar la respuesta de calendario al propio
      recurso del actor cuando no tiene permiso de administración/RRHH sobre calendarios de
      equipo (reutilizar el gate de permiso ya existente si cubre este caso; si no, agregar el
      chequeo puntual sin nuevo permiso)
- [ ] T006 [P] [US1] `frontend/src/pages/KanbanPage.tsx`: al montar, si `!hasPermission('tickets',
      'view')`, resolver `resourceService.me()` y precargar `assigneeFilter` con ese `resource.id`
      (editable después por el usuario, igual que hoy)
- [ ] T007 [P] [US1] `frontend/src/pages/ProjectListsPage.tsx`: mismo criterio de T006 — no filtra
      por asignado hoy; agregar el default para usuarios sin `tickets:view`
- [ ] T008 [US1] Verificar que `frontend/src/pages/MyTasksPage.tsx` ya aplica "Asignado a mí" por
      defecto para todos los roles (spec `005`, línea 16-30) — sin cambio de código esperado, solo
      confirmar en quickstart.md
- [ ] T009 [US1] `frontend/src/pages/DashboardPage.tsx` (shell con `<Sider>`/`<Menu>`): ocultar el
      ítem de menú hacia `/tickets` (vista global) para usuarios sin `tickets:view`; verificar que
      la ruta en `frontend/src/App.tsx` (gate `['view','view_own']`) ya excluye naturalmente al
      Resolutor una vez aplicado T002 (sin cambio de código esperado ahí, solo confirmar)
- [ ] T010 [US1] `frontend/src/pages/DashboardPage.tsx`: auditar las llamadas de precarga de
      catálogos maestros (Clientes/Herramientas/Procesos/Tipos de resolución/Equipos/Tipos de
      acceso) disparadas al montar el shell de sesión y condicionarlas al permiso de
      administración correspondiente de cada catálogo
- [ ] T011 [US1] `frontend/src/pages/DashboardPage.tsx`: agregar modo colapsado al `<Sider>`
      (`collapsible`/`collapsed`/`onCollapse` de Ant Design, `<Menu>` en modo solo-iconos) con un
      control visible de colapsar/expandir, y expandir automáticamente al interactuar o
      seleccionar una opción de navegación

### Tests

- [ ] T012 [P] [US1] `backend/tests/api/test_tickets_view_assigned.py`: 3 tickets de prueba (2
      asignados al Resolutor de prueba, 1 a otro recurso) → `GET /api/tickets` como ese Resolutor
      devuelve solo 2; como Coordinador devuelve 3 (≤5 registros)
- [ ] T013 [P] [US1] Extender el test dirigido de calendario existente (o crear uno nuevo acotado)
      confirmando que un Resolutor solo recibe su propio recurso en la respuesta de calendario

**Checkpoint**: US1 completo y testeable de forma independiente del resto del paquete.

---

## Phase 4: User Story 2 - Motor de SLA corregido y auditoría inicial (Priority: P1)

**Goal**: El SLA de Contacto sigue corriendo durante todo el estado "Contacto" hasta que el
ticket pasa a "En Análisis"; el SLA de Resolución sigue corriendo durante "Resuelto" y se congela
recién al pasar a "Cerrado"; todo Ticket/Tarea nuevo deja una entrada inicial en su Historial de
Estados.

**Independent Test**: Crear un ticket, asignarlo (pasa a "Contacto"), confirmar que el SLA de
Contacto sigue "corriendo"; pasarlo a "En Análisis" y confirmar que se congela ahí; llevarlo a
"Resuelto" y confirmar que el SLA de Resolución sigue "corriendo"; pasarlo a "Cerrado" y confirmar
que recién ahí se congela; confirmar la entrada inicial "Ticket creado en estado Nuevo" desde el
momento de creación.

### Implementación

- [ ] T014 [US2] `backend/domain/fsm/ticket_fsm.py`: cambiar `SLA_PHASE_FOR_STATE["contacto"]` de
      `"ejecucion"` a `"contacto"`; actualizar el comentario explicativo (líneas 44-48) para
      reflejar que la fase de Contacto ahora sigue corriendo dentro del estado FSM `contacto`
- [ ] T015 [US2] `backend/domain/fsm/ticket_fsm.py`: cambiar `STATE_COUNTS_FOR_SLA["resuelto"]` de
      `False` a `True`
- [ ] T016 [US2] `backend/domain/services/sla_service.py`: acotar la condición de congelamiento
      (`new_status in ("resuelto", "cerrado", "cancelado")`, línea ~324) a `("cerrado",
      "cancelado")` únicamente
- [ ] T017 [US2] `backend/domain/services/ticket_service.py`: en la creación de Ticket/Tarea,
      insertar una fila en `ticket_status_transitions` con `from_status="creado"`,
      `to_status=<estado inicial>`, `comment_id=None`, `actor_id=<creador>`, en la misma
      transacción que la creación
- [ ] T018 [US2] `backend/api/routes/tickets.py::_transitions_with_sla()`: reconocer
      `from_status == "creado"` y exponerlo distinguible (p. ej. `is_creation: true`) para que el
      frontend lo renderice como "Ticket creado en estado {to_status}"
- [ ] T019 [US2] `frontend/src/pages/TicketDetailPage.tsx` (render del Historial de Estados) +
      `frontend/src/types/ticket.ts` (tipo de `transitions`): renderizar la entrada con
      `is_creation: true` con el texto de creación en vez del formato "cambio de X a Y"

### Tests

- [ ] T020 [P] [US2] `backend/tests/domain/test_sla_service.py` (extender): un ticket en estado
      "contacto" mantiene el SLA de Contacto "corriendo"; al pasar a "en_analisis" se congela; un
      ticket en "resuelto" mantiene el SLA de Resolución "corriendo"; al pasar a "cerrado" se
      congela (≤5 tickets de prueba)
- [ ] T021 [P] [US2] `backend/tests/api/test_tickets_crud.py` (extender) o nuevo
      `test_tickets_creation_audit.py`: crear un Ticket y una Tarea de prueba y confirmar que
      `GET /api/tickets/{id}` incluye una primera transición con `from_status == "creado"`

**Checkpoint**: US2 completo y testeable de forma independiente.

---

## Phase 5: User Story 3 - Corrección de bugs críticos de UI (Priority: P1)

**Goal**: El menú lateral y los componentes principales dejan de parpadear durante scroll/
interacción en Ticket/Tarea; editar credenciales de un tipo de acceso del Cliente ya no
sobrescribe las de otro tipo.

**Independent Test**: Reproducir el flujo de scroll que antes generaba parpadeo y confirmar
estabilidad del menú; editar credenciales de 2 tipos de acceso distintos de un mismo Cliente y
confirmar que no se mezclan al guardar.

### Implementación

- [ ] T022 [US3] Diagnosticar en Docker real la causa raíz del parpadeo generalizado (candidatos
      de research.md Decisión 8: polling de un componente tipo `NotificationBell` forzando
      re-render de un provider que envuelve el layout completo; o el `<Sider>`/`<Menu>` de
      `frontend/src/pages/DashboardPage.tsx` re-renderizando en cada cambio de un padre no
      memoizado) — documentar el hallazgo concreto antes de tocar código
- [ ] T023 [US3] Aplicar el fix identificado en T022 en el archivo/componente responsable
      (memoización, aislar el estado que dispara el re-render, o extender el patrón de zona
      muerta+RAF de spec `036` si el diagnóstico confirma que es el mismo mecanismo extendido a
      un contenedor superior)
- [ ] T024 [US3] `frontend/src/pages/ClientsPage.tsx`: aislar el estado del formulario de
      credenciales por tipo de acceso activo — forzar remount del formulario al cambiar de
      pestaña (`key={accessId}` en el componente de formulario de credenciales) y/o llamar a
      `form.resetFields()` explícitamente en el cambio de pestaña, sin tocar el resto de la
      pantalla de Cliente (spec `031`)

### Tests

- [ ] T025 [US3] Verificación manual documentada en quickstart.md US3 (el flicker no es
      automatizable de forma confiable sin un entorno de captura de frames; se valida con el
      método de `ResizeObserver` ya usado en spec `036`, extendido al contenedor del menú)

**Checkpoint**: US3 completo y testeable de forma independiente.

---

## Phase 6: User Story 4 - Cascada y campos obligatorios en formularios (Priority: P2)

**Goal**: Todo formulario con Cliente+Proyecto acota el Proyecto al Cliente elegido; el
Usuario/cliente solicitante es obligatorio en Ticket y opcional en Tarea; la Descripción/Nota del
Registro de Tiempo es obligatoria.

**Independent Test**: Cambiar de Cliente en cualquier formulario afectado y confirmar que el
Proyecto se acota/limpia; intentar guardar un Ticket sin solicitante (bloquea) y una Tarea sin él
(no bloquea); intentar guardar un Registro de Tiempo sin descripción (bloquea).

### Implementación

- [ ] T026 [US4] Auditar `frontend/src/pages/SlaRulesPage.tsx`, `frontend/src/pages/ReportsPage.tsx`
      y cualquier otro formulario/filtro con Cliente+Proyecto que aún no aplique la cascada ya
      implementada en Ticket/Tarea (spec `035`) y extenderla ahí
- [ ] T027 [US4] `frontend/src/pages/TicketsPage.tsx` (línea ~527, flag `projectRequiredFlow`):
      ajustar la regla para que `client_contact_id` sea explícitamente obligatorio cuando el
      registro es un Ticket (no una Tarea), sin depender solo de si hay Proyecto seleccionado
- [ ] T028 [US4] `backend/domain/services/ticket_service.py` (o el validador ya usado para
      `project_id` obligatorio de OBS-0045/spec `033`): reforzar server-side que
      `client_contact_id` sea obligatorio al crear un Ticket y opcional al crear una Tarea, con el
      formato de error estándar (spec `013`)
- [ ] T029 [US4] `frontend/src/components/worksessions/WorkSessionForm.tsx` (línea 167): cambiar
      `Form.Item name="note"` de `label="Nota (opcional)"` a obligatorio (`rules={[{ required:
      true, whitespace: true, message: 'La descripción es requerida' }]}`, label "Descripción")
- [ ] T030 [US4] `backend/domain/services/work_session_service.py` (`create()`/`update()`,
      parámetro `note`): validar que no esté vacío ni sea solo espacios, lanzando el error de
      validación estándar si falta

### Tests

- [ ] T031 [P] [US4] `backend/tests/domain/test_work_session_service.py` (extender): crear un
      Registro de tiempo sin `note` u con `note` en blanco falla; con `note` válido pasa (≤5
      registros)
- [ ] T032 [P] [US4] `backend/tests/api/test_tickets_crud.py` (extender): crear un Ticket sin
      `client_contact_id` falla; crear una Tarea sin él no falla

**Checkpoint**: US4 completo y testeable de forma independiente.

---

## Phase 7: User Story 5 - Copiar contraseña y correo de bienvenida (Priority: P2)

**Goal**: "Copiar Contraseña" informa claramente si falla en vez de mostrar éxito falso; al crear
un usuario, "Notificar al Usuario" envía un correo HTML de bienvenida con contraseña temporal y
enlace de cambio válido 30 minutos.

**Independent Test**: Crear un usuario marcando "Notificar al Usuario" y confirmar la llegada del
correo con todos los elementos requeridos y la expiración de 30 minutos del enlace; usar "Copiar
Contraseña" y confirmar el valor en el portapapeles.

### Implementación

- [ ] T033 [US5] `frontend/src/pages/TeamPage.tsx::handleCopyPassword` (línea 248): envolver
      `navigator.clipboard.writeText(...)` en `try/await/catch`, mostrar el toast de éxito
      existente solo si la promesa resuelve, y un toast de error explícito si se rechaza
- [ ] T034 [US5] `backend/infra/email/mailer.py`: agregar `send_welcome_email(to_email, name,
      temp_password, reset_link)` — plantilla HTML vía Jinja2 (ya disponible con Flask, sin
      dependencia nueva) con logo, mensaje de bienvenida, URL de login, contraseña temporal,
      enlace de cambio, aviso de mensaje automatizado y nota de tratamiento de datos; reutiliza el
      mismo mecanismo SMTP por variables de entorno de `send_password_reset_email`
- [ ] T035 [US5] `backend/api/routes/users.py` (creación de usuario): aceptar `notify: bool`
      opcional (default `false`) en el payload; si es `true`, generar el mismo token de un solo
      uso y expiración de 30 min ya usado por el reseteo de contraseña (spec `003`) y llamar a
      `send_welcome_email`; un fallo de envío no revierte la creación del usuario; devolver
      `notification_sent: boolean` en la respuesta
- [ ] T036 [P] [US5] Actualizar el contrato Swagger de `POST /api/users` (Flask-RESTX) con el
      campo `notify` y `notification_sent` (Principio I)
- [ ] T037 [US5] `frontend/src/pages/TeamPage.tsx` (formulario de alta de usuario): agregar
      checkbox "Notificar al Usuario" (default desmarcado) enviado como `notify`; mostrar el
      resultado (`notification_sent`) en el toast de confirmación de alta

### Tests

- [ ] T038 [P] [US5] `backend/tests/api/test_users_notify.py`: crear usuario con `notify=true`
      dispara el envío (mailer mockeado) y genera un token válido de 30 min; con `notify=false` no
      dispara envío; un fallo simulado del envío no revierte la creación del usuario (≤5
      registros)

**Checkpoint**: US5 completo y testeable de forma independiente.

---

## Phase 8: User Story 6 - Rendimiento del Detalle del Cliente (Priority: P3)

**Goal**: "Ver detalle de cliente" carga notablemente más rápido para clientes con historial
extenso, sin peticiones ni renders redundantes.

**Independent Test**: Medir tiempo hasta interactivo y peticiones de red antes/después con el
mismo Cliente de prueba de historial abundante.

### Implementación

- [ ] T039 [US6] Perfilar en DevTools/Network la carga actual de "Ver detalle de cliente"
      (`frontend/src/pages/ClientsPage.tsx`) con un Cliente de prueba de historial extenso y
      documentar los cuellos de botella reales (peticiones redundantes, N+1 en backend, o carga
      ansiosa de todas las pestañas de una vez)
- [ ] T040 [US6] `frontend/src/pages/ClientsPage.tsx`: diferir la carga de datos de las pestañas
      pesadas (Accesos, Proyectos, Contactos) a su selección real en vez de cargarlas todas al
      abrir el modal/detalle (Ant Design `Tabs`, sin librería nueva)
- [ ] T041 [US6] (Condicional al hallazgo de T039) Optimizar la consulta del repositorio de
      Clientes correspondiente si se detecta N+1 o duplicación de peticiones en backend — archivo
      exacto a determinar durante el perfilado

**Checkpoint**: US6 completo y testeable de forma independiente.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T042 [P] Correr `cd frontend && npx tsc -b` y confirmar 0 errores tras completar las 6
      historias
- [ ] T043 [P] Actualizar `README.md` reflejando la spec `038` (mismo patrón usado para las specs
      `035`-`037`)
- [ ] T044 Ejecutar los escenarios de `quickstart.md` completos contra Docker real (los 6
      user stories) antes de dar la feature por completa
- [ ] T045 Confirmar que ningún test nuevo de esta feature insertó más de 5-10 registros y que no
      se corrió la suite completa de pytest (Principio VII) — solo los archivos listados en cada
      historia

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — un solo chequeo de entorno
- **Foundational (Phase 2)**: vacía — no hay bloqueante compartido entre historias
- **User Stories (Phase 3-8)**: cada una depende solo de Phase 1; son independientes entre sí y
  pueden ejecutarse en paralelo o en el orden P1→P2→P3 (US1/US2/US3 → US4/US5 → US6)
- **Polish (Phase 9)**: depende de las historias que efectivamente se hayan completado

### User Story Dependencies

- **US1, US2, US3 (P1)**: sin dependencia entre sí ni de otra historia
- **US4, US5 (P2)**: sin dependencia entre sí ni de US1-3
- **US6 (P3)**: sin dependencia de ninguna otra historia

### Dentro de cada historia

- Migraciones/cambios de dominio antes que cambios de API/repositorio
- Cambios de backend antes que el frontend que los consume (salvo tareas ya marcadas `[P]` por
  tocar archivos disjuntos)
- Tests dirigidos después de la implementación de la historia (no TDD estricto en este paquete —
  son correcciones sobre comportamiento ya en producción, no funcionalidad nueva desde cero)

### Parallel Opportunities

- Todas las 6 historias pueden trabajarse en paralelo por distintas personas/sesiones — no
  comparten archivos entre sí salvo casos ya anotados (`DashboardPage.tsx` en US1 T009/T010/T011
  — mismas 3 tareas, secuenciales entre sí por tocar el mismo archivo)
- Dentro de cada historia, las tareas marcadas `[P]` tocan archivos distintos y pueden ejecutarse
  en paralelo

---

## Parallel Example: User Story 1

```bash
# Backend y frontend de US1 en paralelo (archivos distintos):
Task: "Migración 052_tickets_view_assigned.py"
Task: "KanbanPage.tsx: default assigneeFilter"
Task: "ProjectListsPage.tsx: default assigneeFilter"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3 — las 3 historias P1)

1. Completar Phase 1 (Setup)
2. Completar US1: acceso/vistas por rol restringidas correctamente
3. Completar US2: SLA correcto + auditoría inicial
4. Completar US3: sin parpadeo generalizado ni credenciales cruzadas
5. **Detener y validar** las 3 con quickstart.md antes de continuar con P2/P3

### Entrega incremental

1. Setup → Foundational (vacía) → listo para arrancar
2. US1 → validar independientemente → (opcional) desplegar/demo
3. US2 → validar independientemente → (opcional) desplegar/demo
4. US3 → validar independientemente → (opcional) desplegar/demo
5. US4 → US5 → US6, mismo patrón — cada una entrega valor sin romper las anteriores

---

## Notes

- `[P]` = archivos distintos, sin dependencias entre sí
- Cada historia es completable y testeable de forma independiente (ver quickstart.md)
- Commitear por historia completa (o por tarea si se prefiere granularidad fina), nunca mezclar
  cambios de 2 historias distintas en un mismo commit, para poder revertir una sin afectar a otra
- Evitar: tareas vagas, conflictos de archivo entre historias distintas, dependencias cruzadas que
  rompan la independencia de cada historia
