# Research: Actualización Integral del Manual de Usuario

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

No quedaron marcadores `[NEEDS CLARIFICATION]` en la especificación (ver
[checklists/requirements.md](checklists/requirements.md)). Este documento registra las decisiones
de enfoque tomadas para pasar de la spec al diseño del manual, con su justificación y alternativas
descartadas.

## Decisión 1: Formato de salida — Markdown en vez de edición directa del `.docx`

- **Decision**: El entregable de esta feature es `docs/Manual_de_Usuario.md`, escrito en
  GitHub-Flavored Markdown con bloques ` ```mermaid ` para los diagramas y tablas Markdown estándar.
  La actualización del binario `docs/Manual_de_Usuario.docx` existente se deja como paso posterior
  (conversión manual o con la skill de manejo de documentos Word), fuera del alcance de esta sesión.
- **Rationale**: Esta sesión es 100% de documentación y no incluye herramientas de edición binaria
  de `.docx` en su flujo de trabajo estándar. Un archivo Markdown estructurado con encabezados
  jerárquicos, tablas y fences de diagrama es directamente convertible a Word/PDF (Pandoc,
  Word "Abrir Markdown", o la skill `docx`) sin pérdida de estructura.
- **Alternatives considered**:
  - *Editar el `.docx` directamente*: descartado — no hay una herramienta fiable en esta sesión para
    edición binaria incremental de Word conservando estilos existentes sin riesgo de corromper el
    archivo.
  - *Generar HTML*: descartado — Word/PDF a partir de Markdown es un flujo más simple y ya usado en
    el resto de la documentación del proyecto (`specs/*.md`, `docs/MER.md`).

## Decisión 2: Sintaxis y alcance de los diagramas Mermaid

- **Decision**: Los tres diagramas requeridos se expresan como `flowchart` (ciclo de vida del
  Ticket y regla de SLA) y `flowchart`/`sequenceDiagram`-like para la aprobación de vacaciones,
  reutilizando exactamente los nombres de estado y rol de la Constitución (sección "FSM - Estados y
  transiciones del ticket") para que no haya divergencia terminológica.
- **Rationale**: Mermaid es texto plano versionable, se renderiza nativamente en GitHub/VS
  Code/Artifacts, y es "convertible/exportable" como pide el requerimiento original sin depender de
  una herramienta gráfica externa.
- **Alternatives considered**:
  - *Diagramas como imágenes estáticas (PNG/Draw.io)*: descartado — no son editables como texto ni
    versionables de forma legible en diffs, y el usuario pidió explícitamente "diagramas en formato
    Mermaid (convertibles/exportables)".
  - *PlantUML*: descartado — no es el estándar ya usado en el resto del repositorio; Mermaid es
    soportado nativamente por más visores sin plugin adicional.

## Decisión 3: Fuente de verdad para el ciclo de vida del Ticket y el SLA

- **Decision**: El diagrama de ciclo de vida y la explicación de pausa/reanudación de SLA se
  derivan directamente de la tabla de estados y del diagrama ASCII de
  `.specify/memory/constitution.md` (sección FSM) y de los resúmenes de las specs `022-rrhh-...`
  (motor de SLA dinámico) y `023-historial-sla-reasignacion` (indicadores ✅/⚠️/❌), sin inspeccionar
  el código fuente del backend.
- **Rationale**: La Constitución es la fuente de verdad declarada del proyecto y ya contiene el
  catálogo completo de estados, triggers y campos bloqueados; usarla evita una lectura masiva de
  `backend/domain/` que violaría la restricción de "lectura eficiente" del alcance de esta sesión.
- **Alternatives considered**:
  - *Leer el motor SLA y el FSM en `backend/domain/`*: descartado como fuente primaria — más preciso
    a nivel de código pero fuera del alcance permitido (sesión de solo documentación) y redundante,
    ya que la Constitución resume exactamente esas reglas para consumo de agentes y humanos.

## Decisión 4: Alcance de pantallas a documentar en la guía paso a paso

- **Decision**: Se documentan las 6 vistas explícitamente pedidas por el usuario (Dashboard, Kanban,
  Mis Tareas, Detalle de Ticket, Vista del Cliente/Encargado, Módulo de RRHH), confirmadas como
  existentes en `frontend/src/pages/` (`DashboardPage.tsx`, `KanbanPage.tsx`, `MyTasksPage.tsx`,
  `TicketDetailPage.tsx`, `ClientContactsPage.tsx`/vista de Encargado, `CalendarPage.tsx` +
  `AbsenceRequestsPage.tsx` + `WorkHourTemplatesPage.tsx` para RRHH). El resto de páginas existentes
  (Roles y Permisos, Catálogos, Reportes de Tiempo, etc.) queda fuera del alcance explícito de esta
  actualización y puede añadirse en una iteración futura del manual.
- **Rationale**: Cumple el requerimiento original sin expandir el alcance ("no refactorizaciones ni
  inserciones fuera de lo solicitado", Principio VII); solo se listó el nombre de archivo de cada
  página para confirmar que existe, sin leer su implementación completa.
- **Alternatives considered**:
  - *Documentar absolutamente todas las pantallas del sistema*: descartado — excede lo pedido
    explícitamente por el usuario y multiplicaría el consumo de tokens sin que se haya solicitado.

## Decisión 5: Convención para marcadores de captura de pantalla

- **Decision**: Formato uniforme `[INSERTAR CAPTURA: <descripción específica de qué debe verse>]`,
  colocado inmediatamente después del párrafo que describe la acción/pantalla correspondiente, uno
  por sub-sección relevante (no uno solo por vista completa cuando la vista tiene múltiples estados
  visuales relevantes, ej. Kanban en vista de tablero vs. tarjeta expandida).
- **Rationale**: Coincide con el formato de ejemplo dado por el usuario
  (`[INSERTAR CAPTURA: Detalle de Ticket con historial de SLA]`) y es fácilmente buscable
  (`Ctrl+F "INSERTAR CAPTURA"`) para quien deba completar las imágenes reales después.
- **Alternatives considered**:
  - *Comentarios HTML (`<!-- TODO screenshot -->`)*: descartado — no es visible al leer el Markdown
    renderizado, y el usuario pidió marcadores "explícitos".
