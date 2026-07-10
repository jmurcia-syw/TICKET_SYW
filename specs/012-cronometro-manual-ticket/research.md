# Research: Cronómetro Manual de Tiempo en el Ticket

No quedaron `NEEDS CLARIFICATION` en el Technical Context — el stack, storage y patrones ya
están fijados por la Constitución y por la feature `004-fase2-registro-tiempos` (Registro de
tiempos), que este cronómetro extiende sin introducir tecnología nueva. Este documento resuelve
las decisiones de **diseño técnico** necesarias para pasar de la spec a `data-model.md` /
`contracts/`.

## Decisión 1 — Modelo de datos: una fila por recurso, no por par recurso/ticket

**Decisión**: tabla nueva `ticket_timers` con `resource_id` como **clave primaria** (una fila
por recurso, siempre existe o se crea on-demand); `ticket_id` nullable (NULL cuando el
cronómetro está inactivo).

**Rationale**: la spec (FR-006) exige como máximo un cronómetro activo por recurso a la vez,
sin importar el ticket. Modelar `resource_id` como PK hace esa regla estructural (no se puede
insertar una segunda fila para el mismo recurso) en vez de depender de una validación aplicativa
adicional o de un índice único parcial más complejo.

**Alternativas consideradas**:
- Una fila por par `(resource_id, ticket_id)` con estado — requeriría un índice único parcial
  (`WHERE status IN ('running','paused')`) para impedir dos cronómetros activos del mismo
  recurso en tickets distintos, y una consulta adicional para encontrar "el" cronómetro activo
  del recurso. Más complejo sin aportar valor, dado que solo interesa el cronómetro *actual*.
- Tabla de eventos (`timer_events`: start/pause/resume/finish) reconstruyendo el estado — mucho
  más flexible pero es sobre-ingeniería para una herramienta explícitamente provisional; se
  descarta por Principio de simplicidad y por la directriz de alcance acotado del proyecto.

## Decisión 2 — Cómputo del tiempo transcurrido: basado en timestamps del servidor, no en un proceso en segundo plano

**Decisión**: el servidor guarda `started_at` (momento del último "Iniciar"/"Reanudar") y
`accumulated_seconds` (lo ya sumado en ciclos previos de esa sesión). El tiempo total en
cualquier momento se calcula como `accumulated_seconds + (now - started_at)` si está `running`,
o simplemente `accumulated_seconds` si está `paused`. El frontend solo hace un `setInterval` de
1s para *mostrar* el número corriendo entre pedidos al backend, pero la fuente de verdad es
siempre el cálculo servidor-side con timestamps.

**Rationale**: satisface FR-004/US2 (persistencia entre recargas y sesiones) sin necesitar un
proceso en segundo plano, colas ni tareas programadas — no se requiere `Celery`/`Redis` para
esto (evita nueva infraestructura). Al recargar la página, el frontend simplemente vuelve a
pedir `GET /api/timer` y reconstruye el reloj visual desde el valor servidor-side correcto.

**Alternativas consideradas**:
- Guardar el tiempo transcurrido solo en el navegador (localStorage) — descartado porque no
  sobrevive a un cambio de dispositivo/navegador ni a un cierre de sesión prolongado, y la spec
  (US2) pide explícitamente persistencia server-side.
- Un job periódico que vaya sumando minutos a la fila — innecesario y más frágil (relojes
  desincronizados, riesgo de doble conteo) frente al cálculo derivado directo desde timestamps.

## Decisión 3 — Reutilizar el permiso `work_sessions:manage`, sin permiso nuevo

**Decisión**: todos los endpoints del cronómetro exigen el permiso ya existente
`work_sessions:manage` (el mismo que hoy habilita cargar un Registro de tiempo manual). No se
crea un módulo/permiso nuevo en la matriz RBAC.

**Rationale**: la spec (Assumptions) establece que el cronómetro respeta el mismo universo de
recursos que ya puede registrar tiempo. Reutilizar el permiso evita una migración de
`role_permissions` y mantiene el principio de cambios acotados.

**Alternativas consideradas**: crear `work_sessions:timer` como sub-permiso — se descarta por
falta de necesidad real (ningún escenario de la spec exige diferenciar quién puede cronometrar
de quién puede cargar tiempo manualmente).

## Decisión 4 — "Terminar" reutiliza `WorkSessionService.create()`, no duplica la lógica de registro

**Decisión**: al terminar el cronómetro, el backend llama al mismo `WorkSessionService.create()`
usado por la carga manual (`POST /api/work-sessions`), pasando `duration_minutes` calculado
(redondeado, mínimo 1) y `work_date` de hoy — sin `started_at`/`ended_at` explícitos (ya que el
cronómetro pudo tener pausas intermedias que no forman un rango continuo simple).

**Rationale**: cumple FR-003/FR-009 (el resultado debe ser un Registro de tiempo normal, visible
en los mismos reportes) sin reimplementar validaciones ya existentes (ticket cerrado, recurso
participante, límite diario `MAX_DAILY_MINUTES`). Cualquier regla de negocio del Registro de
tiempo (spec `004`) aplica automáticamente al resultado del cronómetro.

**Alternativas consideradas**: escribir directamente en `work_sessions` desde el servicio del
cronómetro — se descarta porque duplicaría validaciones (duplicar es la anti-patrón que la
directriz de alcance acotado de specs recientes viene evitando).

## Decisión 5 — Advertencia por cronómetro olvidado (FR-010): campo informativo, no bloqueo

**Decisión**: `GET /api/timer` devuelve `running_seconds` (tiempo corriendo en el ciclo actual) y
un flag `stale` (`true` cuando `running_seconds` supera un umbral configurado en backend, valor
de referencia inicial 12 horas). El frontend muestra un banner de advertencia si `stale` es
`true`, pero el cronómetro sigue funcionando y "Terminar" sigue permitido sin restricciones.

**Rationale**: la spec exige advertir, no bloquear (Edge Cases: "el sistema permite terminarlo
igual, pero advierte"). Calcular el flag en el mismo endpoint de lectura evita lógica adicional
en el frontend y mantiene el umbral centralizado y fácil de ajustar.

**Alternativas consideradas**: notificación push/email al superar el umbral — fuera de alcance,
la spec no pide notificaciones (FR: "no dispara notificaciones").

## Resumen de Technical Context (sin incógnitas)

- **Language/Version**: Python 3.12 (backend) · TypeScript strict / React 19 (frontend) — mismo
  stack que specs `004`/`010`.
- **Primary Dependencies**: Flask 3.x + Flask-RESTX, SQLAlchemy 2.x + Alembic, Ant Design 5,
  Zustand 5, Axios — **sin dependencias nuevas** (Principio V); no se usa Celery/Redis ni
  WebSockets.
- **Storage**: PostgreSQL 16 (Docker `sywork_db`), migración Alembic nueva (siguiente a `025`).
- **Testing**: pytest contra Postgres real en Docker, tests dirigidos al cronómetro; `npx tsc -b`
  para typecheck frontend.
- **Target Platform**: Docker Compose on-premise (sin cambios de infraestructura).
- **Project Type**: Web application (backend Flask 3 capas + frontend React SPA).
- **Performance Goals**: cada acción del cronómetro (iniciar/pausar/reanudar/terminar) responde
  en <300ms; el refresco visual en el navegador es local (1s) sin llamadas de red adicionales.
- **Constraints**: cero dependencias nuevas; el cálculo del tiempo transcurrido debe ser
  determinista a partir de timestamps del servidor (no depender de que el navegador quede
  abierto).
- **Scale/Scope**: una fila en `ticket_timers` por recurso activo (decenas, no miles); sin
  impacto de escala relevante.
