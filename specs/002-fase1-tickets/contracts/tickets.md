# API Contract: Tickets

**Base path**: `/api/tickets`
**Auth**: JWT Bearer + permiso del módulo `tickets` **exigidos en backend en TODAS las rutas**
(FR-022 — a diferencia de Fase 0, el enforcement es real). Errores 401/403 sin detalle del
recurso (FR-023 spec 001).

Estados (`status`): `nuevo`, `pre_analisis`, `contacto`, `en_analisis`, `en_ejecucion`,
`en_pruebas`, `pendiente_usuario`, `resuelto`, `cerrado`, `cancelado`.

---

## GET /api/tickets — permiso `tickets:view`

Lista paginada. Query params: `page`, `page_size` (máx 100), `search` (título o número),
`client_id`, `project_id`, `status` (repetible), `priority`, `severity`, `ticket_type`,
`assignee_id`, `sort` (`created_at|-created_at|priority|status`).

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid", "ticket_number": "TK-000123", "title": "...",
      "record_type": "ticket", "ticket_type": "incident",
      "status": "contacto", "priority": "high", "severity": "s2",
      "escalation_level": "n2",
      "client": {"id": "uuid", "name": "..."},
      "project": {"id": "uuid", "name": "..."},
      "assignee": {"id": "uuid", "full_name": "..."},
      "created_at": "iso-8601"
    }
  ],
  "total": 0, "page": 1, "page_size": 20
}
```

## POST /api/tickets — permiso `tickets:create`

Body: `{ title*, description*, ticket_type*, priority*, severity*, client_id*, project_id,
tool_id, process_id, escalation_level (default n2), related_ticket_id }`.
Valida: cliente activo; proyecto activo y del cliente; catálogos activos.

**Response 201**: detalle completo (ver GET /{id}) con `status: "nuevo"` y `ticket_number`
asignado. Header `Location`.
Errores: 400 validación, 404 cliente/proyecto/catálogo inexistente, 409 cliente/proyecto
inactivo.

## GET /api/tickets/{id} — permiso `tickets:view`

**Response 200**: todos los campos + `locked_fields: ["severity", ...]` (según estado,
FR-010) + `close_eligible: bool` (RESUELTO hace 3+ días sin respuesta) +
`comments: [...]` (con adjuntos) + `transitions: [...]` + `assignments: [...]`.

## PATCH /api/tickets/{id} — permiso `tickets:edit`

Edición de campos NO bloqueados por el estado actual. Campo `status` NO editable por esta
vía (400 siempre). Campo bloqueado → 409 `field_locked` con el nombre del campo.

## POST /api/tickets/{id}/assign — permiso `tickets:assign` 🎯

Endpoint independiente de la UI (Principio VI). Body:
`{ "assignee_id": "uuid", "mode": "resolver" | "pre_analysis" }`.
- `resolver`: transición nuevo/pre_analisis → `contacto`
- `pre_analysis`: transición nuevo → `pre_analisis` (asignación al QM)

Efectos atómicos: actualiza asignado y estado; inserta comentario automático
(`asignado`/`pre_analisis`, interno); inserta fila en `ticket_assignments` con `context`
JSONB (skills, carga, prioridad, severidad — FR-019); crea notificación al asignado.

**Response 200**: `{ ticket, assignment: {id, context, ...} }`.
Errores: 400 recurso inactivo, 404, 409 transición inválida desde el estado actual.

## POST /api/tickets/{id}/comments — permiso `tickets:transition` (o `tickets:view` para `comentario_interno`)

Content-Type: `multipart/form-data` (por adjuntos) o JSON sin adjuntos.
Body: `{ comment_type*, body*, files[] }`.

Ejecuta atómicamente la transición asociada al tipo (FR-014, matriz data-model.md):
`confirmacion_atencion` → en_analisis; `termina_analisis` → en_ejecucion;
`solicitud_informacion` → pendiente_usuario; `solicitud_cierre` → resuelto (marca
`resolved_at`); `respuesta_usuario` → en_ejecucion; `comentario_interno` → sin transición.
Un Resolutor solo sobre tickets asignados a él (FR-028).

**Response 201**: `{ comment, ticket: {status, locked_fields} }`.
Errores: 400 tipo/archivo inválido (máx 10 MB), 403 no asignado, 409 `invalid_transition`
con estado actual y acciones válidas en español (FR-008).

## POST /api/tickets/{id}/testing — permiso `tickets:transition`

Toggle EN PRUEBAS (Q1 clarificada): body `{ "direction": "enter" | "exit" }` —
en_ejecucion → en_pruebas o en_pruebas → en_ejecucion. Solo el resolutor asignado.

## POST /api/tickets/{id}/resolution — permiso `tickets:transition`

Aceptación/rechazo de la resolución registrada por el equipo en nombre del usuario (Q2):
body `{ "accepted": bool, "body": "evidencia/observación" }`.
- `accepted: false` → resuelto → en_ejecucion + notificación al resolutor
- `accepted: true` → habilita cierre (no cierra automáticamente)

## POST /api/tickets/{id}/close — permiso `tickets:transition`

Cierre (FR-012). Body: `{ resolution_type_id*, body* }` (body = comentario
`descripcion_solucion`). Precondición: resolución aceptada o `close_eligible` (3+ días).
Efectos: resuelto → cerrado, `closed_at`, notificación a Coordinador y QM (FR-024).
Errores: 409 sin aceptación/elegibilidad, 400 sin tipo de resolución o descripción.

## POST /api/tickets/{id}/cancel — permiso `tickets:cancel`

Body: `{ "body": "motivo*" }` → comentario `cancelacion` + transición a cancelado desde
cualquier estado no final. Solo Coordinador/Admin (seed de permisos).

## GET /api/tickets/{id}/attachments/{attachment_id} — permiso `tickets:view`

Descarga autenticada del adjunto (stream con content-type original).

---

## GET /api/assignment-panel — permiso `assignment_panel:view`

Query: `statuses` (repetible, filtro de columnas).

**Response 200**:
```json
{
  "matrix": [
    { "resource": {"id": "uuid", "full_name": "..."},
      "counts": {"contacto": 2, "en_analisis": 1}, "total": 3 }
  ],
  "unassigned_new": [ { "id": "uuid", "ticket_number": "TK-000124", "title": "...",
                        "priority": "high", "severity": "s1", "client": {...},
                        "created_at": "iso-8601" } ]
}
```
