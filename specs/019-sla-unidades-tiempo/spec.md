# Feature Specification: Unidades de tiempo (minutos/horas/días) al configurar SLA

**Feature Branch**: `019-sla-unidades-tiempo`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "el SLA debe tener la opcion de poner horas y dias, actualmente esta
solo en minutos, por usabilidad no es factible, aunque internamente fuera solo minutos, debe tener
la opciones para no digitar tantos minutos"

**Revisión 2026-07-15**: El usuario acotó el alcance en una segunda entrada: el selector de unidad
(horas/días) aplica **únicamente** al campo "Tiempo límite de diagnóstico, análisis y ejecución"
— el campo "Tiempo límite de contacto" (típicamente 15 min, ver `docs/SLAv1.xlsx`) queda sin
cambios, solo en minutos, porque nunca alcanza magnitudes de horas/días. El pedido reitera que es
"solo diseño y usabilidad" y que "NO es necesario ajustar toda la estructura": el almacenamiento,
el contrato de API y el motor de cómputo de SLA (spec 014) permanecen intactos; el sistema
convierte lo que el usuario ingrese a minutos para su manejo interno.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configurar el tiempo límite de diagnóstico/análisis/ejecución en la unidad más cómoda (Priority: P1)

Como Admin o Coordinador, quiero ingresar el tiempo límite de diagnóstico/análisis/ejecución de una
regla de SLA eligiendo la unidad que me resulte más natural (minutos, horas o días), para no tener
que calcular ni digitar valores en minutos crudos (p. ej. 7200 minutos para "5 días"). El campo de
tiempo de contacto no se ve afectado: sigue siendo un ingreso simple en minutos.

**Why this priority**: Es el problema de usabilidad concreto que motiva la mejora — sin esto, el
Admin sigue obligado a convertir mentalmente días/horas a minutos cada vez que crea una regla.

**Independent Test**: Puede probarse completamente creando una regla de SLA nueva, ingresando el
tiempo de diagnóstico/análisis/ejecución como "5" con unidad "días", y verificando que la regla se
guarda con el mismo tiempo límite (en minutos) que si se hubiera ingresado "7200" con unidad
"minutos".

**Acceptance Scenarios**:

1. **Given** el formulario de alta de una regla de SLA, **When** el Admin selecciona la unidad
   "horas" e ingresa "8" en el campo de tiempo de diagnóstico/análisis/ejecución, **Then** la regla
   se guarda con un tiempo límite equivalente a 480 minutos.
2. **Given** el formulario de alta de una regla de SLA, **When** el Admin selecciona la unidad
   "días" e ingresa "5" en el mismo campo, **Then** la regla se guarda con un tiempo límite
   equivalente a 7200 minutos (5 × 24h).
3. **Given** el formulario de alta de una regla de SLA, **When** el Admin ingresa "15" en el campo
   de tiempo de contacto, **Then** el comportamiento es idéntico al actual (input de solo minutos,
   sin selector de unidad), sin ninguna regresión.
4. **Given** el Admin ingresó un valor en el campo de diagnóstico/análisis/ejecución y luego cambia
   la unidad seleccionada (p. ej. de "minutos" a "horas"), **When** el cambio de unidad ocurre,
   **Then** el valor mostrado se recalcula a la nueva unidad conservando el mismo tiempo total, en
   vez de reinterpretarse como un número distinto de minutos.

---

### User Story 2 - Editar una regla de SLA existente sin convertir mentalmente el valor (Priority: P2)

Como Admin o Coordinador, quiero que al abrir una regla de SLA ya creada, el tiempo límite de
diagnóstico/análisis/ejecución se muestre en una unidad legible (no siempre en minutos), para
entender de un vistazo cuánto tiempo representa sin tener que dividir mentalmente entre 60 o 1440.
El campo de tiempo de contacto se sigue mostrando en minutos, sin cambios.

**Why this priority**: Complementa la Historia 1 — de nada sirve poder crear reglas en horas/días
si al reabrirlas para editarlas el sistema vuelve a mostrar el valor en minutos crudos.

**Independent Test**: Puede probarse abriendo para editar una regla existente cuyo tiempo límite
guardado equivale a un número exacto de horas o días, y verificando que el formulario la presenta
en esa unidad (no en minutos) con el valor numérico correcto, permitiendo cambiar la unidad
libremente antes de guardar.

**Acceptance Scenarios**:

1. **Given** una regla de SLA guardada con tiempo límite de 480 minutos, **When** el Admin abre el
   formulario de edición, **Then** el campo muestra "8" con unidad "horas" (o una presentación
   igualmente legible), no "480" con unidad "minutos".
2. **Given** una regla de SLA guardada con un tiempo límite que no es múltiplo exacto de 60 (p. ej.
   135 minutos), **When** el Admin abre el formulario de edición, **Then** el campo muestra el
   valor en la unidad "minutos" (la única que lo representa sin residuo), evitando mostrar una
   fracción confusa de horas.
3. **Given** el formulario de edición ya abierto con una unidad mostrada, **When** el Admin cambia
   la unidad sin modificar el valor y guarda, **Then** el tiempo límite persistido no cambia
   respecto al que tenía la regla antes de abrir el formulario.

---

### Edge Cases

- ¿Qué pasa si el Admin ingresa un valor fraccionario en horas o días (p. ej. "1.5" horas, "2.5"
  días)? El sistema debe convertirlo a minutos redondeando al minuto entero más cercano, y debe
  seguir aplicando la validación existente de que el resultado sea mayor a 0.
- ¿Qué pasa si la conversión a minutos da como resultado un valor no entero por errores de
  redondeo de punto flotante (p. ej. 0.1 horas)? El sistema redondea al minuto entero más cercano
  antes de guardar, igual que en el caso anterior.
- ¿Qué pasa con las reglas de SLA creadas antes de este cambio (ya almacenadas en minutos)? Siguen
  funcionando sin migración de datos: el valor almacenado no cambia, solo cambia cómo se presenta y
  se edita en el formulario.
- ¿Qué pasa si el Admin selecciona "días" y digita "0"? Se rechaza igual que hoy se rechaza "0"
  minutos (regla vigente: el tiempo límite debe ser mayor a 0 tras la conversión a minutos).
- ¿Qué pasa con el cómputo del contador de SLA ya en curso para tickets existentes (spec
  014-sla-tickets-tareas)? No cambia: el motor de cómputo sigue operando en minutos exactamente
  igual que hoy; esta funcionalidad solo afecta cómo el Admin ingresa/lee el valor en el
  formulario.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El formulario de alta/edición de una regla de SLA DEBE permitir elegir la unidad de
  entrada (minutos, horas o días) exclusivamente para el campo "Tiempo límite de diagnóstico,
  análisis y ejecución". El campo "Tiempo límite de contacto" NO cambia: sigue siendo un ingreso
  simple en minutos, sin selector de unidad.
- **FR-002**: El sistema DEBE convertir el valor ingresado en la unidad seleccionada a minutos antes
  de guardar la regla, sin modificar el modelo de datos, el contrato de la API ni el cómputo de SLA
  existente (que continúa operando exclusivamente en minutos, ver spec
  014-sla-tickets-tareas/FR-001).
- **FR-003**: Al cambiar la unidad seleccionada del campo de diagnóstico/análisis/ejecución con un
  valor ya ingresado, el sistema DEBE recalcular el valor mostrado a la nueva unidad conservando el
  mismo tiempo total (equivalente en minutos), en vez de reinterpretar el número tal cual en la
  nueva unidad.
- **FR-004**: El sistema DEBE seguir validando que el tiempo límite resultante, una vez convertido a
  minutos, sea un entero mayor a 0 — independientemente de la unidad usada para la entrada.
- **FR-005**: El sistema DEBE aceptar valores fraccionarios en horas y días (p. ej. 1.5 horas, 2.5
  días) en el campo de diagnóstico/análisis/ejecución y convertirlos a minutos redondeando al
  minuto entero más cercano.
- **FR-006**: Al editar una regla de SLA existente, el sistema DEBE presentar el valor guardado del
  campo de diagnóstico/análisis/ejecución (siempre almacenado en minutos) en la unidad más grande
  que lo representa sin residuo (días si es múltiplo exacto de 1440, si no horas si es múltiplo
  exacto de 60, si no minutos), permitiendo cambiar la unidad libremente antes de guardar.
- **FR-007**: El cambio DEBE limitarse a la capa de entrada y presentación del campo de
  diagnóstico/análisis/ejecución del formulario de reglas de SLA — el almacenamiento, el contrato
  de API y el motor de cómputo de SLA (contador, pausas, vencimientos) permanecen sin cambios, y no
  se ajusta ninguna otra parte de la estructura existente.

### Key Entities *(include if feature involves data)*

- **Regla de SLA** *(existente, spec 014-sla-tickets-tareas)*: sin cambios en su modelo de datos;
  sus dos tiempos límite (`contact_minutes`, `execution_minutes`) se siguen almacenando en minutos.
  Esta funcionalidad solo cambia cómo el formulario captura y presenta esos valores.
- **Unidad de tiempo de entrada**: estado transitorio de la interfaz (minutos / horas / días)
  asociado a cada campo del formulario mientras el usuario lo completa; no se persiste como parte
  de la regla.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El Admin puede configurar el tiempo límite de la Prioridad "Baja" (5 días,
  equivalente a 7200 minutos) ingresando el número "5" y seleccionando la unidad "días", sin
  digitar ni calcular manualmente el valor en minutos.
- **SC-002**: El 100% de las reglas de SLA creadas antes de este cambio siguen mostrando y
  calculando el mismo tiempo límite en minutos después de la mejora, sin requerir migración de
  datos ni reintroducción manual de valores.
- **SC-003**: El Admin puede alternar la unidad (minutos/horas/días) del campo de
  diagnóstico/análisis/ejecución tantas veces como quiera antes de guardar, sin que el tiempo
  límite equivalente en minutos se altere por el simple cambio de unidad.
- **SC-004**: El Admin puede completar el campo de diagnóstico/análisis/ejecución de una regla de
  SLA en menos tiempo y con menos dígitos a teclear que con el método actual de solo minutos, para
  cualquiera de las combinaciones de Prioridad definidas en `docs/SLAv1.xlsx`.

## Assumptions

- El almacenamiento y el cómputo interno del SLA siguen siendo en minutos enteros; no se modifica
  `sla_rule_model`, `sla_service`, el contrato de la API (`contracts/sla-contract.md` de la spec
  014) ni el motor de contador/pausas ya implementado — el alcance de esta funcionalidad es
  exclusivamente la capa de entrada/presentación del campo `execution_minutes` en
  `SlaRuleForm`/`SlaRulesPage`. No se ajusta ninguna otra parte de la estructura existente,
  incluido el campo `contact_minutes` (tiempo de contacto), que permanece como un ingreso simple en
  minutos.
- Las unidades ofrecidas son minutos, horas y días. No se agregan semanas ni meses por no tener
  caso de uso en `docs/SLAv1.xlsx` (los valores de referencia más grandes son "5 días hábiles").
- El campo de tiempo de contacto no necesita selector de unidad porque en `docs/SLAv1.xlsx` su
  único valor de referencia es fijo y pequeño (15 minutos, sin variar por Prioridad); si en el
  futuro se necesitara expresarlo en horas/días, sería una extensión posterior fuera de este
  alcance.
- Un "día" se sigue tratando como 24 horas corridas para efectos de conversión (mismo criterio ya
  documentado en las Assumptions de la spec 014-sla-tickets-tareas para Prioridad Media/Baja), no
  como día hábil — esta funcionalidad no introduce calendarios de negocio.
- El redondeo de conversiones fraccionarias (horas/días con decimales) a minutos se hace al minuto
  entero más cercano; no se agregan unidades más finas que el minuto.
- El listado de reglas de SLA (`SlaRulesPage`) puede seguir mostrando los tiempos en su unidad más
  legible existente; el foco principal de esta mejora es el formulario de alta/edición donde hoy se
  obliga a digitar minutos crudos.
