# Research: Usuario/cliente por Proyecto, Asignación de Personal y Estructura de Skills

**Feature**: `010-proyecto-personal-skills` · **Date**: 2026-07-09

Sin unknowns de Technical Context (stack ya establecido). Las decisiones siguientes resuelven
los puntos de diseño abiertos de la spec.

## Decisión 1 — Alcance del renombre "Encargado" → "Usuario/cliente"

**Decision**: renombrar (a) la fila del rol en `roles` (`name` y `description`) vía migración
`025` con `UPDATE`, (b) la única referencia por nombre en el backend
(`role_repo.get_by_name("Encargado")` en `backend/api/routes/client_contacts.py`,
centralizándola en una constante `USUARIO_CLIENTE_ROLE_NAME`), y (c) todas las etiquetas
visibles del frontend (32 ocurrencias en 7 archivos: `TicketsPage`, `TicketDetailPage`,
`ClientContactsPage`, `SubtaskList`, `navigation.tsx`, `ProtectedRoute`, `types/ticket.ts`).
**NO** se renombran la tabla `client_contacts`, la entidad `ClientContact`, ni los campos
`client_contact_id` — sus nombres ya son neutros (contacto de cliente) y no contienen la
palabra "Encargado".

**Rationale**: la directriz del solicitante es alcance mínimo. Renombrar tabla/columnas
(`client_contacts` → otra cosa) obligaría a tocar 4 migraciones históricas referenciadas,
repos, modelos, rutas, tests y tipos TS sin ningún cambio visible para el usuario — el nombre
visible es lo que pide el requerimiento (FR-001/002). El `UPDATE` del rol conserva el UUID, por
lo que `role_permissions` y `users.role_id` quedan intactos (FR-002: mismos permisos, mismas
asignaciones).

**Alternatives considered**: (a) renombrar también tablas/campos a `client_users` — rechazado:
alto riesgo de regresión, cero valor visible, viola FR-019; (b) crear rol nuevo y migrar
usuarios — rechazado: rompe FKs y duplica seeds; el `UPDATE` in-place es atómico y reversible.

## Decisión 2 — Modelo del Personal del Proyecto y subgrupos "Equipo"

**Decision**: tres tablas nuevas:

- `project_members` (`id`, `project_id` FK, `user_id` FK, `assigned_at`; `UNIQUE(project_id,
  user_id)`): vínculo persona↔proyecto para **cualquier** usuario (interno o Usuario/cliente).
- `project_teams` (`id`, `project_id` FK, `name`, `created_at`; `UNIQUE(project_id, name)`).
- `project_team_members` (`team_id` FK → `project_teams` ON DELETE CASCADE, `member_id` FK →
  `project_members` ON DELETE CASCADE, PK compuesta).

El rol/tipo de cada persona NO se duplica en `project_members`: se deriva del rol del usuario
(`users.role_id`) al listar — una sola fuente de verdad.

**Rationale**: `project_team_members` referencia a `project_members` (no a `users`) para que
las invariantes salgan gratis del esquema: (a) solo personal ya asignado puede estar en un
subgrupo, (b) desasignar a alguien del proyecto lo elimina en cascada de todos los subgrupos
(escenario 5 de la US3), (c) eliminar un subgrupo no toca `project_members` (escenario 4).
RLS habilitado en las tres tablas, consistente con el resto de maestros.

**Alternatives considered**: (a) guardar el tipo de personal en `project_members` — rechazado:
duplica el rol del usuario y puede divergir; (b) `project_team_members.user_id` directo —
rechazado: permitiría miembros de subgrupo no asignados al proyecto y exigiría limpieza manual
en cascada; (c) equipos globales de empresa (como Teamwork corporativo) — rechazado: la spec
define subgrupos internos a cada Proyecto (Assumption).

## Decisión 3 — Fuente del solicitante del ticket: de Cliente a Proyecto

**Decision**: `tickets.client_contact_id` **se conserva sin cambios de esquema** (decisión de
clarificación con el usuario, 2026-07-09 — opción A). Cambia la fuente del selector y la
validación:

- `GET /api/client-contacts` gana filtro `project_id` (join `client_contacts.user_id` =
  `project_members.user_id` del proyecto): el frontend (TicketsPage/TicketDetailPage) pasa de
  filtrar por `client_id` a filtrar por `project_id`.
- `ticket_service.validate_create/validate_patch`: además del chequeo actual de Cliente
  (`client_contact_mismatch`), cuando el ticket tiene `project_id` se valida que el
  Usuario/cliente esté vinculado a ese Proyecto (409 `contact_not_in_project`). Si el ticket no
  tiene proyecto, se mantiene el comportamiento actual por Cliente (no todos los tickets tienen
  proyecto — el campo es opcional en el esquema).
- Autoservicio: al crear un ticket, si el creador es Usuario/cliente y elige un `project_id`,
  este debe estar entre sus proyectos vinculados (409 `project_not_assigned`); el selector de
  proyectos del autoservicio se filtra a sus membresías.

**Rationale**: conserva intacta la spec `007` (histórico, limpieza al cambiar Cliente, bloqueo
en autoservicio/estados finales) y agrega la restricción por Proyecto solo donde hay proyecto —
sin migración destructiva ni cambio del contrato existente del detalle del ticket.

**Alternatives considered**: (a) eliminar `client_contact_id` del ticket — rechazado por el
usuario en la clarificación; (b) endpoint nuevo `GET /api/projects/{id}/members?role=...` como
fuente del selector — descartado como fuente primaria: el shape que consume el selector ya es
el de client-contacts; un filtro nuevo en el endpoint existente es el diff mínimo.

## Decisión 4 — Migración de datos (backfill de membresías)

**Decision**: en la migración `025`, tras crear `project_members`: insertar una membresía por
cada par distinto (`tickets.project_id`, `client_contacts.user_id`) donde
`tickets.client_contact_id IS NOT NULL AND tickets.project_id IS NOT NULL` (join por
`client_contact_id` → `client_contacts.id`), con `ON CONFLICT DO NOTHING`.

**Rationale**: cumple FR-006/SC-003 — ningún Usuario/cliente que ya figura como solicitante
queda fuera del personal de esos proyectos, y ningún ticket pierde su referencia (no se toca
`tickets`). Idempotente y sin pérdida en re-ejecución.

**Alternatives considered**: backfill también de Resolutores/Coordinadores por historial de
asignaciones — rechazado: la spec solo exige no dejar huérfano al Usuario/cliente; asignar
personal interno es una acción manual del Coordinador desde la UI nueva (alcance mínimo).

## Decisión 5 — Estructura de Skill y semillas

**Decision**: ampliar la tabla `skills` con:

- `skill_type` TEXT NOT NULL, CHECK `IN ('funcional','tecnico')` — en BD/API el código va en
  snake_case sin acento (`tecnico`), la UI muestra "Funcional"/"Técnico" (convención existente
  estados/etiquetas).
- `tool_id` UUID NULL, FK `catalog_tools(id)`.
- `process_id` UUID NULL, FK `catalog_processes(id)`.

Orden de la migración: (1) agregar columnas nullable, (2) backfill de tipo para las skills
preexistentes (JDE_AR y ORACLE_CRM → `funcional`; ORACLE_FUSION, API_REST, SQL_ORACLE,
ORCHESTRATOR → `tecnico`; cualquier otra no listada → `tecnico` por defecto), (3) `SET NOT
NULL` sobre `skill_type`, (4) insertar en `catalog_processes` los procesos "Compras" y
"Mantenimiento" si no existen (mismo patrón `active=true` del seed de `011`), (5) upsert de las
10 semillas por `code` (las existentes JDE_GL/JDE_AP se **actualizan**, no se duplican):

| code | label | tool (nombre) | process (nombre) | skill_type |
|------|-------|---------------|------------------|------------|
| JDE_GL | JDE General Ledger | JDE | Finanzas | funcional |
| JDE_AP | JDE Accounts Payable | JDE | Compras | funcional |
| JDE_MTC | JDE Maintenance Mgmt | JDE | Mantenimiento | funcional |
| BSFN | JDE Business Functions (dev) | JDE | — | tecnico |
| SQL_JDE | SQL sobre JDE | JDE | — | tecnico |
| OIC | Oracle Integration Cloud | Oracle Fusion | Integraciones | tecnico |
| APEX | Oracle APEX (genérico) | — | — | tecnico |
| BI | Business Intelligence (genérico) | — | — | tecnico |
| JAVA_PYTHON_REACT | Java / Python / React (genérico) | — | — | tecnico |
| DBA | Admin. BD (genérico) | — | — | tecnico |

Los `tool_id`/`process_id` de las semillas se resuelven por nombre en la propia migración
(subselect por `name`), nunca por UUID hardcodeado.

**Rationale**: reutiliza los catálogos administrables existentes (Assumption de la spec, cero
tablas nuevas para herramienta/proceso); el CHECK garantiza FR-013 a nivel de esquema además
del servicio. El código `JAVA_PYTHON_REACT` normaliza "JAVA / PYTHON / REACT" a la convención
UPPER_SNAKE de la Constitución (los códigos de skill no admiten espacios/barras); el label
conserva la forma legible.

**Alternatives considered**: (a) enum PostgreSQL para el tipo — rechazado: CHECK + TEXT es el
patrón ya usado (`ck_tickets_status`) y más simple de migrar; (b) catálogo nuevo
`skill_types` administrable — rechazado: son exactamente 2 valores estables definidos por el
solicitante, YAGNI.

## Decisión 6 — UI: página "Personal del Proyecto" con pestañas Personas/Equipos

**Decision**: página nueva `ProjectPeoplePage.tsx` (ruta `/projects/:id/people`), accesible
desde una acción por fila en `ProjectsPage`, con dos pestañas replicando la referencia de
Teamwork: **Personas** (tabla: nombre, correo, tipo/rol como Tag, fecha de asignación, acción
quitar; botón "Asignar personal" con búsqueda de usuarios activos) y **Equipos** (lista de
subgrupos con nombre, miembros como avatares y conteo; crear/renombrar/eliminar subgrupo y
administrar miembros — solo personal ya asignado). Mutaciones visibles solo con permiso de
gestión (`projects:edit`); lectura para cualquier rol con `projects:view`.

**Rationale**: el modal actual de edición de ProjectsPage (196 líneas, formulario simple) no
tiene espacio para dos pestañas con tablas — una página dedicada sigue el patrón ya usado por
`ProjectListsPage` (spec `009`) y respeta el estilo de navegación con breadcrumbs existente.

**Alternatives considered**: (a) tabs dentro del modal de edición — rechazado: UX pobre para
tablas + búsqueda, y el modal se usa también para "crear" donde no existe aún el proyecto;
(b) drawer lateral — rechazado: la referencia de Teamwork es una vista completa con pestañas.

## Decisión 7 — Permisos de los endpoints nuevos

**Decision**: los endpoints de members/teams viven bajo el módulo `projects` existente
(`enforce_module("projects")`, igual que el resto de rutas de proyectos): lectura con
`projects:view`, mutación con `projects:edit`. No se crean permisos nuevos. El filtro
`project_id` de `GET /api/client-contacts` conserva la regla de acceso actual del endpoint
(manage, o `tickets:create`/`tickets:edit`).

**Rationale**: FR-012 pide gestión para Coordinador/Admin — ambos ya tienen `projects:edit`;
crear un módulo de permisos nuevo agregaría seeds y matriz sin necesidad (lección de la spec
`009`: los bugs E2E vinieron de permisos demasiado restrictivos, no demasiado laxos).

**Alternatives considered**: módulo nuevo `project_members:manage` — rechazado: seed adicional
+ matriz de permisos que nadie pidió; YAGNI.
