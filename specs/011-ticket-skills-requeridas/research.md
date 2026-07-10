# Research: Skills Requeridas en el Ticket

## Contexto técnico resuelto

**Language/Version**: Python 3.12 (backend) + TypeScript strict (frontend) — sin cambios sobre
el stack existente.

**Primary Dependencies**: Flask-RESTX, SQLAlchemy 2.x + Alembic, React 19 + Ant Design 5 — todas
ya aprobadas en la Constitución; no se requiere ninguna dependencia nueva.

**Storage**: PostgreSQL 16. Nueva tabla puente `ticket_skills` (many-to-many), mismo patrón que
`resource_skills` (migración `004`).

**Testing**: pytest (API dirigida contra Postgres real en Docker) + `tsc -b` (frontend).

**Target Platform**: Web (Docker Compose: `sywork_db` + `sywork_backend` + `sywork_frontend`).

**Project Type**: Web application (backend + frontend), feature transversal sobre Ticket/Tarea/
Subtarea (misma tabla `tickets`).

**Performance Goals**: sin metas nuevas — SC-001 (<15s para agregar/quitar una Skill) se cumple
con una operación de escritura simple sobre una tabla puente pequeña.

**Constraints**: el cambio de Skills requeridas NO debe estar sujeto a `locked_fields_for(status)`
(FR-002) — a diferencia del resto de la clasificación del ticket (tool_id, process_id, etc.), que
sí se bloquea en ciertos estados vía el PATCH genérico `TicketRepository.update_fields`.

**Scale/Scope**: catálogo de Skills ya existente (~10-20 activos, spec `010`); la relación es
opcional y sin límite máximo por ticket (Assumption del spec).

## Decisión 1 — Reutilizar el patrón exacto de `resource_skills` (spec `004`/`010`)

**Decision**: Modelar "Skills requeridas del ticket" como una tabla puente `ticket_skills
(ticket_id, skill_id)` sin columnas propias más allá de un timestamp de auditoría, idéntica en
forma a `resource_skills` ya existente.

**Rationale**: el proyecto ya resolvió exactamente este problema (relación N:M opcional entre una
entidad y el catálogo de Skills) para Recursos. Reutilizar el mismo patrón minimiza superficie
nueva, es consistente con Principio II (Clean Architecture) y evita introducir un segundo enfoque
para el mismo tipo de relación.

**Alternatives considered**:
- Columna `skill_ids` JSONB en `tickets`: rechazado — pierde integridad referencial (una Skill
  desactivada o borrada no se refleja) y contradice el patrón ya establecido.
- Tabla con `id` propio + timestamps de auditoría completos: rechazado por sobre-ingeniería; la
  tabla `resource_skills` tampoco los tiene y esta relación tiene los mismos requisitos.

## Decisión 2 — Endpoint dedicado de reemplazo total, no el PATCH genérico de ticket

**Decision**: Exponer `PATCH /api/tickets/{id}/skills` como endpoint independiente (recibe la
lista completa de `skill_ids` y reemplaza el set actual), en vez de agregar `skill_ids` como un
campo más al PATCH genérico (`TicketPatch` en `backend/api/routes/tickets.py:674`).

**Rationale**: el PATCH genérico pasa por `TicketService.validate_patch()`, que aplica
`locked_fields_for(ticket.status)` — bloquea campos como `tool_id`/`process_id` en ciertos
estados (p. ej. CONTACTO). El requisito explícito de la spec (FR-002, User Story 2) es que las
Skills requeridas se puedan cambiar en **cualquier** estado, incluidos Cerrado y Cancelado. Un
endpoint dedicado sin paso por `validate_patch` es la forma más simple de garantizar esto sin
tocar la lógica de bloqueo de campos que sí aplica al resto de la clasificación. Es exactamente
el mismo criterio ya usado para `PATCH /api/resources/{id}/skills` (reemplazo total,
independiente del PATCH genérico de recurso).

**Alternatives considered**:
- Excluir `skill_ids` de `locked_fields_for()` dentro del PATCH genérico: rechazado — mezclaría
  dos políticas de bloqueo distintas en la misma función y aumentaría el riesgo de romper el
  comportamiento ya validado del resto de los campos.

## Decisión 3 — Sin servicio de dominio nuevo; operación directa en el repositorio

**Decision**: La actualización de Skills requeridas se resuelve directamente en
`TicketRepository.update_skills(ticket_id, skill_ids)` (Capa 2), llamada desde la ruta (Capa 3),
sin crear un `TicketSkillService` en el dominio.

**Rationale**: no hay reglas de negocio más allá de "el set de Skills debe existir en el
catálogo" (garantizado por la FK) y "sin duplicados" (garantizado por la PK compuesta de la tabla
puente). Es el mismo criterio ya aplicado a `ResourceRepository.update_skills()`, que tampoco
pasa por un servicio de dominio dedicado — la validación de existencia de cada `skill_id` ocurre
implícitamente al filtrar por `db.get(SkillModel, sid)` antes de asignar la relación.

**Alternatives considered**:
- Crear `TicketSkillService` en `backend/domain/services/`: rechazado por sobre-ingeniería —
  no hay lógica de negocio que justifique una capa de dominio propia; se evaluará si aparecen
  reglas nuevas (p. ej. límites por rol) en una fase futura.

## Decisión 4 — Permiso reutilizado: `tickets:edit`

**Decision**: El endpoint `PATCH /api/tickets/{id}/skills` exige el mismo permiso que el resto de
la edición de clasificación del ticket: `@require_permission("tickets", "edit")`.

**Rationale**: FR-005 dice explícitamente "los mismos roles que edición del ticket" (Coordinador,
Resolutor, Admin). No se introduce un permiso `skills:edit_ticket` nuevo porque no hay ningún
caso de uso que requiera diferenciar el acceso a Skills requeridas del resto de la edición del
ticket.

**Alternatives considered**: permiso dedicado `tickets:skills` — rechazado, added complexity sin
un requisito que lo justifique.

## Decisión 5 — Serialización: incluir `skills` en el detalle del ticket existente

**Decision**: Agregar `skills: list[SkillRef]` al payload ya devuelto por
`GET /api/tickets/{id}` (función `_ticket_detail`), en vez de crear un endpoint de lectura
separado.

**Rationale**: FR-004 pide que el detalle del ticket muestre las Skills junto al resto de la
clasificación — no hay necesidad de una llamada adicional. Mismo criterio que `Resource.skills`
en el detalle de recurso.
