# Quickstart: Usuario/cliente por Proyecto, Asignación de Personal y Estructura de Skills

Guía de validación end-to-end contra Docker real. **Solo validación dirigida** — no ejecutar
la suite completa durante el desarrollo (FR-020).

## Prerequisitos

```bash
docker compose up --build -d          # sywork_db + sywork_backend + sywork_frontend
docker compose logs backend | grep "Running upgrade"   # migración 025 aplicada
curl http://localhost:5000/health/    # {"status":"ok", ...}
```

Login en http://localhost:5173 con los usuarios semilla (`admin`, `coordinador`, `resolutor` —
ver `docs/credenciales_dev.txt`) y al menos un Usuario/cliente creado (pantalla de contactos).

Datos previos útiles: un Cliente con 2 Proyectos (A y B) y al menos un ticket existente con
solicitante (para validar el backfill).

## Escenario 0 — Migración de datos (FR-002, FR-006, FR-017, SC-003)

1. Antes de migrar (o sobre un backup): anotar `SELECT COUNT(*) FROM tickets WHERE
   client_contact_id IS NOT NULL`.
2. Tras `alembic upgrade head` (automático al arrancar el backend):
   - `SELECT name FROM roles WHERE name = 'Usuario/cliente'` → 1 fila; `'Encargado'` → 0.
   - El mismo COUNT de tickets → idéntico (0 pérdidas).
   - `SELECT COUNT(*) FROM project_members` → ≥ nº de pares distintos
     (proyecto, usuario_contacto) de los tickets con solicitante y proyecto.
   - `SELECT COUNT(*) FROM skills WHERE skill_type IS NULL` → 0.
   - `SELECT name FROM catalog_processes WHERE name IN ('Compras','Mantenimiento')` → 2 filas.

**Esperado**: rol renombrado con permisos intactos (login del Usuario/cliente sigue
funcionando), membresías backfilled, skills todas con tipo.

## Escenario 1 — Renombre visible en UI (US1, SC-001)

Como Admin, recorrer: Roles y Permisos (rol "Usuario/cliente"), pantalla de contactos (títulos
y botones), creación/edición de ticket (label del selector de solicitante), detalle de ticket.

**Esperado**: 0 apariciones de "Encargado"; el Usuario/cliente entra con sus credenciales y
conserva sus restricciones (sin Maestros/Catálogos/Panel).

## Escenario 2 — Personal del Proyecto (US3, SC-002)

1. Como Coordinador, en Proyectos → acción "Personal" del Proyecto A.
2. Pestaña **Personas**: asignar un Resolutor, un Coordinador y un Usuario/cliente → los 3
   listados con nombre, correo y tipo/rol.
3. Reintentar asignar al mismo Resolutor → rechazo `already_member` (sin duplicado).
4. Pestaña **Equipos**: crear subgrupo "Equipo X" con 2 miembros → visible con conteo; crear
   segundo subgrupo con un miembro repetido (multi-pertenencia OK).
5. Eliminar "Equipo X" → sus miembros siguen en la pestaña Personas.
6. Desasignar al Usuario/cliente del proyecto → desaparece de Personas y de los subgrupos.
7. Como Resolutor (sin `projects:edit`): la vista es de solo lectura (sin botones de
   asignar/quitar/crear equipo).

## Escenario 3 — Solicitante del ticket filtrado por Proyecto (US2, SC-004)

1. Vincular al Usuario/cliente U solo al Proyecto A (no al B, mismo Cliente).
2. Crear ticket en Proyecto A → U aparece en el selector de solicitante; guardar OK.
3. Crear ticket en Proyecto B → U **no** aparece; forzar por API `POST /api/tickets` con
   `client_contact_id` de U y `project_id` de B → **409 `contact_not_in_project`**.
4. Tickets históricos con solicitante → siguen mostrando su solicitante (dato intacto).

## Escenario 4 — Autoservicio acotado a proyectos vinculados (FR-007)

1. Login como Usuario/cliente U (vinculado solo al Proyecto A).
2. Crear ticket de autoservicio: el selector de proyecto solo ofrece el Proyecto A.
3. Por API, `POST /api/tickets` con `project_id` del Proyecto B → **409
   `project_not_assigned`**.
4. Sin `project_id` (ticket solo de Cliente): comportamiento actual sin cambios.

## Escenario 5 — Skills con tipo/herramienta/proceso (US4, SC-005)

1. Como Admin, en Skills: las 10 semillas visibles con su herramienta/proceso/tipo (tabla de
   [research.md Decisión 5](research.md)); JDE_GL y JDE_AP actualizadas, no duplicadas.
2. Crear skill sin tipo → rechazo 400; con tipo y sin herramienta/proceso → 201.
3. Editar una skill (PATCH): cambiar tipo y asignar herramienta → persiste.
4. Recursos existentes conservan sus skills asignadas (JDE_AR etc. con tipo backfilled).

## Escenario 6 — Regresión dirigida (SC-006)

Flujos no tocados siguen operando: transicionar un ticket por comentario tipificado, registrar
tiempo sobre una tarea propia, mover una tarea en el Kanban, listar "Mis Tareas".

## Tests dirigidos (cierre)

```bash
docker exec sywork_backend pytest \
  tests/api/test_project_members.py \
  tests/api/test_skills_structure.py \
  tests/api/test_tickets_client_contact.py \
  tests/domain/test_ticket_service_client_contact.py -v

cd frontend && npx tsc -b     # typecheck estricto sin errores
```
