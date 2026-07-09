# Quickstart: Listas de Tareas, Subtareas, ciclo de vida unificado y fix de Registro de tiempo

## Prerrequisitos

- Stack levantado: `docker compose up -d` (backend + frontend + Postgres).
- Migración aplicada: `docker exec sywork_backend alembic upgrade head` → `024 (head)`.
- Al menos un Cliente con un Proyecto, y al menos una Tarea creada bajo la spec `008` con
  `list_name` de texto libre y estado `pendiente`/`en_progreso`/`hecha` (para validar la
  migración de datos del Escenario 0). Si el entorno es nuevo, crear una manualmente antes de
  aplicar la migración `024`.
- Un usuario interno con `tickets:edit` y `work_sessions` propios (Resolutor/Coordinador/QM).

## Validación dirigida

```bash
# Backend — WORKDIR del contenedor ya es /repo/backend, rutas relativas a tests/
docker exec sywork_backend pytest tests/domain/test_ticket_service_free_transition.py \
  tests/domain/test_work_session_service_tasks.py tests/api/test_tickets_status_transition.py \
  tests/api/test_task_lists.py tests/api/test_tickets_subtasks.py \
  tests/api/test_work_sessions_tasks.py tests/api/test_tickets_tasks.py -v

# Frontend: typecheck
cd frontend && npx tsc -b
```

Regresión completa (Fase de Polish): `docker exec sywork_backend pytest -q` (331 tests, verde).

## Escenario 0 — Migración de datos (previo a cualquier otro escenario)

1. Antes de migrar, anotar el estado y `list_name` de 2-3 Tareas existentes de la spec `008`.
2. Aplicar `alembic upgrade head` → confirmar que corre sin error.
3. Abrir cada una de esas Tareas → confirmar el mapeo de estado (`pendiente`→"Nuevo",
   `en_progreso`→"En Ejecución", `hecha`→"Cerrado", `cancelado` sin cambio) y que su antiguo
   `list_name` ahora aparece como una Lista real seleccionada (mismo nombre, ahora vinculada a
   `task_lists`).
4. Confirmar en `GET /api/projects/{id}/task-lists` que aparecen esas Listas con el `task_count`
   correcto.

## Escenario 1 (US1) — Registro de tiempo en una Tarea propia

1. Crear una Tarea nueva (queda auto-asignada a su creador, spec `008`) → registrar tiempo desde
   su detalle → confirmar `201`, sin 403.
2. Crear una Subtarea dentro de esa Tarea, asignada a **otro** recurso → como el creador de la
   Tarea padre (no el asignado de la Subtarea), intentar registrar tiempo sobre la Subtarea →
   confirmar que el sistema lo permite (FR-001).
3. Como un tercer recurso sin ninguna relación con la Tarea ni la Subtarea, intentar registrar
   tiempo → confirmar que sigue rechazado con 403 `not_assigned` (FR-002, sin regresión).
4. Sobre un Ticket normal ya asignado por Triage, confirmar que el registro de tiempo sigue
   funcionando exactamente igual que antes (sin regresión).

## Escenario 2 (US2) — Ciclo de vida unificado: transición libre + comentario obligatorio

1. Crear una Tarea (estado inicial "Nuevo") → cambiarla directamente a "Cerrado" (saltando todos
   los estados intermedios) vía `PATCH /api/tickets/{id}/status` con un comentario → confirmar
   `200` y que el "Historial de estados" registra la transición con su comentario.
2. Intentar el mismo cambio sin `comment` → confirmar `400 validation_error`.
3. Cambiar la Tarea de "Cerrado" de vuelta a "Nuevo" (retroceso) → confirmar que el sistema lo
   permite sin restricción (a diferencia de un Ticket).
4. Sobre un **Ticket** normal, intentar `PATCH /api/tickets/{id}/status` → confirmar `409
   not_a_task` (sigue usando únicamente sus endpoints de acción existentes).
5. Abrir el detalle de la Tarea → confirmar que Tipo, Severidad, Herramienta, Proceso y Nivel de
   escalamiento aparecen visibles y editables, igual que en un Ticket.
6. Abrir el tablero Kanban → confirmar que la Tarea aparece en la columna correspondiente a su
   estado actual, con un tag "Tarea" distinguible de los Tickets.
7. Arrastrar la tarjeta de la Tarea a cualquier otra columna del Kanban → confirmar que pide un
   comentario y permite el movimiento sin validar una secuencia (a diferencia de arrastrar un
   Ticket, que sigue restringido a `getKanbanTransition`).

## Escenario 3 (US3) — Listas de tareas administrables

1. Abrir un Proyecto → confirmar el panel de Listas (sidebar) según `docs/mockup.html`
   (pantalla `s-lista`).
2. Crear una Lista nueva ("F2: Diseño") → confirmar que aparece con conteo 0.
3. Crear una Tarea asociada a esa Lista → confirmar que el conteo sube a 1 y la Tarea aparece
   agrupada en la vista de Lista y en "Mis Tareas".
4. Intentar asociar la Tarea a una Lista de **otro** Proyecto → confirmar `409 list_mismatch`.

## Escenario 4 (US4) — Subtareas con Encargado propio

1. Dentro de una Tarea, agregar dos Subtareas con Encargados distintos entre sí y distintos del
   Encargado de la Tarea padre.
2. Confirmar que cada Subtarea aparece anidada bajo la Tarea, con su propio badge de estado y
   avatar.
3. Cambiar el estado de una Subtarea → confirmar que no afecta el estado de la Tarea padre ni de
   la otra Subtarea.
4. Como el Encargado de una Subtarea, abrir "Mis Tareas"/Kanban → confirmar que la ve igual que
   cualquier Tarea asignada a él.
5. Intentar crear una Subtarea dentro de otra Subtarea → confirmar `409 nested_subtask_not_allowed`.

## Escenario 5 (US5) — Comentarios simples en Tarea y Subtarea

1. Agregar un comentario a una Tarea sin cambiar su estado → confirmar que aparece en su
   historial sin generar una fila en "Historial de estados".
2. Agregar un comentario a una de sus Subtareas → confirmar que aparece solo en el historial de
   esa Subtarea, no en el de la Tarea padre.

## Escenario 6 (regresión) — Ticket sin cambios de comportamiento

1. Crear y transicionar un Ticket normal por su flujo completo (Triage → comentarios tipificados
   → cierre) → confirmar que funciona exactamente igual que antes de esta spec.
2. Confirmar que `ticket_fsm.py` sigue siendo la única fuente de verdad para Ticket — sin
   bifurcación por tipo de registro.
3. `pytest -q` completo sin regresión; `npx tsc -b` sin errores.
