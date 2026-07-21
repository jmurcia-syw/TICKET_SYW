# Research: Historial de Estados con SLA Visual y Reasignación de Resolutores

## Decisión 1 — El SLA se mide por fase (Contacto/Ejecución), no por estado FSM

**Decisión**: El ícono de cumplimiento (✅/⚠️/❌) se calcula solo sobre las transiciones que
**cierran una fase de SLA** — la transición hacia `contacto` (cierra fase Contacto, spec 014) y
la transición hacia `resuelto`/`cerrado`/`cancelado` (cierra fase Ejecución). El resto de las
transiciones (p. ej. `contacto → en_análisis`, `en_análisis → en_ejecución`) muestran el tiempo
transcurrido sin ícono de cumplimiento (estado neutro, ya cubierto por spec FR-003/Edge Cases).

**Rationale**: `backend/domain/services/sla_service.py` y `ticket_fsm.py`
(`SLA_PHASE_FOR_STATE`) confirman que el motor de SLA tiene solo dos límites configurables por
regla (`contact_minutes`, `execution_minutes`, ver `sla_rule.py`) — no hay un límite por cada
estado individual del FSM. Pedir un ícono por *cada* fila del historial sin distinguir esto
produciría comparaciones sin sentido (comparar la duración de un sub-estado contra el límite de
toda la fase). El ticket ya persiste `sla_contact_result` (`"cumplido"`/`"vencido"`) al cerrar la
fase Contacto (`sla_service.apply_transition`) — se reutiliza tal cual para esa transición en vez
de recalcularlo. El cierre de la fase Ejecución se deriva igual que hace `apply_transition`
(comparando el consumo acumulado contra `execution_minutes`).

**Alternatives considered**:
- Mostrar un ícono en cada transición comparando contra el límite de la fase vigente en ese
  momento → descartado: para transiciones internas de una misma fase (ej. `en_análisis →
  en_ejecución`) no hay un "límite parcial" definido; induciría a error a quien lea el historial.
- Agregar un límite de SLA por cada estado del FSM (rediseño del modelo de SLA) → descartado por
  exceder el alcance (spec exige "no refactorizar la entidad Ticket ni el motor de SLA").

## Decisión 2 — Cálculo del tiempo disponible reutiliza `compute_available_seconds`

**Decisión**: El "tiempo transcurrido" de cada transición usa la misma función de dominio
`compute_available_seconds` (spec 022, ya implementada) sobre el intervalo
`[transición anterior.created_at, transición actual.created_at]`, con el recurso/calendario
**actual** del ticket (mismo criterio que usa `sla.compute_state` hoy para el tramo vigente).

**Rationale**: Reutilizar la función ya validada evita duplicar lógica de disponibilidad
(festivos, horario, ausencias parciales) y mantiene consistencia visual con el contador de SLA
que ya se muestra en el detalle del ticket (`SlaCounter`). Es una ayuda de UI (spec Assumptions),
no una auditoría legal-financiera, así que usar el calendario/regla *actual* del recurso para
leer tramos históricos es una simplificación aceptable y documentada.

**Alternatives considered**:
- Reloj de pared puro (diferencia simple de timestamps) → descartado: sería inconsistente con el
  contador de SLA vigente del mismo ticket, que ya usa el motor dinámico (spec 022) cuando hay
  recurso asignado.
- Reconstruir el calendario/regla histórica exacta vigente en cada momento pasado → descartado
  por sobre-ingeniería fuera de alcance (la regla de SLA de un ticket rara vez cambia, y cuando
  cambia ya se recalcula vía `recalc_rule_for_project_or_priority_change`).

## Decisión 3 — Reasignación es un endpoint nuevo, no una extensión de `/assign`

**Decisión**: Se crea `POST /api/tickets/{id}/reassign` como endpoint independiente. `/assign`
(`backend/api/routes/tickets.py:933`) **no se modifica**.

**Rationale**: `/assign` dispara un trigger FSM (`assign_resolver`/`assign_qm` vía
`AssignmentService.validate`) y solo es válido desde estados donde esa transición existe (p. ej.
`nuevo → contacto`). Un ticket ya asignado y en `en_análisis`/`en_ejecución` no tiene un trigger
FSM válido para "reasignar sin cambiar de estado" — forzarlo por `/assign` rompería el contrato
FSM o requeriría tocarlo, lo cual la Constitución prohíbe explícitamente sin aprobación de
arquitectura ("los endpoints de acción crítica `/assign`/`/status` no pueden ser refactorizados
para acoplarlos a la UI sin aprobación explícita"). El nuevo endpoint solo cambia `assignee_id` y
registra el evento, sin invocar el FSM.

**Alternatives considered**:
- Extender `/assign` con un modo `"reassign"` que omita el trigger FSM → descartado: mezcla dos
  contratos distintos (Triage Push original vs. corrección/escalamiento) en el mismo endpoint,
  contradice el principio de endpoints de acción "independientes y agnósticos al caller".

## Decisión 4 — Persistencia de la reasignación: tabla nueva `ticket_reassignments`

**Decisión**: Tabla append-only análoga a `ticket_assignments` (`AssignmentModel`), con columnas
`ticket_id`, `actor_id`, `previous_assignee_id` (nullable, por si no había resolutor previo),
`new_assignee_id`, `reason` (texto libre opcional), `created_at`.

**Rationale**: `ticket_assignments` documenta el contexto de la *asignación inicial* (Gold
Standard Dataset con skills/carga del momento, FR-018/019 de spec 010) — mezclar ahí la
reasignación ensuciaría ese dataset de entrenamiento. Una tabla dedicada, del mismo estilo
append-only, mantiene la trazabilidad pedida ("resolutor anterior ➡️ nuevo resolutor") sin tocar
el esquema ni la semántica de `ticket_assignments`.

**Alternatives considered**:
- Reutilizar `ticket_assignments` con `resulting_status = ticket.status` sin cambio →
  descartado: contaminaría el dataset de asignación inicial usado para el futuro AI Dispatcher
  (Principio VI).

## Decisión 5 — Permiso reutilizado, sin nuevo permiso

**Decisión**: `POST /reassign` reusa `require_permission("tickets", "assign")`, el mismo permiso
ya usado por `/assign`.

**Rationale**: La spec (Assumptions) indica que el permiso requerido es el mismo de asignación
existente; no se justifica un permiso granular nuevo para un caso de uso tan cercano al ya
existente, y evita tocar el modelo de roles/permisos fuera de alcance.
