# Feature Specification: Cronómetro Manual de Tiempo en el Ticket

**Feature Branch**: `012-cronometro-manual-ticket`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Incluir en el ticket un contador manual de tiempo trabajado, de
carácter provisional: el usuario lo inicia, lo pausa y lo termina de forma manual, y el
contador acumula el tiempo que se trabajó en ese ticket durante ese ciclo."

## Clarifications

### Session 2026-07-09

- Q: Al terminar el cronómetro, ¿el tiempo acumulado debe crear/alimentar automáticamente un
  Registro de tiempo formal (el mismo de Reporte de Tiempos), o es un contador informal e
  independiente? → A: Crea Registro de tiempo formal — el total acumulado se guarda como un
  Registro de tiempo (igual que la carga manual existente) y aparece en Reporte de Tiempos.
- Q: Si el usuario recarga la página, cierra el navegador o cierra sesión mientras el
  cronómetro está corriendo, ¿qué pasa con el tiempo acumulado al volver? → A: Se conserva — el
  estado (corriendo/pausado, tiempo acumulado) se guarda en el servidor y persiste entre
  sesiones/recargas.
- Q: ¿Quién puede ver que el cronómetro está corriendo en un ticket? → A: Solo quien lo inició
  — es personal por recurso; otros usuarios con acceso al ticket no lo ven ni lo controlan.
- Q: ¿Terminar el cronómetro en un ticket ya Cerrado/Cancelado debe permitirse igual, o
  bloquearse como la carga manual de tiempo hoy? → A: Bloquear, igual que hoy — no se registra
  tiempo (ni por cronómetro ni manual) en un ticket cerrado salvo Admin; el cronómetro sigue
  disponible para pausarlo/reanudarlo, pero "Terminar" falla con el mismo error que ya existe
  para la carga manual hasta que un Admin lo registre en su nombre o el ticket se reabra.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Iniciar, pausar y terminar el cronómetro mientras se trabaja el ticket (Priority: P1)

Un recurso que puede registrar tiempo en un ticket (típicamente el Resolutor asignado) abre el
detalle del ticket en el que va a trabajar y presiona "Iniciar" para poner en marcha un
cronómetro que cuenta el tiempo transcurrido en tiempo real. Si se distrae con otra tarea,
presiona "Pausar" sin perder lo acumulado, y "Reanudar" cuando retoma. Al terminar de trabajar
en ese ciclo, presiona "Terminar": el tiempo total acumulado se guarda automáticamente como un
Registro de tiempo del ticket, sin que el recurso tenga que volver a tipear las horas a mano.

**Why this priority**: es la funcionalidad central solicitada — sin poder iniciar, pausar y
terminar el cronómetro no existe la feature.

**Independent Test**: iniciar el cronómetro en un ticket, pausarlo, reanudarlo y terminarlo;
verificar que se crea un Registro de tiempo con la duración acumulada correcta, visible en el
Reporte de Tiempos existente.

**Acceptance Scenarios**:

1. **Given** un ticket donde el recurso puede registrar tiempo, **When** presiona "Iniciar",
   **Then** el cronómetro comienza a contar desde cero y queda visible en el detalle del ticket.
2. **Given** un cronómetro corriendo, **When** el recurso presiona "Pausar", **Then** el conteo
   se detiene conservando el tiempo acumulado hasta ese momento, y el control pasa a mostrar
   "Reanudar".
3. **Given** un cronómetro pausado, **When** el recurso presiona "Reanudar", **Then** el conteo
   continúa sumando desde el tiempo previamente acumulado.
4. **Given** un cronómetro corriendo o pausado con tiempo acumulado, **When** el recurso
   presiona "Terminar", **Then** se crea un Registro de tiempo del ticket con la duración total
   acumulada, el cronómetro vuelve a cero y queda listo para un nuevo ciclo.

---

### User Story 2 - El cronómetro conserva su estado entre recargas y sesiones (Priority: P1)

Mientras el cronómetro está corriendo o pausado, si el recurso recarga la página, navega a otra
pantalla y vuelve, cierra el navegador o cierra sesión y entra más tarde, el cronómetro conserva
su estado (corriendo o pausado) y el tiempo acumulado hasta ese momento, sin que el recurso
pierda el trabajo ya registrado.

**Why this priority**: sin esto, el cronómetro sería frágil frente a un flujo de trabajo real
donde el usuario cambia de pantalla o pierde la sesión con frecuencia; aunque la herramienta es
provisional, debe ser confiable mientras existe.

**Independent Test**: iniciar el cronómetro, recargar la página del ticket y confirmar que
sigue corriendo con el tiempo correcto (sin reiniciar a cero).

**Acceptance Scenarios**:

1. **Given** un cronómetro corriendo, **When** el recurso recarga la página del detalle del
   ticket, **Then** el cronómetro sigue corriendo y muestra el tiempo transcurrido correcto.
2. **Given** un cronómetro pausado con 12 minutos acumulados, **When** el recurso cierra sesión
   y vuelve a entrar una hora después, **Then** el cronómetro sigue pausado mostrando los 12
   minutos acumulados (no avanzó mientras estaba pausado).
3. **Given** un cronómetro corriendo, **When** el recurso cierra el navegador sin pausarlo ni
   terminarlo y vuelve al día siguiente, **Then** el cronómetro sigue corriendo reflejando el
   tiempo transcurrido real (sujeto a la advertencia de umbral de la sección Edge Cases).

---

### User Story 3 - El cronómetro es personal por recurso (Priority: P2)

El cronómetro es una herramienta personal: solo el recurso que lo inició lo ve corriendo y puede
pausarlo, reanudarlo o terminarlo. Otros usuarios que abren el mismo ticket (Coordinador, otro
Resolutor) no ven el cronómetro de otra persona ni pueden controlarlo; si varios recursos
trabajan el mismo ticket, cada uno maneja el suyo de forma independiente.

**Why this priority**: aclara el alcance de colaboración de la funcionalidad; no bloquea el
valor central (Historias 1 y 2) pero evita malentendidos operativos si no se define.

**Independent Test**: con dos recursos distintos con acceso al mismo ticket, uno inicia su
cronómetro; el otro recurso abre el mismo ticket y no ve ningún cronómetro corriendo.

**Acceptance Scenarios**:

1. **Given** un recurso A con su cronómetro corriendo en un ticket, **When** un recurso B (u
   otro rol con acceso) abre el mismo ticket, **Then** no ve el cronómetro de A corriendo ni el
   tiempo que lleva acumulado.
2. **Given** dos recursos distintos, cada uno con acceso a su propio ticket, **When** ambos
   inician su propio cronómetro, **Then** cada uno cuenta y se controla de forma independiente,
   sin que uno vea ni afecte el del otro, y cada uno genera su propio Registro de tiempo al
   terminar.

---

### Edge Cases

- ¿Qué pasa si el cronómetro queda corriendo varios días sin pausarse ni terminarse (olvido)?
  El sistema permite terminarlo igual, pero advierte al recurso cuando vuelve a la pantalla si
  superó un umbral razonable, para evitar Registros de tiempo desproporcionados por olvido.
- ¿Qué pasa si el ticket pasa a un estado final (Cerrado/Cancelado) mientras el cronómetro sigue
  corriendo? El recurso puede pausarlo o dejarlo corriendo, pero "Terminar" se bloquea con el
  mismo error que ya existe para la carga manual de tiempo en tickets cerrados (spec `004`); el
  tiempo acumulado no se pierde (el cronómetro no se resetea) hasta que un Admin lo registre en
  su nombre o el ticket se reabra.
- ¿Puede un mismo recurso tener más de un cronómetro corriendo a la vez, en tickets distintos?
  No — un recurso tiene como máximo un cronómetro activo (corriendo o pausado) a la vez, para
  evitar cómputos ambiguos de dedicación simultánea.
- ¿Qué pasa si se presiona "Terminar" sin haber acumulado tiempo (se inició y se pausó de
  inmediato, en menos de un minuto)? No se genera un Registro de tiempo con duración cero; el
  control de "Terminar" requiere al menos un minuto acumulado para tener efecto.
- ¿El cronómetro reemplaza la carga manual de horas ya existente (spec `004`)? No — convive con
  ella; el recurso puede seguir cargando tiempo manualmente para trabajo que no cronometró en
  vivo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a un recurso con permiso para registrar tiempo en un
  ticket iniciar un cronómetro manual sobre ese ticket, que cuenta el tiempo transcurrido en
  tiempo real desde cero.
- **FR-002**: El sistema DEBE permitir pausar un cronómetro en curso sin perder el tiempo
  acumulado, y reanudarlo después para seguir contando desde donde quedó.
- **FR-003**: El sistema DEBE permitir terminar el cronómetro en cualquier momento (corriendo o
  pausado, con tiempo acumulado mayor a cero), generando un Registro de tiempo del ticket con la
  duración total acumulada, equivalente a un registro cargado manualmente.
- **FR-004**: El sistema DEBE conservar el estado del cronómetro (corriendo/pausado, tiempo
  acumulado) entre recargas de página, navegación y cierres/reaperturas de sesión, sin que el
  recurso pierda el progreso.
- **FR-005**: El cronómetro DEBE ser visible y controlable únicamente por el recurso que lo
  inició; ningún otro usuario que acceda al mismo ticket DEBE poder verlo corriendo ni
  controlarlo.
- **FR-006**: El sistema DEBE permitir como máximo un cronómetro activo (corriendo o pausado)
  por recurso a la vez, sin importar el ticket; iniciar uno nuevo mientras hay otro activo en
  otro ticket DEBE impedirse o exigir primero terminar/descartar el anterior.
- **FR-007**: El sistema NO DEBE generar un Registro de tiempo con duración cero; "Terminar"
  exige al menos un minuto acumulado para tener efecto.
- **FR-008**: El sistema DEBE bloquear "Terminar" cuando el ticket está en estado Cerrado (salvo
  para quien tiene permiso administrativo sobre registros de tiempo de terceros), igual que hoy
  bloquea la carga manual de tiempo en tickets cerrados (spec `004`); el cronómetro conserva su
  tiempo acumulado sin resetearse mientras el bloqueo esté vigente, para no perder el progreso.
- **FR-009**: El Registro de tiempo generado por el cronómetro DEBE aparecer junto con los
  registros cargados manualmente en los mismos listados y reportes existentes (Reporte de
  Tiempos), sin una vista separada.
- **FR-010**: El sistema DEBE advertir al recurso cuando un cronómetro lleva corriendo de forma
  continua más allá de un umbral razonable (p. ej. una jornada laboral extendida), para evitar
  acumulaciones desproporcionadas por olvido.

### Key Entities

- **Cronómetro manual del ticket** (nueva, de carácter provisional): estado por recurso y
  ticket (inactivo | en curso | pausado), tiempo acumulado, momento de inicio o de la última
  reanudación; al terminar se convierte en un Registro de tiempo existente y vuelve a estado
  inactivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un recurso puede iniciar, pausar, reanudar o terminar el cronómetro de un ticket
  en menos de 5 segundos por acción, sin salir del detalle del ticket.
- **SC-002**: El 100% de los cronómetros terminados generan un Registro de tiempo cuya duración
  coincide (±1 minuto) con el tiempo real transcurrido, descontando las pausas.
- **SC-003**: El 100% de los cronómetros en curso o pausados sobreviven a una recarga de página
  o a un cierre y reapertura de sesión, sin pérdida del tiempo acumulado.
- **SC-004**: Cero Registros de tiempo con duración cero son generados por el cronómetro.

## Assumptions

- Es una herramienta provisional: complementa, no reemplaza, la carga manual de horas ya
  existente (specs `004`/`005`); ambas conviven sin conflicto.
- Un recurso solo puede tener un cronómetro activo (corriendo o pausado) a la vez, en cualquier
  ticket, para evitar dedicaciones simultáneas ambiguas.
- El cronómetro respeta el mismo permiso que hoy habilita registrar tiempo sobre el ticket (el
  mismo universo de recursos que ya puede cargar un Registro de tiempo manual); no se crea un
  permiso nuevo.
- El umbral exacto para la advertencia de cronómetro olvidado (FR-010) queda a definir en la
  fase de planificación; se asume un valor cercano a una jornada laboral extendida (p. ej.
  12 horas) como referencia inicial, ajustable sin impacto en el resto de la funcionalidad.
- Terminar o pausar el cronómetro no dispara notificaciones ni requiere comentario tipificado,
  igual que cargar un Registro de tiempo manual hoy.
- "Terminar" con el ticket en estado Cerrado se bloquea igual que la carga manual de tiempo
  (spec `004`), reutilizando la misma regla de negocio en vez de crear una excepción nueva; el
  cronómetro no se pierde por este bloqueo, queda disponible para terminarse apenas se resuelva
  (reapertura del ticket, o carga administrativa por un Admin).
