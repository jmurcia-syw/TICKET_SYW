# Feature Specification: Reseteo de Contraseñas y Credenciales Semilla Estables

**Feature Branch**: `003-reseteo-contrasenas`

**Created**: 2026-07-07

**Status**: Draft

**Input**: User description: "Reseteo de contraseñas y credenciales semilla — feature de Fase 1 Tickets. Al instalar el proyecto en un equipo nuevo, la migración de seed genera una contraseña provisional aleatoria compartida por los 4 usuarios semilla y la imprime una única vez en el log del backend; si se pierde, es irrecuperable. Se necesita: (1) credenciales semilla estables en Desarrollo, documentadas, (2) que un Admin pueda resetear la contraseña de cualquier usuario real sin depender de logs, (3) que el propio usuario pueda recuperar su contraseña por correo sin depender de un Admin."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un administrador restablece el acceso de un usuario (Priority: P1)

Un usuario real (no de prueba) olvidó su contraseña o nunca recibió la provisional que se generó al crear su cuenta. Un administrador, desde la pantalla de gestión de usuarios, dispara el restablecimiento de esa cuenta y obtiene una nueva contraseña temporal para comunicársela por un canal seguro.

**Why this priority**: Es el problema que ya está ocurriendo hoy en producción/instalaciones reales — sin esto, una contraseña perdida es irrecuperable y bloquea al usuario permanentemente.

**Independent Test**: Puede probarse por completo disparando el restablecimiento sobre una cuenta existente y confirmando que el usuario puede iniciar sesión con la nueva contraseña mostrada, sin tocar ninguna otra pieza de esta funcionalidad.

**Acceptance Scenarios**:

1. **Given** una cuenta de usuario activa existente, **When** un administrador restablece su contraseña, **Then** el sistema genera una contraseña temporal nueva y única, y la muestra en pantalla una sola vez.
2. **Given** una contraseña temporal recién generada para un usuario, **When** ese usuario inicia sesión con ella, **Then** el acceso es exitoso.
3. **Given** un identificador de usuario que no existe, **When** un administrador intenta restablecer su contraseña, **Then** el sistema informa que el usuario no fue encontrado, sin generar nada.

---

### User Story 2 - Las cuentas de demostración tienen credenciales estables en Desarrollo (Priority: P2)

Cada vez que alguien instala el proyecto en un equipo nuevo (Desarrollo/pruebas locales), las 4 cuentas de demostración (administrador, coordinador, gestor de calidad, resolutor) deben poder iniciarse sesión con credenciales conocidas y documentadas, sin depender de revisar logs de contenedores que pueden perderse o rotar.

**Why this priority**: Es fricción recurrente y ya causó pérdida de tiempo real durante instalaciones — pero es un problema de conveniencia de desarrollo, no de un usuario real bloqueado, por eso va después de la Historia 1.

**Independent Test**: Puede probarse instalando el proyecto desde cero dos veces en entornos distintos y confirmando que las 4 cuentas de demostración quedan con la misma contraseña documentada ambas veces, sin leer ningún log.

**Acceptance Scenarios**:

1. **Given** una instalación nueva en un entorno de Desarrollo, **When** se completa la puesta en marcha inicial, **Then** las 4 cuentas de demostración quedan con una contraseña conocida de antemano, documentada en el proyecto.
2. **Given** dos instalaciones distintas en Desarrollo, **When** se comparan las credenciales de las cuentas de demostración, **Then** son idénticas entre ambas instalaciones.
3. **Given** una instalación marcada como producción, **When** se completa la puesta en marcha inicial, **Then** las cuentas de demostración reciben una contraseña única e impredecible, nunca la fija de Desarrollo.

---

### User Story 3 - Un usuario recupera su propia contraseña por correo (Priority: P3)

Un usuario que olvidó su contraseña la recupera por sí mismo desde la pantalla de inicio de sesión, sin necesidad de contactar a un administrador: solicita la recuperación con su correo, recibe un mensaje, y define una contraseña nueva.

**Why this priority**: Mejora la autonomía del usuario y reduce la carga sobre los administradores, pero no es bloqueante mientras exista la Historia 1 como vía de emergencia — por eso es la de menor prioridad.

**Independent Test**: Puede probarse por completo solicitando la recuperación con el correo de una cuenta existente, completando el flujo con el mensaje recibido, y confirmando el inicio de sesión con la contraseña nueva — sin depender de ningún administrador.

**Acceptance Scenarios**:

1. **Given** una cuenta activa con un correo registrado, **When** el usuario solicita recuperar su contraseña con ese correo, **Then** recibe un mensaje que le permite definir una contraseña nueva.
2. **Given** un correo que no corresponde a ninguna cuenta registrada, **When** alguien solicita recuperación con ese correo, **Then** el sistema responde de la misma forma que si la cuenta existiera, sin revelar que no existe.
3. **Given** un mensaje de recuperación ya usado una vez, **When** se intenta usar nuevamente para definir otra contraseña, **Then** el sistema lo rechaza.
4. **Given** un mensaje de recuperación emitido hace más tiempo del permitido, **When** el usuario intenta usarlo, **Then** el sistema lo rechaza por vencido.
5. **Given** una cuenta que fue desactivada después de solicitar la recuperación, **When** el usuario intenta completar el cambio de contraseña con un mensaje aún vigente, **Then** el sistema lo rechaza.

### Edge Cases

- ¿Qué pasa si un administrador restablece la contraseña de un usuario justo cuando ese usuario tiene una sesión activa? La sesión activa no se corta de inmediato; sigue vigente hasta su vencimiento natural.
- ¿Qué pasa si se solicita recuperación por correo para una cuenta que existe pero está desactivada? El sistema responde igual que para cualquier otra solicitud (sin revelar el estado de la cuenta), pero el cambio de contraseña no se completa mientras la cuenta siga desactivada.
- ¿Qué pasa si alguien solicita recuperación por correo repetidamente en poco tiempo para la misma cuenta? Fuera de alcance de esta fase (ver Assumptions).
- ¿Qué pasa si una instalación de Desarrollo se reconfigura después para ser productiva? Debe recibir credenciales únicas nuevas para las cuentas de demostración, no conservar la fija de Desarrollo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir que un administrador restablezca la contraseña de cualquier cuenta de usuario existente, sin necesidad de acceder a logs del servidor ni a ningún otro canal externo.
- **FR-002**: Al restablecer una contraseña, el sistema DEBE generar una contraseña temporal nueva y única, y mostrarla una única vez en la interfaz del administrador que la solicitó.
- **FR-003**: El sistema DEBE informar claramente, en el momento de mostrar cualquier contraseña temporal, que no volverá a mostrarse.
- **FR-004**: Un intento de restablecer la contraseña de una cuenta inexistente DEBE ser rechazado, informando que el usuario no fue encontrado.
- **FR-005**: Las cuentas de demostración del sistema (administrador, coordinador, gestor de calidad, resolutor) DEBEN quedar con una contraseña estable y conocida de antemano en cada instalación de Desarrollo.
- **FR-006**: La contraseña estable de las cuentas de demostración descrita en FR-005 NO DEBE aplicarse en instalaciones de producción; estas DEBEN recibir siempre una contraseña única e impredecible, generada en el momento de la instalación.
- **FR-007**: El proyecto DEBE dejar documentada, para uso interno del equipo de desarrollo, la lista de cuentas de demostración y su contraseña estable, en un formato que no sea legible a simple vista.
- **FR-008**: El sistema DEBE permitir que un usuario solicite la recuperación de su propia contraseña usando únicamente su correo, sin intervención de un administrador.
- **FR-009**: Ante una solicitud de recuperación de contraseña, el sistema DEBE responder de forma idéntica exista o no una cuenta asociada al correo indicado, para no revelar qué correos están registrados.
- **FR-010**: Toda solicitud de recuperación de contraseña DEBE dejar de ser válida después de un tiempo límite desde que fue emitida.
- **FR-011**: Toda solicitud de recuperación de contraseña DEBE dejar de ser válida en cuanto se use una vez para definir una contraseña nueva.
- **FR-012**: El sistema DEBE rechazar la finalización de una recuperación de contraseña si la cuenta asociada está desactivada, aunque la solicitud siga vigente.
- **FR-013**: El mecanismo de inicio de sesión mediante cuenta corporativa externa (Google) existente DEBE permanecer sin cambios.

### Key Entities

- **Cuenta de usuario**: representa a una persona que puede iniciar sesión en el sistema; tiene credenciales, un estado activo/inactivo, y un rol asociado.
- **Solicitud de recuperación de contraseña**: vínculo temporal y de un solo uso asociado a una cuenta de usuario, que autoriza definir una contraseña nueva sin intervención de un administrador; vence tras un tiempo límite o al usarse una vez, lo que ocurra primero.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador puede restablecer el acceso de un usuario bloqueado en menos de 1 minuto, sin necesidad de revisar logs ni archivos del servidor.
- **SC-002**: Poner en marcha una instalación nueva de Desarrollo nunca requiere buscar en logs para conocer las credenciales de las cuentas de demostración.
- **SC-003**: El 100% de las instalaciones marcadas como producción reciben credenciales únicas para sus cuentas de demostración, nunca la contraseña fija documentada para Desarrollo.
- **SC-004**: Un usuario que olvidó su contraseña puede recuperar el acceso por sí mismo, sin contactar a un administrador, en menos de 5 minutos.
- **SC-005**: Ninguna solicitud de recuperación de contraseña permite distinguir si un correo dado tiene o no una cuenta registrada en el sistema.

## Assumptions

- "Administrador" se refiere a cualquier usuario con permiso de gestión sobre cuentas de usuario (mismo permiso que ya controla la gestión de usuarios existente).
- El envío de los mensajes de recuperación de contraseña se hace desde una cuenta de correo propia del equipo del proyecto; esta fase no asume un servicio de envío de correo transaccional de pago.
- Limitar la frecuencia de solicitudes de recuperación (para prevenir abuso) queda fuera de alcance de esta fase.
- Las sesiones activas de un usuario no se invalidan de forma forzada cuando su contraseña cambia; siguen vigentes hasta su vencimiento normal.
- El inicio de sesión mediante Google no se modifica ni se retira.
