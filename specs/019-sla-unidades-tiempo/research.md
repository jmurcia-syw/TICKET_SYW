# Research: Unidades de tiempo (minutos/horas/días) al configurar SLA

Todas las incógnitas de esta funcionalidad se resolvieron por inspección directa del código
existente (`SlaRuleForm.tsx`, `SlaRulesPage.tsx`, `types/sla.ts`) — no requirió investigación
externa. Se documentan aquí las decisiones y sus alternativas descartadas.

## Decisión 1 — `execution_minutes` sigue siendo la fuente de verdad, vía un control compuesto

- **Decision**: `Form.Item name="execution_minutes"` se mantiene exactamente igual (mismo `name`,
  mismas `rules`), pero su hijo deja de ser un `InputNumber` plano y pasa a ser un componente
  controlado nuevo, `ExecutionTimeInput` (definido a nivel de módulo dentro del propio
  `SlaRuleForm.tsx`, sin archivo nuevo), que agrupa un `InputNumber` (monto) y un `Select` (unidad:
  minutos/horas/días) con `Space.Compact`. Ant Design le inyecta `value`/`onChange` a
  `ExecutionTimeInput` igual que a cualquier otro control de `Form.Item`: `value` llega en minutos
  (el valor real del campo) y `onChange` reporta minutos hacia el `Form` — la conversión
  monto↔unidad↔minutos vive enteramente dentro del componente.
- **Rationale**: Es el cambio de menor superficie posible (`SlaRuleFormData`, `onFinish`,
  `slaService`, el contrato de API y el backend no se enteran de que existió una unidad distinta a
  minutos — cumple "puedes convertir todo lo que ingrese el usuario en minutos para tu manejo",
  "NO es necesario ajustar toda la estructura") y evita el problema de UX de una alternativa más
  simple (ver abajo): al mantener `Form.Item` visiblemente renderizado (con su control compuesto
  como único hijo), los mensajes de validación (`required`, `min: 1`) se siguen mostrando en su
  lugar habitual, justo debajo del campo.
- **Alternatives considered**:
  - Ocultar el `Form.Item name="execution_minutes"` original (`hidden`) y agregar el
    `InputNumber`+`Select` como controles sueltos, sincronizados a mano con
    `form.setFieldValue` — descartado tras detectar que `hidden` también suprime el
    `validateStatus`/mensaje de error del campo, dejando errores de validación invisibles para el
    usuario (regresión de UX que el propio cambio busca evitar).
  - Cambiar `SlaRuleFormData.execution_minutes` por una estructura `{ amount, unit }` y convertir
    en `SlaRulesPage.handleSubmit` — descartado: propaga el cambio a un tipo compartido
    (`types/sla.ts`) sin necesidad, cuando el problema es puramente de entrada en un componente.
  - Convertir en el backend (aceptar unidad en el endpoint) — descartado explícitamente por el
    usuario y por FR-002/FR-007 del spec: el backend/API no cambian.

## Decisión 2 — Regla de "unidad más grande sin residuo" al editar (FR-006)

- **Decision**: Al abrir el formulario para editar una regla existente, se deriva la unidad y el
  monto a mostrar a partir de `execution_minutes` con esta prioridad: si es múltiplo exacto de
  1440 (minutos por día) → unidad "días"; si no, si es múltiplo exacto de 60 → unidad "horas"; si
  no → unidad "minutos" con el valor tal cual. Ejemplo: 7200 → "5" días; 480 → "8" horas; 135 →
  "135" minutos.
- **Rationale**: Es la lectura más legible sin inventar fracciones (evita mostrar "2.25 horas"
  para 135 minutos, que sería más confuso que "135 minutos"), cumpliendo FR-006 y el Acceptance
  Scenario 2 de la Historia 2 del spec.
- **Alternatives considered**: Guardar la unidad usada al crear la regla (requeriría un campo
  nuevo en el modelo de datos) — descartado: viola el alcance "no ajustar toda la estructura" y no
  es necesario porque la regla de "unidad más grande sin residuo" ya da una representación
  determinística y legible sin persistir nada adicional.

## Decisión 3 — Redondeo de conversiones fraccionarias (FR-005)

- **Decision**: `minutos = Math.round(monto * factorDeUnidad)`, con `factorDeUnidad` = 1
  (minutos), 60 (horas) o 1440 (días). Se aplica `Math.round` (no `Math.floor`/`Math.ceil`) para no
  sesgar sistemáticamente el tiempo límite hacia abajo o hacia arriba.
- **Rationale**: Simple, predecible, y consistente con que el dominio de SLA (`sla_service.py`)
  espera un entero de minutos — no se introduce ninguna unidad más fina que el minuto (spec,
  Assumptions).
- **Alternatives considered**: Rechazar valores fraccionarios que no den un entero exacto de
  minutos — descartado: es más restrictivo de lo que pidió el usuario ("no digitar tantos
  minutos"); 1.5 horas (90 min exactos) y 2.5 días (3600 min exactos) ya son válidos sin redondeo,
  y los pocos casos con residuo (p. ej. 0.03 horas) son edge cases raros mejor resueltos con
  redondeo que con un error bloqueante.

## Decisión 4 — Reinicialización del estado local de unidad/monto al abrir el formulario

- **Decision**: `SlaRulesPage.tsx` mantiene un contador de estado `formResetToken` (número),
  incrementado tanto en `openCreate` como en `openEdit`, y lo pasa como prop `key` a
  `<SlaRuleForm key={formResetToken} .../>`. Esto fuerza a React a desmontar/remontar
  `SlaRuleForm` cada vez que se abre el modal (para crear o para editar una regla distinta),
  permitiendo que el estado local de unidad/monto se inicialice limpio a partir del valor vigente
  de `execution_minutes` en ese momento (0 controles previos que "arrastren" un estado de la
  apertura anterior). El `Form` (instancia de `Form.useForm()`) sigue viviendo en `SlaRulesPage` y
  no se pierde con el remount del hijo.
- **Rationale**: Es la solución de menor complejidad para un problema conocido de Ant Design +
  estado local no controlado por el Form: sin un remount explícito, un `useEffect` tendría que
  distinguir "el usuario está escribiendo" de "el formulario se acaba de abrir para otra regla",
  lo que añade complejidad no justificada para un formulario de 2 campos.
- **Alternatives considered**: `useEffect` con `Form.useWatch('execution_minutes', form)` que
  re-derive unidad/monto cada vez que el valor observado cambie "desde afuera" — descartado:
  requiere una bandera adicional para no pisar lo que el propio usuario está tipeando (el mismo
  `setFieldValue` interno también dispararía el watch), complejidad evitable con la estrategia de
  `key`.

## Decisión 5 — El campo de contacto no cambia

- **Decision**: `Form.Item name="contact_minutes"` permanece exactamente igual (un único
  `InputNumber` en minutos, sin selector de unidad).
- **Rationale**: Alcance explícito del spec (FR-001): el problema de usabilidad real está en el
  campo de diagnóstico/análisis/ejecución (puede llegar a 7200 min); el de contacto es un valor
  fijo y pequeño (15 min en `docs/SLAv1.xlsx`) que no lo necesita.
- **Alternatives considered**: Aplicar el mismo selector a ambos campos por consistencia visual —
  descartado explícitamente por el usuario en su segunda entrada de `/speckit-specify`.

**Output**: Todas las incógnitas del Technical Context quedaron resueltas; no quedan
`NEEDS CLARIFICATION` pendientes para el diseño de Fase 1.
