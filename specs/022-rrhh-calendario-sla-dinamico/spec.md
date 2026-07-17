# Feature Specification: RRHH — Franjas Horarias, Calendario Superpuesto y Motor de SLA Dinámico

**Feature Branch**: `022-rrhh-calendario-sla-dinamico`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Fase 5: Módulo de RRHH (Franjas Horarias Integradas), Calendarios
Superpuestos y Motor de SLA Dinámico — ampliar la Fase 5 (specs 020/021, ya completa) con: (1)
un menú desplegable "RRHH" (Calendario/Permisos) con Franjas Horarias globales por país que el
equipo hereda automáticamente, con modo "Personalizado" cuando un usuario edita su propio
horario desde su Perfil; (2) un calendario de equipo estilo Google Calendar con vistas
Mes/Semana/Día, superposición de múltiples miembros (+ "Seleccionar todo") y permisos/ausencias
parciales por horas que impactan el ticket del usuario; (3) un motor de SLA que solo consume
tiempo cuando el técnico está dentro de su horario laboral y disponible, pausando fuera de
horario y reanudando en la siguiente ventana, con visualización de carga de trabajo; (4) una
vista diaria que prioriza estrictamente por Prioridad/Severidad, resaltando los niveles críticos
superiores (P1/P2/S1/S2)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - RRHH administra Franjas Horarias globales y modo Personalizado (Priority: P1)

Una persona del equipo de RRHH necesita definir, para cada país donde SyWork tiene consultores,
una "Franja Horaria" estándar (huso horario y horas laborales) y aplicarla a todo el equipo de
ese país de una sola vez, sin tener que editar el horario de cada recurso uno por uno. Cuando un
consultor necesita un horario distinto al estándar de su país (por ejemplo, un turno especial),
lo ajusta desde su propio Perfil; a partir de ese momento su horario queda marcado como
"Personalizado" y deja de recibir las actualizaciones masivas que RRHH aplique después a la
Franja de su país. RRHH necesita poder ver, en una sola pantalla, quién está en modo
Personalizado para saber a quién no le llegará un cambio masivo.

**Why this priority**: Es la base de datos de la que dependen el calendario superpuesto y el
motor de SLA dinámico (ambos necesitan saber la disponibilidad real de cada persona). Sin esta
historia no hay una fuente confiable de horarios por la que empezar.

**Independent Test**: Puede probarse por completo creando una Franja Horaria para un país,
verificando que todo el equipo de ese país la refleja, editando el horario de una persona desde
su Perfil y confirmando que pasa a "Personalizado" y ya no cambia cuando RRHH actualiza la
Franja de su país de nuevo.

**Acceptance Scenarios**:

1. **Given** un país sin Franja Horaria creada, **When** RRHH crea una Franja Horaria para ese
   país (huso horario y horas laborales estándar), **Then** todos los recursos de ese país que
   no estén en modo Personalizado adoptan esa Franja como su horario vigente.
2. **Given** una Franja Horaria ya asignada a un equipo, **When** RRHH edita las horas laborales
   de esa Franja, **Then** el cambio se refleja automáticamente en la disponibilidad de todos los
   recursos heredados, sin que RRHH tenga que editarlos individualmente.
3. **Given** un recurso heredando la Franja de su país, **When** ese usuario edita su propio
   horario desde su Perfil, **Then** el recurso queda marcado "Personalizado" y su horario ya no
   cambia ante futuras ediciones de la Franja global de su país.
4. **Given** varios recursos en modo Personalizado, **When** RRHH abre la pantalla de gestión de
   Franjas Horarias, **Then** ve un listado de todos los recursos en modo Personalizado,
   diferenciado de los que heredan una Franja global.
5. **Given** el rol RRHH, **When** inicia sesión, **Then** ve un menú desplegable "RRHH" con las
   opciones "Calendario" y "Permisos", con el mismo comportamiento visual que el menú "Maestros".

---

### User Story 2 - Motor de SLA Dinámico basado en disponibilidad real (Priority: P1)

Un Coordinador necesita que el tiempo de SLA de Diagnóstico/Análisis/Ejecución de un ticket
refleje el tiempo real que el técnico asignado estuvo disponible para trabajarlo, no el tiempo de
reloj corrido. Si un ticket entra fuera del horario laboral del técnico, o mientras está de
vacaciones o en un festivo, el contador no debe avanzar hasta que el técnico vuelva a estar
disponible; y debe pausarse automáticamente en el instante exacto en que termina su jornada,
reanudándose en la siguiente ventana disponible.

**Why this priority**: Es el valor de negocio central de esta ampliación — sin él, el SLA sigue
siendo un simple reloj de pared que no refleja la disponibilidad real del equipo, que es
justamente el problema que esta fase busca resolver.

**Independent Test**: Puede probarse de forma aislada asignando un ticket con SLA a un técnico
con una Franja Horaria conocida y verificando que el tiempo consumido coincide exactamente con
las horas de disponibilidad real, sin necesidad de que existan aún el calendario superpuesto o
la vista diaria.

**Acceptance Scenarios**:

1. **Given** un técnico con jornada de 8:00 a 18:00 y 1 hora de disponibilidad restante ese día,
   **When** un ticket con SLA le entra a las 17:00, **Then** el contador consume esa 1 hora,
   entra en pausa automáticamente a las 18:00, y se reanuda a las 8:00 del siguiente día laboral
   sin intervención manual.
2. **Given** un ticket con SLA que entra fuera del horario laboral del técnico asignado,
   **When** se registra la hora de entrada, **Then** el contador no descuenta tiempo hasta que
   comience la siguiente ventana de disponibilidad del técnico.
3. **Given** un técnico con una ausencia aprobada (total o parcial) o un festivo en su calendario,
   **When** el reloj de SLA de un ticket suyo debería estar corriendo, **Then** el tiempo
   correspondiente a esa ausencia/festivo no se descuenta del SLA.
4. **Given** un ticket que ya estaba abierto y acumulando tiempo de SLA antes de que este motor
   entre en operación, **When** el motor se activa, **Then** el tiempo ya consumido hasta ese
   momento permanece igual (no se recalcula retroactivamente) y solo el tiempo adicional a partir
   de la activación se calcula con la nueva lógica de disponibilidad.
5. **Given** un recurso con tickets con SLA asignados, **When** se consulta su carga de trabajo,
   **Then** el sistema muestra cuánto tiempo disponible real le queda frente al tiempo
   comprometido por esos tickets.

---

### User Story 3 - Calendario de Equipo Superpuesto (Priority: P2)

Un Coordinador o RRHH necesita ver, en una sola pantalla tipo Google Calendar, la disponibilidad
combinada de varios miembros del equipo a la vez (o de todo el equipo con un solo clic), con
vistas de Mes, Semana y Día, incluyendo cumpleaños, festivos y días especiales o religiosos.
Además, cuando alguien solicita un permiso corto (una cita médica de 2 horas, o media jornada),
la solicitud debe registrarse por horas —no solo por día completo— y ese tiempo debe verse
reflejado tanto en el calendario como en la disponibilidad del ticket que tenga asignado ese
usuario durante esas horas.

**Why this priority**: Construye visualmente sobre los datos de disponibilidad ya definidos en
US1 (Franjas Horarias) y consumidos en US2 (SLA dinámico); no aporta valor por sí sola sin esa
base, pero es necesaria para que un Coordinador tome decisiones de asignación con una vista
completa del equipo.

**Independent Test**: Puede probarse seleccionando varios miembros del equipo (o "Seleccionar
todo"), alternando entre vistas Mes/Semana/Día, y registrando una ausencia parcial por horas para
verificar que aparece correctamente superpuesta junto con festivos y cumpleaños, y que el ticket
del usuario refleja esa indisponibilidad parcial.

**Acceptance Scenarios**:

1. **Given** el calendario de equipo abierto, **When** el usuario selecciona varios miembros del
   equipo o la opción "Seleccionar todo", **Then** ve las agendas de todos los seleccionados
   superpuestas en una misma vista, incluyendo festivos, cumpleaños y días especiales/religiosos
   en común.
2. **Given** el calendario abierto, **When** el usuario alterna entre las vistas Mes, Semana y
   Día, **Then** la información se reorganiza consistentemente sin perder la selección de
   miembros activa.
3. **Given** un usuario que solicita un permiso de 2 horas para una cita médica, **When** la
   solicitud se aprueba (mismo flujo de doble aprobación ya existente para ausencias), **Then**
   ese bloque de horas aparece en el calendario del equipo y reduce la disponibilidad real del
   ticket asignado a esa persona durante esas horas.
4. **Given** una solicitud de media jornada (4 horas), **When** se registra, **Then** se procesa
   con el mismo flujo y visibilidad que cualquier otra ausencia, sin pasos adicionales para quien
   la solicita.
5. **Given** un recurso con tickets con SLA asignados, **When** se visualiza su día en el
   calendario, **Then** se muestra gráficamente cuánta carga de trabajo tiene comprometida frente
   a su tiempo disponible real restante.

---

### User Story 4 - Vista Diaria priorizada por criticidad (Priority: P3)

Un técnico o Coordinador que abre la vista de Día del calendario necesita ver primero, sin tener
que buscarlos, los tickets de mayor criticidad del día: los de prioridad y severidad más altas
deben aparecer resaltados y en las primeras posiciones de la lista, para que la atención se
dirija de inmediato a lo más urgente.

**Why this priority**: Es una mejora de presentación sobre datos que ya existen una vez resueltas
US2 y US3; no introduce lógica de negocio nueva, solo ordenamiento y énfasis visual.

**Independent Test**: Puede probarse abriendo la vista de Día de un técnico con varios tickets de
distinta prioridad/severidad asignados y verificando que el orden y el resaltado visual
corresponden estrictamente al nivel de criticidad de cada uno.

**Acceptance Scenarios**:

1. **Given** un técnico con varios tickets asignados el mismo día, **When** se abre la vista de
   Día, **Then** los tickets aparecen ordenados estrictamente por prioridad y luego por
   severidad, de mayor a menor criticidad.
2. **Given** tickets de criticidad alta (prioridad crítica/alta o severidad s1/s2) en la agenda
   del día, **When** se renderiza la lista, **Then** esos tickets se resaltan visualmente frente
   al resto.

---

### Edge Cases

- ¿Qué pasa si RRHH edita una Franja Horaria mientras un ticket de un recurso heredado tiene el
  reloj de SLA corriendo en ese momento? El nuevo horario debe aplicar a partir del momento del
  cambio, sin alterar el tiempo ya consumido antes de la edición.
- ¿Qué pasa si un festivo y una ausencia aprobada coinciden el mismo día para el mismo recurso?
  El día cuenta como no disponible una sola vez (no se descuenta doble ni se generan
  inconsistencias en el cálculo de disponibilidad).
- ¿Qué pasa si un recurso no tiene ninguna hora disponible en todo el día (ausencia de jornada
  completa o festivo)? El SLA de sus tickets asignados permanece en pausa todo ese día.
- ¿Qué pasa con los días sin horario laboral configurado (ej. fines de semana no incluidos en la
  Franja)? Se tratan como no disponibles para efectos de SLA y de la vista diaria.
- ¿Qué pasa cuando los miembros seleccionados para la superposición del calendario están en husos
  horarios distintos? Cada evento se muestra en la referencia horaria que corresponda para que la
  superposición siga siendo comparable.
- ¿Qué pasa si una solicitud de ausencia parcial por horas se solapa con otra solicitud ya
  aprobada del mismo usuario el mismo día? El sistema no debe permitir dos ausencias aprobadas que
  se solapen en el mismo rango de horas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST mostrar, únicamente al rol RRHH, un menú desplegable "RRHH" con
  las opciones "Calendario" y "Permisos", con el mismo comportamiento visual/estructural que el
  menú desplegable "Maestros" ya existente para otros roles administrativos.
- **FR-002**: El rol RRHH MUST poder crear, editar y desactivar Franjas Horarias globales,
  cada una asociada a un país, con huso horario y horas laborales estándar (por día de la
  semana).
- **FR-003**: Cuando una Franja Horaria global se actualiza, el sistema MUST propagar el cambio
  automáticamente a la disponibilidad de todos los recursos que la tengan asignada (modo
  "Heredado"), sin requerir edición individual por recurso.
- **FR-004**: Cuando un usuario modifica su propio horario laboral desde su Perfil, el sistema
  MUST marcar automáticamente ese recurso como "Personalizado" y MUST excluirlo de futuras
  actualizaciones masivas de la Franja Horaria de su país.
- **FR-005**: El sistema MUST permitir a RRHH visualizar, en una sola pantalla, el listado de
  todos los recursos en modo "Personalizado", diferenciándolos de los que heredan una Franja
  Horaria global.
- **FR-006**: El sistema MUST calcular el consumo de tiempo de SLA (fase de
  Diagnóstico/Análisis/Ejecución) considerando únicamente los intervalos en los que el técnico
  asignado está dentro de su horario laboral vigente y disponible (sin festivo ni ausencia
  aprobada activa).
- **FR-007**: El sistema MUST pausar automáticamente el contador de SLA en el instante exacto en
  que el técnico asignado sale de su ventana de disponibilidad, y MUST reanudarlo automáticamente
  al inicio de la siguiente ventana disponible, sin intervención manual.
- **FR-008**: El sistema MUST tratar el tiempo transcurrido fuera del horario laboral del técnico
  asignado (incluyendo tickets recibidos fuera de horario) como no consumido para efectos de SLA.
- **FR-009**: Para tickets que ya estaban abiertos y acumulando tiempo de SLA antes de la entrada
  en operación de este motor dinámico, el sistema MUST conservar el tiempo ya consumido sin
  recalcularlo retroactivamente, aplicando la nueva lógica de disponibilidad solo al tiempo
  transcurrido a partir de la entrada en operación.
- **FR-010**: El sistema MUST mostrar, para cada recurso, una visualización de su carga de
  trabajo comprometida (suma de tiempo de SLA pendiente de los tickets que tiene asignados)
  frente a su tiempo disponible real restante.
- **FR-011**: El sistema MUST ofrecer un calendario de equipo con vistas conmutables de Mes,
  Semana y Día.
- **FR-012**: El sistema MUST permitir seleccionar múltiples miembros del equipo (incluyendo una
  opción "Seleccionar todo") para superponer sus agendas —incluyendo cumpleaños, festivos y días
  especiales o religiosos— en una misma vista.
- **FR-013**: El sistema MUST permitir registrar solicitudes de ausencia o permiso parciales,
  especificando un rango de horas dentro de un día (no solo el día completo), usando el mismo
  flujo de doble aprobación (Jefe directo + RRHH) ya existente para ausencias de día completo.
- **FR-014**: El tiempo de una ausencia o permiso parcial aprobado MUST reflejarse en el
  calendario del equipo y MUST reducir la disponibilidad real considerada para el cálculo de SLA
  de los tickets asignados a esa persona durante ese rango de horas.
- **FR-015**: La vista de Día del calendario MUST listar los tickets asignados al recurso
  ordenados estrictamente por Prioridad y luego por Severidad, de mayor a menor criticidad.
- **FR-016**: La vista de Día MUST resaltar visualmente los tickets de criticidad alta (prioridad
  crítica o alta, severidad s1 o s2) frente al resto de los tickets listados.
- **FR-017**: El sistema MUST impedir que dos solicitudes de ausencia/permiso aprobadas para el
  mismo usuario se solapen en el mismo rango de horas del mismo día.

### Key Entities

- **Franja Horaria (plantilla global)**: representa un horario laboral estándar por país —
  país, huso horario, horas laborales por día de la semana. Puede estar asignada a múltiples
  recursos ("Heredado").
- **Horario del Recurso**: representa el horario laboral vigente de un recurso individual, en
  uno de dos modos — "Heredado" (sigue automáticamente a la Franja Horaria de su país) o
  "Personalizado" (horario propio, definido por el usuario desde su Perfil, inmune a cambios
  masivos de la Franja).
- **Solicitud de Ausencia/Permiso**: representa una petición de tiempo no disponible de un
  usuario, ya sea de día completo o de un rango de horas dentro de un día, sujeta a doble
  aprobación (Jefe directo + RRHH).
- **Carga de Trabajo (vista calculada)**: relación entre el tiempo de SLA comprometido por los
  tickets asignados a un recurso y su tiempo disponible real restante; no es un dato que se
  almacene, se calcula a partir de los tickets con SLA y la disponibilidad vigente del recurso.
- **Ticket (consumido, sin cambios propios)**: se usa como fuente de lectura de prioridad,
  severidad y recurso asignado para el cálculo de SLA dinámico, la carga de trabajo y el orden de
  la vista diaria; esta feature no introduce cambios al ciclo de vida ni a los controladores del
  Ticket más allá de leer estos datos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: RRHH puede actualizar el horario laboral de todo un equipo de un país editando una
  única Franja Horaria, sin editar recursos de forma individual.
- **SC-002**: RRHH puede identificar el 100% de los recursos en modo "Personalizado" desde una
  sola pantalla, sin revisar recurso por recurso.
- **SC-003**: El tiempo de SLA consumido por un ticket coincide exactamente con las horas reales
  de disponibilidad del técnico asignado, verificable con el escenario estricto descrito (jornada
  8-18h, ticket entrante a las 17h con 1h de disponibilidad restante: consume esa 1h, pausa a las
  18h, reanuda a las 8h del día siguiente).
- **SC-004**: Un Coordinador puede ver la disponibilidad combinada de un equipo completo (o de
  cualquier subconjunto elegido) en una sola vista de calendario, sin tener que abrir calendarios
  individuales uno por uno.
- **SC-005**: El 100% de los tickets de criticidad alta (prioridad crítica/alta, severidad
  s1/s2) aparecen en las primeras posiciones de la vista diaria de agenda de su técnico asignado.
- **SC-006**: Una solicitud de ausencia parcial por horas se registra, aprueba y refleja en el
  calendario y en la disponibilidad del ticket sin pasos adicionales frente a una ausencia de día
  completo.

## Assumptions

- **Retroactividad del SLA dinámico**: al entrar en operación este motor, el tiempo de SLA ya
  consumido en tickets previamente abiertos permanece congelado tal cual; solo el tiempo
  transcurrido a partir de la activación se calcula con la nueva lógica de disponibilidad. No se
  reescribe el historial de tickets ya en curso (decisión confirmada explícitamente).
- **Migración de horarios individuales existentes**: los recursos que ya tenían un horario
  laboral configurado antes de existir las Franjas Horarias globales (spec 020) quedan marcados
  automáticamente como "Personalizado" al desplegarse esta feature, conservando su horario actual
  sin cambios y quedando excluidos de futuras actualizaciones masivas (decisión confirmada
  explícitamente).
- **Mapeo de criticidad**: el enunciado original se refiere a niveles "P1/P2/S1/S2"; en el
  sistema, la prioridad del ticket usa los valores crítica/alta/media/baja y la severidad usa
  s1-s4. Se asume que "P1/P2" corresponde a prioridad crítica y alta, y "S1/S2" corresponde
  directamente a severidad s1 y s2.
- **Alcance de la ausencia por horas**: la doble aprobación (Jefe directo + RRHH) ya existente
  para ausencias de día completo aplica igual para ausencias parciales por horas, sin un flujo de
  aprobación distinto ni simplificado.
- **Alcance por tipo de registro**: al igual que el motor de SLA original (spec 014), el cálculo
  de disponibilidad y el SLA dinámico aplican solo a Tickets, no a Tareas ni Subtareas.
- **Límite de alcance de cambios**: esta feature se acota a la gestión de horarios/perfiles de
  usuario, la lógica de cálculo de SLA, y las vistas de calendario/RRHH; no introduce cambios a
  otros controladores o flujos del Ticket fuera de la lectura de prioridad/severidad/asignación
  necesaria para estos cálculos.
- **Alcance de validación**: la validación funcional de esta feature se limita a pruebas
  dirigidas sobre el cálculo de horas de SLA, usando un conjunto reducido de datos de prueba (5 a
  10 registros); no se ejecuta la suite global de integración como parte de esta fase (directriz
  explícita del usuario).
- **"Día" en la vista diaria (FR-015/FR-016)**: el Ticket no tiene un campo de fecha propio (no
  existe "fecha programada" ni "vencimiento" en la entidad). La vista de Día muestra la agenda
  vigente del recurso — el conjunto de tickets abiertos actualmente asignados a él — ordenada por
  criticidad; "Día" identifica de quién se está viendo la agenda (o el momento en que se consulta),
  no un filtro por una fecha propia del ticket.
