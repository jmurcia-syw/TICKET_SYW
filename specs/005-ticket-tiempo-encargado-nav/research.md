# Research: Registro de tiempo en el ticket, rol Encargado y navegación

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

No quedaron marcadores `NEEDS CLARIFICATION` en el Technical Context — el stack y la arquitectura
ya están fijados por la Constitución y por el precedente de Fases 1-2. Este documento resuelve
las decisiones de diseño propias de esta fase, investigadas contra el código real antes de
plani­ficar (ver hallazgos citados en cada decisión).

## Decisión 1: Hora de inicio/fin se agrega a `work_sessions`, no a una entidad nueva

- **Decision**: Agregar `started_at`/`ended_at` (TIMESTAMPTZ, nullable) a la tabla `work_sessions`
  ya existente, en vez de crear una entidad de "sesión con timer" separada.
- **Rationale**: `backend/domain/entities/work_session.py` y `work_session_service.py` ya
  implementan el registro atómico de tiempo con sus reglas (límite 24h/día, ventana de edición).
  Agregar dos columnas nullable es el cambio mínimo; la duración sigue siendo la fuente de verdad
  para esas reglas (se recalcula desde inicio/fin, o se fija manualmente si el usuario no carga
  horas exactas — FR-001b).
- **Alternatives considered**: Entidad nueva "TimeEntry v2" con motor de reglas propio —
  rechazada, duplicaría lógica ya probada (18 tests de dominio existentes) sin necesidad.

## Decisión 2: El "Encargado" se modela con una tabla `client_contacts`, no reutilizando `resources`

- **Decision**: Nueva tabla `client_contacts` (`user_id` FK `users.id` único, `client_id` FK
  `clients.id`), en vez de agregar `client_id` a la tabla `resources`.
- **Rationale**: `resources` (`backend/infra/models/resource_model.py`) representa personal
  interno con campos irrelevantes para un Encargado (nacionalidad, tipo de contrato,
  compensación, skills, equipo/jefe). Mezclar un contacto externo ahí ensuciaría ese modelo y
  arriesgaría exponer datos de compensación por accidente. `client_contacts` es el equivalente de
  `resources` pero para el lado del cliente — mismo patrón de "tabla ligera vinculada a `users`
  por `user_id`", solo que apuntando a `clients` en vez de tener perfil de RRHH.
- **Alternatives considered**: Campo `client_id` nullable directo en `users` — rechazado, mezcla
  un concepto de un solo rol en una tabla genérica compartida por todos los roles.

## Decisión 3: Nuevo permiso `tickets:view_own`, sin decorador nuevo

- **Decision**: Se agrega el permiso `tickets:view_own` (otorgado solo a Encargado). Los
  endpoints `GET /api/tickets` y `GET /api/tickets/{id}` dejan de usar únicamente
  `@require_permission("tickets", "view")` y pasan a validar manualmente
  `current_user_has("tickets","view") or current_user_has("tickets","view_own")`, filtrando por
  `created_by = caller` cuando el caller solo tiene `view_own`.
- **Rationale**: Hoy `tickets:view` es todo-o-nada (`backend/api/routes/tickets.py:347,443` —
  confirmado por lectura directa del código) — cualquier rol con ese permiso ve todos los
  tickets, correcto para Coordinador/QM/Admin/Resolutor (que usan el historial como base de
  conocimiento, según el spec de Fase 1). Encargado necesita una semántica distinta ("view_own"),
  igual patrón ya validado en `work_sessions:view_own` vs `view_all` de la Fase 2 anterior — se
  reutiliza la misma convención en vez de inventar una nueva.
- **Alternatives considered**: Hardcodear `if role.name == "Encargado"` en el endpoint —
  rechazado, rompe el modelo de permisos parametrizados por rol ya vigente (Principio VI:
  reglas explícitas, no ad-hoc por nombre de rol).

## Decisión 4: Creación de ticket por Encargado usa valores por defecto para campos de triage interno

- **Decision**: Cuando el creador del ticket es un Encargado, el formulario de creación no pide
  `ticket_type`/`priority`/`severity`/`client_id` — se completan con defaults
  (`incident`/`medium`/`s3`) y el `client_id` se resuelve automáticamente desde su fila en
  `client_contacts`. Coordinador/QM pueden reclasificar estos valores después, igual que hoy
  hacen con cualquier ticket en Triage.
- **Rationale**: Confirmado en `backend/api/routes/tickets.py:391` que hoy esos 4 campos son
  obligatorios en el payload de creación — son taxonomía interna de triage (tipo
  incidente/evolutivo/preventivo, severidad S1-S4) que un usuario externo no tiene por qué
  conocer ni completar correctamente. Es el patrón estándar de mesas de ayuda: el solicitante
  describe el problema en texto libre, el equipo interno lo clasifica.
- **Alternatives considered**: Exponer los mismos 6 campos que usa Coordinador — rechazado, viola
  el principio de "usuario básico" del spec (FR-008) y generaría clasificaciones incorrectas por
  desconocimiento del dominio interno.

## Decisión 5: Navegación con `state` de React Router, sin mover los filtros a la URL

- **Decision**: Cada pantalla que enlaza al detalle de un ticket (Kanban, Tickets, Panel de
  Asignación) pasa `navigate('/tickets/:id', { state: { from: { pathname, label } } })`. El
  detalle lee `useLocation().state?.from` y, si existe, lo usa para el botón "Volver"; si no
  existe (acceso directo por URL), cae al default `/tickets` (FR-013).
- **Rationale**: Confirmado por lectura de código que hoy `TicketDetailPage.tsx:73` hace
  `navigate('/tickets')` fijo, sin relación con ningún flujo de asignación — el "redirige a
  Asignar" que describe el usuario no se reproduce tal cual en el código actual, pero el defecto
  real (ignora el origen) sí existe y es la causa raíz a corregir. `state` de React Router es la
  forma estándar y ya soportada (v6.28, sin librería nueva) de pasar este contexto sin tocar la
  URL.
- **Alternatives considered**: Mover los filtros de `TicketsPage` a query params de la URL para
  poder usar `navigate(-1)` (retroceso de historial) — más "correcto" a largo plazo, pero es un
  cambio más amplio a una pantalla que no forma parte del pedido explícito de esta fase; queda
  fuera de alcance (ver Assumptions del spec). `state` resuelve los 3 orígenes pedidos (Kanban,
  Tickets, Panel) sin ese refactor.
