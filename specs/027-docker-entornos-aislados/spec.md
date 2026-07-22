# Feature Specification: Configuración de Entornos Aislados (Test y Producción) en Docker Compose

**Feature Branch**: `027-docker-entornos-aislados`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Necesito configurar la arquitectura de despliegue Docker en nuestro servidor Ubuntu para poder ejecutar dos ambientes completamente independientes (Test y Producción) sobre la misma máquina, diferenciados por puertos y archivos de variables de entorno. Requerimientos: (1) redirección de puertos — Test en puertos alternativos (8080/3001), Producción en puertos principales (80/3000); (2) soporte de archivos `.env.test` y `.env.prod` independientes para BD, secretos, URLs y configuración regional; (4) guía de ejecución en README/documentación técnica para levantar, detener y revisar logs de cada ambiente de forma aislada en el servidor Ubuntu."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Levantar y validar el ambiente de Test sin afectar Producción (Priority: P1)

Como responsable de despliegue, quiero levantar el ambiente de Test con sus propios puertos y su propio archivo de variables de entorno, para validar una nueva versión de la aplicación (incluyendo las sesiones de pruebas del framework `UAT/`) sin tocar ni arriesgar el ambiente de Producción que sirve a usuarios reales.

**Why this priority**: Es el flujo de mayor frecuencia de uso — cada iteración de UAT (`UAT/01_Iterations/`) depende de tener un ambiente de Test disponible y aislado antes de promover cambios a Producción. Sin esto, el equipo no tiene dónde validar con seguridad.

**Independent Test**: Se puede probar levantando únicamente el ambiente de Test (usando `.env.test`) en el servidor Ubuntu, confirmando que responde en sus puertos alternativos (ej. `8080`/`3001`) y que ninguna acción realizada allí (crear datos, cambiar configuración) es visible en Producción, incluso si Producción no está corriendo en ese momento.

**Acceptance Scenarios**:

1. **Given** el servidor Ubuntu con Docker instalado y el archivo `.env.test` presente, **When** el operador levanta el ambiente de Test, **Then** todos los servicios del ambiente quedan accesibles en sus puertos alternativos designados (ej. `8080` o `3001` para la aplicación) y usan exclusivamente los datos/configuración de `.env.test`.
2. **Given** el ambiente de Test corriendo, **When** el operador crea o modifica datos dentro de ese ambiente, **Then** esos cambios no aparecen en el ambiente de Producción (aunque esté corriendo simultáneamente en el mismo servidor).
3. **Given** el ambiente de Test corriendo, **When** el operador lo detiene, **Then** el ambiente de Producción (si está corriendo) continúa disponible sin interrupción.

---

### User Story 2 - Levantar el ambiente de Producción de forma aislada (Priority: P2)

Como responsable de despliegue, quiero levantar el ambiente de Producción con sus puertos principales y su propio archivo de variables de entorno, para servir la aplicación real a los usuarios finales, sin que la existencia o el estado del ambiente de Test lo afecte.

**Why this priority**: Es el ambiente que efectivamente usan los usuarios finales del sistema de tickets; debe poder operar de forma estable incluso mientras el equipo prueba cambios en Test.

**Independent Test**: Se puede probar levantando únicamente el ambiente de Producción (usando `.env.prod`) y confirmando que responde en sus puertos principales (ej. `80` o `3000`), usando exclusivamente los datos/configuración de `.env.prod`, con o sin el ambiente de Test corriendo en paralelo.

**Acceptance Scenarios**:

1. **Given** el servidor Ubuntu con Docker instalado y el archivo `.env.prod` presente, **When** el operador levanta el ambiente de Producción, **Then** todos los servicios quedan accesibles en sus puertos principales designados (ej. `80` o `3000`) y usan exclusivamente los datos/configuración de `.env.prod`.
2. **Given** el ambiente de Producción corriendo, **When** el operador levanta también el ambiente de Test en el mismo servidor, **Then** Producción sigue respondiendo en sus puertos sin degradación ni cambio de configuración.
3. **Given** ambos ambientes corriendo simultáneamente, **When** el operador detiene el ambiente de Test, **Then** Producción no sufre ninguna interrupción ni reinicio.

---

### User Story 3 - Detener y revisar logs de un ambiente específico de forma segura (Priority: P3)

Como responsable de despliegue, quiero poder detener y consultar los logs de un ambiente puntual (Test o Producción) de manera explícita, para diagnosticar problemas sin riesgo de afectar por error el otro ambiente.

**Why this priority**: Reduce el riesgo operativo de una intervención manual incorrecta (ej. detener Producción por error al querer reiniciar Test), y habilita diagnóstico ágil durante incidentes o sesiones de prueba.

**Independent Test**: Se puede probar ejecutando la acción de "ver logs" y "detener" sobre un ambiente nombrado explícitamente (Test o Producción) y verificando que solo ese ambiente se ve afectado, mientras el otro (si está corriendo) permanece intacto y sus logs no se mezclan.

**Acceptance Scenarios**:

1. **Given** ambos ambientes corriendo, **When** el operador solicita los logs del ambiente de Test, **Then** solo se muestran los registros de los servicios de Test, sin mezclarse con los de Producción.
2. **Given** ambos ambientes corriendo, **When** el operador detiene explícitamente el ambiente de Test, **Then** únicamente los servicios de Test se detienen y los de Producción continúan corriendo.
3. **Given** la documentación técnica publicada, **When** un operador nuevo en el equipo sigue los pasos documentados, **Then** logra levantar, detener y revisar logs de cualquiera de los dos ambientes sin necesidad de asistencia adicional.

---

### Edge Cases

- ¿Qué ocurre si `.env.test` o `.env.prod` no existe (o le faltan variables obligatorias) al intentar levantar ese ambiente? El sistema debe fallar de forma clara antes de arrancar servicios a medias, en vez de arrancar con valores vacíos o incorrectos.
- ¿Qué ocurre si, por un error de configuración, ambos archivos de entorno terminan asignando el mismo puerto a un servicio? El sistema debe impedir o señalar claramente el conflicto de puertos, en vez de fallar silenciosamente o dejar que un ambiente "robe" el puerto del otro.
- ¿Qué ocurre si el operador ejecuta el comando de detener/ver logs sin especificar explícitamente el ambiente (Test o Producción)? Debe quedar inequívoco a cuál ambiente aplica la acción, para evitar detener Producción por error.
- ¿Qué ocurre si ambos ambientes se levantan simultáneamente por primera vez en un servidor nuevo? Ambos deben poder inicializar sus propios datos (ej. esquema de base de datos) sin interferir entre sí.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir levantar el ambiente de Test y el ambiente de Producción de forma independiente en el mismo servidor Ubuntu, pudiendo ambos estar activos al mismo tiempo sin conflicto.
- **FR-002**: El ambiente de Test DEBE exponer sus servicios de cara al usuario (aplicación) en puertos alternativos distintos a los de Producción (ej. `8080` o `3001`).
- **FR-003**: El ambiente de Producción DEBE exponer sus servicios de cara al usuario (aplicación) en los puertos principales designados para producción (ej. `80` o `3000`).
- **FR-004**: Cuando el acceso directo a la base de datos sea necesario, el puerto expuesto por la base de datos DEBE ser distinto entre el ambiente de Test y el de Producción, para evitar colisión.
- **FR-005**: El sistema DEBE cargar la configuración de cada ambiente desde un archivo de variables de entorno dedicado y separado (`.env.test` para Test, `.env.prod` para Producción), cubriendo como mínimo: conexión a base de datos, secretos/credenciales, URLs de servicio y configuración regional (idioma/zona horaria).
- **FR-006**: Los datos (base de datos y cualquier estado persistente) del ambiente de Test DEBEN estar completamente aislados de los del ambiente de Producción — ninguna operación en un ambiente debe leer, escribir o modificar datos del otro.
- **FR-007**: El sistema DEBE permitir iniciar, detener y consultar los logs de cada ambiente de forma individual e inequívoca, sin requerir detener ni afectar el otro ambiente.
- **FR-008**: El sistema DEBE evitar colisiones de nombres (contenedores, redes, volúmenes) entre el stack de Test y el de Producción, de modo que ambos puedan coexistir en el mismo servidor.
- **FR-009**: La documentación técnica del proyecto (README o equivalente) DEBE incluir los pasos para levantar, detener y revisar logs de cada ambiente de forma aislada en el servidor Ubuntu.
- **FR-010**: El sistema DEBE fallar de forma explícita (sin levantar servicios parcialmente configurados) cuando el archivo de entorno correspondiente al ambiente solicitado no existe o le faltan variables obligatorias.
- **FR-011**: El puerto `80`/`3000` expuesto por Docker Compose para Producción DEBE entenderse como mapeo interno de tráfico, no como el punto de entrada final HTTPS al usuario — la terminación TLS/HTTPS de cara al usuario queda fuera de alcance de esta feature y depende del proxy inverso pendiente (`TODO(HOSTING)` en la Constitución). Esta feature no debe introducir ni asumir HTTP directo al usuario final como solución definitiva de Producción.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un operador puede levantar el ambiente de Test sin detener el ambiente de Producción, y ambos quedan accesibles simultáneamente cada uno en sus propios puertos.
- **SC-002**: El 100% de las variables de configuración usadas por el ambiente de Test (base de datos, secretos, URLs, configuración regional) provienen únicamente de `.env.test`, y el 100% de las del ambiente de Producción provienen únicamente de `.env.prod` — ningún valor se filtra entre archivos.
- **SC-003**: Una acción de creación o modificación de datos realizada en el ambiente de Test produce cero cambios observables en el ambiente de Producción, verificado tras ejecutar la acción con ambos ambientes activos.
- **SC-004**: Un operador nuevo en el equipo, siguiendo únicamente la documentación técnica publicada, logra levantar, detener y revisar los logs de cualquiera de los dos ambientes en menos de 10 minutos sin soporte adicional.
- **SC-005**: Detener o reiniciar el ambiente de Test no genera ninguna interrupción medible (caída de conexión, reinicio de contenedor) en el ambiente de Producción cuando ambos están activos, y viceversa.

## Assumptions

- Cada ambiente (Test y Producción) ejecuta su propio conjunto completo de servicios (base de datos, backend, frontend y los servicios de soporte que correspondan) — no se comparte una misma instancia de base de datos entre ambientes.
- El servidor Ubuntu ya cuenta con Docker y Docker Compose instalados, y el usuario de despliegue tiene los permisos necesarios para operarlos.
- Ambos ambientes conviven en el mismo host Ubuntu (no se requieren servidores físicos o virtuales separados); el aislamiento se logra a nivel de puertos, variables de entorno, y nombres/volúmenes de contenedor.
- El manejo de secretos dentro de `.env.test` y `.env.prod` sigue la práctica ya vigente en el proyecto para el archivo `.env` (variables de entorno no versionadas en git); esta feature no introduce un gestor de secretos nuevo.
- La estrategia de contenido/datos del ambiente de Test (qué datos de prueba usa, si se reinicia periódicamente, si se anonimiza data de Producción) queda fuera de alcance de esta feature — solo se cubre el aislamiento de infraestructura (puertos, variables, datos en ejecución), no el ciclo de vida del contenido de prueba.
- La migración de esquema de base de datos (Alembic) se ejecuta de forma independiente en cada ambiente cuando corresponda; esta feature no define una estrategia de sincronización de esquemas entre Test y Producción.
- La terminación TLS/HTTPS de Producción de cara al usuario final queda explícitamente fuera de alcance de esta feature y sigue pendiente del `TODO(HOSTING)` (proxy inverso) ya registrado en la Constitución del proyecto (decisión confirmada por el usuario: Opción A). Los puertos `80`/`3000` entregados aquí son el mapeo interno de Docker Compose, no la exposición final al usuario.
