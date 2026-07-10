# API Contract: Cronómetro manual (`timer`)

**Auth**: JWT Bearer obligatorio en todos los endpoints. Errores 401/403 sin detalle interno
(Principio IV). Namespace Flask-RESTX: `timer`, `path="/api/timer"`. Todos los endpoints exigen
permiso `work_sessions:manage` (mismo permiso que la carga manual de tiempo — no se crea uno
nuevo). El `resource_id` **siempre** se resuelve del usuario autenticado; ningún endpoint acepta
`resource_id` explícito — a diferencia de `work_sessions`, aquí no existe variante "para otro
recurso" (FR-005).

---

## GET /api/timer — permiso `work_sessions:manage`

Devuelve el cronómetro actual del recurso autenticado (a lo sumo uno existe — FR-006).

**Response 200** (cronómetro inactivo):
```json
{ "status": "inactive", "ticket_id": null, "ticket_number": null,
  "total_seconds": 0, "running_seconds": 0, "stale": false }
```

**Response 200** (cronómetro activo — corriendo o pausado):
```json
{ "status": "running", "ticket_id": "uuid", "ticket_number": "TK-000123",
  "total_seconds": 754, "running_seconds": 754, "stale": false }
```

- `total_seconds`: tiempo acumulado total del ciclo actual (incluye tramos pausados y el tramo
  en curso), calculado al momento de la respuesta.
- `running_seconds`: tiempo transcurrido desde el último "Iniciar"/"Reanudar" sin interrupciones
  (0 si `status = paused`); se usa para decidir `stale`.
- `stale`: `true` cuando `running_seconds` supera el umbral configurado (referencia inicial: 12
  horas) — el frontend lo usa para mostrar una advertencia (FR-010), no bloquea ninguna acción.

---

## POST /api/timer/start — permiso `work_sessions:manage`

Body:
```json
{ "ticket_id": "uuid" }
```

Inicia un cronómetro nuevo (`accumulated_seconds = 0`) sobre el ticket indicado.

**Response 201**: el estado del cronómetro (mismo shape que `GET /api/timer`, `status:
"running"`).

**Response 400**: `ticket_id` ausente o inválido.

**Response 403**: el recurso no participa del `ticket_id` indicado (misma regla que
`work_sessions:manage` al cargar tiempo manual — FR-005/FR-006 de spec `004`).

**Response 404**: `ticket_id` no existe.

**Response 409**: `{"error": "timer_already_active", "ticket_id": "uuid-del-otro-ticket"}` — el
recurso ya tiene un cronómetro `running` o `paused` en otro ticket (FR-006); debe pausarlo o
terminarlo antes de iniciar uno nuevo.

---

## POST /api/timer/pause — permiso `work_sessions:manage`

Sin body. Pausa el cronómetro activo del recurso.

**Response 200**: el estado actualizado (`status: "paused"`).

**Response 409**: `{"error": "no_active_timer"}` si no hay cronómetro `running`, o
`{"error": "already_paused"}` si ya está `paused`.

---

## POST /api/timer/resume — permiso `work_sessions:manage`

Sin body. Reanuda el cronómetro pausado del recurso.

**Response 200**: el estado actualizado (`status: "running"`).

**Response 409**: `{"error": "no_paused_timer"}` si no hay cronómetro `paused` (incluye el caso
de no tener ningún cronómetro activo).

---

## POST /api/timer/finish — permiso `work_sessions:manage`

Body opcional:
```json
{ "note": "opcional, se pasa al Registro de tiempo generado" }
```

Termina el cronómetro activo (`running` o `paused`) y crea un `WorkSession` (spec `004`) con la
duración total acumulada, reutilizando `WorkSessionService.create()` (mismas validaciones:
ticket cerrado, participación del recurso, límite diario). El cronómetro vuelve a `inactive`.

**Response 201**: el `WorkSession` creado (mismo shape que `POST /api/work-sessions`, ver
`specs/004-fase2-registro-tiempos/contracts/work-sessions.md`).

**Response 404**: no hay cronómetro activo para el recurso.

**Response 400**: `{"error": "daily_limit_exceeded", "current_total_minutes": n}` — el
`WorkSession` resultante haría superar el límite diario del recurso (regla heredada tal cual de
`WorkSessionService`, spec `004`, mismo código 400 que la carga manual); el cronómetro **no** se
resetea en este caso, para que el recurso pueda corregir y reintentar.

**Response 409**:
- `{"error": "duration_too_short"}` — el total acumulado es menor a 1 minuto (FR-007); el
  cronómetro **no** se resetea, para no perder el progreso por un click accidental.
- `{"error": "ticket_closed"}` — el ticket está `cerrado` (regla heredada tal cual de
  `WorkSessionService`, spec `004`); el cronómetro tampoco se resetea en este caso.
