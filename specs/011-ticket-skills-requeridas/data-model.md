# Data Model: Skills Requeridas en el Ticket

## Entidad: `ticket_skills` (tabla puente, sin entidad de dominio propia)

Relación muchos-a-muchos opcional entre `tickets` (que también almacena Tareas y Subtareas,
spec `008`) y el catálogo `skills` (spec `010`, ya con `skill_type`/`tool_id`/`process_id`).

| Columna | Tipo | Null | Notas |
|---------|------|------|-------|
| `ticket_id` | UUID | NO | FK → `tickets.id` ON DELETE CASCADE. PK compuesta (parte 1). |
| `skill_id` | UUID | NO | FK → `skills.id` **sin** ON DELETE CASCADE (a propósito — ver FR-007 abajo). PK compuesta (parte 2). |
| `assigned_at` | TIMESTAMPTZ | NO | `server_default now()`. Solo auditoría, sin uso funcional. |

**Constraints**:
- PK compuesta `(ticket_id, skill_id)` — garantiza FR-003 (no duplicados) sin lógica de
  aplicación adicional.
- Sin RLS propio: la tabla no expone datos sensibles por sí misma; el acceso ya está mediado por
  el permiso `tickets:edit`/`tickets:view` en la API (mismo criterio que `resource_skills`, que
  tampoco tiene RLS propio — hereda el control de acceso de la tabla `resources`).

**Sin entidad de dominio dedicada**: no se crea un dataclass `TicketSkill` — se modela como
`Ticket.skills: list[Skill]` (reutilizando el dataclass `Skill` ya existente en
`backend/domain/entities/resource.py`), igual que `Resource.skills`.

## Cambios sobre entidades existentes

### `Ticket` (dominio, `backend/domain/entities/ticket.py`)

- **Campo nuevo**: `skills: list[Skill] = field(default_factory=list)` — igual patrón que
  `Resource.skills`. No participa en `locked_fields_for()` (Decisión 2, research.md): el campo
  no se edita vía `Ticket.locked_fields()`/PATCH genérico, sino por el endpoint dedicado.

### `TicketModel` (infra, `backend/infra/models/ticket_model.py`)

- Tabla asociativa `ticket_skills_table` (mismo patrón que `resource_skills_table` en
  `resource_model.py`).
- Relación `skills = relationship("SkillModel", secondary=ticket_skills_table, lazy="joined")`.
- `to_entity()` incluye `skills=[s.to_entity() for s in (self.skills or [])]`.

### `TicketRepository` (infra, `backend/infra/repositories/ticket_repo.py`)

- Método nuevo `update_skills(ticket_id: UUID, skill_ids: list[UUID]) -> Optional[Ticket]`:
  reemplazo total del set de Skills (idéntico a `ResourceRepository.update_skills`), filtrando
  por Skills existentes vía `db.get(SkillModel, sid)`.
- Método nuevo `count_tickets_with_skill(skill_id: UUID) -> int` (FR-007): cuenta cuántos
  tickets tienen esa Skill como requerida, usado por `SkillService.validate_delete()` para
  bloquear `DELETE /api/skills/{id}` con `409 skill_in_use` (mismo patrón que
  `count_active_resources_with_skill`).

### Serialización API (`backend/api/routes/tickets.py`)

- `_ticket_detail()` agrega `"skills": [{"id": ..., "code": ..., "label": ...}, ...]` al payload
  de detalle de ticket (FR-004), reutilizando el mismo shape `_skill_ref` ya definido en
  `resources.py` (se importa o se replica el modelo Swagger localmente).

## Migración

**Archivo**: `backend/infra/migrations/versions/027_ticket_skills.py`
**`down_revision`**: `"026"` (sigue a `026_ticket_timers.py`)

```
op.create_table(
    "ticket_skills",
    sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id", ondelete="CASCADE"),
              nullable=False, primary_key=True),
    sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.id"),
              nullable=False, primary_key=True),
    sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), nullable=False,
              server_default=sa.text("now()")),
)
```

Sin backfill: la tabla nace vacía — todos los tickets existentes quedan con cero Skills
requeridas por defecto (SC-002), sin afectar ningún dato existente.

## Diagrama de relación

```
tickets (1) ──< ticket_skills >── (1) skills
   │  ya incluye Tarea/Subtarea (misma tabla, spec 008)
   └── Ticket.skills: list[Skill]  (dominio, análogo a Resource.skills)
```
