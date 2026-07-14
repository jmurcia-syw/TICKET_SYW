# Feature Specification: SLAs por Proyecto y Prioridad

**Feature Branch**: `014-sla-tickets-tareas`

**Created**: 2026-07-10

**Updated**: 2026-07-14 (alcance revisado: SLA por Proyecto, 2 fases según `docs/SLAv1.xlsx`)

**Status**: Draft

**Input**: User description: "Fase 4 del roadmap SDD V3: SLAs por prioridad/cliente/proyecto con estados que pausan el contador. Ver docs/SDD V3.docx (roadmap y alcances) y docs/Regla de actividad de estados.xlsx (flujo de estados) como fuentes de verdad. Contexto del sistema: Tickets y Tareas comparten la misma tabla/ciclo de vida (10 estados: NUEVO → PRE-ANÁLISIS/CONTACTO → EN ANÁLISIS → EN EJECUCIÓN ⇄ EN PRUEBAS → PENDIENTE DE USUARIO → RESUELTO → CERRADO, + CANCELADO), definido en backend/domain/fsm/ticket_fsm.py. La Fase 4 debe definir: SLA (tiempo límite) configurable por combinación de prioridad/cliente/proyecto, un contador que corre mientras el ticket está en estados 'activos' y se pausa en estados como PENDIENTE DE USUARIO (ya hay placeholders 'SLA pausado (Fase 4)' y '—:—:—' en el detalle del ticket), y probablemente alertas/indicadores visuales cuando el SLA está por vencer o vencido (el dashboard ya tiene un stat 'Vencen hoy')."

**Revisión 2026-07-14**: Tras revisar `docs/SLAv1.xlsx` (única fuente de tiempos objetivo real, tipo
de servicio "Correctivo"), el alcance se ajusta: (1) el SLA se configura **por Proyecto** (no por
combinación Prioridad × Cliente × Proyecto con fallback), y sigue siendo editable por el Admin; (2)
el documento define exactamente **2 fases medibles**, no 3 — "Tiempo de contacto" (15 min, fijo,
no varía por prioridad) y "Tiempo de respuesta Diagnóstico, Análisis y Ejecución" (varía por
Prioridad: Crítica 1h / Alta 8h / Media 2 días hábiles / Baja 5 días hábiles). La "Severidad" del
Excel corresponde al campo `priority` ya existente en el ticket (`critical/high/medium/low` →
Crítica/Alta/Media/Baja), no al campo `severity` (`s1-s4`).

## Clarifications

### Session 2026-07-14

- Q: ¿Quién recibe la notificación de vencimiento de SLA (FR-010)? → A: El Resolutor/encargado
  asignado al ticket, y únicamente los Coordinadores que sean Personal asignado a ese Proyecto
  (`ProjectMember` con rol Coordinador) — no todos los Coordinadores del sistema.
- Q: ¿Las Tareas y Subtareas quedan sujetas a las reglas de SLA en esta fase? → A: No. En esta
  fase el SLA aplica solo a registros con `record_type_id` = "Ticket". Tareas y Subtareas quedan
  fuera de alcance del cómputo de SLA (aunque siguen usando el mismo FSM/tabla sin cambios); se
  deja como extensión posible de una fase futura.
- Q: ¿El SLA puede bloquear o condicionar una transición de estado del FSM? → A: No, nunca. El SLA
  es exclusivamente de medición y alerta — el FSM y sus transiciones (`ticket_fsm.py`) no cambian
  ni se ven restringidos por el estado del SLA. Ambos sistemas interactúan (el cambio de estado
  dispara el recálculo de SLA) pero son independientes: un fallo o inconsistencia en el cálculo de
  SLA nunca debe impedir una transición válida.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configurar tiempos límite de SLA por Proyecto (Priority: P1)

Como Admin o Coordinador, quiero definir, para cada Proyecto y cada nivel de Prioridad, el tiempo
límite de contacto y el tiempo límite de diagnóstico/análisis/ejecución, para que el sistema sepa
cuánto tiempo tiene el equipo de soporte antes de que un ticket se considere vencido, con valores
propios de cada proyecto (editables, no un valor global fijo).

**Why this priority**: Sin una tabla de tiempos configurada no existe ningún SLA que medir — es
el cimiento del que dependen todas las demás historias.

**Independent Test**: Puede probarse completamente creando/editando una regla de SLA para una
combinación de Proyecto + Prioridad desde la pantalla de configuración y verificando que persiste
y aparece en el listado, sin necesidad de que exista todavía ningún contador corriendo.

**Acceptance Scenarios**:

1. **Given** que no existe una regla de SLA para la combinación (Proyecto=ERP, Prioridad=Alta),
   **When** el Admin crea una regla con tiempo de contacto=15min y tiempo de diagnóstico/análisis/
   ejecución=8h, **Then** la regla queda guardada y visible en el listado de configuración.
2. **Given** una regla de SLA existente, **When** el Admin la edita para cambiar el tiempo de
   diagnóstico/análisis/ejecución, **Then** los tickets que ya estén en curso usan el nuevo tiempo
   únicamente para los cómputos futuros, sin alterar el historial ya registrado.
3. **Given** un ticket cuyo Proyecto no tiene ninguna regla configurada para su Prioridad, **When**
   el sistema resuelve el SLA aplicable, **Then** señala explícitamente la ausencia de SLA
   configurado ("sin SLA") en vez de fallar silenciosamente o de aplicar un valor de otro proyecto.

---

### User Story 2 - Ver el contador de SLA en el ticket (Priority: P1)

Como Resolutor o Coordinador, quiero ver en el detalle del ticket cuánto tiempo queda (o cuánto
tiempo lleva vencido) del SLA vigente, con indicación clara de si el contador está corriendo o
pausado, para priorizar mi trabajo sin tener que calcularlo manualmente.

**Why this priority**: Es el valor visible mínimo que un SLA configurado debe producir; sin esto
la configuración de la Historia 1 no tiene ningún efecto perceptible para el usuario final.

**Independent Test**: Puede probarse abriendo el detalle de un ticket con SLA configurado y
verificando que el contador (reemplazando el placeholder actual "—:—:—") muestra tiempo
transcurrido/restante coherente con el estado del ticket y con la regla configurada.

**Acceptance Scenarios**:

1. **Given** un ticket en estado NUEVO recién creado con SLA configurado, **When** el Resolutor
   abre el detalle, **Then** ve el contador de SLA en fase "Contacto" corriendo y el tiempo límite
   de contacto correspondiente al Proyecto/Prioridad del ticket.
1b. **Given** un ticket que pasa al estado CONTACTO, **When** se consulta el contador, **Then** la
   fase "Contacto" queda congelada (cumplida o vencida, según lo consumido) y el contador entra en
   la fase "Diagnóstico, Análisis y Ejecución" con su propio tiempo límite según la Prioridad.
2. **Given** un ticket que pasa a estado PENDIENTE DE USUARIO, **When** se consulta el contador,
   **Then** el contador se congela (deja de avanzar) y la UI indica explícitamente "SLA pausado",
   reemplazando el placeholder existente.
3. **Given** un ticket que regresa de PENDIENTE DE USUARIO a EN EJECUCIÓN, **When** se consulta
   el contador, **Then** el contador reanuda desde el tiempo acumulado antes de la pausa (no se
   reinicia ni se pierde el tiempo ya consumido).
4. **Given** un ticket cuyo tiempo consumido supera el tiempo límite configurado, **When** se
   consulta el contador, **Then** la UI muestra el tiempo vencido en un estado visual distinto
   (p. ej. color/etiqueta de alerta) en vez de simplemente mostrar un número negativo o crecer sin
   indicación.

---

### User Story 3 - Alertas e indicadores de SLA en listados y dashboard (Priority: P2)

Como Coordinador, quiero ver de un vistazo qué tickets están próximos a vencer o ya vencidos en
el listado de Tickets y en el dashboard, para poder reasignar prioridades antes de incumplir con
el cliente.

**Why this priority**: Extiende el valor de las Historias 1 y 2 desde la vista de un ticket
individual hacia una vista agregada, que es donde el Coordinador realmente toma decisiones de
priorización — pero depende de que el contador (Historia 2) ya exista.

**Independent Test**: Puede probarse configurando SLA para varios tickets con distintos niveles
de consumo (a tiempo, próximo a vencer, vencido) y verificando que el listado de Tickets los
distingue visualmente y que el stat "Vencen hoy" del dashboard refleja el conteo correcto.

**Acceptance Scenarios**:

1. **Given** varios tickets con distintos niveles de consumo de SLA, **When** el Coordinador abre
   el listado de Tickets, **Then** cada fila muestra un indicador visual de estado de SLA
   (a tiempo / próximo a vencer / vencido) sin necesidad de abrir el detalle.
2. **Given** tickets cuyo SLA vence dentro de las próximas 24 horas, **When** el Coordinador abre
   el dashboard, **Then** el stat "Vencen hoy" cuenta exactamente esos tickets (reemplazando el
   valor fijo en 0 actual).
3. **Given** un ticket que acaba de vencer su SLA, **When** ocurre el vencimiento, **Then** el
   Resolutor/encargado asignado y los Coordinadores que sean Personal de ese Proyecto reciben una
   notificación dentro de la aplicación (reutilizando el sistema de notificaciones existente)
   indicando el ticket y la fase de SLA vencida.

---

### Edge Cases

- ¿Qué pasa si un ticket cambia de Proyecto (y por tanto de regla de SLA aplicable) mientras el
  contador ya lleva tiempo corriendo? El sistema debe recalcular el tiempo límite de la fase
  vigente a partir de la nueva regla (mismo Proyecto nuevo + Prioridad actual) sin descartar el
  tiempo ya consumido en la fase actual.
- ¿Qué pasa si se cancela un ticket antes de vencer su SLA? El contador debe detenerse
  definitivamente y no debe contarse en las métricas de "vencidos" ni generar alertas nuevas.
- ¿Qué pasa si no existe ninguna regla de SLA para el Proyecto del ticket en su Prioridad actual?
  El ticket debe mostrar explícitamente "Sin SLA configurado" en vez de un contador engañoso, y no
  debe contarse en ningún stat de vencimiento. No existe fallback automático entre proyectos ni
  entre prioridades — cada combinación Proyecto+Prioridad se configura de forma independiente.
- ¿Qué pasa si cambia la Prioridad del ticket mientras el contador corre? El sistema recalcula el
  tiempo límite de la fase vigente usando la regla del mismo Proyecto con la nueva Prioridad
  (mismo tratamiento que un cambio de Proyecto), conservando el tiempo ya consumido en la fase.
- ¿Qué pasa con el SLA de una Tarea o Subtarea? Quedan fuera de alcance de esta fase (FR-012): no
  se les calcula ni se les muestra ningún contador de SLA, aunque comparten tabla/FSM con los
  Tickets. Es una extensión posible de una fase futura.
- ¿Qué pasa si el Admin borra o desactiva una regla de SLA mientras hay tickets en curso usándola?
  Los tickets en curso conservan el tiempo límite ya asignado en el momento de entrar a la fase
  actual; solo los tickets nuevos o las próximas transiciones de fase usan la regla vigente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir configurar, para cada combinación de Proyecto × Prioridad,
  dos tiempos límite independientes: tiempo de contacto y tiempo de diagnóstico/análisis/ejecución,
  expresados en horas y minutos.
- **FR-002**: El sistema DEBE tratar cada combinación Proyecto+Prioridad como una regla
  independiente y editable — sin fallback automático hacia otro proyecto ni hacia una regla
  "solo por prioridad" cuando falta la regla específica del proyecto.
- **FR-003**: El sistema DEBE indicar explícitamente cuando un ticket no tiene ninguna regla de
  SLA configurada para su Proyecto+Prioridad, en vez de mostrar un contador basado en un valor
  supuesto.
- **FR-004**: Cada estado del ciclo de vida (NUEVO, PRE-ANÁLISIS, CONTACTO, EN ANÁLISIS, EN
  EJECUCIÓN, EN PRUEBAS, PENDIENTE DE USUARIO, RESUELTO, CERRADO, CANCELADO) DEBE tener definido
  explícitamente si el tiempo transcurrido en ese estado cuenta o no para el consumo del SLA, y a
  cuál de las 2 fases (Contacto / Diagnóstico-Análisis-Ejecución) pertenece.
- **FR-004b**: El sistema DEBE agrupar los estados en exactamente 2 fases de SLA secuenciales:
  "Contacto" (NUEVO, PRE-ANÁLISIS) y "Diagnóstico, Análisis y Ejecución" (CONTACTO, EN ANÁLISIS,
  EN EJECUCIÓN, EN PRUEBAS). Al salir de la fase "Contacto" (el ticket entra al estado CONTACTO),
  el resultado de esa fase (cumplido/vencido) queda congelado y el contador de la segunda fase
  arranca en cero con su propio tiempo límite (no hereda el consumo de la fase anterior).
- **FR-005**: El sistema DEBE pausar el contador de la fase de SLA vigente mientras el ticket
  permanece en un estado marcado como "no cuenta para SLA" (p. ej. PENDIENTE DE USUARIO) y
  reanudarlo, sin perder el tiempo ya consumido en esa fase, al volver a un estado que sí cuenta.
- **FR-006**: El sistema DEBE detener definitivamente el contador de SLA cuando el ticket llega a
  RESUELTO, CERRADO o CANCELADO (estos tres detienen el cómputo; solo CERRADO y CANCELADO son
  estados finales del FSM — RESUELTO puede reabrirse vía "Rechazar resolución", momento en el que
  el contador de la fase de ejecución se reanuda).
- **FR-007**: El detalle del ticket DEBE mostrar, para la fase de SLA vigente, el tiempo consumido,
  el tiempo límite aplicable y el estado del contador (corriendo, pausado, vencido, sin SLA
  configurado), y el resultado congelado de la fase de Contacto una vez superada, reemplazando el
  placeholder estático actual.
- **FR-008**: El sistema DEBE marcar visualmente, en el listado de Tickets, cada registro según su
  estado de SLA (a tiempo, próximo a vencer, vencido) sin requerir abrir el detalle.
- **FR-009**: El dashboard DEBE calcular el stat "Vencen hoy" a partir de los tickets cuyo SLA
  vence dentro de las próximas 24 horas, en vez del valor fijo actual.
- **FR-010**: El sistema DEBE generar una notificación interna (reutilizando el mecanismo de
  notificaciones ya existente) dirigida al Resolutor/encargado asignado al ticket y a los
  Coordinadores que sean Personal asignado a ese Proyecto (no a todos los Coordinadores del
  sistema) cuando un ticket incumple el tiempo límite de la fase de SLA vigente.
- **FR-011**: Un ticket que cambia de Proyecto o de Prioridad DEBE recalcular la regla de SLA
  aplicable a la fase vigente a partir de ese momento, conservando el tiempo ya consumido en esa
  fase antes del cambio.
- **FR-012**: El SLA aplica únicamente a registros con `record_type_id` = "Ticket". Las Tareas y
  Subtareas (mismo ciclo de vida/tabla, `record_type_id` = "Tarea"/subtarea) quedan fuera de
  alcance del cómputo de SLA en esta fase — no tienen `sla_rule_id` ni contador — y podrán
  incorporarse en una fase futura.
- **FR-013**: Solo roles con permiso administrativo (Admin/Coordinador, según el esquema de
  permisos existente) DEBEN poder crear, editar o desactivar reglas de SLA.
- **FR-014**: El cómputo o estado del SLA NUNCA DEBE bloquear, condicionar ni invalidar una
  transición de estado del FSM (`ticket_fsm.py`). El SLA es puramente informativo/de medición; un
  ticket puede avanzar de estado con SLA vencido con total normalidad, y un error en el cálculo de
  SLA no debe impedir que la transición de estado se complete.

### Key Entities *(include if feature involves data)*

- **Regla de SLA**: Combinación de Proyecto + Prioridad que define los 2 tiempos límite (contacto,
  diagnóstico/análisis/ejecución). No hay reglas de respaldo — cada Proyecto+Prioridad es
  independiente y editable por el Admin/Coordinador.
- **Estado de SLA por ticket**: Snapshot del consumo de SLA de un ticket para su fase vigente —
  fase actual (Contacto / Diagnóstico-Análisis-Ejecución), tiempo acumulado en esa fase, tiempo
  límite aplicable, timestamp de la última pausa/reanudación, si está corriendo/pausado/vencido, y
  el resultado ya congelado de la fase de Contacto si fue superada.
- **Flag de pausa y fase por estado**: Propiedad de cada estado del ciclo de vida que indica si el
  tiempo transcurrido en ese estado suma o no al consumo de SLA, y a cuál de las 2 fases
  pertenece.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El Coordinador puede identificar, sin abrir ningún ticket individual, cuáles están
  vencidos o próximos a vencer directamente desde el listado o el dashboard.
- **SC-002**: El 100% de los tickets con una regla de SLA aplicable muestran un contador de tiempo
  consumido coherente con las transiciones de estado registradas en su historial.
- **SC-003**: El tiempo que un ticket pasa en un estado marcado como "pausa SLA" nunca se computa
  como tiempo consumido del límite.
- **SC-004**: Los usuarios reciben una notificación dentro de la aplicación en un lapso razonable
  (minutos, no horas) después de que un ticket incumple su SLA.
- **SC-005**: El Admin puede configurar una nueva regla de SLA completa (los 2 tiempos límite) en
  menos de 2 minutos.

## Assumptions

- Los calendarios laborales por país, feriados y tipos de contrato de soporte (5x8 / 7x24)
  mencionados en el SDD V3 como moduladores del SLA quedan fuera de alcance de esta fase: el
  contador de Fase 4 corre en tiempo continuo (24x7), y la incorporación de calendarios de negocio
  se aborda en la Fase 5 del roadmap ("Asignación por disponibilidad + calendarios por
  país/recurso"), que depende de esta base. Los tiempos de `docs/SLAv1.xlsx` expresados en "días
  hábiles" (Prioridad Media = 2 días hábiles, Baja = 5 días hábiles) se cargan en esta fase como
  días calendario × 24h (aproximación documentada), a ajustar cuando exista calendario de negocio.
- Los tiempos límite se configuran y muestran en horas y minutos, sin fracciones más finas.
- La actualización manual del "tiempo estimado de resolución" por parte del Resolutor durante los
  estados EN ANÁLISIS/EN EJECUCIÓN (mencionada en el SDD V3) es una funcionalidad relacionada pero
  distinta del tiempo límite de SLA configurado por regla; esta fase no la modifica.
- El motor de FSM sigue siendo actualizado manualmente por Coordinador/Resolutor (la
  automatización completa del motor FSM es Fase 6 del roadmap); esta fase solo agrega el cómputo
  y la visualización del SLA sobre las transiciones ya existentes.
- El SLA se define por Proyecto, no por Cliente ni de forma global — un mismo Cliente con varios
  Proyectos puede tener tiempos distintos por proyecto, y no existe una regla "por defecto" que
  aplique cuando falta la específica del proyecto (FR-002/FR-003).
- Los estados EN ANÁLISIS, EN EJECUCIÓN y EN PRUEBAS se agrupan en una sola fase ("Diagnóstico,
  Análisis y Ejecución") junto con CONTACTO, medida con un único tiempo límite por Prioridad según
  `docs/SLAv1.xlsx` — el documento no define un tiempo separado para EN PRUEBAS ni para EN
  EJECUCIÓN, así que no se inventa un tercer tiempo límite no soportado por la fuente.
- El SLA es una capa de medición añadida sobre el FSM existente, no una modificación de este: las
  transiciones, sus reglas y sus triggers (`ticket_fsm.py`) permanecen exactamente iguales; el SLA
  solo lee el estado resultante para calcular fase/consumo (FR-014). Los dos sistemas interactúan
  en una sola dirección (FSM → SLA) y nunca al revés.
