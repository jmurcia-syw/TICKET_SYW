# Feature Specification: Script de Datos Semilla — Clientes Aris y Vaxthera

**Feature Branch**: `026-seed-clientes-proyectos`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "Creación de Script de Datos Semilla (Seeders / Fixtures Base) — poblar la base de datos con los datos iniciales de clientes (Aris, Vaxthera), sus proyectos, usuarios con rol Usuario/cliente, configuración de país/zona horaria, matriz de SLA por proyecto y listas de tareas, tomados directamente de la estructura real de estos clientes en el sistema origen (Teamwork)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Poblar un entorno nuevo con los datos reales de Aris y Vaxthera (Priority: P1)

Como responsable de implantar o preparar un entorno (desarrollo, pruebas o demo), quiero ejecutar un único script de siembra que cree de una sola vez los clientes Aris y Vaxthera con su país/zona horaria, sus proyectos, los usuarios con rol "Usuario/cliente" y las listas de tareas de cada proyecto de Soporte, en lugar de tener que darlos de alta manualmente pantalla por pantalla.

**Why this priority**: Es el valor central de la funcionalidad: sin este script no hay forma rápida y repetible de tener un entorno representativo de estos dos clientes reales para probar o demostrar el sistema.

**Independent Test**: Se puede probar de forma independiente ejecutando el script contra una base de datos limpia (o un entorno de pruebas) y verificando en las pantallas de Maestros > Clientes, Maestros > Proyectos y el listado de Listas de Tareas que Aris y Vaxthera, sus proyectos y sus listas aparecen exactamente como se especificó.

**Acceptance Scenarios**:

1. **Given** una base de datos sin el cliente Aris, **When** se ejecuta el script de siembra, **Then** el cliente Aris queda creado con país/zona horaria Colombia (`America/Bogota`), sus 3 proyectos (Evolutivo, Preventa, Soporte) y los usuarios `Eliseon@aris.ming.com` y `paulaBlanco@aris.ming.com` con rol "Usuario/cliente" asignados a Aris y a sus proyectos.
2. **Given** una base de datos sin el cliente Vaxthera, **When** se ejecuta el script de siembra, **Then** el cliente Vaxthera queda creado con país/zona horaria Ecuador (`America/Guayaquil`), su proyecto Soporte y el usuario `pablo@vaxthera.com` con rol "Usuario/cliente" asignado a Vaxthera y a su proyecto Soporte.
3. **Given** el proyecto Soporte de Aris recién creado, **When** se revisa su configuración de SLA, **Then** tiene configurada una matriz de 4 niveles (Crítico, Alto, Medio, Bajo) con tiempos de respuesta y resolución.
4. **Given** los proyectos Evolutivo y Preventa de Aris y el proyecto Soporte de Vaxthera recién creados, **When** se revisa su configuración de SLA, **Then** ninguno tiene una matriz de SLA activa.
5. **Given** el proyecto Soporte de Aris recién creado, **When** se revisan sus Listas de Tareas, **Then** existen exactamente las 8 listas indicadas (Servicios Correctivos, Servicios Adaptativos, Servicios Evolutivos, Servicios Administrativos, Seguimiento, Coordinación, Servicios preventivos IT, Redwood).
6. **Given** el proyecto Soporte de Vaxthera recién creado, **When** se revisan sus Listas de Tareas, **Then** existen exactamente las 5 listas indicadas (Servicios Evolutivos, Servicios Administrativos, Servicios Correctivos, Servicios Adaptativos, Seguimiento (Completadas)).

---

### User Story 2 - Re-ejecutar el script sin duplicar datos (Priority: P2)

Como responsable de mantener el entorno de desarrollo/pruebas, quiero poder volver a ejecutar el script de siembra (por ejemplo tras resetear parcialmente la base de datos o al actualizar el propio script) sin que se dupliquen clientes, proyectos, usuarios o listas de tareas ya existentes.

**Why this priority**: Sin esta garantía el script solo sirve una vez; el equipo necesita poder correrlo de forma repetida como parte de su flujo habitual de preparación de entornos.

**Independent Test**: Se puede probar de forma independiente ejecutando el script dos veces seguidas sobre el mismo entorno y verificando que la segunda ejecución no crea registros adicionales (mismo conteo de clientes, proyectos, usuarios y listas antes y después).

**Acceptance Scenarios**:

1. **Given** que el script ya se ejecutó una vez y Aris/Vaxthera ya existen con todos sus datos, **When** se ejecuta el script nuevamente, **Then** no se crean clientes, proyectos, usuarios ni listas de tareas duplicados.
2. **Given** que solo una parte de los datos existe (por ejemplo el cliente Aris ya existe pero le falta el proyecto Preventa), **When** se ejecuta el script, **Then** el script completa únicamente lo que falta sin duplicar ni alterar lo que ya existía.

---

### User Story 3 - Validar el motor de SLA con datos reales de estos clientes (Priority: P3)

Como responsable de calidad, quiero que los datos sembrados reflejen fielmente qué proyectos tienen SLA y cuáles no (incluyendo el caso de Vaxthera/Soporte, que explícitamente no debe tener SLA), para poder validar el comportamiento del motor de SLA y de las pantallas de Ticket/Tarea con casos reales representativos.

**Why this priority**: Es un beneficio secundario del script (sirve como fixture de pruebas), pero no es el objetivo principal de la siembra inicial de datos.

**Independent Test**: Se puede probar de forma independiente creando un Ticket en cada uno de los 4 proyectos sembrados y verificando que solo el de Aris/Soporte muestra countdown/indicadores de SLA activos.

**Acceptance Scenarios**:

1. **Given** un Ticket nuevo creado en el proyecto Soporte de Aris, **When** se abre su detalle, **Then** se muestran los indicadores de cumplimiento de SLA según la matriz de 4 niveles configurada.
2. **Given** un Ticket nuevo creado en el proyecto Soporte de Vaxthera, **When** se abre su detalle, **Then** no se muestra ningún indicador o countdown de SLA, dado que el proyecto está explícitamente sin SLA.

---

### Edge Cases

- ¿Qué ocurre si el cliente Aris o Vaxthera ya existe pero con un país/zona horaria distinto al indicado? El script DEBE forzar la convergencia: actualiza país/zona horaria al valor sembrado (sin tocar ningún otro campo del cliente) y lo reporta como "actualizado" — los valores de este seed son fijos y no dependen de lo que hubiera antes.
- ¿Qué ocurre si alguno de los correos de usuario (`Eliseon@aris.ming.com`, `paulaBlanco@aris.ming.com`, `pablo@vaxthera.com`) ya existe en el sistema con un rol distinto a "Usuario/cliente"? El script DEBE forzar su rol a "Usuario/cliente" (estos 3 emails son, por definición de esta feature, Encargados de sus proyectos — nunca recursos ni parte del equipo) y reportarlo como "actualizado".
- ¿Qué ocurre si ya existe una lista de tareas con el mismo nombre en el proyecto de destino (por ejemplo "Seguimiento")? El script no debe crear una lista duplicada.
- ¿Qué ocurre si el script se ejecuta contra un entorno que ya tiene Tickets/Tareas creados sobre estos clientes? El script no debe modificar ni eliminar Tickets, Tareas ni registros de tiempo existentes; solo debe completar los datos maestros faltantes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE crear el cliente "Aris" con país/zona horaria Colombia (`America/Bogota`) si aún no existe.
- **FR-002**: El sistema DEBE crear el cliente "Vaxthera" con país/zona horaria Ecuador (`America/Guayaquil`) si aún no existe.
- **FR-003**: El sistema DEBE crear los usuarios `Eliseon@aris.ming.com` y `paulaBlanco@aris.ming.com` con rol "Usuario/cliente" como Encargados del cliente Aris (no como recursos ni miembros del equipo del proyecto), con acceso a sus proyectos.
- **FR-004**: El sistema DEBE crear el usuario `pablo@vaxthera.com` con rol "Usuario/cliente" como Encargado del cliente Vaxthera (no como recurso ni miembro del equipo del proyecto), con acceso a su proyecto Soporte.
- **FR-004a**: Cada uno de los 3 usuarios "Usuario/cliente" DEBE quedar registrado como Encargado de su Cliente (visible en Maestros > Usuarios/clientes), no únicamente como miembro operativo de sus Proyectos — ambos vínculos son necesarios y no son intercambiables.
- **FR-005**: El sistema DEBE crear para Aris los proyectos "Evolutivo", "Preventa" y "Soporte".
- **FR-006**: El sistema DEBE crear para Vaxthera el proyecto "Soporte".
- **FR-007**: Los proyectos "Evolutivo" y "Preventa" de Aris DEBEN quedar sin matriz de SLA configurada.
- **FR-008**: El proyecto "Soporte" de Aris DEBE quedar configurado con una matriz de SLA de 4 niveles (Crítico, Alto, Medio, Bajo), usando tiempos estándar recomendados de respuesta/resolución para cada nivel.
- **FR-009**: El proyecto "Soporte" de Vaxthera DEBE quedar explícitamente sin matriz de SLA configurada.
- **FR-010**: El sistema DEBE crear en el proyecto Soporte de Aris exactamente estas 8 Listas de Tareas, en este orden: Servicios Correctivos, Servicios Adaptativos, Servicios Evolutivos, Servicios Administrativos, Seguimiento, Coordinación, Servicios preventivos IT, Redwood.
- **FR-011**: El sistema DEBE crear en el proyecto Soporte de Vaxthera exactamente estas 5 Listas de Tareas, en este orden: Servicios Evolutivos, Servicios Administrativos, Servicios Correctivos, Servicios Adaptativos, Seguimiento (Completadas).
- **FR-012**: El proceso de siembra DEBE poder ejecutarse repetidamente sin crear clientes, proyectos, usuarios o listas de tareas duplicados (re-ejecución segura), y DEBE forzar la convergencia de los campos que sí tienen un valor fijo en esta spec (país/zona horaria de Aris/Vaxthera, rol de los 3 usuarios) al valor aquí especificado si encuentra un valor distinto, sin importar que eso implique reiniciar servicios o sobrescribir un valor divergente — estos datos semilla son fijos y no negociables. Esto no afecta a ningún otro cliente, proyecto o usuario del sistema fuera de los aquí listados.
- **FR-013**: El proceso de siembra NO DEBE crear ni modificar Tickets, Tareas, registros de tiempo u otros datos transaccionales; su alcance se limita a los datos maestros aquí listados (clientes, proyectos, usuarios, configuración de SLA, listas de tareas).
- **FR-014**: El proceso de siembra DEBE dejar constancia (log o salida legible) de qué registros creó y cuáles ya existían y fueron omitidos, para que quien lo ejecute pueda verificar el resultado.

### Key Entities

- **Cliente**: Aris y Vaxthera; cada uno con nombre, país y zona horaria (`America/Bogota` / `America/Guayaquil`).
- **Usuario/cliente (Encargado)**: usuario con rol "Usuario/cliente", identificado por email, registrado como Encargado de un Cliente y con acceso a uno o más Proyectos de ese Cliente — nunca un recurso o miembro del equipo del proyecto.
- **Proyecto**: pertenece a un Cliente; tiene nombre (Evolutivo, Preventa, Soporte) y, opcionalmente, una matriz de SLA asociada.
- **Matriz de SLA**: conjunto de 4 niveles de prioridad (Crítico, Alto, Medio, Bajo), cada uno con tiempo de respuesta y de resolución; un Proyecto puede no tener matriz de SLA (sin SLA).
- **Lista de Tareas**: pertenece a un Proyecto; tiene nombre y posición/orden dentro del proyecto.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tras ejecutar el script una sola vez sobre un entorno limpio, el 100% de los clientes, proyectos, usuarios y listas de tareas especificados quedan visibles y correctamente configurados en las pantallas correspondientes, sin pasos manuales adicionales.
- **SC-002**: Ejecutar el script por segunda vez sobre el mismo entorno produce cero registros duplicados (mismo conteo de clientes, proyectos, usuarios y listas antes y después de la segunda ejecución).
- **SC-003**: Un Ticket creado en el proyecto Soporte de Aris muestra indicadores de SLA correctos según la matriz de 4 niveles en el 100% de los casos probados, mientras que uno creado en el proyecto Soporte de Vaxthera no muestra ningún indicador de SLA.
- **SC-004**: El tiempo para preparar un entorno de desarrollo/demo con los datos de Aris y Vaxthera se reduce de una tarea manual de varios pasos a la ejecución de un único script.

## Assumptions

- Los tiempos de respuesta/resolución de la matriz de SLA de Aris/Soporte no fueron fijados de forma exacta por quien solicitó la funcionalidad ("o tiempos estándar recomendados"); se usan los valores sugeridos en la solicitud (Crítico 2h/4h, Alto 4h/8h, Medio 8h/24h, Bajo 24h/48h) como valores por defecto razonables, reutilizando la misma estructura de matriz de SLA de 4 niveles ya existente en el sistema.
- "Seguimiento (Completadas)" en el proyecto Soporte de Vaxthera se siembra como una Lista de Tareas más, con ese nombre literal, ya que el sistema actual no distingue listas "activas" de "completadas" como una propiedad de la lista en sí (esa distinción existía en el sistema origen del cual se exportaron los datos, pero no es un concepto modelado en este sistema).
- La creación de credenciales/contraseña inicial para los 3 usuarios nuevos reutiliza el mecanismo de alta y reseteo de contraseñas ya existente en el sistema (spec 003); no es necesario definir un mecanismo nuevo.
- "Asignados al equipo y proyectos del cliente Aris" se interpreta como: los usuarios quedan asociados al Cliente Aris y tienen acceso a los 3 proyectos de Aris (Evolutivo, Preventa, Soporte), no solo a uno de ellos.
- El script se ejecuta manualmente por un miembro del equipo técnico contra un entorno de desarrollo o pruebas (no es un proceso automático disparado por la aplicación en producción).
- No se siembran Tickets, Tareas ni registros de tiempo de ejemplo dentro de las listas creadas; las listas quedan vacías, listas para uso real o de pruebas posteriores.
