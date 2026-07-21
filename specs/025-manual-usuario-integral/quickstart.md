# Quickstart: Validación del Manual de Usuario actualizado

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Data model**: [data-model.md](data-model.md)

Esta guía valida el entregable `docs/Manual_de_Usuario.md` sin ejecutar código ni pruebas
automatizadas (Principio VII de la Constitución) — es una revisión de contenido, no una suite de
tests.

## Prerrequisitos

- Tener `docs/Manual_de_Usuario.md` generado (salida de la fase de implementación de esta feature).
- Un visor Markdown con soporte de tablas y Mermaid (VS Code con extensión Markdown Preview Mermaid
  Support, GitHub, o un Artifact) para confirmar que los diagramas renderizan.
- Acceso de lectura a `.specify/memory/constitution.md` y a `specs/022-*`, `specs/023-*`,
  `specs/024-*` para contrastar terminología.

## Pasos de validación (mapeados a los Success Criteria de la spec)

1. **Abrir el documento** en el visor Markdown elegido y confirmar que los tres bloques
   ` ```mermaid ` renderizan sin errores de sintaxis (sin nodos huérfanos, sin flechas rotas).
   → Verifica **SC-003**.

2. **Leer solo el Resumen Arquitectónico** (cronometrar la lectura) y confirmar que, sin leer el
   resto del documento, se puede responder: *"¿qué módulo determina si un resolutor aparece
   disponible al reasignar un ticket?"* (respuesta esperada: Calendarios/RRHH). Debe tomar menos de
   3 minutos. → Verifica **SC-001**.

3. **Recorrer la guía paso a paso** y confirmar, para cada una de las 6 vistas en alcance (Dashboard,
   Kanban, Mis Tareas, Detalle de Ticket, Vista del Cliente/Encargado, Módulo de RRHH), que existe
   al menos un marcador `[INSERTAR CAPTURA: ...]` con descripción específica (no genérica tipo
   "captura de pantalla"). → Verifica **SC-002**.

4. **Comparar los tres diagramas** contra la tabla de estados y el diagrama ASCII de
   `.specify/memory/constitution.md` (sección "FSM - Estados y transiciones del ticket") y contra
   los resúmenes de `specs/022-rrhh-calendario-sla-dinamico` y
   `specs/023-historial-sla-reasignacion`: los nombres de estado, rol y trigger deben coincidir
   exactamente (sin sinónimos ni renombres). → Verifica **SC-003** y **FR-012**.

5. **Buscar un caso de error común** (ej. `Ctrl+F "no veo el botón Reasignar"` o "el SLA no
   avanza") y confirmar que existe un bloque de nota/advertencia dedicado con la explicación,
   ubicable sin leer el documento completo. → Verifica **SC-004**.

6. **Revisar el renderizado general**: encabezados jerárquicos correctos (`#`/`##`/`###` sin saltos
   de nivel), tablas Markdown bien formadas (separador `|---|` con al menos 3 guiones), y ausencia
   de HTML roto o rutas de imagen locales inválidas. → Verifica **SC-005**.

7. **(Opcional, fuera de esta sesión)** Convertir el Markdown a `.docx`/PDF con la herramienta
   disponible en ese momento (ej. Pandoc, o la skill de manejo de documentos Word) y confirmar
   visualmente que la conversión no rompe tablas ni diagramas. Este paso no es parte del entregable
   de esta feature (ver Assumptions en spec.md) pero sirve como prueba de que el formato Markdown
   elegido es realmente "listo para exportar".

## Resultado esperado

Todos los pasos 1-6 deben pasar sin ajustes adicionales al documento. Si algún paso falla, corregir
directamente `docs/Manual_de_Usuario.md` (no el código de la aplicación) y repetir el paso fallido.
