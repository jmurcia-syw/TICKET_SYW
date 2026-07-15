# Convenciones — UAT

## Nomenclatura de IDs

| Entidad | Formato | Ejemplo | Regla |
|---|---|---|---|
| Iteración | `ITER-XXX` | `ITER-001` | Consecutivo global, 3 dígitos, nunca se reutiliza. |
| Observación | `OBS-XXXX` | `OBS-0001` | Consecutivo global (no por iteración), 4 dígitos, persiste entre iteraciones, nunca se reutiliza ni se renumera. |
| Delivery | `DEL-XXX` | `DEL-001` | Consecutivo global, 3 dígitos, nunca se reutiliza. |
| Imagen | `OBS-XXXX-NN.png` | `OBS-0001-01.png` | `NN` consecutivo dentro de la misma observación, empieza en `01`. |

El siguiente ID disponible de cada entidad es siempre el consecutivo del último registrado en `02_Backlog/BACKLOG.md` (no existe contador separado que se pueda desincronizar).

## Tipos de observación

- **Defecto**: la funcionalidad no se comporta como se espera (bug).
- **Mejora**: la funcionalidad se comporta como se espera, pero se propone un cambio (UX, performance, alcance adicional).

## Quién reporta

El framework no está atado a una sola persona. Una iteración puede incluir observaciones reportadas por distintos consultores probando en paralelo (Gerente de Desarrollo u otros consultores asignados a validación). Por eso:

- El frontmatter de `ITER-XXX.md` tiene `responsable_sesion`: quien coordina esa iteración (no necesariamente quien reporta cada hallazgo).
- Cada observación individual tiene su propio campo **Reportado por**, con el nombre de quien la encontró.
- `BACKLOG.md` mantiene la columna "Reportado por" para poder filtrar/atribuir por persona.

## Estados de una observación

```
Abierta ──► En Desarrollo ──► Lista para Validar ──► Verificada (Cerrada)
                                       │
                                       ├──► Reabierta ──► (vuelve a En Desarrollo)
                                       │
Abierta/En Desarrollo ──► Rechazada
Abierta/En Desarrollo ──► Diferida
```

| Estado | Quién lo asigna | Significado |
|---|---|---|
| `Abierta` | Quien reporta | Recién reportada, sin atender. |
| `En Desarrollo` | Desarrollador | Se está trabajando la corrección. |
| `Lista para Validar` | Desarrollador | Corregida en una versión ya disponible para retest. |
| `Verificada` | Quien valida | Confirmada como resuelta en una iteración posterior. Estado final de cierre. |
| `Reabierta` | Quien valida | Una observación `Verificada` volvió a fallar. Vuelve al ciclo como `En Desarrollo`. |
| `Rechazada` | Desarrollador o validador (con justificación) | No es un defecto real / no aplica. Estado final. |
| `Diferida` | Validador | Se pospone a una Delivery futura. No bloquea la Delivery actual. |

## Campos obligatorios de una observación

Cada observación dentro de un `ITER-XXX.md` sigue este bloque:

```
### OBS-XXXX — <título corto y descriptivo>

- **Módulo/Pantalla:** <ej. Tickets > Crear ticket>
- **Tipo:** Defecto | Mejora
- **Estado:** <estado al momento de esta iteración>
- **Reportado por:** <nombre>
- **Iteración de origen:** ITER-XXX
- **Iteración de cierre:** ITER-XXX | —

**Descripción**
<qué se observó, en lenguaje de negocio>

**Pasos para reproducir** (solo Defecto)
1. ...

**Resultado esperado / Situación actual** (Defecto: esperado vs actual · Mejora: situación actual)
...

**Resultado actual / Propuesta de mejora**
...

**Criterios de aceptación**
- [ ] ...
- [ ] ...

**Evidencia**
![<descripción>](images/OBS-XXXX-01.png)
```

Los criterios de aceptación se redactan como checklist verificable — no "debe funcionar bien", sino condiciones concretas que se puedan marcar como cumplidas o no durante el retest.

## Reglas de inmutabilidad

- Un `ITER-XXX.md`, una vez creado, no se vuelve a editar. Si una observación cambia de estado, eso se refleja en `BACKLOG.md`, no reescribiendo la iteración pasada.
- Si una observación se reabre, se referencia la iteración de reapertura en `BACKLOG.md`; el detalle de la reapertura (qué volvió a fallar) se documenta como una entrada nueva dentro de la iteración actual, citando el `OBS-XXXX` original.

## BACKLOG.md — estructura

Tabla única, una fila por observación, siempre actualizada al estado más reciente:

| ID | Módulo/Pantalla | Tipo | Estado | Reportado por | Iteración origen | Iteración cierre | Descripción corta |
|---|---|---|---|---|---|---|---|

## Deliveries

Una Delivery se genera cuando se decide que el estado acumulado de varias iteraciones es aceptable como corte de versión. Incluye: iteraciones cubiertas, observaciones cerradas, observaciones diferidas explícitamente, y el acta de aceptación firmada (nombre, rol y fecha).
