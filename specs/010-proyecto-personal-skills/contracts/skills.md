# Contract: Skills — estructura ampliada

Endpoints existentes en `backend/api/routes/resources.py` (módulo `resources`). JWT +
permisos actuales sin cambios.

## GET /api/skills

**200** — cada item gana 5 campos:
```json
{
  "items": [
    {
      "id": "uuid",
      "code": "JDE_GL",
      "label": "JDE General Ledger",
      "active": true,
      "skill_type": "funcional",
      "tool_id": "uuid | null",
      "tool_name": "JDE | null",
      "process_id": "uuid | null",
      "process_name": "Finanzas | null"
    }
  ],
  "total": 10
}
```

## POST /api/skills

**Body**:
```json
{
  "code": "OTM_TMS",
  "label": "Oracle Transportation Mgmt",
  "skill_type": "funcional",
  "tool_id": "uuid (opcional)",
  "process_id": "uuid (opcional)"
}
```

- `skill_type` **obligatorio**, valores `funcional | tecnico` → 400 `validation_error` si
  falta o es otro valor (FR-013).
- `tool_id`/`process_id` opcionales; si vienen deben existir en su catálogo → 404 `not_found`
  (FR-014).

**201**: objeto skill (shape del GET).

## PATCH /api/skills/{skill_id} (nuevo)

Editar `label`, `skill_type`, `tool_id`, `process_id` (FR-018 — hoy solo existe DELETE; el
alta/edición de estos campos requiere PATCH).

**200**: objeto skill actualizado. **Errores**: 400 `validation_error` (skill_type inválido) ·
404 · 401/403/500.

## Semillas (migración 025)

Ver tabla completa en [research.md — Decisión 5](../research.md). 10 skills upsert por `code`;
procesos "Compras" y "Mantenimiento" agregados a `catalog_processes` si no existen.
