# API Contract: Notificaciones y Catálogos

**Auth**: JWT Bearer obligatorio (FR-022). Errores 401/403 sin detalle del recurso.

---

## Notificaciones

### GET /api/notifications — usuario autenticado (sus propias notificaciones)

Query: `unread=true|false` (default: todas), `page`, `page_size`.

**Response 200**:
```json
{
  "items": [
    { "id": "uuid", "event_type": "assigned", "message": "Se te asignó el ticket TK-000123",
      "ticket": {"id": "uuid", "ticket_number": "TK-000123", "title": "..."},
      "read": false, "created_at": "iso-8601" }
  ],
  "total": 0, "unread_count": 3
}
```

`event_type`: `assigned`, `user_replied`, `resolution_rejected`, `closed`, `close_eligible`.

### PATCH /api/notifications/read

Body: `{ "ids": ["uuid", ...] }` o `{ "all": true }`. Marca como leídas solo las del
usuario autenticado. **Response 200**: `{ "updated": n }`.

---

## Catálogos (herramienta, proceso, tipo de resolución, tipo de registro)

Base: `/api/catalogs/{catalog}` donde `{catalog}` ∈ `tools`, `processes`,
`resolution-types`, `record-types`.

### GET /api/catalogs/{catalog} — permiso `catalogs:view`

Query: `active=true|false|all` (default true). **Response 200**:
`{ "items": [{ "id": "uuid", "name": "JDE", "active": true }], "total": n }`

### POST /api/catalogs/{catalog} — permiso `catalogs:create`

Body: `{ "name": "..." }`. Nombre único por catálogo → 409 si duplicado.
**Response 201** con el registro.

### PATCH /api/catalogs/{catalog}/{id}/deactivate | /activate — permiso `catalogs:deactivate`

No se puede desactivar un valor en uso por tickets abiertos (no finales) → 409
`in_use` con el conteo. Valores desactivados no aparecen en selectores de tickets nuevos;
los tickets existentes conservan la referencia.

Nota `record-types`: se siembra con `Ticket` y `Tarea`, ambos administrables como cualquier
otro catálogo. Independientemente de qué valores estén activos aquí, la creación de tickets
en esta fase solo acepta el valor "Ticket" (regla de dominio, FR-030) — el catálogo dinámico
no habilita por sí solo la funcionalidad de Tareas.

---

## Enforcement global (FR-022 — se aplica también a los maestros de Fase 0)

- Todas las rutas de `/api/*` exigen JWT válido + usuario activo + permiso módulo/acción,
  **excepto**: `POST /api/auth/login`, `POST /api/auth/google`, `GET /health/`.
- Mapa maestros → permisos ya sembrados en Fase 0: `clients`, `projects`, `resources`,
  `skills`, `users`, `roles`, `compensation`.
- El decorador `@require_permission(module, action)` reemplaza al `@require_role` no usado;
  token ausente/inválido → 401; permiso faltante → 403; ambos con payload genérico.
- La excepción de "propio perfil" del Resolutor (FR-012 spec 001) se mantiene: la valida el
  servicio, no el decorador.
