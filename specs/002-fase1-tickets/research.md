# Research: Fase 1 — Tickets

**Date**: 2026-07-02 | **Feature**: specs/002-fase1-tickets

## Decisión 1 — Máquina de estados desde Fase 1 con python-transitions

**Decision**: Codificar la matriz de transiciones (FR-008) como una máquina de estados en
`backend/domain/fsm/ticket_fsm.py` usando `python-transitions`, disparada por acciones
manuales (asignar, comentar, botones). El servicio de comentarios consulta la FSM para
validar y ejecutar la transición.

**Rationale**: La Constitución exige `python-transitions` para FSM y prohíbe implementaciones
custom. Aunque en Fase 1 no hay automatización, centralizar la matriz en el dominio garantiza
que UI y API no puedan producir transiciones inválidas (SC-002) y que la Fase 6 (motor
automático + triggers) solo agregue callbacks sin rediseño.

**Alternatives considered**: dict de transiciones válidas hecho a mano (viola la
Constitución); validación en cada endpoint (dispersa la regla, riesgo de divergencia).

## Decisión 2 — Comentario tipificado = operación atómica comentario+transición

**Decision**: Un único endpoint `POST /api/tickets/{id}/comments` recibe `{type, body,
attachments}`; el `CommentService` resuelve si el tipo dispara transición (FR-014), la valida
contra la FSM, y persiste comentario + transición + notificación en una sola transacción.

**Rationale**: Evita estados intermedios inconsistentes (comentario sin transición o
viceversa) y refleja el modelo del Excel donde el comentario ES el trigger. Los tipos sin
efecto (Comentario interno) pasan por el mismo endpoint sin transición.

**Alternatives considered**: endpoints separados `/comments` y `/status` (permite
divergencia y doble round-trip); PATCH de estado directo (contradice FR-011/SC-004 — el
estado nunca se edita a mano).

## Decisión 3 — Gold Standard Dataset como tabla append-only con snapshot JSONB

**Decision**: Tabla `ticket_assignments` sin UPDATE/DELETE; cada asignación inserta una fila
con FKs (ticket, asignador, asignado) y columna `context JSONB` con el snapshot: skills del
asignado (códigos), conteo de tickets abiertos, prioridad/severidad del ticket.

**Rationale**: El snapshot debe reflejar el momento de la decisión (los skills y la carga
cambian); JSONB permite enriquecer el contexto en fases futuras sin migraciones. Append-only
garantiza el dataset íntegro para entrenar al Triage Agent (Principio VI).

**Alternatives considered**: reconstruir el contexto por joins al consultarlo (falso: los
datos cambian con el tiempo); tabla normalizada de contexto (rígida para un dataset ML).

## Decisión 4 — Enforcement: decorador @require_permission + registro global

**Decision**: Reescribir `backend/api/middleware/rbac.py` como
`@require_permission("tickets", "create")`: valida JWT (reutiliza `jwt_required_active`),
carga los permisos del rol (cacheados por request en `g`) y devuelve 403 sin detalle si
falta el permiso. Aplicarlo a TODAS las rutas de tickets y maestros (FR-022). Rutas públicas:
`/api/auth/login`, `/api/auth/google`, `/health`.

**Rationale**: El patrón ya existe probado en el endpoint de compensación (Fase 0); se
generaliza. Los permisos por rol cambian poco: una consulta por request es aceptable al
volumen objetivo (10-30 usuarios).

**Alternatives considered**: middleware global before_request con tabla ruta→permiso (más
mágico, difícil de leer por endpoint); mantener enforcement solo frontend (rechazado en
clarificación Q3).

## Decisión 5 — Adjuntos en filesystem con volumen Docker

**Decision**: Archivos en `/repo/uploads/tickets/{ticket_id}/{uuid}-{filename}` (volumen ya
montado); metadatos (nombre, tamaño, content-type, ruta) en `comment_attachments`. Descarga
vía endpoint autenticado que sirve el archivo (nunca URL pública directa).

**Rationale**: On-premise sin object storage; los adjuntos de soporte (logs, capturas) no
requieren cifrado (Assumption de la spec). Volumen Docker sobrevive reinicios.

**Alternatives considered**: bytea en Postgres (infla la DB y las copias de seguridad,
peor streaming); S3/MinIO (infraestructura nueva no justificada a este volumen).

## Decisión 6 — Número consecutivo con secuencia de Postgres

**Decision**: `ticket_number` entero de una secuencia Postgres dedicada, mostrado como
`TK-{n:06d}` (ej. TK-000123). La secuencia garantiza unicidad sin bloqueos a nivel de
aplicación.

**Rationale**: Concurrencia resuelta por la DB; formato legible exigido por FR-002.
Global (no por cliente) según Assumption de la spec.

**Alternatives considered**: MAX+1 en aplicación (condición de carrera); UUID visible
(ilegible para humanos, rechazado por FR-002).

## Decisión 7 — Notificaciones por polling, sin websockets

**Decision**: Tabla `notifications` + endpoint `GET /api/notifications?unread=true`;
la campana del frontend consulta al cargar cada vista y cada 60 s (intervalo simple).
Marcar leídas: `PATCH /api/notifications/read`.

**Rationale**: SC-006 solo exige que la notificación aparezca "en la siguiente
carga/refresco". Websockets/SSE agregan infraestructura (y Celery/Redis del stack aprobado
aún no se necesita) sin requisito que lo justifique en esta fase.

**Alternatives considered**: SSE (complejidad en proxy on-premise); Celery+Redis+push
(reservado para Fase 6 donde sí habrá triggers automáticos y Google Chat).

## Decisión 8 — Bloqueo de campos por estado en el dominio

**Decision**: Mapa `FIELD_LOCKS: dict[Estado, set[campo]]` en `ticket_service.py`; el PATCH
de ticket rechaza con 409 los campos bloqueados para el estado actual (FR-010). El frontend
deshabilita los mismos campos leyendo la misma matriz expuesta en la respuesta del detalle
(`locked_fields: [...]`).

**Rationale**: Una sola fuente de verdad (dominio) que la UI consume; evita duplicar la
matriz en TypeScript y que diverja.

**Alternatives considered**: lógica solo en frontend (violable por API); columnas por estado
en DB (sobre-ingeniería).

## Decisión 9 — RLS en tickets

**Decision**: Política RLS sobre `tickets` coherente con Fase 0: roles con permiso completo
ven todo; el Resolutor puede leer todos los tickets (necesita contexto e historial de
soluciones — ver SDD V3 "Concepto de Skills") pero la API solo le permite transicionar los
asignados a él (FR-028, validación en servicio).

**Rationale**: El SDD V3 indica que los resolutores consultan el historial de tickets como
base de conocimiento; restringir lectura rompería ese caso de uso. La restricción crítica es
de escritura/transición, que se aplica en dominio + API.

**Alternatives considered**: RLS de lectura por asignado (rompe la base de conocimiento);
sin RLS (pierde la doble protección del Principio IV).
