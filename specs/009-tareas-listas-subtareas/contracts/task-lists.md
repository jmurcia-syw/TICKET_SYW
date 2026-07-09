# Contrato — `task_lists` (nuevo namespace)

Mismo patrón que `client_contacts` (spec `007`): CRUD simple anidado bajo su padre jerárquico
(Proyecto), protegido por el permiso ya existente `tickets:create` (sin permiso nuevo — mismo
criterio que Decisión 5 de la spec `008`: la Lista es un detalle de organización de Tareas, no
justifica una entrada nueva en la matriz de Roles y Permisos). Se usa `create`, no `edit`,
porque un Resolutor —que puede crear Tareas pero no tiene `tickets:edit`— necesita poder
organizarlas en Listas (encontrado en validación manual E2E: con `edit` un Resolutor quedaba
sin acceso a la pantalla de Listas).

## `GET /api/projects/{project_id}/task-lists`

Lista las Listas de un Proyecto, ordenadas por `position`. Cada item incluye `task_count`
(conteo de Tareas asociadas, `record_type = 'Tarea'`, `parent_task_id IS NULL` — una Subtarea no
cuenta aparte, ya cuenta dentro de su Tarea padre) — para el sidebar del mockup (`s-lista`).

**Respuesta 200**:

```json
{
  "items": [
    { "id": "...", "project_id": "...", "name": "F1: Definiciones y Alistamiento", "position": 0, "task_count": 4 }
  ]
}
```

## `POST /api/projects/{project_id}/task-lists`

**Input**: `{ "name": "F2: Diseño" }` — `position` se asigna automáticamente al final.

**Respuestas**:
- `201` — Lista creada.
- `400 validation_error` — `name` vacío.
- `404` — Proyecto no encontrado.

## `PATCH /api/task-lists/{id}`

**Input**: `{ "name": "..." }` y/o `{ "position": 2 }` — renombrar o reordenar.

**Respuestas**:
- `200` — Lista actualizada.
- `404` — Lista no encontrada.

Sin `DELETE` en esta spec (Edge Case documentado en spec.md — eliminar una Lista con Tareas
queda fuera de alcance; se revisita si el uso real lo requiere).
