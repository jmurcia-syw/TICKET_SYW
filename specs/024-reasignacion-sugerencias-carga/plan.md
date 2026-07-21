# Implementation Plan: Sugerencias de Carga y Disponibilidad en la Reasignación

**Branch**: `024-reasignacion-sugerencias-carga` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/024-reasignacion-sugerencias-carga/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Dar a `ReassignModal` (spec 023) las mismas ayudas visuales que ya tiene `AssignModal` (Triage
Push, spec 010/020): carga actual por candidato, orden por menor carga, indicador "Menor carga"
y etiqueta de no disponibilidad (fuera de horario/festivo/ausencia), sin bloquear la reasignación.
Se extrae la lógica de obtención (`useResourceCandidates`) y el grid de tarjetas de candidato
(`ResourceCandidateGrid`) de `AssignModal` a piezas compartidas, y `ReassignModal` las reutiliza
en vez de duplicar la lógica o quedarse con el `Select` plano actual.

## Technical Context

**Language/Version**: TypeScript strict / React 19 (frontend), sin cambios de versión.

**Primary Dependencies**: Ant Design 5 (`Select` reemplazado por el mismo patrón de grid de
tarjetas que ya usa `AssignModal`), Axios vía los servicios existentes — sin dependencias nuevas
(Principio V).

**Storage**: N/A — no hay cambios de esquema ni de backend; se reutilizan tal cual los tres
endpoints ya usados por `AssignModal` (`GET /api/resources`, `GET /api/tickets/panel` vía
`ticketService.panel()`, `GET` de disponibilidad vía `calendarService.getAvailability()`).

**Testing**: Sin suite de tests frontend nueva (cambio de UI/UX puro, sin lógica de negocio
nueva); se valida manualmente en navegador contra Docker real, igual que se hizo para spec 023.

**Target Platform**: Web app (Docker Compose on-premise), sin cambios.

**Project Type**: Web application — cambio exclusivamente en `frontend/`, el backend no se toca.

**Performance Goals**: Sin requisitos nuevos; mismas tres llamadas ya usadas por `AssignModal`
por apertura de modal (recursos activos, panel de carga, disponibilidad).

**Constraints**: NO se modifica ningún endpoint de backend ni el flujo de `/assign` o
`/reassign` (spec 023) — el alcance es 100% de presentación/UI. NO se introduce un directorio
`hooks/` nuevo a nivel de proyecto (fuera de la convención de estructura de la Constitución);
el hook compartido se coloca junto a sus dos únicos consumidores en `components/tickets/`.

**Scale/Scope**: 2 componentes existentes tocados (`AssignModal.tsx` refactorizado para no
duplicar lógica, `ReassignModal.tsx` actualizado), 2 archivos nuevos y pequeños (`useResourceCandidates.ts`,
`ResourceCandidateGrid.tsx`), ambos colocados en `frontend/src/components/tickets/`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. API-First**: ✅ No aplica — no se agregan ni modifican endpoints; se reutilizan los tres
  ya documentados en Swagger para la asignación inicial.
- **II. Clean Architecture**: ✅ La lógica de obtención/combinación de datos (carga +
  disponibilidad) vive en un hook de datos (`useResourceCandidates`), no en los componentes de
  presentación; `ResourceCandidateGrid` sigue el principio de "componentes tontos" (solo recibe
  props y renderiza), igual que el resto de `frontend/src/components/`.
- **III. Tipado estricto**: ✅ Sin `any`; se reutilizan los tipos `Resource`, `Availability`,
  `AvailabilityReason` ya existentes.
- **IV. Seguridad en profundidad**: ✅ No aplica — no hay cambios de autenticación, autorización
  ni de datos sensibles; mismas llamadas ya autorizadas que usa la asignación inicial.
- **V. Gobernanza de librerías**: ✅ Cero dependencias nuevas.
- **VI. AI-Native**: ✅ No aplica — no se toca el endpoint de acción (`/reassign`) ni el Gold
  Standard Dataset; es una mejora puramente de presentación sobre datos ya existentes.
- **VII. Alcance y tokens**: ✅ Cambio acotado a `frontend/src/components/tickets/`; sin tests
  backend nuevos (no hay lógica de dominio nueva); sin ejecutar suites completas.
- **Gate de gobernanza explícito**: El refactor de `AssignModal.tsx` es *preservador de
  comportamiento* (mismo UX, misma data) — no es la clase de refactor "no solicitado" que el
  Principio VII prohíbe, porque es un prerrequisito directo para cumplir FR-001 a FR-004 de esta
  spec ("las mismas sugerencias... como la asignación inicial") sin duplicar lógica.

Sin violaciones. No aplica tabla de Complexity Tracking.

**Re-chequeo post-diseño (Fase 1)**: `data-model.md`/`quickstart.md` confirman que no se tocó
ningún endpoint ni modelo de datos — solo se reorganizó código frontend existente en piezas
reutilizables. Gates siguen en verde.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/src/components/tickets/
├── AssignModal.tsx                 # refactor: usa useResourceCandidates + ResourceCandidateGrid
├── ReassignModal.tsx               # actualizado: reemplaza el Select plano por el mismo grid
├── ResourceCandidateGrid.tsx       # NUEVO — grid de tarjetas "tonto" (carga, Menor carga,
│                                    #   etiqueta de no disponibilidad), extraído de AssignModal
└── useResourceCandidates.ts        # NUEVO — hook de datos: resources + workload + availability
                                     #   (mismas 3 llamadas que ya hacía AssignModal)
```

**Structure Decision**: Web application ya establecida (frontend React + backend Flask). Esta
feature es exclusivamente frontend: no agrega proyectos ni capas nuevas, solo extrae una pieza de
datos (`useResourceCandidates.ts`) y una de presentación (`ResourceCandidateGrid.tsx`) dentro del
directorio ya existente `frontend/src/components/tickets/`, para que `AssignModal` y
`ReassignModal` compartan exactamente la misma lógica de carga/disponibilidad en vez de
duplicarla — sin crear un directorio `hooks/` a nivel de proyecto, fuera de la convención actual.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
