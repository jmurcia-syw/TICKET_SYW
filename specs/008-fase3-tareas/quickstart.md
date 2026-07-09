# Quickstart: Fase 3 — Manejo de Tareas

## Prerrequisitos

- Stack levantado: `docker compose up -d` (backend + frontend + Postgres).
- Migración aplicada: `docker exec sywork_backend alembic upgrade head` → `023 (head)`.
- Un usuario interno (Admin/Coordinador/QM/Resolutor) con al menos un Cliente y Proyecto
  asignados/visibles.
- Dos Clientes distintos, cada uno con al menos un Ticket existente, para probar el "Registro
  relacionado" cruzado (Escenario 3).

## Validación dirigida

```bash
# Backend: solo los archivos nuevos/tocados por esta funcionalidad
docker exec sywork_backend pytest backend/tests/domain/test_task_fsm.py -v
docker exec sywork_backend pytest backend/tests/domain/test_ticket_service_tasks.py -v
docker exec sywork_backend pytest backend/tests/api/test_tickets_tasks.py -v

# Frontend: typecheck (no hay suite de tests automatizada en este repo)
cd frontend && npx tsc -b
```

Regresión completa (Fase de Polish, no durante el desarrollo de cada tarea):
```bash
docker exec sywork_backend pytest -q
```

## Escenario 1 (US1) — Crear una Tarea sin campos de clasificación de incidente

1. Como Resolutor (o cualquier rol interno), abrir "Nuevo ticket" y elegir "Tarea" en el control
   Ticket/Tarea.
2. Confirmar que los campos Tipo, Severidad, Herramienta, Proceso y Nivel de escalamiento
   desaparecen del formulario; Cliente, Proyecto, título y descripción siguen presentes.
3. Completar título, descripción, Cliente y Proyecto; guardar.
4. Abrir el detalle → confirmar que aparece como "Tarea" (no "Ticket") y en estado "Pendiente".
5. Abrir "Mis Tareas" → confirmar que la Tarea aparece distinguible visualmente de los Tickets.
6. Repetir el paso 1 logueado como Encargado → confirmar que el control Ticket/Tarea no aparece
   (su flujo de autoservicio sigue creando solo Tickets, sin cambios).

## Escenario 2 (US2) — Registro relacionado

1. Con la Tarea del Escenario 1, editar "Registro relacionado" y elegir un Ticket existente del
   **mismo** Cliente. Guardar.
2. Confirmar que el detalle de la Tarea muestra un enlace de navegación a ese Ticket.
3. Abrir el detalle del Ticket relacionado → confirmar que lista la Tarea que lo referencia
   (relación inversa).
4. Intentar vincular la Tarea a un Ticket de **otro** Cliente → confirmar 409
   `related_ticket_mismatch` y que la UI lo comunica con un mensaje claro.
5. Repetir el escenario 4 pero sobre un **Ticket normal** (no Tarea) editando su propio "Registro
   relacionado" hacia otro Cliente → confirmar el mismo rechazo (el fix de FR-005 aplica a ambos
   tipos de registro, no solo a Tareas).

## Escenario 3 (US1/US2 extendido) — Ciclo de vida de la Tarea

1. Sobre la Tarea Pendiente, ejecutar la transición "Iniciar" → confirmar que pasa a
   "En progreso" sin pedir ningún comentario tipificado.
2. Ejecutar "Completar" → confirmar que pasa a "Hecha" y que título/descripción/prioridad/lista/
   "Registro relacionado" quedan bloqueados para edición directa (`locked_fields`).
3. Ejecutar "Reabrir" desde "Hecha" → confirmar que vuelve a "En progreso" y los campos se
   desbloquean.
4. Ejecutar "Cancelar" desde "Pendiente" o "En progreso" → confirmar que pasa a "Cancelada".
5. Ejecutar "Reabrir" desde "Cancelada" → confirmar que vuelve a "En progreso".
6. Intentar `POST /api/tickets/{id}/task-transition` sobre un **Ticket** (no Tarea) → confirmar
   409 `not_a_task`.

## Escenario 4 (US3) — Agrupamiento por Lista en "Mis Tareas"

1. Crear dos Tareas con el campo "Lista" = "Esta semana" y una tercera sin lista.
2. Abrir "Mis Tareas" → confirmar que las dos primeras aparecen agrupadas bajo "Esta semana" y la
   tercera bajo "Sin lista".
3. Confirmar que los Tickets asignados (ya existentes) siguen apareciendo igual que antes de esta
   fase, sin ser forzados a ninguna lista.

## Escenario 5 (regresión) — Tickets sin cambios de comportamiento

1. Crear un Ticket normal (control en "Ticket") → confirmar que el formulario completo de
   clasificación (tipo, severidad, herramienta, proceso, escalamiento) sigue apareciendo igual
   que antes de esta fase.
2. Confirmar que el ciclo de vida de 10 estados del Ticket (comentarios tipificados, Panel de
   Asignación, cierre controlado) sigue funcionando exactamente igual — `task_fsm.py` no
   interviene en ningún Ticket.
3. Confirmar que la suite completa de backend pasa sin regresión (`pytest -q`).
4. `npx tsc -b` en frontend sin errores.
