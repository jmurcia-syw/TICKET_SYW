# Data Model: SLAs por Proyecto y Prioridad

Modelo revisado 2026-07-14 según `docs/SLAv1.xlsx` (única fuente real de tiempos objetivo): 2
fases medibles (Contacto / Diagnóstico-Análisis-Ejecución), reglas keyed por Proyecto+Prioridad
sin jerarquía de fallback.

## Entidad: `SlaRule` (tabla `sla_rules`)

Regla configurable de tiempos límite, por Proyecto. Corresponde a la Historia 1 (FR-001, FR-002,
FR-013).

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID (PK) | |
| `project_id` | UUID (FK `projects.id`), **NOT NULL** | El SLA siempre se define a nivel de Proyecto (no hay regla global ni solo-por-cliente). |
| `priority` | enum (`critical`, `high`, `medium`, `low`) | Reutiliza `PRIORITIES` de `backend/domain/entities/ticket.py`. Obligatorio. Corresponde a la columna "Severidad" de `docs/SLAv1.xlsx`. |
| `contact_minutes` | int | Tiempo límite de la fase "Contacto". > 0. Valor sugerido del Excel: 15 min para todas las prioridades, pero editable por proyecto. |
| `execution_minutes` | int | Tiempo límite de la fase "Diagnóstico, Análisis y Ejecución". > 0. Valores sugeridos del Excel por prioridad: Crítica 60, Alta 480, Media 2880 (2d×24h), Baja 7200 (5d×24h) — ver Assumptions del spec sobre "días hábiles". |
| `active` | bool | Default `true`. Desactivar en vez de borrar (edge case: tickets en curso conservan su límite ya asignado). |
| `created_at` / `updated_at` | timestamp | |

**Restricción de unicidad**: `(project_id, priority)` único — evita reglas duplicadas para la
misma combinación exacta.

**Sin fallback**: a diferencia del diseño anterior, no existe una regla "solo por prioridad" que
aplique cuando falta la fila específica del proyecto. Si `(project_id, priority)` no tiene fila
activa, el ticket queda en `sin_sla` (FR-002, FR-003).

## Extensión de `Ticket` (columnas nuevas en `tickets`, tabla ya existente)

Aplican únicamente a registros con `record_type_id` = "Ticket" (FR-012, clarificación
2026-07-14). Tareas y Subtareas comparten la misma tabla/columnas pero el motor de SLA no las
calcula ni las popula en esta fase — `sla_rule_id`/`sla_phase` quedan `NULL` para ellas por
diseño, no por defecto accidental. Es una extensión posible de una fase futura.

| Campo | Tipo | Notas |
|-------|------|-------|
| `sla_rule_id` | UUID (FK `sla_rules.id`), nullable | Regla resuelta para el `project_id`+`priority` vigente del ticket; se re-resuelve si cambia Proyecto o Prioridad (FR-011). `NULL` = sin SLA configurado. |
| `sla_phase` | enum (`contacto`, `ejecucion`, `cerrado`), nullable | Fase de SLA vigente. `NULL` = sin SLA. `cerrado` = ambas fases terminaron (ticket en RESUELTO/CERRADO/CANCELADO). |
| `sla_phase_limit_minutes` | int, nullable | Tiempo límite de la fase **vigente** (`contact_minutes` o `execution_minutes` de la regla), congelado al entrar a la fase para no verse afectado si la regla se edita después. |
| `sla_consumed_seconds` | int | Default 0. Acumulado de tiempo en la fase vigente únicamente — se reinicia a 0 al pasar de fase (Contacto → Ejecución), porque cada fase mide un objetivo distinto. |
| `sla_last_resume_at` | timestamp, nullable | Momento desde el que se sigue sumando tiempo real en la fase vigente. `NULL` si el contador está pausado o detenido. |
| `sla_status` | enum (`sin_sla`, `corriendo`, `pausado`, `vencido`, `detenido`) | Derivado, pero persistido para poder filtrar/ordenar el listado sin recalcular en cada fila (FR-008, FR-009). Se refiere a la fase vigente (o `detenido` cuando `sla_phase='cerrado'`). |
| `sla_contact_result` | enum (`pendiente`, `cumplido`, `vencido`), nullable | Snapshot congelado del resultado de la fase "Contacto" una vez superada (FR-007) — no se recalcula al avanzar de fase. `NULL` mientras la fase Contacto sigue vigente o si no hay SLA. |
| `sla_contact_consumed_seconds` | int, nullable | Snapshot del tiempo consumido en la fase Contacto al momento de cerrarla (histórico, para mostrar en el detalle). |

**Cálculo de tiempo consumido de la fase vigente en un instante dado** (dominio puro,
`sla_service.py`):

```
consumed = sla_consumed_seconds + (now - sla_last_resume_at if sla_last_resume_at else 0)
```

**Transición de estado** (efecto lateral en los endpoints `/status`, `/testing`, `/resolution`,
`/close`, `/cancel` ya existentes):

1. Si la fase vigente estaba activa (`sla_last_resume_at` no nulo): `sla_consumed_seconds += now -
   sla_last_resume_at`.
2. Determinar la fase del nuevo estado vía `SLA_PHASE_FOR_STATE` (ver tabla abajo):
   - Si el nuevo estado es `pendiente_usuario`: la fase no cambia, solo se pausa
     (`sla_last_resume_at = NULL`, `sla_status = 'pausado'`).
   - Si el nuevo estado es final para SLA (`resuelto`, `cerrado`, `cancelado`): `sla_phase =
     'cerrado'`, `sla_last_resume_at = NULL`, `sla_status = 'detenido'`.
   - Si la fase calculada es distinta de la fase vigente (p. ej. de `contacto` a `ejecucion`, al
     entrar al estado FSM `contacto`): congelar el resultado de la fase saliente
     (`sla_contact_result = 'vencido' if consumed >= contact_minutes*60 else 'cumplido'`,
     `sla_contact_consumed_seconds = consumed`), luego reiniciar `sla_consumed_seconds = 0`,
     `sla_phase_limit_minutes = execution_minutes` de la regla, `sla_phase = 'ejecucion'`,
     `sla_last_resume_at = now`.
   - Si la fase no cambió y el nuevo estado cuenta para SLA: `sla_last_resume_at = now`.
3. Recalcular `sla_status` de la fase vigente (`vencido` si `consumed >=
   sla_phase_limit_minutes*60`, si no `corriendo`/`pausado`).

**Reapertura desde RESUELTO** (`reject_resolution` → `en_ejecucion`): reanuda la fase `ejecucion`
con el `sla_consumed_seconds`/`sla_phase_limit_minutes` que tenía congelados, no la reinicia.

## Fase de SLA por estado (`SLA_PHASE_FOR_STATE` + `STATE_COUNTS_FOR_SLA`, en
`backend/domain/fsm/ticket_fsm.py`)

Diccionarios de solo lectura junto a `STATUSES`/`TRANSITIONS` (no alteran transiciones
existentes):

| Estado | Fase de SLA | Cuenta para SLA |
|--------|:---:|:---:|
| `nuevo` | Contacto | ✅ |
| `pre_analisis` | Contacto | ✅ |
| `contacto` | Diagnóstico-Análisis-Ejecución | ✅ |
| `en_analisis` | Diagnóstico-Análisis-Ejecución | ✅ |
| `en_ejecucion` | Diagnóstico-Análisis-Ejecución | ✅ |
| `en_pruebas` | Diagnóstico-Análisis-Ejecución | ✅ *(agrupado con Ejecución — `docs/SLAv1.xlsx` no define un tiempo separado para pruebas)* |
| `pendiente_usuario` | (mantiene la fase vigente, no la cambia) | ❌ (FR-005, caso explícito del spec) |
| `resuelto` | — (cierra el cómputo) | ❌ (ya cumplió el objetivo; ver reapertura arriba) |
| `cerrado` | — (cierra el cómputo) | ❌ (final) |
| `cancelado` | — (cierra el cómputo) | ❌ (final) |

## Relaciones

```
projects (1) ── (N) sla_rules   [project_id obligatorio]
sla_rules (1) ── (N) tickets    [sla_rule_id, opcional/nullable]
```

## Validaciones de negocio

- `contact_minutes`, `execution_minutes` > 0 (FR-001).
- `project_id` es obligatorio en toda regla — no se permite una regla sin proyecto.
- No se permite una segunda regla activa para la misma `(project_id, priority)` — unicidad de
  FR-002/Edge Cases.
- Desactivar (`active=false`) una regla no la borra; los tickets que ya la tienen congelada en
  `sla_rule_id` conservan su `sla_phase_limit_minutes` (Historia 1, escenario 2 y Edge Cases).
