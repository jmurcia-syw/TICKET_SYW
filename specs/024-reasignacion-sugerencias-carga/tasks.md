# Tasks: Sugerencias de Carga y Disponibilidad en la Reasignación

**Input**: Design documents from `specs/024-reasignacion-sugerencias-carga/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md)

**Tests**: Sin tests automatizados nuevos — feature 100% frontend de presentación, sin lógica de
dominio backend nueva (Principio VII, research.md Decisión 2). La validación es manual, guiada
por `quickstart.md`, más `tsc -b --noEmit` para tipos.

**Organización**: `useResourceCandidates.ts` y `ResourceCandidateGrid.tsx` son prerequisito
compartido real de ambas historias (research.md Decisión 1) — van en Foundational. US1 y US2
reutilizan exactamente esas dos piezas ya integradas en `ReassignModal.tsx`; US2 se apoya en el
mismo punto de integración que US1 porque el grid muestra carga y disponibilidad en la misma
tarjeta (igual que ya hace `AssignModal`), así que sus tareas se centran en la exclusión del
resolutor actual y la verificación específica de la etiqueta de disponibilidad.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1 o US2
- Todas las descripciones incluyen la ruta de archivo exacta

---

## Phase 1: Foundational (prerrequisito compartido de US1 y US2)

**Purpose**: Extraer de `AssignModal.tsx` las dos piezas que ambas historias reutilizan, sin
cambiar su comportamiento actual (research.md Decisión 1).

**⚠️ CRITICAL**: Ninguna historia puede integrarse en `ReassignModal.tsx` hasta que este grupo
esté completo y `AssignModal.tsx` siga funcionando igual que antes.

- [X] T001 [P] Crear `frontend/src/components/tickets/useResourceCandidates.ts` — hook que combina `resourceService.list({active:true, page_size:100})`, `ticketService.panel()` (mapa `resource.id -> total`) y `calendarService.getAvailability()` (mapa `resource_id -> Availability`), devolviendo `{resources, workload, availability}`; misma lógica que hoy vive inline en el `useEffect` de `AssignModal.tsx`
- [X] T002 [P] Crear `frontend/src/components/tickets/ResourceCandidateGrid.tsx` — componente "tonto" (props: `resources`, `workload`, `availability`, `selected`, `onSelect`, `search`) que renderiza el grid de tarjetas clicables con nombre, skills, barra de carga coloreada, badge "Menor carga" y etiqueta de no disponibilidad (fuera de horario/festivo/ausencia); extraído tal cual del JSX actual de `AssignModal.tsx` (líneas ~132-199)
- [X] T003 Refactorizar `frontend/src/components/tickets/AssignModal.tsx` para usar `useResourceCandidates` (T001) y `ResourceCandidateGrid` (T002) en vez de su lógica/JSX inline, preservando el mismo comportamiento visual (búsqueda, orden por menor carga, badges) — depende de T001, T002

**Checkpoint**: `AssignModal` sigue funcionando igual que antes del refactor (verificar
manualmente: abrir "Asignar (Triage)" en un ticket sin asignar, confirmar que carga, orden,
badge "Menor carga" y etiquetas de disponibilidad se ven igual que antes de T003).

---

## Phase 2: User Story 1 - Ver carga de trabajo al reasignar (Priority: P1) 🎯 MVP

**Goal**: El selector de reasignación muestra la carga de cada candidato, ordenado de menor a
mayor, con el candidato de menor carga marcado — igual que la asignación inicial.

**Independent Test**: Abrir "Reasignar" en un ticket asignado y verificar que el selector
muestra carga por candidato, orden ascendente y badge "Menor carga" (quickstart.md Escenario 1).

- [X] T004 [US1] En `frontend/src/components/tickets/ReassignModal.tsx`, reemplazar el `Select` plano por `useResourceCandidates` (T001) + `ResourceCandidateGrid` (T002), pasando como `resources` la lista ya filtrada para excluir `currentAssigneeId` (regla existente de spec 023), y conservando el campo de motivo y el flujo de envío (`ticketService.reassign`) sin cambios — depende de T001, T002, T003
- [X] T005 [US1] Validar manualmente contra Docker real: quickstart.md Escenario 1 (carga visible, orden ascendente, badge "Menor carga" en `ReassignModal`) — depende de T004

**Checkpoint**: US1 completa y verificable de forma independiente.

---

## Phase 3: User Story 2 - Ver disponibilidad al reasignar (Priority: P2)

**Goal**: El selector de reasignación muestra la etiqueta de no disponibilidad (fuera de
horario/festivo/ausencia) por candidato, sin bloquear la reasignación — igual que la asignación
inicial.

**Independent Test**: Con un candidato actualmente no disponible, abrir "Reasignar" y verificar
que se muestra la etiqueta con el motivo correcto, y que reasignar hacia ese candidato igual
se completa (quickstart.md Escenario 2).

- [X] T006 [US2] Confirmar en `frontend/src/components/tickets/ReassignModal.tsx` que el filtro que excluye `currentAssigneeId` (T004) se aplica sobre `resources` antes de pasarlo a `ResourceCandidateGrid`, de modo que los mapas `workload`/`availability` (ya indexados por `resource_id`) seguidos siguen resolviendo correctamente para los candidatos restantes — depende de T004
- [X] T007 [US2] Validar manualmente contra Docker real: quickstart.md Escenario 2 (etiqueta de no disponibilidad visible con el motivo correcto, y la reasignación hacia ese candidato se completa igual, sin bloqueo) — depende de T006

**Checkpoint**: US1 y US2 funcionan de forma independiente y en conjunto.

---

## Final Phase: Polish & Validación

- [X] T008 [P] Ejecutar `npx tsc -b --noEmit` (frontend) para confirmar que el refactor de `AssignModal.tsx` y la integración en `ReassignModal.tsx` no rompen tipos
- [X] T009 Comparación visual final en navegador: el mismo Recurso muestra la misma carga y el mismo estado de disponibilidad tanto en "Asignar (Triage)" como en "Reasignar" para el mismo ticket/momento

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: Sin dependencias externas — BLOQUEA ambas historias.
- **User Story 1 (Phase 2)**: Depende de Foundational (T001-T003) completo.
- **User Story 2 (Phase 3)**: Depende de T004 (US1) — reutiliza el mismo punto de integración en `ReassignModal.tsx`, ya que el grid muestra carga y disponibilidad en la misma tarjeta.
- **Polish (Final Phase)**: Depende de que US1 y US2 estén completas.

### Parallel Opportunities

- T001 y T002 en paralelo (archivos distintos, sin dependencia entre sí).
- T008 puede correr en paralelo con T009 una vez ambas historias estén integradas.

---

## Parallel Example: Foundational

```bash
Task: "Crear useResourceCandidates.ts en frontend/src/components/tickets/useResourceCandidates.ts"
Task: "Crear ResourceCandidateGrid.tsx en frontend/src/components/tickets/ResourceCandidateGrid.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1: Foundational (T001-T003) — `AssignModal` sin regresión.
2. Completar Phase 2: User Story 1 (T004-T005) — carga visible en `ReassignModal`.
3. **STOP y VALIDAR**: quickstart.md Escenario 1.

### Incremental Delivery

1. Foundational + US1 → demo (MVP: carga visible al reasignar).
2. US2 → demo (disponibilidad visible al reasignar, no bloqueante).

### Alcance explícitamente fuera de esta feature

- No se toca ningún endpoint de backend ni el modelo de datos.
- No se crea un directorio `hooks/` a nivel de proyecto (research.md Decisión 1).
- No se agregan tests automatizados backend (no hay lógica de dominio nueva).
