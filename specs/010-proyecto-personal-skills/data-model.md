# Data Model: Usuario/cliente por Proyecto, Asignación de Personal y Estructura de Skills

**Feature**: `010-proyecto-personal-skills` · **Date**: 2026-07-09
**Migración**: `backend/infra/migrations/versions/025_project_members_skills.py` (down_revision: `024`)

## Entidades nuevas

### ProjectMember (`project_members`)

Vínculo persona ↔ Proyecto, válido para cualquier usuario del sistema (FR-008/FR-009).

| Columna | Tipo | Constraints |
|---------|------|-------------|
| `id` | UUID PK | `gen_random_uuid()` |
| `project_id` | UUID | FK `projects(id)`, NOT NULL, index |
| `user_id` | UUID | FK `users(id)`, NOT NULL |
| `assigned_at` | TIMESTAMPTZ | NOT NULL, default `now()` |

- `UNIQUE(project_id, user_id)` — asignación única por persona/proyecto (FR-009).
- RLS habilitado (consistente con maestros).
- El **tipo/rol** de la persona NO se almacena aquí: se deriva de `users.role_id` al listar
  (una sola fuente de verdad — research Decisión 2).

Entidad de dominio: `backend/domain/entities/project_member.py` — dataclass `ProjectMember`
(`id, project_id, user_id, assigned_at`), sin imports de framework.

### ProjectTeam (`project_teams`) — subgrupo "Equipo"

| Columna | Tipo | Constraints |
|---------|------|-------------|
| `id` | UUID PK | `gen_random_uuid()` |
| `project_id` | UUID | FK `projects(id)`, NOT NULL, index |
| `name` | TEXT | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |

- `UNIQUE(project_id, name)` — nombre único dentro del Proyecto (Assumption).
- Puede quedar vacío (edge case).
- RLS habilitado.

Entidad de dominio: dataclass `ProjectTeam` (`id, project_id, name, created_at`) en el mismo
módulo `project_member.py`.

### ProjectTeamMember (`project_team_members`)

| Columna | Tipo | Constraints |
|---------|------|-------------|
| `team_id` | UUID | FK `project_teams(id)` **ON DELETE CASCADE**, PK compuesta |
| `member_id` | UUID | FK `project_members(id)` **ON DELETE CASCADE**, PK compuesta |

Invariantes que salen del esquema (research Decisión 2):
- Solo personal ya asignado al Proyecto puede pertenecer a un subgrupo (FK a
  `project_members`).
- Desasignar del Proyecto ⇒ sale de todos los subgrupos (cascade por `member_id`) — US3
  escenario 5.
- Eliminar un subgrupo ⇒ sus miembros siguen asignados al Proyecto (cascade solo por
  `team_id`) — US3 escenario 4.
- Una persona puede estar en varios subgrupos (PK compuesta, no unique por member).

## Entidades modificadas

### Skill (`skills`) — ampliada (US4)

| Columna nueva | Tipo | Constraints |
|---------------|------|-------------|
| `skill_type` | TEXT | NOT NULL, CHECK `skill_type IN ('funcional','tecnico')` (`ck_skills_type`) |
| `tool_id` | UUID | FK `catalog_tools(id)`, NULL |
| `process_id` | UUID | FK `catalog_processes(id)`, NULL |

Dataclass `Skill` (en `backend/domain/entities/resource.py`) += `skill_type: str`,
`tool_id: Optional[uuid.UUID]`, `process_id: Optional[uuid.UUID]`.

`SkillService.validate_create/validate_update`: rechaza `skill_type` ausente o fuera del
catálogo de 2 valores (400 `validation_error`); `tool_id`/`process_id` opcionales pero, si
vienen, deben existir en su catálogo (404 `not_found`).

### Rol "Encargado" (`roles`) — renombrado (US1)

`UPDATE roles SET name = 'Usuario/cliente', description = 'Usuario externo de un Cliente:
solo crea y ve sus propios tickets' WHERE name = 'Encargado'`. El UUID no cambia ⇒
`role_permissions` y `users.role_id` intactos (FR-002). Constante backend:
`USUARIO_CLIENTE_ROLE_NAME = "Usuario/cliente"` reemplaza el literal `"Encargado"` en
`client_contacts.py`.

### Ticket (`tickets`) — sin cambios de esquema

`client_contact_id` se conserva tal cual (clarificación 2026-07-09). Cambia solo la
validación de servicio (ver contracts/tickets.md): si el ticket tiene `project_id`, el
solicitante debe estar en `project_members` de ese proyecto.

## Migración `025` — orden de operaciones

1. `UPDATE roles` (renombre Encargado → Usuario/cliente).
2. `CREATE TABLE project_members` + unique + index + RLS.
3. `CREATE TABLE project_teams` + unique + index + RLS.
4. `CREATE TABLE project_team_members` (cascades) + RLS.
5. **Backfill de membresías** (FR-006): `INSERT INTO project_members (project_id, user_id)
   SELECT DISTINCT t.project_id, cc.user_id FROM tickets t JOIN client_contacts cc ON
   cc.id = t.client_contact_id WHERE t.project_id IS NOT NULL ON CONFLICT DO NOTHING`.
6. `ALTER TABLE skills ADD COLUMN skill_type TEXT NULL, tool_id UUID FK NULL, process_id
   UUID FK NULL`.
7. **Backfill de tipo** (FR-017): JDE_AR, ORACLE_CRM → `funcional`; resto de preexistentes →
   `tecnico`; luego `ALTER COLUMN skill_type SET NOT NULL` + CHECK.
8. `INSERT` en `catalog_processes` de "Compras" y "Mantenimiento" si no existen (FR-016).
9. Upsert de las 10 semillas de skills por `code` (tabla en research Decisión 5), resolviendo
   `tool_id`/`process_id` por subselect de nombre (FR-015).

`downgrade`: revertir renombre del rol, drop de las 3 tablas (orden inverso), drop de las 3
columnas de `skills` (las semillas nuevas quedan — son datos de catálogo, mismo criterio que
migraciones previas).

## Diagrama de relaciones (nuevo/modificado)

```
users ──< project_members >── projects
              │
              └──< project_team_members >── project_teams >── projects

client_contacts (user_id → users)   [sin cambios de esquema]
tickets.client_contact_id           [sin cambios de esquema; validación por project_members]

skills ── tool_id ──> catalog_tools
   └──── process_id ─> catalog_processes
   └──── skill_type ∈ {funcional, tecnico}
```
