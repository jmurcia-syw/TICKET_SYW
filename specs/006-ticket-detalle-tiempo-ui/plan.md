# Implementation Plan: Refactorización visual y de navegación del detalle del Ticket (flujo tipo Teamwork)

**Branch**: `develp_Jp` (sin rama dedicada por feature en este repo) | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-ticket-detalle-tiempo-ui/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Reorganizar el detalle del Ticket (y agregar la pantalla "Mis Tareas") para consolidar el registro
de tiempo en un modal enfocado en vez de una tabla siempre visible, mostrar fecha de
inicio/estimado/real con un indicador de color de consumo, y dejar lista la navegación (más un
mecanismo real de filtros guardados compartidos entre "Tickets" y "Mis Tareas") para la futura
organización por listas/subtareas. Es una funcionalidad **100% frontend**: reutiliza endpoints y
datos que ya existen (`work_sessions`, `estimated_resolution_minutes`, `ticketService.list`,
`resourceService.me()`) — no requiere migraciones, endpoints nuevos ni cambios de esquema.

## Technical Context

**Language/Version**: TypeScript 5 (strict) sobre React 19, sin cambios de versión.

**Primary Dependencies**: Ant Design 5 (`Modal`, `Segmented`, `Statistic`, `Table`), Zustand 5
(`persist` middleware — ya usado en `authStore.ts`), React Router 6. Ninguna dependencia nueva
(Principio V de la constitución).

**Storage**: N/A para datos de negocio (no hay migraciones). Los filtros guardados se persisten en
`localStorage` del navegador vía `zustand/middleware persist`, igual que ya hace `authStore`.

**Testing**: El frontend no tiene suite de tests automatizados configurada (no hay Vitest/Jest en
`package.json`); la validación es `npx tsc -b` (typecheck) + verificación manual guiada por
`quickstart.md`, igual que en Fase 2.1. No aplica pytest porque no se toca el backend.

**Target Platform**: Navegador web (misma SPA existente), responsive (desktop + mobile/tablet ya
soportado por el layout `Row`/`Col` de Ant Design).

**Project Type**: Web application (frontend + backend ya detectados) — esta funcionalidad solo
toca `frontend/`.

**Performance Goals**: Sin objetivo nuevo de performance; la transición de revelado fluido debe
sentirse instantánea (animación CSS corta, sin bloquear la interacción, en línea con el resto de
la UI ya existente).

**Constraints**: Sin cambios de contrato de API ni de base de datos (ver Assumptions del spec).
Debe respetar el alcance mínimo pedido explícitamente por el usuario: solo los archivos
estrictamente necesarios, sin refactors masivos, y sin ejecutar la suite completa de tests durante
la implementación.

**Scale/Scope**: 2 pantallas existentes modificadas (`TicketDetailPage`, `TicketsPage`), 1
pantalla nueva (`MyTasksPage`/"Mis Tareas"), ~4-5 componentes nuevos o refactorizados de UI.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (API-First / Dominio primero)**: N/A para esta funcionalidad — no se toca
  dominio ni se agregan endpoints; toda la lógica que se necesita ya está expuesta por la API
  existente. **PASS**.
- **Principio II (Clean Architecture 3 capas)**: Los cambios viven exclusivamente en
  `frontend/src/{pages,components,store,services}`; los componentes de presentación siguen siendo
  "tontos" (reciben datos de `services/` ya existentes); la única pieza de estado nuevo
  (`savedFiltersStore`) es un store de Zustand, igual patrón que `authStore`. **PASS**.
- **Principio III (Tipado estricto)**: Todo el código nuevo en TypeScript strict, sin `any`.
  **PASS**.
- **Principio IV (Seguridad en profundidad)**: Sin cambios de autenticación/autorización; se
  reutilizan los permisos ya vigentes (`work_sessions:manage`, `tickets:view`/`view_own`) para
  decidir modo lectura/escritura. Los filtros guardados solo contienen criterios de búsqueda (no
  datos sensibles) y se guardan client-side. **PASS**.
- **Principio V (Gobernanza de librerías)**: No se agrega ninguna dependencia nueva; se reutiliza
  Ant Design y Zustand (`persist`, ya presente en el proyecto). **PASS**.
- **Principio VI (AI-Native)**: No aplica — no hay endpoints de acción crítica ni datos de
  entrenamiento involucrados en este cambio puramente de presentación. **PASS**.

**Resultado**: Sin violaciones. No se requiere entrada en "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/006-ticket-detalle-tiempo-ui/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No se genera carpeta `contracts/`: esta funcionalidad no agrega ni modifica ningún endpoint de
API (ver Constitution Check, Principio I) — todos los datos se obtienen de servicios ya existentes
(`workSessionService`, `ticketService`, `resourceService`).

### Source Code (repository root)

Proyecto tipo "Web application" ya establecido (`backend/` + `frontend/`). Esta funcionalidad solo
toca `frontend/src/`:

```text
frontend/src/
├── pages/
│   ├── TicketDetailPage.tsx        # MODIFICADO: reordena layout (resumen de tiempo → comentarios
│   │                                # → actividad), fecha de inicio + indicador de consumo,
│   │                                # placeholder de lista/subtareas, integra el modal de tiempo
│   ├── TicketsPage.tsx             # MODIFICADO: integra la barra de filtros guardados
│   └── MyTasksPage.tsx             # NUEVO: pantalla "Mis Tareas" (arranca con "Asignado a mí")
├── components/
│   ├── tickets/
│   │   └── SavedFiltersBar.tsx     # NUEVO: seleccionar/guardar/eliminar filtros guardados,
│   │                                # compartido entre TicketsPage y MyTasksPage
│   └── worksessions/
│       ├── TicketWorkSessions.tsx  # MODIFICADO: pasa de tabla siempre visible a resumen
│       │                            # compacto (totales + indicador) que abre el modal
│       ├── TimeLogModal.tsx        # NUEVO: modal único con histórico + alta/edición/borrado
│       │                            # (reemplaza el uso de WorkSessionForm como modal aparte
│       │                            # dentro del flujo del ticket)
│       └── WorkSessionForm.tsx     # MODIFICADO MÍNIMO: soporta modo embebido (sin su propio
│                                    # `<Modal>` envolvente) para usarse dentro de TimeLogModal;
│                                    # WorkSessionsPage.tsx sigue usándolo como hoy (modal propio)
├── store/
│   └── savedFiltersStore.ts        # NUEVO: Zustand + persist (mismo patrón que authStore.ts)
├── config/
│   └── navigation.tsx              # MODIFICADO: agrega entrada de menú "Mis Tareas"
└── App.tsx                          # MODIFICADO: agrega ruta `/my-tasks`
```

**Structure Decision**: Se mantiene la estructura ya vigente del proyecto
(`pages/`, `components/`, `store/`, `services/`, `types/`). No se crean carpetas nuevas de primer
nivel; los componentes nuevos van dentro de los directorios de dominio ya existentes
(`components/tickets/`, `components/worksessions/`). No hay cambios en `backend/`.

## Complexity Tracking

*Sin violaciones de la Constitution Check — tabla no aplica.*
