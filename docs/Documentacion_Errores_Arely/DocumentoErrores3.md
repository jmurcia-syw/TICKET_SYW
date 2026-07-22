EA-018 — El registro de tiempo continúa disponible
después de cerrar el ticket

Módulo/Pantalla: Tickets ? Detalle del Ticket ? Registro de tiempos

Tipo: Bug

Estado: Abierta

Reportado por: Arely Pazmiño

Iteración de origen: ITER-004

Iteración de cierre: —

Descripción

Al cambiar un ticket al estado Cerrado, el sistema continúa permitiendo iniciar o mantener
activo el registro de tiempo asociado al ticket.

Resultado esperado / Situación actual

Situación actual: El ticket se encuentra cerrado, pero el registro de tiempo continúa
disponible, lo que permite seguir contabilizando horas sobre un ticket que ya finalizó.

Resultado actual / Propuesta de mejora

Al cerrar un ticket, el sistema debería detener automáticamente cualquier registro de tiempo
activo y deshabilitar la posibilidad de iniciar nuevos registros.

Esto permitiría que el recurso pueda continuar registrando tiempo en otros tickets o tareas
activos.

Criterios de aceptación

?  Al cambiar un ticket al estado Cerrado, cualquier cronómetro activo debe detenerse

automáticamente.

?  El sistema no debe permitir iniciar un nuevo registro de tiempo en un ticket cerrado.
?  El tiempo registrado antes del cierre debe conservarse correctamente.
?  El usuario debe poder iniciar el registro de tiempo en otro ticket activo.

Evidencia:

EA-0019 — El registro de tiempo permite registrar
actividad fuera del horario laboral del calendario

Módulo/Pantalla: Tickets ? Registro de tiempos

Tipo: Observación

Estado: Abierta

Reportado por: Arely Pazmiño

Iteración de origen: ITER-004

Iteración de cierre: —

Descripción

Se verificó que el sistema permite continuar registrando tiempo fuera del horario laboral
configurado en el calendario. Durante la prueba, el registro se realizó aproximadamente a
las 23:02 y el SLA se encontraba pausado.

Adicionalmente, el registro aparece asociado a la fecha siguiente, posiblemente debido a la
hora en la que se realizó la actividad.

Resultado esperado / Situación actual

Situación actual: El sistema permite registrar tiempo fuera del horario laboral configurado y
se debe verificar si la fecha asignada al registro corresponde correctamente a la fecha y
hora real de inicio de la actividad.

Resultado actual / Propuesta de mejora

Definir la regla de negocio para el registro de tiempo fuera del horario laboral.

Podrían considerarse las siguientes alternativas:

1.  Permitir el registro fuera de horario, pero mostrar una advertencia al usuario.
2.  Permitirlo y clasificarlo como tiempo fuera de jornada laboral.
3.  Bloquearlo, salvo que exista una autorización especial.
4.  Permitirlo, pero mantener correctamente la fecha real en la que inició el trabajo.

Criterios de aceptación

?  Definir si se permite registrar tiempo fuera del horario laboral.
?  El sistema debe conservar correctamente la fecha y hora real de inicio y finalización.
?  El registro debe diferenciar, si corresponde, entre tiempo laboral y tiempo fuera de

jornada.

?  El comportamiento debe ser consistente con la configuración del SLA y del

calendario.

Evidencia:

EA-0020 — El calendario del recurso no
muestra la configuración de jornada
laboral

Módulo/Pantalla: Equipo ? Perfil del recurso / Calendario

Tipo: Observación

Estado: Abierta

Reportado por: Arely Pazmiño

Iteración de origen: ITER-004

Iteración de cierre: —

Descripción

Se verificó que el calendario configurado para los clientes permite visualizar la información
correspondiente a los días y horarios laborales. Sin embargo, al consultar el calendario de
un recurso interno, como Luis Andrade (@sywork.net), no se muestra información
relacionada con su jornada laboral o disponibilidad.

Actualmente, el calendario del recurso únicamente muestra información como su
cumpleaños.

Resultado esperado / Situación actual

Situación actual: El calendario del recurso no muestra claramente sus días laborales,
horarios de trabajo, feriados aplicables, ausencias o disponibilidad. Solo se visualiza
información personal como el cumpleaños.

Resultado actual / Propuesta de mejora

El calendario del recurso debería mostrar la información relevante para la planificación y
asignación de trabajo, incluyendo:

?  Calendario base asignado.
?  País del calendario.
?  Días laborales.
?  Horario de trabajo.
?  Feriados aplicables.
?  Vacaciones.
?  Ausencias.
?  Permisos.
?  Excepciones de calendario.

?  Horas disponibles y ocupadas.

Esto es especialmente importante porque el Panel de Asignación debe utilizar la
disponibilidad real de los recursos para asignar tickets y tareas.

Criterios de aceptación

?  El sistema muestra el calendario laboral asignado al recurso.
?  Se visualizan correctamente los días y horarios laborales.
?  Se muestran los feriados correspondientes al calendario asignado.
?  Se pueden identificar ausencias y excepciones.
?  La disponibilidad del recurso puede ser utilizada por el Panel de Asignación.
?  La información del calendario del recurso se encuentra separada de eventos

personales como cumpleaños.

Evidencia:


