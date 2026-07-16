# Quickstart — Validación de Festivos por API, Categorización y Cumpleaños

Valida las 3 historias de usuario de `spec.md`. Ver contrato en
[contracts/festivos-api-cumpleanos.md](contracts/festivos-api-cumpleanos.md) y modelo en
[data-model.md](data-model.md).

## Prerrequisitos

- Entorno Docker Compose levantado (`sywork_db`, `sywork_backend`, `sywork_frontend`,
  `sywork_worker`), incluyendo la migración de esta fase (`alembic upgrade head`) que agrega
  `category`/`source` a `holidays` y crea `holiday_sync_status`.
- Conectividad saliente desde `sywork_backend`/`sywork_worker` hacia `date.nager.at` (o el
  entorno de prueba simula/mockea la respuesta si no hay internet disponible).
- Al menos un Cliente o Recurso con `country="CO"` configurado (ya existe de spec 020).

## Escenario 1 — Festivos oficiales completos vía sincronización (US1, FR-001 a FR-004, FR-015)

1. Con un país que aún no tiene ningún festivo con `source='api'` (o recién configurado),
   `GET /api/holidays?country=CO`.
2. **Resultado esperado**: la respuesta incluye el calendario oficial completo de Colombia para
   el año en curso, incluyendo el 20 de julio ("Día de la Independencia") — ya no faltan festivos
   como en la carga manual original de spec 020.
3. Simular una falla de la fuente externa (ej. país sin cobertura o sin red) y repetir la
   consulta. **Resultado esperado**: no hay error HTTP; la respuesta trae lo que ya exista en
   base (posiblemente vacía la primera vez), y ninguna otra funcionalidad del sistema
   (asignación de tickets, aprobación de ausencias) se ve afectada.
4. Verificar que la tarea periódica de sincronización está registrada:
   `docker exec sywork_worker celery -A backend.workers.celery_app inspect registered` debe
   listar la tarea de sincronización de festivos.

## Escenario 2 — Categorización visual y efecto en disponibilidad (US2, FR-005 a FR-010)

1. Confirmar que un festivo sincronizado automáticamente (ej. "Día de la Independencia") tiene
   `category: "oficial"` y `source: "api"`.
2. `POST /api/holidays` con `category="regional_religioso"` para crear una celebración local (ej.
   "Virgen del Rosario de Chiquinquirá", 9 de julio, país `CO`).
3. Abrir `/calendar`, pestaña Cliente, con un cliente de país `CO`. **Resultado esperado**: ambos
   festivos aparecen en el calendario con colores/etiquetas distintos según su categoría.
4. `GET /api/resources/availability` para un recurso de país `CO` en la fecha del festivo
   regional/religioso creado en el paso 2. **Resultado esperado**: `available: true` (el festivo
   regional/religioso no afecta disponibilidad). Repetir en la fecha de un festivo oficial (ej.
   20 de julio). **Resultado esperado**: `available: false, reason: "holiday"`.
5. Editar manualmente (vía `PATCH /api/holidays/{id}`) el festivo oficial sincronizado del paso
   1. **Resultado esperado**: `source` pasa a `"manual"`. Forzar una nueva sincronización (o
   esperar la siguiente corrida periódica) y verificar que ese festivo editado **no** fue
   sobrescrito.

## Escenario 3 — Cumpleaños del equipo en el calendario (US3, FR-011 a FR-014)

1. Configurar `birth_date` en el perfil de un Recurso activo (Maestros > Equipo) si aún no lo
   tiene.
2. Abrir `/calendar`, pestaña Equipo, y seleccionar ese Recurso.
3. **Resultado esperado**: aparece un evento anual en la fecha (día/mes) de su cumpleaños, con
   color/ícono distinto a los festivos oficiales y regionales/religiosos mostrados en la misma
   vista.
4. Navegar el calendario al mes/año siguiente. **Resultado esperado**: el evento de cumpleaños
   vuelve a aparecer automáticamente en la misma fecha del año siguiente.
5. Seleccionar un Recurso sin `birth_date` configurado. **Resultado esperado**: no aparece ningún
   evento de cumpleaños para ese recurso, sin error en consola ni en la interfaz.

## Verificación de contrato (opcional, vía curl/Swagger UI)

```bash
# Festivos de un país, con categoría y origen
curl -H "Authorization: Bearer $TOKEN" "http://localhost:5000/api/holidays?country=CO"

# Crear un festivo regional/religioso
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"country":"CO","holiday_date":"2026-07-09","name":"Virgen del Rosario de Chiquinquirá","category":"regional_religioso"}' \
  http://localhost:5000/api/holidays
```

**Resultado esperado**: `200`/`201` con las formas descritas en
[contracts/festivos-api-cumpleanos.md](contracts/festivos-api-cumpleanos.md).
