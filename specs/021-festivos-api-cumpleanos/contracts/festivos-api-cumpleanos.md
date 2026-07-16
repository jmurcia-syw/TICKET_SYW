# Contract: Festivos sincronizados por API, categorización y cumpleaños (spec 021)

Extiende los endpoints de festivos ya existentes (`backend/api/routes/calendar.py`, spec 020). No
agrega endpoints públicos nuevos para la sincronización en sí (es automática, ver `research.md`
Decisión 2) ni para los cumpleaños (son un cómputo puramente frontend, ver Decisión 7).

## Festivos — cambios en endpoints existentes

### `GET /api/holidays?country=CO` — listar festivos de un país

**Sin cambio de permiso.** Cambios de comportamiento y forma de respuesta:

- Si no existe ningún festivo con `source='api'` para `country` (o no hay fila en
  `holiday_sync_status` para ese país), el handler intenta una sincronización síncrona única
  contra la fuente externa (timeout corto) **antes** de consultar la base y responder. Un fallo
  de esa sincronización no produce error HTTP — simplemente responde con lo que ya exista en base
  (research.md, Decisión 2).
- Cada ítem gana dos campos:

```json
{"items": [{
  "id": "uuid", "country": "CO", "holiday_date": "2026-07-20",
  "name": "Día de la Independencia", "active": true,
  "category": "oficial | regional_religioso",
  "source": "api | manual"
}]}
```

### `POST /api/holidays` — crear un festivo (sin cambios de permiso, `holidays:manage`)

**Body**, campo nuevo opcional `category` (default `"oficial"` si se omite, por compatibilidad):

```json
{"country": "CO", "holiday_date": "2026-07-09", "name": "Virgen del Rosario de Chiquinquirá", "category": "regional_religioso"}
```

El festivo creado por esta vía siempre queda con `source="manual"` (FR-010: los
"Regional/Religioso" solo se crean a mano; los "Oficial" manuales también quedan protegidos de
sobrescritura futura — Decisión 6 de `research.md`).

**400** `validation_error`: además de las reglas ya vigentes (fecha inválida, duplicado), ahora
también si `category` no es uno de los dos valores permitidos.

### `PATCH /api/holidays/{id}` — editar un festivo existente (endpoint nuevo)

**Permiso**: `require_permission("holidays", "manage")` (mismo permiso ya usado por
crear/activar/desactivar).

**Body** (todos los campos opcionales, actualización parcial):
```json
{"name": "string", "holiday_date": "YYYY-MM-DD", "category": "oficial | regional_religioso"}
```

**200**: el festivo actualizado, con `source` forzado a `"manual"` sin importar su valor previo
(FR-009 — cualquier edición manual bloquea futuras sobrescrituras automáticas). **404** si el
festivo no existe. **400** `validation_error` en los mismos casos que `POST`.

*Nota de alcance*: `country` **no** es editable por este endpoint (mover un festivo de país
equivale a crear uno nuevo y desactivar el anterior — evita ambigüedad con la unicidad
`(country, holiday_date, name)`).

### `PATCH /api/holidays/{id}/deactivate` / `/activate` (sin cambios de forma)

Mismo contrato ya existente. Efecto adicional: fuerza `source="manual"` en la fila afectada
(Decisión 6).

## Disponibilidad — sin cambio de contrato, cambio de comportamiento interno

`GET /api/resources/availability` (spec 020) mantiene exactamente la misma firma y forma de
respuesta. Internamente, el `reason: "holiday"` solo puede producirse ahora por un festivo con
`category = "oficial"` — un festivo `regional_religioso` activo en la fecha no genera ningún
indicador de no-disponibilidad (FR-007). No hay cambio observable en el contrato HTTP, solo en el
criterio de negocio que decide `available`.

## Cumpleaños — sin endpoint nuevo

No hay contrato de backend para esta historia: `CalendarPage.tsx` ya recibe `birth_date` como
parte de la respuesta existente de `GET /api/resources` y genera los eventos de cumpleaños
enteramente en el cliente (Decisión 7 de `research.md`).
