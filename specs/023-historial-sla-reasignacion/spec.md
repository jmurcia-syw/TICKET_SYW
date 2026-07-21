# Feature Specification: Historial de Estados con SLA Visual y Reasignación de Resolutores

**Feature Branch**: `023-historial-sla-reasignacion`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "Ajuste Visual en Historial de Estados (SLA) y Reasignación de Resolutores — agregar tiempo transcurrido e indicador de cumplimiento SLA (✅/⚠️/❌) a cada cambio de estado del Historial de Estados del ticket, y permitir reasignar un Ticket/Tarea a otro resolutor desde el detalle del ticket, dejando la reasignación (resolutor anterior ➡️ nuevo resolutor) registrada y visible en el historial de actividad."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver tiempo y cumplimiento de SLA por cambio de estado (Priority: P1)

Como Resolutor, Jefe de equipo o rol RRHH que revisa un ticket, quiero ver en el Historial de Estados cuánto tiempo permaneció el ticket en cada estado anterior y si ese tramo cumplió o no el SLA configurado, para identificar de un vistazo en qué etapa se produjo un retraso sin tener que calcularlo manualmente.

**Why this priority**: Es el ajuste de menor esfuerzo y mayor valor inmediato: reutiliza datos ya registrados (transiciones de estado y SLA por Proyecto/Prioridad de la feature 014/019) y resuelve una necesidad de trazabilidad que hoy requiere cálculo manual.

**Independent Test**: Puede probarse abriendo el Historial de Estados de un ticket con al menos dos transiciones registradas y verificando que cada fila muestra la duración del estado anterior y un ícono de cumplimiento (✅ dentro de plazo, ⚠️/❌ fuera de plazo), sin necesidad de que exista la funcionalidad de reasignación.

**Acceptance Scenarios**:

1. **Given** un ticket con una transición de estado registrada hace más tiempo del límite de SLA configurado para ese estado/prioridad, **When** el usuario abre el Historial de Estados, **Then** la fila de esa transición muestra el tiempo transcurrido exacto en el estado anterior y un ícono de incumplimiento (⚠️ o ❌).
2. **Given** un ticket con una transición realizada dentro del límite de SLA, **When** el usuario abre el Historial de Estados, **Then** la fila muestra el tiempo transcurrido y un ícono de cumplimiento (✅).
3. **Given** un ticket cuyo Proyecto/Prioridad no tiene un SLA configurado para el estado en cuestión, **When** el usuario abre el Historial de Estados, **Then** la fila muestra el tiempo transcurrido sin ícono de incumplimiento ni de cumplimiento (estado neutro, no se penaliza por falta de configuración).

### User Story 2 - Reasignar el ticket a otro resolutor (Priority: P2)

Como Jefe de equipo o rol con permiso de asignación, quiero reasignar un Ticket o Tarea a otro resolutor desde el propio detalle del ticket, para corregir un error de asignación inicial o escalar el caso a alguien con mayor experiencia, y que esa reasignación quede registrada automáticamente mostrando el resolutor anterior y el nuevo.

**Why this priority**: Depende de que exista ya una asignación previa, pero es independiente de la mejora visual del SLA; entrega valor por sí sola al resolver un problema operativo real (correcciones y escalamientos).

**Independent Test**: Puede probarse abriendo un ticket ya asignado a un Resolutor, ejecutando la acción "Reasignar" hacia otro Resolutor activo, y verificando que el ticket queda asignado al nuevo resolutor y que en el historial/actividad del ticket aparece una entrada "Resolutor A ➡️ Resolutor B" con autor y fecha, sin depender de los indicadores visuales de SLA.

**Acceptance Scenarios**:

1. **Given** un ticket asignado al Resolutor A, **When** un usuario con permiso de asignación reasigna el ticket al Resolutor B (activo y sin restricciones), **Then** el ticket queda asignado al Resolutor B y se crea automáticamente una entrada de historial visible "Resolutor A ➡️ Resolutor B" con el autor de la acción y la fecha/hora.
2. **Given** un ticket sin permiso de asignación para el usuario actual, **When** el usuario intenta reasignar el ticket, **Then** el sistema rechaza la acción y no se genera ninguna entrada de historial.
3. **Given** un ticket que ya está asignado al Resolutor A, **When** un usuario intenta "reasignar" seleccionando nuevamente al Resolutor A, **Then** el sistema no genera una entrada de reasignación duplicada ni un cambio real de estado.

### Edge Cases

- ¿Qué pasa si se reasigna un ticket que está en un estado final (Cerrado/Cancelado)? El sistema debe impedir la reasignación y explicar por qué (el ticket ya no admite cambios de asignación).
- ¿Qué pasa si el nuevo resolutor seleccionado no cumple con las Skills requeridas del ticket? El sistema debe permitir la reasignación pero advertir visualmente (mismo criterio que la alerta de disponibilidad no bloqueante ya usada al asignar, spec 020), sin bloquear la acción.
- ¿Qué pasa si un ticket nunca tuvo un SLA configurado en ninguna de sus transiciones? El Historial de Estados debe mostrar el tiempo transcurrido de cada tramo sin ícono de cumplimiento en ninguna fila.
- ¿Qué pasa con la primera transición de un ticket recién creado (sin estado anterior)? No debe mostrarse tiempo transcurrido ni ícono de SLA para esa fila inicial.
- ¿Qué pasa si el ticket es una Tarea o Subtarea en lugar de un Ticket raíz? Debe aplicar el mismo comportamiento de Historial de Estados e igual acción de reasignación, ya que ambos comparten el mismo ciclo de vida.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE calcular y mostrar, para cada transición del Historial de Estados de un Ticket/Tarea, el tiempo transcurrido exacto que el ticket permaneció en el estado anterior (diferencia entre la transición actual y la inmediatamente previa).
- **FR-002**: El sistema DEBE mostrar un ícono de cumplimiento de SLA por cada transición: cumplido (✅) cuando el tiempo transcurrido está dentro del límite configurado para ese Proyecto/Prioridad/estado, o incumplido (⚠️/❌) cuando lo excede.
- **FR-003**: Cuando no exista un SLA configurado para la combinación Proyecto/Prioridad/estado de una transición, el sistema DEBE mostrar el tiempo transcurrido sin ícono de cumplimiento ni de incumplimiento.
- **FR-004**: La primera transición de un ticket (creación, sin estado anterior) NO DEBE mostrar tiempo transcurrido ni ícono de SLA.
- **FR-005**: El sistema DEBE permitir a un usuario con permiso de asignación de tickets reasignar un Ticket, Tarea o Subtarea a otro recurso (resolutor) desde el detalle del ticket.
- **FR-006**: El sistema DEBE rechazar la reasignación cuando el usuario que la solicita no tiene permiso de asignación, sin registrar ninguna entrada de historial.
- **FR-007**: El sistema DEBE rechazar la reasignación cuando el ticket se encuentra en un estado final (Cerrado/Cancelado), informando el motivo.
- **FR-008**: El sistema DEBE registrar automáticamente cada reasignación efectiva (resolutor anterior, nuevo resolutor, autor de la acción, fecha/hora), sin pasos manuales adicionales del usuario.
- **FR-009**: El historial/actividad del ticket DEBE mostrar cada reasignación de forma distinguible, indicando "resolutor anterior ➡️ nuevo resolutor".
- **FR-010**: El sistema NO DEBE registrar una reasignación cuando el resolutor seleccionado es el mismo que ya tenía asignado el ticket.
- **FR-011**: Cuando el nuevo resolutor no cumple con las Skills requeridas del ticket, el sistema DEBE permitir igualmente la reasignación mostrando una advertencia visual no bloqueante.

### Key Entities

- **Transición de estado**: Registro existente (estado origen, estado destino, autor, fecha/hora) de un Ticket/Tarea; se le agregan los campos derivados "tiempo transcurrido en el estado anterior" y "cumplimiento de SLA" para su visualización.
- **Reasignación**: Nuevo registro de actividad del ticket que documenta el cambio de resolutor: resolutor anterior, nuevo resolutor, autor de la acción y fecha/hora. Se muestra en el historial/actividad junto a las transiciones de estado y demás eventos del ticket.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede identificar, sin cálculos manuales, en cuál cambio de estado se incumplió el SLA en menos de 5 segundos de revisar el Historial de Estados.
- **SC-002**: El 100% de las transiciones de estado con un SLA configurado muestran el ícono de cumplimiento correcto (✅ o ⚠️/❌) acorde al tiempo real transcurrido.
- **SC-003**: Toda reasignación completada exitosamente queda visible en el historial de actividad del ticket en el mismo momento, sin recargas ni acciones adicionales del usuario.
- **SC-004**: El 100% de los intentos de reasignación sin permiso o sobre tickets en estado final son rechazados sin generar registros de historial inconsistentes.

## Assumptions

- El cálculo de "tiempo transcurrido" y "cumplimiento de SLA" se basa en los mismos datos de transiciones de estado y configuración de SLA por Proyecto/Prioridad ya existentes (specs 014 y 019); esta feature no modifica cómo se calcula ni configura el SLA, solo agrega su visualización en el historial.
- "Reasignar" es una acción explícita distinta del flujo de asignación inicial; no cambia el estado del ticket por sí misma, solo el resolutor (assignee) asignado.
- El permiso requerido para reasignar es el mismo permiso de asignación de tickets que ya existe en el sistema (no se crea un permiso nuevo).
- La advertencia por Skills faltantes al reasignar reutiliza el mismo criterio no bloqueante ya definido para la asignación inicial (spec 020), sin bloquear la reasignación.
- Los íconos visuales (✅/⚠️/❌) son una ayuda de UI; no se persiste un valor booleano de "cumplido/incumplido" en base de datos si puede derivarse en el momento de la respuesta a partir de la duración y el SLA aplicable — la especificación no impone una decisión de almacenamiento.
