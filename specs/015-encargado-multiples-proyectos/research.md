# Research: Encargado (Usuario/cliente) en múltiples Proyectos

**Feature**: `015-encargado-multiples-proyectos` · **Date**: 2026-07-14

No hay `[NEEDS CLARIFICATION]` pendientes del spec — este documento registra las decisiones de
diseño concretas, verificadas contra el código real antes de planificar.

## Decisión 1 — Dónde vive hoy la restricción a un solo Proyecto

**Hallazgo** (verificado en código, no en specs previas): el modelo de datos (`project_members`,
spec 010) ya es muchos-a-muchos y `ticket_service`/`client_contact_repo` ya filtran
correctamente por proyecto. La restricción real está solo en dos puntos:

1. `POST /api/client-contacts` (`backend/api/routes/client_contacts.py:160-231`) acepta un único
   `project_id` y crea exactamente una fila en `project_members`.
2. El modal "Nuevo Usuario/cliente" (`frontend/src/pages/ClientContactsPage.tsx:122-130`) usa un
   `<Select>` simple (no `mode="multiple"`), y no existe ninguna acción para agregar/quitar
   Proyectos después del alta.

**Decisión**: no se requiere migración de esquema. El trabajo es (a) relajar el endpoint de alta
para aceptar varios Proyectos y (b) agregar un sub-recurso para gestionar Proyectos de un
Usuario/cliente ya existente, reutilizando `ProjectMemberRepository` (ya existe, spec 010).

**Alternativas consideradas**: reutilizar directamente el endpoint genérico
`POST/DELETE /api/projects/{project_id}/members` desde `ClientContactsPage.tsx` — rechazada
porque (i) para el `DELETE` requiere conocer el `project_members.id` (no expuesto hoy en el
listado de contactos, que solo trae `{id, name}` del Proyecto) y (ii) mezclaría en la pantalla de
Usuarios/cliente una llamada pensada para la pantalla de "Personal del Proyecto", rompiendo la
cohesión del contrato por recurso.

## Decisión 2 — Forma del campo en el alta

**Decisión**: `POST /api/client-contacts` cambia `project_id: string` (singular) por
`project_ids: string[]` (uno o más). No se mantiene el nombre singular como alias: es un único
consumidor interno (el propio frontend de este monorepo, sin API pública externa), por lo que no
aplica una compatibilidad hacia atrás. `client_id` directo (forma legada, spec 007, sin
Proyecto) se mantiene sin cambios.

**Rationale**: evita ambigüedad de dos campos (`project_id` y `project_ids`) conviviendo, y
simplifica la validación de "mismo Cliente" a un solo camino.

## Decisión 3 — Validación de "mismo Cliente"

**Decisión**: se agrega una validación de dominio en `ClientContactService`
(`backend/domain/services/client_contact_service.py`) que, dada una lista de Proyectos
resueltos, verifica que todos compartan `client_id` y que estén activos; devuelve el `client_id`
común o levanta `ClientContactBusinessError` (400 `validation_error` si hay Clientes distintos,
404 si algún Proyecto no existe, 409 si alguno está inactivo — mismos códigos que hoy usa el
alta con un solo proyecto).

**Rationale**: mantiene la regla de negocio en Capa 1 (Principio I), reutilizable tanto por el
alta (US1) como por la gestión posterior de Proyectos (US2).

## Decisión 4 — Gestión de Proyectos de un Usuario/cliente existente (US2)

**Decisión**: dos endpoints nuevos, acotados al recurso `client-contacts` (mismo patrón de
`contracts/client-contacts.md` de spec 010):

- `POST /api/client-contacts/{contact_id}/projects` — agrega un Proyecto (valida mismo Cliente,
  Proyecto activo, no duplicado vía `ProjectMemberRepository.is_member`).
- `DELETE /api/client-contacts/{contact_id}/projects/{project_id}` — quita la membresía
  (resuelve el `project_members.id` internamente vía un método nuevo
  `get_by_project_and_user(project_id, user_id)` en `ProjectMemberRepository`, luego reutiliza
  `ProjectMemberRepository.delete`).

Ambos bajo el mismo permiso que el alta: `client_contacts:manage`.

**Alternativas consideradas**: exponer `member_id` en el listado de contactos para poder llamar
al endpoint genérico de proyectos directamente — rechazada porque acopla la pantalla de
Usuarios/cliente al modelo interno de `project_members` sin necesidad; el sub-recurso dedicado
es más simple de consumir desde el frontend (solo necesita `project_id`, que ya tiene).

## Decisión 5 — UI

**Decisión**:
- El modal "Nuevo Usuario/cliente" cambia su `<Select>` de Proyecto a `mode="multiple"`
  (Ant Design 5, ya aprobado — Principio V), con al menos un Proyecto requerido salvo que se use
  la forma legada de Cliente directo.
- La columna "Proyectos" de la tabla agrega una acción por fila ("Gestionar proyectos") que abre
  un modal simple: multi-select para agregar y un botón "Quitar" por cada `Tag` de Proyecto ya
  asignado.

**Rationale**: reutiliza los mismos componentes Ant Design ya usados en la página (`Select`,
`Tag`, `Modal`), sin nuevas dependencias (Principio V) ni pantallas nuevas.
