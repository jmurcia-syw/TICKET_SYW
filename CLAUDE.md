<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

**Active feature**: Script de Datos Semilla (Seeders/Fixtures) — Clientes Aris y Vaxthera — un único script `backend/scripts/seed_clients_aris_vaxthera.py` (patrón de `seed_tickets.py`, sin migración de Alembic) que crea de forma idempotente los clientes Aris (Colombia, `America/Bogota`) y Vaxthera (Ecuador, `America/Guayaquil`), sus proyectos (Aris: Evolutivo/Preventa sin SLA y Soporte con matriz de SLA de 4 niveles; Vaxthera: Soporte explícitamente sin SLA), los 3 usuarios "Usuario/cliente" (`Eliseon@aris.ming.com`, `paulaBlanco@aris.ming.com`, `pablo@vaxthera.com`) y las Listas de Tareas de cada proyecto Soporte (8 para Aris, 5 para Vaxthera).
**Spec**: specs/026-seed-clientes-proyectos/spec.md
**Plan**: specs/026-seed-clientes-proyectos/plan.md
**Research**: specs/026-seed-clientes-proyectos/research.md
**Data model**: specs/026-seed-clientes-proyectos/data-model.md
**Quickstart**: specs/026-seed-clientes-proyectos/quickstart.md
**Constitution**: .specify/memory/constitution.md

**Previous feature (completada)**: Actualización Integral del Manual de Usuario (v3.2, alcance ampliado a toda la app) — `docs/Manual_de_Usuario.md` y `docs/Manual_de_Usuario.docx` con resumen arquitectónico, 3 diagramas Mermaid (ciclo de vida del Ticket, aprobación de vacaciones/permisos, pausa/reanudación de SLA) y guía paso a paso de las 12 áreas de pantallas (Tickets, Kanban, Mis Tareas, Panel de Asignación, Detalle de Ticket, Vista Usuario/cliente, RRHH, Registro/Reporte de Tiempos, los 8 Maestros, Mi Perfil, Login/Reset), verificada navegando la app real en Docker
**Spec**: specs/025-manual-usuario-integral/spec.md
**Plan**: specs/025-manual-usuario-integral/plan.md
**Research**: specs/025-manual-usuario-integral/research.md
**Data model**: specs/025-manual-usuario-integral/data-model.md
**Quickstart**: specs/025-manual-usuario-integral/quickstart.md

**Previous feature (completada)**: Sugerencias de Carga y Disponibilidad en la Reasignación — el selector de nuevo resolutor en "Reasignar" (spec 023) muestra la misma carga de trabajo, orden por menor carga y etiqueta de no disponibilidad (fuera de horario/festivo/ausencia) que ya tiene la asignación inicial (Triage Push)
**Spec**: specs/024-reasignacion-sugerencias-carga/spec.md
**Plan**: specs/024-reasignacion-sugerencias-carga/plan.md
**Research**: specs/024-reasignacion-sugerencias-carga/research.md
**Data model**: specs/024-reasignacion-sugerencias-carga/data-model.md
**Quickstart**: specs/024-reasignacion-sugerencias-carga/quickstart.md

**Previous feature (completada)**: Ajuste Visual en Historial de Estados (SLA) y Reasignación de Resolutores — tiempo transcurrido e indicador de cumplimiento SLA (✅/⚠️/❌) por cada cambio de estado, y reasignación de Ticket/Tarea a otro resolutor con registro visible "resolutor anterior ➡️ nuevo resolutor"
**Spec**: specs/023-historial-sla-reasignacion/spec.md
**Plan**: specs/023-historial-sla-reasignacion/plan.md
**Research**: specs/023-historial-sla-reasignacion/research.md
**Data model**: specs/023-historial-sla-reasignacion/data-model.md
**Quickstart**: specs/023-historial-sla-reasignacion/quickstart.md

**Previous feature (completada)**: RRHH — Franjas Horarias globales por país (herencia + modo Personalizado), Calendario de Equipo Superpuesto (Mes/Semana/Día, ausencias parciales por horas) y Motor de SLA Dinámico basado en disponibilidad real
**Spec**: specs/022-rrhh-calendario-sla-dinamico/spec.md
**Plan**: specs/022-rrhh-calendario-sla-dinamico/plan.md
**Research**: specs/022-rrhh-calendario-sla-dinamico/research.md
**Data model**: specs/022-rrhh-calendario-sla-dinamico/data-model.md
**Quickstart**: specs/022-rrhh-calendario-sla-dinamico/quickstart.md

**Previous feature (completada)**: Festivos sincronizados por API pública, categorización visual (Oficial vs. Regional/Religioso) y cumpleaños de Recursos en el Calendario
**Spec**: specs/021-festivos-api-cumpleanos/spec.md
**Plan**: specs/021-festivos-api-cumpleanos/plan.md
**Research**: specs/021-festivos-api-cumpleanos/research.md
**Data model**: specs/021-festivos-api-cumpleanos/data-model.md
**Quickstart**: specs/021-festivos-api-cumpleanos/quickstart.md

**Previous feature (completada)**: Fase 5 SDD V3 — Calendarios multi-zona horaria con festivos por país, horario laboral semanal, gestión de vacaciones/permisos con doble aprobación (Jefe directo + rol RRHH) y alerta de disponibilidad (sin bloquear) al asignar tickets
**Spec**: specs/020-calendarios-vacaciones-disponibilidad/spec.md
**Plan**: specs/020-calendarios-vacaciones-disponibilidad/plan.md
**Research**: specs/020-calendarios-vacaciones-disponibilidad/research.md
**Data model**: specs/020-calendarios-vacaciones-disponibilidad/data-model.md
**Quickstart**: specs/020-calendarios-vacaciones-disponibilidad/quickstart.md

**Previous feature (completada)**: Unidades de tiempo (minutos/horas/días) al configurar SLA — el campo "Tiempo límite de diagnóstico, análisis y ejecución" acepta horas/días y convierte a minutos
**Spec**: specs/019-sla-unidades-tiempo/spec.md
**Plan**: specs/019-sla-unidades-tiempo/plan.md

**Previous feature (en curso)**: Accesos y conexiones múltiples del Cliente (VPN/URL por ambiente/Escritorio remoto) en Maestros > Clientes — resuelve OBS-0001/OBS-0008/OBS-0017 del framework UAT
**Spec**: specs/018-cliente-accesos-conexiones/spec.md
**Plan**: specs/018-cliente-accesos-conexiones/plan.md

**Previous feature (implementada, pendiente de validación manual)**: Contenido enriquecido (formato, imágenes pegadas y adjuntos) en comentarios y descripción de Ticket/Tarea
**Spec**: specs/017-contenido-enriquecido-ticket/spec.md
**Plan**: specs/017-contenido-enriquecido-ticket/plan.md

**Previous feature (completada)**: Corregir el Cliente de un Usuario/cliente y desambiguar Proyectos homónimos
**Spec**: specs/016-corregir-cliente-encargado/spec.md
**Plan**: specs/016-corregir-cliente-encargado/plan.md

**Previous feature (completada)**: Encargado (Usuario/cliente) en múltiples Proyectos
**Spec**: specs/015-encargado-multiples-proyectos/spec.md
**Plan**: specs/015-encargado-multiples-proyectos/plan.md

**Previous feature (completada)**: SLAs por Proyecto y Prioridad (Fase 4 SDD V3)
**Spec**: specs/014-sla-tickets-tareas/spec.md
**Plan**: specs/014-sla-tickets-tareas/plan.md

**Previous feature (completada)**: Manejo Global de Errores y Notificaciones (API a Frontend)
**Spec**: specs/013-manejo-errores-notificaciones/spec.md
**Plan**: specs/013-manejo-errores-notificaciones/plan.md

**Previous feature (completada)**: Skills Requeridas en el Ticket
**Spec**: specs/011-ticket-skills-requeridas/spec.md
**Plan**: specs/011-ticket-skills-requeridas/plan.md

**Previous feature (completada)**: Cronómetro Manual de Tiempo en el Ticket (provisional)
**Spec**: specs/012-cronometro-manual-ticket/spec.md
**Plan**: specs/012-cronometro-manual-ticket/plan.md

**Previous feature (completada)**: Usuario/cliente por Proyecto, Asignación de Personal y Estructura de Skills
**Spec**: specs/010-proyecto-personal-skills/spec.md
**Plan**: specs/010-proyecto-personal-skills/plan.md

**Previous feature (completada, validada end-to-end contra Docker real)**: Listas de Tareas, Subtareas, ciclo de vida unificado y fix de Registro de tiempo
**Spec**: specs/009-tareas-listas-subtareas/spec.md
**Plan**: specs/009-tareas-listas-subtareas/plan.md

**Previous feature (completada)**: Fase 3 — Manejo de Tareas
**Spec**: specs/008-fase3-tareas/spec.md
**Plan**: specs/008-fase3-tareas/plan.md

**Previous feature (completada, validada end-to-end contra Docker real)**: Selección manual del Encargado solicitante en el Ticket
**Spec**: specs/007-ticket-encargado-cliente/spec.md
**Plan**: specs/007-ticket-encargado-cliente/plan.md

**Previous feature (implementada, pendiente de validación manual)**: Refactorización visual y de navegación del detalle del Ticket (flujo tipo Teamwork)
**Spec**: specs/006-ticket-detalle-tiempo-ui/spec.md
**Plan**: specs/006-ticket-detalle-tiempo-ui/plan.md

**Previous feature (completada)**: Registro de tiempo en el detalle del ticket, rol Encargado y navegación
**Spec**: specs/005-ticket-tiempo-encargado-nav/spec.md
**Plan**: specs/005-ticket-tiempo-encargado-nav/plan.md

**Previous feature (completada)**: Fase 2 — Registro diario de tiempos por recurso
**Spec**: specs/004-fase2-registro-tiempos/spec.md
**Plan**: specs/004-fase2-registro-tiempos/plan.md
**Data model**: specs/004-fase2-registro-tiempos/data-model.md

**Previous feature (completada)**: Fase 1 — Tickets
**Spec**: specs/002-fase1-tickets/spec.md
**Plan**: specs/002-fase1-tickets/plan.md
**Data model**: specs/002-fase1-tickets/data-model.md

**Sub-feature (completada)**: Reseteo de contraseñas y credenciales semilla
**Spec**: specs/003-reseteo-contrasenas/spec.md
**Plan**: specs/003-reseteo-contrasenas/plan.md

**Previous feature (completada)**: Fase 0 — Maestros
**Spec anterior**: specs/001-fase0-maestros/spec.md
**Data model maestros**: specs/001-fase0-maestros/data-model.md
**MER actual**: docs/MER.md
<!-- SPECKIT END -->
