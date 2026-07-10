# Quickstart: Cronómetro Manual de Tiempo en el Ticket

Guía de validación end-to-end contra Docker real.

## Prerequisitos

```bash
docker compose up --build -d          # sywork_db + sywork_backend + sywork_frontend
docker compose logs backend | grep "Running upgrade"   # migración de ticket_timers aplicada
curl http://localhost:5000/health/    # {"status":"ok", ...}
```

Login en http://localhost:5173 con un usuario `resolutor` (o cualquier recurso con permiso
`work_sessions:manage`) con al menos un ticket asignado en estado abierto, y otro ticket en
estado `Cerrado`.

## Escenario 0 — Migración

1. Tras `alembic upgrade head`: `SELECT COUNT(*) FROM ticket_timers` → `0` (tabla nueva, vacía).
2. Ningún dato existente de `work_sessions` ni `tickets` se modifica.

## Escenario 1 — Ciclo completo iniciar → pausar → reanudar → terminar (US1, SC-001, SC-002)

1. Abrir el detalle de un ticket abierto asignado al recurso. `GET /api/timer` → `status:
   "inactive"`.
2. Presionar "Iniciar" (`POST /api/timer/start` con `ticket_id`). El cronómetro se muestra
   corriendo desde 0.
3. Esperar ~1 minuto real (o simular con datos en BD si el test es automatizado). Presionar
   "Pausar" (`POST /api/timer/pause`). El número deja de avanzar; `GET /api/timer` devuelve
   `status: "paused"` y `total_seconds` estable.
4. Presionar "Reanudar" (`POST /api/timer/resume`). El número vuelve a avanzar desde el valor
   pausado.
5. Presionar "Terminar" (`POST /api/timer/finish`). Verificar: se crea un `WorkSession` nuevo
   (`GET /api/work-sessions?ticket_id=...`) con `duration_minutes` ≈ tiempo transcurrido real
   (±1 min); `GET /api/timer` vuelve a `status: "inactive"`.

**Esperado**: el Registro de tiempo generado aparece en `GET /api/work-sessions/summary` del
recurso, igual que uno cargado manualmente.

## Escenario 2 — Persistencia entre recargas y sesiones (US2, SC-003)

1. Iniciar el cronómetro en un ticket.
2. Recargar la página del detalle del ticket (F5). El cronómetro sigue corriendo con el tiempo
   correcto (no vuelve a 0).
3. Cerrar sesión y volver a entrar. `GET /api/timer` refleja el mismo `status` y un
   `total_seconds` mayor (si seguía `running`) o igual (si estaba `paused`) al de antes de cerrar
   sesión.

**Esperado**: ninguna recarga ni cierre de sesión reinicia el cronómetro.

## Escenario 3 — Visibilidad personal (US3)

1. Con el Recurso A logueado, iniciar el cronómetro en el Ticket X.
2. Loguear al Recurso B (con acceso de lectura al mismo Ticket X, p. ej. Coordinador u otro
   Resolutor) en otra sesión/navegador. `GET /api/timer` de B devuelve `status: "inactive"` (no
   ve el cronómetro de A).
3. B inicia su propio cronómetro en su propio Ticket Y (un mismo ticket solo admite un
   resolutor asignado a la vez vía Triage — la independencia del cronómetro no depende de
   compartir ticket). Ambos cronómetros avanzan de forma independiente; cada `Terminar` genera
   un `WorkSession` distinto, uno por recurso.

## Escenario 4 — Un solo cronómetro activo por recurso (FR-006)

1. Con el cronómetro del Recurso A corriendo en el Ticket X, intentar `POST /api/timer/start`
   con `ticket_id` del Ticket Y (distinto).
2. **Esperado**: `409 timer_already_active` con el `ticket_id` del cronómetro en curso (X); el
   cronómetro de X no se ve afectado.

## Escenario 5 — Ticket cerrado bloquea "Terminar" (Clarificación 2026-07-09, FR-008)

1. Iniciar el cronómetro en un ticket abierto.
2. Mientras corre, cerrar el ticket por el flujo normal (fuera del cronómetro).
3. Presionar "Terminar". **Esperado**: `409 ticket_closed` (mismo error que ya existe para la
   carga manual de tiempo, spec `004`); el cronómetro **no** se resetea — `GET /api/timer` sigue
   mostrando el tiempo acumulado.
4. Un Admin (`work_sessions:manage_all`) puede registrar el tiempo en nombre del recurso vía
   `POST /api/work-sessions` con `resource_id` explícito (camino ya existente), o el ticket puede
   reabrirse para permitir que el propio recurso termine su cronómetro.

## Escenario 6 — Duración mínima (FR-007)

1. Iniciar el cronómetro y presionar "Terminar" antes de que pase un minuto.
2. **Esperado**: `409 duration_too_short`; no se crea ningún `WorkSession`; el cronómetro sigue
   activo (no se resetea), para no perder el intento.
