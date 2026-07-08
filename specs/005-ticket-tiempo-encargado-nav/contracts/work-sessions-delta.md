# API Contract Delta: `work_sessions` — hora de inicio/fin

Extiende `specs/004-fase2-registro-tiempos/contracts/work-sessions.md`. Solo se documentan los
campos y comportamientos **nuevos**; el resto del contrato (permisos, códigos de error de
límite diario/ventana de edición, endpoints de resumen) no cambia.

## POST /api/work-sessions — campos nuevos

Body (agrega `started_at`/`ended_at`, ambos opcionales):
```json
{
  "ticket_id": "uuid", "work_date": "2026-07-08",
  "started_at": "2026-07-08T14:00:00-05:00",
  "ended_at": "2026-07-08T18:00:00-05:00",
  "duration_minutes": 240,
  "note": "opcional"
}
```

- Si se envían `started_at` y `ended_at`, `duration_minutes` es opcional — el backend lo
  calcula. Si el cliente igual lo envía, se ignora el valor recibido y se usa el calculado (evita
  inconsistencias entre lo que muestra el formulario y lo que persiste).
- Si no se envían `started_at`/`ended_at`, el comportamiento es idéntico al contrato original
  (Fase 2): `duration_minutes` es obligatorio.
- Enviar solo uno de los dos (`started_at` sin `ended_at`, o viceversa) → 400
  `validation_error` ("ambos o ninguno").
- `ended_at <= started_at` → 400 `validation_error` ("la hora de fin debe ser posterior al
  inicio").

## PATCH /api/work-sessions/{id} — campos nuevos

Acepta además `started_at`/`ended_at` con las mismas reglas que POST. Si se actualizan, la
duración se recalcula; si se actualiza solo `duration_minutes` (sin tocar `started_at`/
`ended_at`), estos quedan como estaban (referencia informativa, no se borran).

## GET /api/work-sessions — response, campos nuevos

Cada item del listado ahora incluye `started_at`/`ended_at` (`null` si no se cargaron).

## GET /api/work-sessions?ticket_id={id} — ya soportado, sin cambios

El filtro por `ticket_id` (contracts/work-sessions.md original) es el que usa la nueva sección
embebida en el detalle del ticket — no se agrega ningún endpoint nuevo para esto.
