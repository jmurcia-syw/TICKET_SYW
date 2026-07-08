# Tasks: Refactorización visual y de navegación del detalle del Ticket (flujo tipo Teamwork)

**Input**: Design documents from `specs/006-ticket-detalle-tiempo-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: No solicitados explícitamente en el spec (el frontend tampoco tiene suite automatizada
configurada — ver plan.md, Technical Context). No se generan tareas de test; la validación es
`npx tsc -b` + los escenarios manuales de `quickstart.md`.

**Organización**: Tareas agrupadas por User Story para implementación y validación independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] modal de tiempo, [US2] fecha de inicio + consumo, [US3] Mis Tareas + filtros
  guardados, [US4] premisa visual de listas/subtareas

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): Ant Design 5
  (`Modal`, `Segmented`, `Statistic`) y Zustand 5 con `persist` (ya usado en
  `frontend/src/store/authStore.ts`) alcanzan para toda la funcionalidad; sin cambios en
  `frontend/package.json` ni en `backend/requirements.txt` (ver research.md Decisiones 2 y 3)

**Checkpoint**: sin cambios de dependencias.

---

## Phase 2: Foundational

**Nota**: las 4 historias son mayormente independientes entre sí — US1/US2 tocan el detalle del
ticket (`TicketDetailPage`, `TicketWorkSessions`), US3 es un store nuevo + una pantalla nueva +
`TicketsPage`, y US4 es un agregado visual sobre lo que dejen US1 y US3. No hay una base de datos,
migración ni entidad de backend compartida que bloquee a todas (esta funcionalidad no toca
`backend/`, ver plan.md). No se listan tareas foundational forzadas; cada historia arranca
directamente en su propia fase, con las dependencias inter-historia anotadas explícitamente abajo.

---

## Phase 3: User Story 1 — Registro de tiempo en modal, con revelado fluido (P1) 🎯 MVP

**Goal**: reemplazar la tabla de tiempo siempre visible por un resumen compacto que abre un modal
único (historial + alta/edición/borrado); al cerrarlo, revelar en un solo flujo el resumen de
tiempo, los comentarios y la actividad del ticket. **Independent Test**: Escenario 1 del
quickstart.

- [X] T002 [P] [US1] `frontend/src/components/worksessions/WorkSessionForm.tsx`: agregar prop
  opcional `embedded?: boolean` — cuando es `true`, renderizar solo el `<Form>` interno sin su
  `<Modal>` envolvente; comportamiento por defecto (con `<Modal>` propio) sin cambios para no
  romper `frontend/src/pages/WorkSessionsPage.tsx`, que sigue invocándolo igual que hoy (ver
  research.md Decisión 5)
- [X] T003 [US1] Nuevo `frontend/src/components/worksessions/TimeLogModal.tsx`: modal único que
  combina el histórico de tiempo del ticket (misma consulta que hoy usa `TicketWorkSessions`,
  `workSessionService.list({ ticket_id })`) con `WorkSessionForm` en modo `embedded` (T002) para
  alta/edición; borrado con las mismas reglas de ventana de 7 días y permiso
  `work_sessions:manage` ya vigentes (depende de T002)
- [X] T004 [US1] `frontend/src/components/worksessions/TicketWorkSessions.tsx`: reemplazar la
  tabla siempre visible por un resumen compacto (`Statistic` de total registrado + acción
  "Registrar tiempo" que abre `TimeLogModal` de T003); usuarios sin `work_sessions:manage` ven el
  resumen en modo solo lectura, sin la acción de abrir el modal (FR-010) (depende de T003)
- [X] T005 [US1] `frontend/src/pages/TicketDetailPage.tsx`: reordenar el layout para que, debajo
  del resumen de tiempo (T004), comentarios y actividad (`Historial de estados`, hoy en la
  columna lateral) queden en un único flujo visual consolidado en ese orden — mover la tarjeta de
  actividad fuera de la columna lateral hacia el flujo principal, debajo de comentarios (depende
  de T004)
- [X] T006 [US1] `frontend/src/pages/TicketDetailPage.tsx`: agregar el comportamiento de
  revelado/colapso fluido (estado booleano + `transition` CSS de `max-height`/`opacity`, sin
  dependencia nueva — ver research.md Decisión 2): colapsa al cerrar `TimeLogModal`, se revela de
  nuevo con scroll hacia arriba desde comentarios/actividad; preservar el comportamiento existente
  de `TicketBreadcrumb`/"Volver a..." sin cambios (FR-011) (depende de T005)

**Checkpoint US1**: Escenario 1 del quickstart ejecutable end-to-end.

---

## Phase 4: User Story 2 — Fecha de inicio y consumo estimado vs. real (P2)

**Goal**: mostrar fecha de inicio (derivada del primer registro de tiempo), tiempo estimado y
total real, con un indicador de color de consumo. **Independent Test**: Escenario 2 del
quickstart.

- [X] T007 [P] [US2] `frontend/src/types/workSession.ts`: agregar helpers puros
  `earliestWorkDate(sessions)` (fecha del registro más antiguo, o `null` si no hay ninguno) y
  `getConsumptionLevel(estimatedMinutes, actualMinutes)` → `'success' | 'warning' | 'error' |
  'none'` según los umbrales de research.md Decisión 6 (<80% / 80–100% / >100% / sin estimado)
- [X] T008 [US2] `frontend/src/components/worksessions/TicketWorkSessions.tsx`: calcular y
  exponer (props/callback hacia `TicketDetailPage`) `startDate` y `consumptionLevel` usando los
  helpers de T007 sobre los mismos `work_sessions` ya cargados (sin fetch adicional) (depende de
  T007, T004)
- [X] T009 [US2] `frontend/src/pages/TicketDetailPage.tsx`: mostrar "Fecha de inicio" (o "Aún sin
  iniciar" si `startDate` es `null`) y el indicador de color de consumo junto a "Tiempo estimado
  de solución", usando los tokens ya existentes (`colorSuccess`/`colorWarning`/`colorError` de
  `theme.ts`) (depende de T008)

**Checkpoint US2**: Escenario 2 del quickstart completo.

---

## Phase 5: User Story 3 — "Mis Tareas" con filtros guardados (P3)

**Goal**: pantalla nueva "Mis Tareas" (arranca con "Asignado a mí") + mecanismo de filtros
guardados compartido con "Tickets". **Independent Test**: Escenario 3 del quickstart.

- [X] T010 [P] [US3] Nuevo `frontend/src/store/savedFiltersStore.ts`: Zustand + `persist` (mismo
  patrón que `frontend/src/store/authStore.ts`), namespaced por `userId` de `useAuthStore`;
  preset `builtIn: true` "Asignado a mí" no eliminable (FR-015); `addFilter` rechaza nombres
  duplicados del mismo usuario (FR-016); `removeFilter` bloqueado para presets `builtIn` (ver
  data-model.md, Filtro guardado)
- [X] T011 [US3] Nuevo `frontend/src/components/tickets/SavedFiltersBar.tsx`: UI para
  seleccionar/aplicar/guardar/eliminar filtros de `savedFiltersStore` (T010); al aplicar el
  preset "Asignado a mí", resuelve el `assignee_id` en runtime vía `resourceService.me()` (mismo
  patrón que `frontend/src/pages/WorkSessionsPage.tsx:52`), no un valor guardado (depende de T010)
- [X] T012 [US3] `frontend/src/pages/TicketsPage.tsx`: integrar `SavedFiltersBar` (T011) en
  `PageToolbar`, conectando "guardar filtro actual" / "aplicar filtro guardado" con el estado de
  filtros local ya existente de la pantalla (depende de T011)
- [X] T013 [US3] Nuevo `frontend/src/pages/MyTasksPage.tsx`: reutiliza `ticketService.list` +
  `resourceService.me()` (mismo patrón que `WorkSessionsPage.tsx`) para mostrar por defecto los
  tickets asignados al usuario actual; integra `SavedFiltersBar` (T011) igual que `TicketsPage`
  (T012) (depende de T011)
- [X] T014 [P] [US3] `frontend/src/config/navigation.tsx`: agregar entrada de menú "Mis Tareas"
  (`key: '/my-tasks'`, módulo `tickets`, mismas acciones `['view', 'view_own']` que "Tickets")
- [X] T015 [US3] `frontend/src/App.tsx`: agregar ruta `/my-tasks` → `MyTasksPage` (T013) envuelta
  en `ProtectedRoute` con el mismo `requiredPermission` que la ruta `/tickets` (depende de T013,
  T014)

**Checkpoint US3**: Escenario 3 del quickstart completo.

---

## Phase 6: User Story 4 — Premisa visual de listas y subtareas (P4)

**Goal**: dejar un lugar visual reservado (sin lógica) para listas/subtareas en el detalle del
ticket y en "Mis Tareas". **Independent Test**: Escenario 4 del quickstart.

- [X] T016 [US4] `frontend/src/pages/TicketDetailPage.tsx`: agregar un indicio visual informativo
  de "lista" (p. ej. `Descriptions.Item` o `Tag`, sin control funcional) y un espacio "Subtareas —
  Próximamente" con el mismo lenguaje visual que las tarjetas placeholder de "SLA"/"Sesión de
  trabajo (Focus Room)" ya existentes (depende de T005)
- [X] T017 [US4] `frontend/src/pages/MyTasksPage.tsx`: agregar un elemento visual (encabezado o
  nota) que sugiera el futuro agrupamiento por listas, sin implicar funcionalidad real (depende de
  T013)

**Checkpoint US4**: Escenario 4 del quickstart completo — las 4 historias funcionan
independientemente.

---

## Phase 7: Polish y validación transversal

- [X] T018 [P] Ejecutar `cd frontend && npx tsc -b` (typecheck completo — no es la suite de tests,
  es el build check habitual) y corregir cualquier error de tipos introducido por T002-T017 —
  sin errores
- [ ] T019 Ejecutar `quickstart.md` (Escenarios 1-5) contra el entorno real (Docker o `pnpm dev`
  con backend en Docker): confirmar los 4 escenarios de historia + el escenario 5 de regresión
  (permiso de solo lectura en tiempo, `WorkSessionsPage.tsx` sin cambios de comportamiento, resto
  de `TicketDetailPage.tsx` sin regresiones)

**Checkpoint Final**: quickstart completo en verde, sin regresión en Fases 0-2.1, sin ejecutar la
suite completa de tests del proyecto (directriz explícita del usuario — ver spec.md, Assumptions).

---

## Dependencies & Execution Order

```
Phase 1 (T001) → Phase 3/US1 (T002 → T003 → T004 → T005 → T006)
US1 (T004) → Phase 4/US2 (T007∥ → T008 → T009)
Phase 1 → Phase 5/US3 (T010∥ → T011 → {T012, T013}∥; T014∥ → T015)
US1 (T005) + US3 (T013) → Phase 6/US4 (T016, T017 — independientes entre sí)
Todo → Phase 7 (T018∥, T019)
```

- US1 es el MVP; US2 depende de US1 (agrega fecha/consumo al mismo resumen que crea T004).
- US3 es independiente de US1/US2 (store + pantalla + integración de filtros propios).
- US4 depende de que T005 (layout final del detalle) y T013 (pantalla "Mis Tareas") ya existan,
  para tener dónde colocar el indicio visual — no depende de la lógica de ninguna de las dos.

## Parallel Example: User Story 1

```bash
# T002 (WorkSessionForm embebido) es independiente y puede arrancar de inmediato:
Task: "frontend/src/components/worksessions/WorkSessionForm.tsx — prop embedded"  # T002

# T003, T004, T005, T006 son secuenciales (cada uno depende del anterior) dentro de US1
```

## Parallel Example: User Story 3

```bash
# En paralelo desde el inicio de la fase:
Task: "Store frontend/src/store/savedFiltersStore.ts"          # T010
Task: "Nav frontend/src/config/navigation.tsx"                  # T014

# Tras T010:
Task: "SavedFiltersBar frontend/src/components/tickets/SavedFiltersBar.tsx"  # T011

# Tras T011, en paralelo entre sí:
Task: "Integrar en TicketsPage.tsx"   # T012
Task: "Nueva MyTasksPage.tsx"         # T013
```

---

## Implementation Strategy

1. **MVP = Phase 1 + US1**: modal de tiempo + revelado fluido, funcionando end-to-end.
2. Incrementos independientes: US2 (fecha/consumo, requiere US1 ya en pantalla) → US3 (Mis
   Tareas + filtros guardados, independiente) → US4 (premisa visual, requiere US1 y US3 ya
   construidos) — en ese orden por prioridad, aunque US3 podría adelantarse en paralelo a US1/US2
   por ser independiente.
3. Cada checkpoint valida su escenario del quickstart antes de avanzar.
4. Alcance estrictamente acotado a los archivos listados arriba (directriz explícita del
   usuario): sin refactors fuera de estos archivos, sin dependencias nuevas, sin correr la suite
   completa de tests durante la implementación.

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- [Story] mapea la tarea a su user story para trazabilidad
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
