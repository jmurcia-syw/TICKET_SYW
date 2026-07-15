---

description: "Task list for Unidades de tiempo (minutos/horas/días) al configurar SLA"

---

# Tasks: Unidades de tiempo (minutos/horas/días) al configurar SLA

**Input**: Design documents from `specs/019-sla-unidades-tiempo/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [quickstart.md](./quickstart.md)

**Tests**: No solicitadas explícitamente en el spec ni por el usuario, y el frontend no tiene suite
de tests configurada (Principio VII de la constitución) — no se generan tareas de test.

**Organization**: Tareas agrupadas por historia de usuario (US1 = P1, US2 = P2) para permitir
implementación y validación independiente de cada una.

## Path Conventions

Proyecto tipo "Web application" ya establecido. Esta funcionalidad toca **únicamente**:
- `frontend/src/components/sla/SlaRuleForm.tsx`
- `frontend/src/pages/SlaRulesPage.tsx`

Ningún archivo de `backend/` ni `frontend/src/types/sla.ts` cambia (ver plan.md, Scale/Scope).

---

## Phase 1: Setup

**Purpose**: Confirmar el punto de partida antes de modificar el formulario existente.

- [X] T001 Confirmado que no se requiere ninguna dependencia nueva (Principio V de la
  constitución): `InputNumber`, `Select` y `Space.Compact` de Ant Design 5.24 ya están
  disponibles y `SlaRuleFormData` no necesitó cambios de shape.

**Checkpoint**: Baseline confirmado, sin dependencias nuevas que aprobar.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura compartida que ambas historias de usuario necesitan antes de
implementarse.

**⚠️ CRITICAL**: Ninguna historia de usuario puede completarse sin esta fase.

- [X] T002 [P] Agregado, dentro de `frontend/src/components/sla/SlaRuleForm.tsx` (helpers a nivel
  de módulo, sin archivo nuevo — alcance mínimo del plan.md), el tipo `TimeUnit = 'minutes' |
  'hours' | 'days'` y dos funciones puras: `unitToMinutes(amount, unit)` (redondeando con
  `Math.round`, factores 1/60/1440 — ver data-model.md) y `minutesToDisplayUnit(minutes)` (regla
  de "unidad más grande sin residuo": días si `% 1440 === 0`, si no horas si `% 60 === 0`, si no
  minutos — ver research.md Decisión 2).
- [X] T003 [P] En `frontend/src/pages/SlaRulesPage.tsx`, agregado el estado `formResetToken`
  (número), incrementado en `openCreate` y en `openEdit`, y pasado como prop `key` a
  `<SlaRuleForm key={formResetToken} .../>` (research.md Decisión 4), para forzar que el
  componente reinicialice su estado local de unidad/monto cada vez que se abre el modal.

**Checkpoint**: Helpers de conversión y mecanismo de reinicialización listos — ambas historias
pueden implementarse.

---

## Phase 3: User Story 1 - Configurar el tiempo límite de diagnóstico/análisis/ejecución en la unidad más cómoda (Priority: P1) 🎯 MVP

**Goal**: Al crear una regla de SLA nueva, el campo "Tiempo límite de diagnóstico, análisis y
ejecución" acepta un monto + unidad (minutos/horas/días) y guarda el equivalente exacto en
minutos. El campo de contacto no cambia.

**Independent Test**: Crear una regla de SLA nueva ingresando "5" con unidad "días" en el campo de
diagnóstico/análisis/ejecución y verificar que se guarda con el mismo tiempo límite (7200 minutos)
que si se hubiera ingresado "7200" con unidad "minutos".

### Implementation for User Story 1

- [X] T004 [US1] En `frontend/src/components/sla/SlaRuleForm.tsx`, el `Form.Item
  name="execution_minutes"` conserva su `name`/`rules`, pero su hijo pasa a ser un componente
  compuesto nuevo `ExecutionTimeInput` (controlado vía `value`/`onChange` inyectados por
  `Form.Item`, igual que cualquier otro control) que renderiza, con `Space.Compact`, un
  `InputNumber` (monto) y un `Select` (unidad, opciones minutos/horas/días, default `'minutes'`);
  reemplazada la etiqueta fija "(minutos)". *(Ajuste sobre el diseño original de research.md: se
  descartó la variante de `Form.Item hidden` porque suprime también el mensaje de validación —
  ver research.md Decisión 1 actualizada.)*
- [X] T005 [US1] Dentro de `ExecutionTimeInput`, los `onChange` del `InputNumber` y del `Select`
  calculan `unitToMinutes(amount, unit)` (helper de T002) e invocan el `onChange` recibido de
  `Form.Item` con el resultado, conservando las reglas de validación existentes (`required`,
  `min: 1` sobre el valor en minutos). Verificado en navegador: con el campo vacío el envío marca
  "Requerido" en Proyecto/Prioridad/Contacto pero **no** en este campo tras ingresar un monto
  válido — confirma que `Form.Item` recibe el valor en minutos correctamente.
- [X] T006 [US1] Dentro de `ExecutionTimeInput.handleUnitChange`, al cambiar la unidad con un
  monto ya ingresado se recalcula el monto mostrado a partir del total de minutos vigente (no se
  reinterpreta el número tal cual en la nueva unidad) — Acceptance Scenario 4 de la Historia 1.
  Verificado en navegador: "5" con unidad "minutos" → cambiar a "días" mostró "0.003472222..."
  (5/1440, redondeable a 5 minutos exactos al reconvertir), confirmando que se preserva el tiempo
  total en vez de reinterpretar el número.
- [X] T007 [US1] Verificación de regresión (sin cambio de código esperado): confirmado que
  `Form.Item name="contact_minutes"` en `frontend/src/components/sla/SlaRuleForm.tsx` sigue siendo
  un único `InputNumber` en minutos, sin selector de unidad (FR-001).

**Checkpoint**: Historia 1 completamente funcional — se puede crear una regla de SLA en
minutos/horas/días de forma independiente.

---

## Phase 4: User Story 2 - Editar una regla de SLA existente sin convertir mentalmente el valor (Priority: P2)

**Goal**: Al abrir una regla de SLA existente para editar, el campo de diagnóstico/análisis/
ejecución muestra el valor guardado en la unidad más legible (no siempre minutos), permitiendo
cambiar la unidad libremente antes de guardar.

**Independent Test**: Abrir para editar una regla con 480 minutos guardados y verificar que el
campo muestra "8" con unidad "horas" (no "480" con unidad "minutos"); repetir con 7200 minutos
("5" días) y con 135 minutos ("135" minutos, sin fracción de horas).

### Implementation for User Story 2

- [X] T008 [US2] Dentro de `ExecutionTimeInput`, el estado local `unit`/`amount` se inicializa (vía
  `useState` con inicializador basado en el `value` recibido al montar) a partir del valor vigente
  de `execution_minutes` usando `minutesToDisplayUnit` (helper de T002); en modo alta
  (`execution_minutes` vacío) inicializa en unidad `'minutes'` con monto vacío, igual que el
  comportamiento anterior al cambio.
- [X] T009 [P] [US2] En `frontend/src/pages/SlaRulesPage.tsx`, confirmado que `formResetToken` (de
  T003) se incrementa tanto en `openCreate` como en `openEdit`, disparando el remount (y por tanto
  la reinicialización de T008) en cada apertura del modal sin arrastrar el estado de la apertura
  anterior.
- [X] T010 [US2] Confirmado por inspección de `ExecutionTimeInput.handleUnitChange`: si `amount`
  es `null` (nada ingresado) el cambio de unidad solo actualiza el estado visual sin invocar
  `onChange`; si hay un monto, el `onChange` emitido corresponde al mismo total de minutos
  (recalculado, no reinterpretado) — no se dispara ninguna escritura que altere el valor
  persistido cuando el usuario solo cambia la unidad de visualización.

**Checkpoint**: Ambas historias (US1 y US2) funcionan de forma independiente y en conjunto.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verificación final, sin afectar el alcance de ninguna historia individual.

- [X] T011 [P] Ejecutado `npx tsc -b` dentro de `frontend/`: cero errores en los archivos tocados
  (`SlaRuleForm.tsx`, `SlaRulesPage.tsx`). Persisten errores preexistentes no relacionados
  (`RichTextEditor.tsx`, `RichTextViewer.tsx`, `ClientsPage.tsx` por dependencias no instaladas en
  este entorno) — fuera de alcance de esta sesión (Principio VII).
- [~] T012 Recorrido parcial de `specs/019-sla-unidades-tiempo/quickstart.md` en el navegador
  (stack Docker real, tras reiniciar `sywork_frontend` por HMR obsoleto): se confirmó el
  Escenario 4 (cambio de unidad preserva el valor total: 5 min → 0.003472 días, round-trip
  exacto) y la integración con la validación del Form (Escenario 6, vía T005). Los escenarios que
  requieren completar el `Select` de Proyecto/Prioridad (1, 2, 3, 5, 7) no pudieron ejecutarse en
  esta sesión por una limitación del tooling de automatización del navegador (los clics sobre esos
  `Select` — ya existentes, no tocados por este cambio — dejaron de registrarse de forma
  consistente tras varios paneles abiertos superpuestos); no se detectó ningún indicio de que sea un
  defecto del código. Recomendado repetir el recorrido completo manualmente o en una sesión de
  navegador fresca antes de dar el feature por validado end-to-end.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — puede iniciar de inmediato.
- **Foundational (Phase 2)**: Depende de Setup. Bloquea ambas historias de usuario.
- **User Story 1 (Phase 3)**: Depende de Foundational (T002, T003). Sin dependencia de US2.
- **User Story 2 (Phase 4)**: Depende de Foundational (T002, T003) y reutiliza la UI creada en
  US1 (T004-T006) — en la práctica se implementa después de US1 porque comparte el mismo bloque
  de código del formulario, pero es una historia conceptualmente independiente (afecta solo el
  camino de "editar", no el de "crear").
- **Polish (Phase 5)**: Depende de que US1 y US2 estén completas.

### Parallel Opportunities

- T002 y T003 (Foundational) tocan archivos distintos y pueden hacerse en paralelo.
- T009 (US2, `SlaRulesPage.tsx`) puede hacerse en paralelo a T008/T010 (US2, `SlaRuleForm.tsx`) —
  archivos distintos.
- T011 (typecheck) no depende de T012 (validación manual) y puede correr en paralelo.
- El resto de tareas de US1 (T004-T007) son secuenciales por tocar el mismo archivo y depender
  unas de otras.

---

## Parallel Example: Foundational

```bash
# Lanzar juntas las dos tareas de la Fase 2 (archivos distintos):
Task: "Agregar helpers de conversión de unidad en frontend/src/components/sla/SlaRuleForm.tsx"
Task: "Agregar formResetToken/key en frontend/src/pages/SlaRulesPage.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Fase 1: Setup.
2. Completar Fase 2: Foundational (helpers de conversión + mecanismo de `key`).
3. Completar Fase 3: Historia 1 (crear reglas en minutos/horas/días).
4. **DETENER y VALIDAR**: probar la Historia 1 de forma independiente (Escenarios 1-4 de
   quickstart.md).
5. Esto ya resuelve el problema de usabilidad principal reportado por el usuario.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. Historia 1 (P1) → validar de forma independiente → es el MVP.
3. Historia 2 (P2) → validar de forma independiente (Escenarios 5-7 de quickstart.md).
4. Fase de Polish → typecheck + recorrido completo de quickstart.md.

---

## Notes

- [P] = archivos distintos, sin dependencia entre sí.
- [US1]/[US2] = trazabilidad a la historia de usuario correspondiente del spec.md.
- Ambas historias tocan mayormente el mismo archivo (`SlaRuleForm.tsx`); por eso casi todas las
  tareas de implementación son secuenciales dentro de cada historia.
- Sin tareas de test (no solicitadas, sin suite de frontend configurada) — la validación es
  `npx tsc -b` + los escenarios de `quickstart.md` (T011, T012).
- Confirmar cada checkpoint antes de avanzar a la siguiente fase.
