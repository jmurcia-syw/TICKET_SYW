# Data Model: Unidades de tiempo (minutos/horas/días) al configurar SLA

Esta funcionalidad no crea ni modifica ninguna tabla, columna ni entidad de dominio en el backend.
Todo lo descrito a continuación son **conceptos de estado de cliente (view-model)**, internos a
`SlaRuleForm.tsx`, que nunca se persisten ni viajan al backend.

## Entidad ya existente (sin cambios de esquema)

### Regla de SLA (`SlaRule` / `sla_rules`, spec 014-sla-tickets-tareas)

Sin cambios de campos. Sigue almacenando y exponiendo, en minutos enteros:

| Campo | Tipo | Notas |
|-------|------|-------|
| `contact_minutes` | `number` (entero) | Tiempo límite de contacto. Sin cambios — esta funcionalidad no lo toca. |
| `execution_minutes` | `number` (entero) | Tiempo límite de diagnóstico/análisis/ejecución. Sigue siendo la única representación persistida; el formulario ahora ofrece una entrada alternativa (horas/días) que se convierte a este mismo campo antes de guardar. |

`SlaRuleFormData` (`frontend/src/types/sla.ts`) **no cambia**: sigue siendo
`{ project_id, priority, contact_minutes: number, execution_minutes: number }`.

## Conceptos derivados (estado de cliente, no persistidos)

### Unidad de tiempo de entrada (`TimeUnit`)

Estado local de `SlaRuleForm.tsx`, existe solo mientras el formulario está abierto:

| Campo | Tipo | Notas |
|-------|------|-------|
| `unit` | `'minutes' \| 'hours' \| 'days'` | Unidad actualmente seleccionada para el campo de diagnóstico/análisis/ejecución. Default `'minutes'` al crear; derivada del valor guardado al editar (ver regla abajo). |
| `amount` | `number \| null` | Monto mostrado en el `InputNumber`, expresado en `unit`. Puede ser fraccionario (p. ej. `1.5` con `unit = 'hours'`). |

**Conversión a minutos** (única dirección que persiste, vía `form.setFieldValue`):

| Unidad | Factor a minutos | Ejemplo |
|--------|-------------------|---------|
| `minutes` | × 1 | `15` → `15` |
| `hours` | × 60 | `8` → `480` |
| `days` | × 1440 (24h × 60min) | `5` → `7200` |

`minutos = Math.round(amount * factor)` (ver research.md Decisión 3). Se valida `minutos > 0`
(misma regla ya vigente en `contact_minutes`/`execution_minutes`).

**Derivación al editar** (única dirección para prellenar la UI, ver research.md Decisión 2), a
partir del `execution_minutes` guardado:

```
si execution_minutes % 1440 == 0 → unit = 'days',   amount = execution_minutes / 1440
si no, execution_minutes % 60 == 0 → unit = 'hours',  amount = execution_minutes / 60
si no                              → unit = 'minutes', amount = execution_minutes
```

## Sin cambios

- **Regla de SLA**: modelo, contrato de API y motor de cómputo (`sla_service.py`) — sin cambios
  (spec FR-002/FR-007).
- **Campo de contacto (`contact_minutes`)**: sigue siendo un ingreso simple en minutos, sin unidad
  seleccionable (spec FR-001).
