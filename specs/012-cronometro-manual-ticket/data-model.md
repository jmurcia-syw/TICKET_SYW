# Data Model: Cronómetro Manual de Tiempo en el Ticket

## Entidad: `TicketTimer` (nueva)

Representa el cronómetro manual **actual** de un recurso — a lo sumo uno por recurso, según
FR-006 y la Decisión 1 de `research.md`.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `resource_id` | UUID (**PK**, FK `resources.id`) | Un recurso ⇒ una fila; se crea la primera vez que inicia un cronómetro (upsert) o se aprovisiona vacía. |
| `ticket_id` | UUID nullable (FK `tickets.id`) | `NULL` cuando `status = inactive`; obligatorio cuando `running`/`paused`. |
| `status` | texto | `inactive` \| `running` \| `paused`. Default `inactive`. |
| `accumulated_seconds` | entero | Segundos acumulados en ciclos previos de la sesión actual (antes del tramo `running` en curso, si lo hay). Default `0`. Reinicia a `0` al terminar (`finish`) o al iniciar un cronómetro nuevo. |
| `started_at` | timestamptz nullable | Momento del último "Iniciar"/"Reanudar". `NULL` si `paused`/`inactive`. Tiempo transcurrido en curso = `now() - started_at`. |
| `created_at` / `updated_at` | timestamptz | Auditoría estándar del proyecto. |

**Cómputo derivado (no persistido)**: `total_seconds = accumulated_seconds + (running ?
now() - started_at : 0)`.

**Transiciones de estado** (todas exigen que el `resource_id` efectivo sea el del usuario
autenticado — FR-005, sin excepción de "ver todos"):

```
inactive --start(ticket_id)--> running (accumulated_seconds=0, started_at=now, ticket_id=ticket_id)
running  --pause--------------> paused  (accumulated_seconds += now-started_at, started_at=NULL)
paused   --resume-------------> running (started_at=now)
running  --finish-------------> inactive (crea WorkSession con accumulated_seconds+= now-started_at;
                                           luego resetea accumulated_seconds=0, ticket_id=NULL)
paused   --finish-------------> inactive (crea WorkSession con accumulated_seconds actual;
                                           luego resetea accumulated_seconds=0, ticket_id=NULL)
```

Transiciones inválidas (ej. `start` estando ya `running`/`paused` en otro ticket, `pause` estando
`inactive`, `finish` con `total_seconds < 60`) devuelven error de dominio (ver
`contracts/timer.md`).

**Relación con `WorkSession`** (entidad ya existente, `backend/domain/entities/work_session.py`,
sin cambios de esquema): `finish` crea un `WorkSession` nuevo reutilizando
`WorkSessionService.create()` — mismas reglas de validación (ticket cerrado, recurso
participante, límite diario) que la carga manual. El `TicketTimer` no queda referenciado desde
`WorkSession`; es un dato transitorio, no histórico (lo histórico es el `WorkSession` resultante).

## Migración

Nueva migración Alembic (`down_revision` = `025`) que crea `ticket_timers`:

- PK `resource_id` (FK `resources.id`, `ON DELETE CASCADE`).
- FK `ticket_id` → `tickets.id` (`ON DELETE SET NULL` — si un ticket se elimina, el cronómetro
  vuelve a estado inconsistente que el backend trata como si el ticket no existiera; caso de
  borde infrecuente, no bloqueante).
- `CHECK` de dominio: `status IN ('inactive','running','paused')`.
- `CHECK`: `(status = 'inactive' AND ticket_id IS NULL AND started_at IS NULL) OR (status =
  'paused' AND ticket_id IS NOT NULL AND started_at IS NULL) OR (status = 'running' AND
  ticket_id IS NOT NULL AND started_at IS NOT NULL)` — invariante de consistencia a nivel de
  base de datos.
- RLS habilitado con la misma política app-level ya usada en `project_members`/`project_teams`
  (migración `025`): acceso permitido cuando `app.authenticated` está seteado o la conexión es
  el usuario de servicio `sywork_user` — la RLS de este proyecto no filtra por fila a nivel de
  Postgres, el aislamiento por `resource_id` real se aplica en la capa API (FR-005), igual que
  en el resto de tablas del sistema.

No se modifican `tickets`, `work_sessions` ni ninguna otra tabla existente.
