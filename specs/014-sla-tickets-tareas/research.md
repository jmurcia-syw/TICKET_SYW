# Research: SLAs por Proyecto y Prioridad

Todos los aspectos del Technical Context tenían resolución directa a partir de la Constitución,
el FSM ya implementado y el SDD V3 — no quedan `NEEDS CLARIFICATION` sin resolver. Este documento
registra las decisiones de diseño que sí requerían elegir entre alternativas.

## Decisión 1: Dónde vive el cálculo de consumo de SLA

**Decision**: Snapshot incremental en columnas nuevas de `tickets` (`sla_consumed_seconds`,
`sla_last_resume_at`, `sla_status`, `sla_phase_limit_minutes`), actualizado como efecto secundario
de cada endpoint de transición de estado existente. *(Nombre de campo actualizado en la revisión
2026-07-14 — ver `data-model.md`: el modelo de una sola fase/`sla_limit_minutes` fue reemplazado
por el modelo de 2 fases de la Decisión 5, que usa `sla_phase_limit_minutes` +
`sla_contact_result`/`sla_contact_consumed_seconds` para el snapshot congelado de la fase
Contacto. El mecanismo de snapshot incremental descrito aquí no cambia, solo los nombres de
columna.)*

**Rationale**: Corrección (verificado al iniciar `/speckit-implement`): sí existe
`ticket_status_transitions` (`backend/infra/models/ticket_model.py::StatusTransitionModel`,
poblada vía `TicketRepository.add_transition` en cada cambio de estado), pero solo registra
`from_status/to_status/actor/timestamp` de forma append-only para el historial visible en la UI —
no tiene columnas de "consumo acumulado" ni de pausa por fase, y recorrerla en cada lectura de
ticket para reconstruir el consumo de SLA sería O(n) por lectura y una responsabilidad ajena a su
propósito actual. El snapshot incremental en columnas de `tickets` sigue siendo la opción más
simple: O(1) de lectura, no requiere tocar `StatusTransitionModel`, y es suficiente para todos los
requisitos (FR-005 a FR-007).

**Alternatives considered**:
- *Derivar el consumo de SLA recorriendo `ticket_status_transitions` en cada lectura*: reutiliza
  una tabla ya existente (no hay que inventar un log de eventos nuevo), pero es O(n) por lectura y
  mezclaría una responsabilidad de auditoría de estados con el cómputo de SLA. Se descarta por
  ahora; queda como candidato si una fase futura necesita recalcular SLA retroactivamente para
  tickets ya cerrados.
- *Cálculo en caliente recorriendo comentarios tipificados*: frágil (los comentarios no son un
  log de transiciones 1:1 garantizado) y O(n) por lectura. Descartado.

## Decisión 2: Motor de detección de vencimientos

**Decision**: Tarea periódica Celery (`backend/workers/sla_tasks.py`) cada 5 minutos que consulta
tickets activos con `sla_status != 'vencido'` y `sla_phase_limit_minutes` no nulo, evalúa si el
consumo proyectado ya superó el límite, actualiza `sla_status='vencido'` y dispara notificación.
*(Nombre de campo actualizado 2026-07-14, ver nota de la Decisión 1.)*

**Rationale**: Celery + Redis ya están aprobados en la Constitución explícitamente para "SLA
timers" — es la única pieza del stack que hasta ahora no tenía código real. Evita que el
vencimiento dependa de que un usuario abra el ticket (requisito FR-010 / SC-004: notificación en
minutos, no cuando alguien mire la pantalla).

**Alternatives considered**:
- *Cálculo perezoso al leer el ticket* (sin tarea periódica): más simple, pero no puede disparar
  notificaciones proactivas si nadie abre el ticket — incumple FR-010. Descartado como único
  mecanismo, aunque el cálculo perezoso se mantiene para refrescar el estado mostrado en cada
  lectura (la tarea periódica es solo para el disparo de notificaciones, no la única fuente de
  verdad del estado visual).

## Decisión 3: Resolución de la regla de SLA aplicable (revisada 2026-07-14)

**Decision**: Búsqueda directa por `(project_id, priority)` exacto, sin jerarquía de fallback. Si
no hay fila activa para esa combinación, el ticket queda en `sin_sla`.

**Rationale**: `docs/SLAv1.xlsx` (fuente real de tiempos objetivo) y la petición explícita del
usuario acotan el SLA a nivel de Proyecto — no existe en la fuente ni fue solicitado un nivel
"solo Cliente" o "solo Prioridad" como respaldo. Mantener un único punto de resolución sin
jerarquía es más simple, más predecible para el Admin, y evita inventar semántica de fallback no
pedida (Principio VII).

**Alternatives considered** (descartadas tras la revisión de alcance):
- *Jerarquía (Prioridad, Cliente, Proyecto) > (Prioridad, Cliente) > (Prioridad)*: era el diseño
  original antes de revisar `SLAv1.xlsx`; se descarta porque el documento no define un nivel de
  Cliente y el usuario pidió explícitamente que el SLA sea por Proyecto.
- Promediar o combinar reglas coincidentes: descartado por ambigüedad de negocio no solicitada.

## Decisión 4: Alcance de "Tareas"/"Subtareas" frente al SLA (revisada 2026-07-14)

**Decision**: El SLA aplica únicamente a registros con `record_type_id` = "Ticket". Las columnas
`sla_*` se agregan a la tabla `tickets` (compartida con Tareas/Subtareas, spec 008/009) pero el
motor de dominio (`sla_service.py`) solo las popula cuando `record_type` = "Ticket" — para
Tareas/Subtareas quedan `NULL` (`sin_sla` implícito, sin necesidad de un flag adicional).

**Rationale**: Clarificación explícita del usuario (2026-07-14, C2): en esta fase, Tareas y
Subtareas no tienen SLA (aunque podrían tenerlo en una fase futura) y su FSM permanece "libre"
(sin cambios de esta feature). Extender el cómputo a Tareas/Subtareas ahora sería alcance no
solicitado (Principio VII).

**Alternatives considered**: Aplicar el SLA a toda la tabla `tickets` sin distinguir
`record_type` (diseño original antes de esta clarificación) — descartado porque el usuario acotó
explícitamente el alcance a Tickets.

## Decisión 5: Número de fases de SLA (revisada 2026-07-14, reemplaza el diseño original de 3
tiempos)

**Decision**: 2 fases secuenciales, no 3: "Contacto" (`nuevo`, `pre_analisis`) y "Diagnóstico,
Análisis y Ejecución" (`contacto`, `en_analisis`, `en_ejecucion`, `en_pruebas`). Cada fase tiene su
propio tiempo límite y su propio contador — al cerrar la fase Contacto se congela su resultado y
la fase de Ejecución arranca en cero (no es acumulativa entre fases).

**Rationale**: `docs/SLAv1.xlsx` (única fuente de tiempos objetivo verificada) define exactamente
2 métricas — "Tiempo de contacto" (15 min, fijo) y "Tiempo de respuesta Diagnóstico y Análisis"
(por Prioridad) — sin un tercer tiempo de "resolución" separado. El diseño original (FR-001 con 3
tiempos: atención/análisis/resolución) no tenía respaldo en ninguna fuente verificada y fue el
hallazgo crítico (U1) del `/speckit-analyze` inicial. `en_ejecucion`/`en_pruebas` se agrupan con
`contacto`/`en_analisis` en la segunda fase en vez de crear una tercera fase inventada.

**Alternatives considered**: Mantener 3 fases y asumir que "Ejecución" y "Pruebas" tienen un
tiempo propio no documentado — descartado por falta de fuente; se prefiere modelar solo lo que el
Excel realmente define y extender después si aparece una métrica adicional.

## Decisión 6: Independencia SLA↔FSM y audiencia de notificaciones (clarificación 2026-07-14)

**Decision**: (a) El SLA es una capa de solo-lectura sobre el FSM: nunca bloquea ni condiciona una
transición (`ticket_fsm.apply` no recibe ni consulta datos de SLA). Un error en `sla_service.py`
se captura y no debe propagarse como fallo del endpoint de transición (FR-014). (b) Las
notificaciones de vencimiento (FR-010) se dirigen al Resolutor/encargado asignado al ticket y a
los `ProjectMember` del proyecto del ticket cuyo rol de usuario sea Coordinador — no a todos los
Coordinadores del sistema.

**Rationale**: Clarificaciones explícitas del usuario (U1, C1). (a) evita que un bug o borde no
cubierto del motor de SLA deje tickets "atascados" sin poder cambiar de estado — el SLA es
información de gestión, no una regla de negocio bloqueante. (b) reutiliza el modelo de membresía
`ProjectMember`/"Personal" ya existente (spec 010) en vez de notificar a todos los Coordinadores
del sistema, evitando ruido para proyectos en los que no participan.

**Alternatives considered**: Notificar a todos los Coordinadores (diseño original, más simple pero
generaría ruido en clientes con múltiples Coordinadores/proyectos) — descartado tras la
clarificación del usuario.
