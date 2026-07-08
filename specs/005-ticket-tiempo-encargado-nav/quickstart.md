# Quickstart: Registro de tiempo en el ticket, rol Encargado y navegación

**Prerequisitos**: `docker compose up -d`, migraciones `018_work_sessions_start_end.py` ...
`021_encargado_role_permissions.py` aplicadas. Referencias:
[contracts/work-sessions-delta.md](contracts/work-sessions-delta.md),
[contracts/tickets-delta.md](contracts/tickets-delta.md), [data-model.md](data-model.md).

```bash
docker exec sywork_backend alembic current              # → 021 (head)
docker exec sywork_backend python -m pytest tests/ -q
```

---

## Escenario 1 — Registro de tiempo embebido en el ticket (US1)

1. Como Resolutor, abrir el detalle de un ticket asignado.
2. En la sección "Registros de tiempo", cargar un registro con hora de inicio 14:00 y hora de
   fin 18:00 → verificar que la duración se calcula sola (4h) y aparece en el historial de esa
   misma pantalla, con nota y autor.
3. Cargar un segundo registro fijando la duración manualmente (sin horas de inicio/fin) → debe
   guardarse igual.
4. Editar el primer registro (dentro de la ventana de 7 días) → el cambio se refleja sin salir
   del detalle. Eliminarlo → desaparece del historial embebido.
5. Verificar que el mismo registro también aparece en `/registro-tiempos` (vista global,
   sin cambios) — ambos puntos de entrada muestran los mismos datos.

## Escenario 2 — Tiempo estimado (US2)

1. Crear un ticket indicando 8 horas de tiempo estimado.
2. En el detalle, verificar que se muestra "8h estimadas" junto al total de tiempo real
   registrado (Escenario 1).
3. Crear un ticket sin tiempo estimado → el detalle debe mostrar "Sin estimar", no un campo vacío.

## Escenario 3 — Rol Encargado (US3)

1. Como Admin, dar de alta un Encargado vinculado a un Cliente existente
   (`POST /api/client-contacts`).
2. Iniciar sesión como ese Encargado → crear un ticket solo con título y descripción.
3. Verificar: el ticket nace en NUEVO, con el Cliente del Encargado auto-asignado (sin que lo
   haya elegido), y con `ticket_type/priority/severity` en sus valores por defecto.
4. Como Coordinador, abrir el detalle de ese ticket → verificar que se ve explícitamente
   "Encargado: <nombre>" diferenciado del Cliente.
5. Crear un segundo Encargado y un segundo ticket con esa cuenta. Volver a iniciar sesión con el
   primer Encargado → su listado de tickets NO debe incluir el del segundo Encargado.
6. Como el Encargado, intentar acceder a `/kanban`, `/assignment-panel`, `/registro-tiempos` →
   el sistema debe impedirlo.

## Escenario 4 — Navegación (US4)

1. Entrar al Kanban, abrir un ticket → hacer clic en "Volver" → debe regresar al Kanban.
2. Entrar a Tickets, aplicar un filtro (ej. estado NUEVO), abrir un ticket → "Volver" → debe
   regresar a Tickets con ese mismo filtro aplicado.
3. Entrar al Panel de Asignación, abrir un ticket → "Volver" → debe regresar al Panel de
   Asignación (nunca a una pantalla de asignación individual).
4. Pegar la URL de un ticket directamente en una pestaña nueva → "Volver" → debe ir al listado de
   Tickets (origen por defecto).

## Escenario 5 — Regresión Fase 1/2

1. El ciclo de vida FSM, comentarios, Triage Push y Panel de Asignación siguen funcionando sin
   cambios para Admin/Coordinador/QM/Resolutor.
2. Las pantallas globales "Registro de Tiempos"/"Reporte de Tiempos" de Fase 2 siguen mostrando
   los mismos datos que la nueva sección embebida (misma fuente, `work_sessions`).
