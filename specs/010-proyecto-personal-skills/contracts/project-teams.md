# Contract: Subgrupos "Equipo" del Proyecto (project teams)

Módulo de permisos: `projects` — GET `projects:view`, mutaciones `projects:edit`. JWT
obligatorio.

## GET /api/projects/{project_id}/teams

**200**:
```json
{
  "items": [
    {
      "id": "uuid-team",
      "project_id": "uuid",
      "name": "Infraestructura",
      "members": [
        { "member_id": "uuid-member", "user_id": "uuid", "full_name": "...", "email": "...", "role_name": "..." }
      ],
      "member_count": 1,
      "created_at": "2026-07-09T12:00:00+00:00"
    }
  ],
  "total": 1
}
```

## POST /api/projects/{project_id}/teams

**Body**: `{ "name": "Equipo X" }` — nombre no vacío, único dentro del proyecto.

**201**: objeto team (members vacío).

**Errores**: 400 `validation_error` (nombre vacío) · 404 (proyecto) · 409 `duplicate_name` ·
401/403/500.

## PATCH /api/project-teams/{team_id}

Renombrar subgrupo. **Body**: `{ "name": "Nuevo nombre" }`.

**200**: objeto team. **Errores**: 400 · 404 · 409 `duplicate_name` · 401/403/500.

## DELETE /api/project-teams/{team_id}

Elimina el subgrupo. Sus miembros **siguen asignados** al proyecto (solo se borra la
agrupación).

**204**. **Errores**: 404 · 401/403/500.

## PUT /api/project-teams/{team_id}/members

Reemplaza el conjunto de miembros del subgrupo (patrón "lista completa", igual que
`resource_skills`).

**Body**: `{ "member_ids": ["uuid-member", "..."] }` — cada uno debe ser un `project_member`
del **mismo** proyecto.

**200**: objeto team con members actualizado.

**Errores**: 400 `validation_error` · 404 `not_found` (team) · 409 `member_not_in_project`
(algún id no es personal asignado de ese proyecto) · 401/403/500.
