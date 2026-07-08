# API Contract: Registro de tiempos (`work_sessions`)

**Auth**: JWT Bearer obligatorio en todos los endpoints. Errores 401/403 sin detalle interno
(Principio IV). Namespace Flask-RESTX: `work-sessions`, `path="/api/work-sessions"`.

---

## GET /api/work-sessions — permiso `work_sessions:view_own` (propios) o `work_sessions:view_all`

Lista los registros de tiempo. Un caller con solo `view_own` recibe siempre sus propios
registros, ignorando cualquier `resource_id` distinto que envíe. Un caller con `view_all`
(Coordinador/QM/Admin) puede filtrar por cualquier recurso.

Query: `resource_id` (uuid, opcional — solo relevante con `view_all`), `ticket_id` (uuid,
opcional), `date_from`, `date_to` (ISO date, opcional — default: últimos 30 días), `page`,
`page_size`.

**Response 200**:
```json
{
  "items": [
    { "id": "uuid", "resource_id": "uuid", "resource_name": "...",
      "ticket_id": "uuid", "ticket_number": "TK-000123",
      "work_date": "2026-07-07", "duration_minutes": 90, "note": "Análisis de log",
      "created_by": "uuid", "updated_by": null,
      "created_at": "iso-8601", "updated_at": "iso-8601" }
  ],
  "total": 0
}
```

**Response 400**: parámetros inválidos (rango de fechas invertido, uuid malformado).

---

## POST /api/work-sessions — permiso `work_sessions:manage`

Body:
```json
{ "ticket_id": "uuid", "work_date": "2026-07-07", "duration_minutes": 90, "note": "opcional" }
```

`resource_id` NO viaja en el body — se toma del usuario autenticado (su `resource_id` asociado).
Excepción: Admin con permiso `work_sessions:manage_all` puede incluir `resource_id` explícito
para registrar en nombre de otro recurso (corrección administrativa).

**Response 201**: el registro creado (mismo shape que en el listado).

**Response 400**: `duration_minutes <= 0`, `work_date` futura, o el total diario del recurso
superaría 1440 minutos (`{"error": "daily_limit_exceeded", "current_total_minutes": n}`).

**Response 403**: el recurso no participa del `ticket_id` indicado (no es ni fue asignado), y
quien llama no tiene `work_sessions:manage_all`.

**Response 404**: `ticket_id` no existe.

**Response 409**: el ticket está en estado `cerrado` y quien llama no tiene
`work_sessions:manage_all`.

---

## PATCH /api/work-sessions/{id} — permiso `work_sessions:manage` (propio) o `manage_all` (Admin)

Body (todos los campos opcionales, al menos uno requerido):
```json
{ "duration_minutes": 60, "note": "actualizado" }
```
Con `work_sessions:manage_all` además se acepta `work_date` y `ticket_id` (corrección
administrativa completa).

**Response 200**: el registro actualizado.

**Response 403**:
- El registro no pertenece al recurso del caller y este no tiene `manage_all`.
- El registro está fuera de la ventana de edición de 7 días y el caller no tiene `manage_all`
  (`{"error": "edit_window_expired"}`).

**Response 400**: mismas validaciones que POST (límite diario, fecha futura, etc.) recalculadas
sobre el nuevo valor.

---

## DELETE /api/work-sessions/{id} — permiso `work_sessions:manage` (propio) o `manage_all` (Admin)

**Response 204**: eliminado. Genera una fila `action='deleted'` en `work_session_edits` con el
snapshot previo — el registro deja de listarse pero su historial de auditoría persiste.

**Response 403**: mismas reglas que PATCH (dueño / ventana de edición).

---

## GET /api/work-sessions/summary — permiso `work_sessions:view_own` (propio) o `view_all`

Reporte agregado por recurso y día (US3). Query: `resource_id` (opcional con `view_all`;
ignorado y forzado al propio con solo `view_own`), `date_from`, `date_to` (obligatorios).

**Response 200**:
```json
{
  "resource_id": "uuid",
  "resource_name": "...",
  "range": { "date_from": "2026-07-01", "date_to": "2026-07-07" },
  "days": [
    { "work_date": "2026-07-01", "total_minutes": 480, "sin_registro": false },
    { "work_date": "2026-07-02", "total_minutes": 0, "sin_registro": true }
  ],
  "total_minutes": 480
}
```

Si `resource_id` no se especifica y el caller tiene `view_all`, el `Response 200` es una lista
de objetos con esta misma forma, uno por recurso con al menos un registro en el rango o con
tickets asignados activos.

**Response 400**: rango de fechas inválido o mayor a 92 días (límite razonable para evitar
reportes desmedidos).
