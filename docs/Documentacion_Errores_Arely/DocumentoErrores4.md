EA-021 — El SLA contabiliza tiempo fuera del horario
laboral al cambiar el estado del ticket

Módulo/Pantalla: Tickets → Detalle del Ticket → SLA

Tipo: Bug

Estado: Abierta

Reportado por: Arely Pazmiño

Iteración de origen: ITER-004

Iteración de cierre: —

Descripción

Se realizó una prueba con un recurso que tiene configurado un horario laboral de 08:00 a
17:00. Durante la prueba, se registró tiempo sobre un ticket aproximadamente a las 23:00,
fuera del horario laboral, mientras el SLA se encontraba pausado.

Posteriormente, al regresar al horario laboral, el SLA mostraba aproximadamente 1 hora y
20 minutos restantes, lo que indica que el sistema conservaba correctamente tiempo
disponible para el cumplimiento del SLA.

Sin embargo, al cambiar el estado del ticket a Solicitud de información, el SLA pasó a
mostrar un tiempo de 10 horas y posteriormente apareció como vencido.

Resultado esperado / Situación actual

Situación actual: El SLA muestra un tiempo consumido superior al tiempo laboral real
transcurrido. En la prueba, el ticket comenzó a contabilizarse dentro del horario laboral y
había transcurrido aproximadamente una hora; sin embargo, el sistema muestra
aproximadamente tres horas de tiempo consumido y marca el SLA como vencido.

Resultado actual / Propuesta de mejora

Revisar el cálculo del SLA para garantizar que únicamente se contabilice el tiempo
correspondiente al horario laboral configurado.

El sistema no debería sumar:

●  Tiempo fuera del horario laboral.
●  Tiempo durante el cual el SLA se encuentra pausado.
●  Tiempo correspondiente a períodos no laborales.

Criterios de aceptación

●  El tiempo del SLA se contabiliza únicamente dentro del horario laboral configurado.
●  El tiempo registrado fuera del horario laboral no afecta el contador del SLA.
●  Cuando el SLA está pausado, el contador no debe consumir tiempo.
●  El sistema debe calcular correctamente el tiempo transcurrido y el tiempo restante.
●  El ticket no debe aparecer como vencido antes de que realmente se consuma el

tiempo laboral configurado.

Evidencia:

EA-022 — El SLA contabiliza tiempo
incorrectamente cuando el ticket es
creado fuera del horario laboral

Módulo/Pantalla: Tickets → Detalle del Ticket → SLA

Tipo: Bug

Estado: Abierta

Reportado por: Arely Pazmiño

Iteración de origen: ITER-004

Iteración de cierre: —

Descripción

Se creó un ticket fuera del horario laboral configurado. El calendario tiene un horario de
trabajo de 08:00 a 17:00.

El ticket fue creado fuera de este horario y posteriormente asignado a un resolutor. El SLA
comenzó a contabilizarse cuando inició el horario laboral.

Durante la prueba, había transcurrido aproximadamente una hora dentro del horario
laboral. Sin embargo, el sistema mostraba que habían transcurrido aproximadamente tres
horas y el SLA aparecía como Vencido.

Resultado esperado / Situación actual

Situación actual: El sistema parece contabilizar tiempo adicional al tiempo laboral real
transcurrido desde el inicio del SLA.

Resultado actual / Propuesta de mejora

Revisar el cálculo del tiempo transcurrido cuando un ticket se crea fuera de la jornada
laboral.

Si el ticket se crea fuera del horario laboral, el sistema debería:

1.  Registrar la fecha y hora de creación.
2.  Esperar hasta el siguiente período laboral.
3.  Iniciar el SLA únicamente dentro del horario configurado.
4.  Contabilizar exclusivamente el tiempo laboral transcurrido.

Criterios de aceptación

●  Un ticket creado fuera del horario laboral no consume tiempo de SLA mientras el

calendario se encuentre fuera de jornada.

●  El contador comienza únicamente al iniciar el siguiente período laboral.
●  El sistema calcula correctamente el tiempo laboral transcurrido.
●  El tiempo mostrado en el SLA coincide con el tiempo real consumido dentro del

calendario laboral.

●  El SLA no se marca como vencido antes de alcanzar el tiempo límite configurado.

Evidencia:

EA-0023 — Se permite asignar un ticket
fuera del horario laboral

Módulo/Pantalla: Tickets → Panel de Asignación / Detalle del Ticket

Tipo: Observación

Estado: Abierta

Reportado por: Arely Pazmiño

Iteración de origen: ITER-004

Iteración de cierre: —

Descripción

Se verificó que es posible crear un ticket y asignarlo a un resolutor aunque la operación se
realice fuera del horario laboral configurado.

Resultado esperado / Situación actual

Situación actual: El sistema permite crear y asignar tickets fuera de la jornada laboral.

Resultado actual / Propuesta de mejora

Validar si este comportamiento corresponde a la regla de negocio esperada.

Se recomienda permitir la creación y asignación fuera del horario laboral, ya que un ticket
puede llegar en cualquier momento. Sin embargo, el sistema debería diferenciar claramente
entre:

●  Hora de creación del ticket.
●  Hora de asignación.
●
●

Inicio efectivo del SLA.
Inicio de la jornada laboral.

Criterios de aceptación

●  El sistema permite crear tickets fuera del horario laboral.
●  El sistema permite asignarlos si el usuario tiene permisos.
●  El SLA respeta el calendario configurado.
●  El tiempo fuera de la jornada no se contabiliza incorrectamente.
●  La hora real de creación y asignación se conserva en el historial.

