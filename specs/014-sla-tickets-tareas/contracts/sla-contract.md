# Contract: SLA (reglas y estado por ticket)

## `GET /api/sla-rules`

Lista paginada de reglas de SLA. Permiso: `sla_rules:manage` para ver el CRUD completo (Admin/
Coordinador); no expuesto a otros roles (no hay necesidad de que Resolutor liste reglas — solo ve
el resultado aplicado en el ticket). Soporta filtro opcional `?project_id=uuid`.

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "project_id": "uuid",
      "project_name": "string",
      "priority": "high",
      "contact_minutes": 15,
      "execution_minutes": 480,
      "active": true,
      "created_at": "iso8601"
    }
  ],
  "total": 0, "page": 1, "page_size": 20
}
```

## `POST /api/sla-rules`

Crea una regla. Permiso: `sla_rules:manage`.

**Request**:
```json
{
  "project_id": "uuid",
  "priority": "high",
  "contact_minutes": 15,
  "execution_minutes": 480
}
```

**Response 201**: objeto `SlaRule` (igual forma que en `GET`).

**Errores** (contrato estándar `{success:false, message, code}` de la spec 013):
- 400 `VALIDATION_ERROR`: `contact_minutes`/`execution_minutes` ≤ 0, o falta `project_id`.
- 404 `NOT_FOUND`: `project_id` no existe.
- 409 `DUPLICATE_RULE`: ya existe una regla activa para la misma combinación
  `(project_id, priority)`.

## `PATCH /api/sla-rules/{id}`

Edita tiempos límite o `active`. Permiso: `sla_rules:manage`. No permite cambiar
`priority`/`project_id` (para cambiar la combinación, se crea una regla nueva y se desactiva la
anterior — evita reasignar accidentalmente tickets ya congelados a otra combinación).

**Request**: subconjunto de `{contact_minutes, execution_minutes, active}`.

**Response 200**: objeto `SlaRule` actualizado.

## `DELETE /api/sla-rules/{id}`

No implementado — desactivar (`PATCH {active:false}`) es la única baja soportada (ver
data-model.md: los tickets en curso referencian `sla_rule_id`).

## Extensión de `GET /api/tickets/{id}` (`_ticket_detail_out`, sin nueva ruta)

Se agrega un bloque `sla` al payload ya existente:

```json
{
  "...": "... campos existentes sin cambios ...",
  "sla": {
    "phase": "contacto | ejecucion | cerrado | null",
    "status": "sin_sla | corriendo | pausado | vencido | detenido",
    "phase_limit_minutes": 480,
    "consumed_seconds": 3600,
    "rule_id": "uuid|null",
    "contact_result": "pendiente | cumplido | vencido | null",
    "contact_consumed_seconds": 900
  }
}
```

`contact_result`/`contact_consumed_seconds` quedan `null` mientras la fase Contacto sigue vigente;
se congelan al pasar a la fase Ejecución (FR-004b, FR-007).

## Extensión de `GET /api/tickets` (listado, sin nueva ruta)

Cada item del listado agrega el mismo bloque `sla` (versión resumida: `phase`, `status`, sin
`rule_id` ni el detalle de `contact_*`) para pintar el indicador visual sin una llamada adicional
por fila (FR-008).

## Extensión de filtros de `GET /api/tickets` (para el stat "Vencen hoy")

`TicketsPage.tsx` calcula hoy sus `StatCard` haciendo `ticketService.list({status:[...], page_size:1}).then(r => r.total)` — sin endpoint de dashboard dedicado. Se sigue el mismo patrón: se
agregan dos filtros nuevos de query string a `GET /api/tickets`:

- `sla_status=vencido|corriendo|pausado|sin_sla` — filtra por estado de SLA.
- `sla_expiring_within_hours=24` — filtra tickets activos cuyo tiempo restante hasta vencer el
  límite es ≤ N horas (para "Vencen hoy" se usa `24`).

`TicketsPage.tsx` agrega una quinta llamada `ticketService.list({sla_expiring_within_hours: 24, page_size: 1}).then(r => r.total)` al `Promise.all` ya existente en `loadStats` — reemplaza el
valor fijo `"—"` del `StatCard` "Vencen hoy" (FR-009). No se crea ningún endpoint nuevo.
