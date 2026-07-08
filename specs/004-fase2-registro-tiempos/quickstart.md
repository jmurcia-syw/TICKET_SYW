# Quickstart: Fase 2 — Registro diario de tiempos por recurso

**Prerequisitos**: `docker compose up -d` (Postgres + backend + frontend), migraciones
`015_create_work_sessions.py`...`017_work_sessions_permissions.py` aplicadas (el backend las
ejecuta al arrancar), al menos un ticket existente de Fase 1 asignado a un Resolutor semilla.
Referencias: [contracts/work-sessions.md](contracts/work-sessions.md), [data-model.md](data-model.md).

Verificación rápida del arranque:

```bash
docker exec sywork_backend alembic current                # → 017 (head)
curl -s http://localhost:5000/health/ | head -1            # → status ok
docker exec sywork_backend python -m pytest tests/ -q
```

---

## Escenario 1 — Alta de un registro de tiempo (US1)

1. Login como un Resolutor con al menos un ticket asignado en estado activo (no CERRADO).
2. Registrar una entrada de tiempo para hoy contra ese ticket: 1h 30min, nota "Análisis inicial".
3. Verificar: aparece en el listado del día; el resumen diario del recurso muestra 90 min totales.
4. Registrar una segunda entrada el mismo día contra otro ticket asignado (30 min) → el resumen
   diario sube a 120 min, ambas entradas quedan independientes.
5. Intentar registrar tiempo contra un ticket NO asignado a este recurso → 403.
6. Intentar registrar una entrada que llevaría el total del día a más de 24h → 400
   `daily_limit_exceeded`.
7. Intentar registrar con `work_date` de mañana → 400.
8. Intentar registrar con `duration_minutes: 0` → 400.

## Escenario 2 — Corregir o eliminar un registro (US2)

1. Con la entrada creada en el Escenario 1 (dentro de los últimos 7 días), editar sus minutos
   (90 → 60) y la nota → el resumen diario se recalcula de inmediato.
2. Eliminar una de las entradas del día → desaparece del listado y del resumen; verificar que
   `work_session_edits` registró la fila `action='deleted'` con el snapshot previo.
3. Simular una entrada con `work_date` de hace más de 7 días (o ajustar el reloj de prueba) y
   verificar que PATCH/DELETE devuelven 403 `edit_window_expired` para el Resolutor dueño.
4. Como Admin, editar esa misma entrada fuera de la ventana de edición → permitido
   (`work_sessions:manage_all`).

## Escenario 3 — Reporte por recurso y período (US3)

1. Cargar entradas de tiempo para 2-3 recursos distintos en una semana, dejando
   intencionalmente un día laborable sin ningún registro para uno de ellos.
2. Como Coordinador, consultar `GET /api/work-sessions/summary` filtrando esa semana para un
   recurso → el total coincide con la suma manual de sus entradas.
3. Verificar que el día sin registro aparece explícitamente como
   `{"total_minutes": 0, "sin_registro": true}`, no omitido.
4. Como el propio Resolutor (sin `work_sessions:view_all`), intentar consultar el resumen de
   otro recurso pasando su `resource_id` → el sistema lo ignora y devuelve solo el propio.

## Escenario 4 — Regresión de Fase 1

1. El ciclo de vida de tickets (FSM), asignación y comentarios de `002-fase1-tickets` siguen
   funcionando sin cambios — esta fase no modifica `tickets`, `ticket_comments` ni sus reglas.
2. Un ticket CERRADO sigue permitiendo consultar (no crear) sus registros de tiempo históricos.
