# Quickstart — Validación de Calendarios, Vacaciones (RRHH) y Disponibilidad

Valida las 4 historias de usuario de `spec.md`. Ver contratos en
[contracts/calendar-disponibilidad.md](contracts/calendar-disponibilidad.md) y modelo en
[data-model.md](data-model.md).

## Prerrequisitos

- Entorno Docker Compose levantado (`sywork_db`, `sywork_backend`, `sywork_frontend`).
- Migraciones aplicadas hasta la última de esta fase (`alembic upgrade head`), incluyendo el seed
  del rol RRHH, el catálogo `catalog_absence_types` y algunos festivos de ejemplo (≤10 registros
  de prueba, Principio VII).
- Un usuario con rol Admin (o Coordinador) para configurar Cliente/Recursos.
- Un usuario con rol RRHH (creado/asignado en `Roles y Permisos`).
- Al menos dos Recursos activos: uno con `manager_id` apuntando al otro (relación Jefe directo).

## Escenario 1 — Alerta de disponibilidad al asignar (US1, FR-013/014/015/016)

1. Configurar el Recurso "Resolutor A": país `CO`, `timezone`
   `America/Bogota`, sin horario laboral propio (usa el default).
2. Crear un festivo de prueba: `POST /api/holidays` con `country=CO`, `holiday_date` = hoy.
3. En Maestros > Panel de Asignación, abrir "Asignar" sobre un ticket NUEVO.
4. **Resultado esperado**: la tarjeta de "Resolutor A" muestra el indicador rojo "No disponible:
   día festivo" con tooltip del nombre del festivo; el botón "Asignar resolutor" sigue habilitado.
5. Completar la asignación. **Resultado esperado**: la asignación se registra igual (200), sin
   ningún bloqueo — confirma FR-015.
6. Repetir sin el festivo de prueba (desactivarlo) y fuera del horario laboral por defecto (ej.
   correr la prueba a las 22:00 hora de Bogotá) → debe verse "No disponible: fuera de horario
   laboral" en su lugar.
7. Repetir dentro de horario, sin festivo, sin ausencia aprobada → sin ningún indicador.

## Escenario 2 — Solicitud y doble aprobación de ausencia (US2, FR-008 a FR-012)

1. Con el usuario vinculado a "Resolutor B" (subordinado de "Resolutor A" vía `manager_id`),
   crear una solicitud: `POST /api/absence-requests` con tipo "Incapacidad médica", rango de 3
   días, adjuntando un PDF de prueba.
2. **Resultado esperado**: `201`, `manager_status=pending`, `hr_status=pending`,
   `overall_status=pending`.
3. Iniciar sesión como "Resolutor A" (jefe directo) → `GET
   /api/absence-requests?scope=manager` debe listar la solicitud. Aprobarla:
   `PATCH .../decision` con `role=manager`, `decision=approved`.
4. **Resultado esperado**: `manager_status=approved`, `overall_status` sigue `pending` (falta
   RRHH).
5. Iniciar sesión como un usuario con rol RRHH → `GET /api/absence-requests?scope=hr` debe listar
   la misma solicitud. Aprobarla con `role=hr`.
6. **Resultado esperado**: `hr_status=approved`, `overall_status=approved`.
7. Repetir el flujo con una segunda solicitud y hacer que RRHH la **rechace** en vez de aprobarla
   antes de que el jefe decida. **Resultado esperado**: `overall_status=rejected` de inmediato,
   sin esperar al jefe (FR-011a).
8. Intentar que "Resolutor A" apruebe/rechace su propia solicitud → **403** (FR-012).

## Escenario 3 — Calendario con festivos por país (US3, FR-001/002/004/005)

1. Configurar `timezone`/`country` en un Cliente desde Maestros > Clientes.
2. Abrir la vista de Calendario > pestaña "Cliente", seleccionar ese cliente.
3. **Resultado esperado**: el calendario muestra el festivo de prueba del Escenario 1 en la fecha
   correcta, resaltado visualmente.
4. Abrir la pestaña "Equipo" con "Resolutor A" (país `CO`) y otro recurso de país distinto (ej.
   `MX`, sin festivos cargados).
5. **Resultado esperado**: cada miembro muestra únicamente los festivos de su propio país; el
   recurso sin festivos cargados se ve sin marcas, sin error (edge case).

## Escenario 4 — Horario laboral por defecto (US4, FR-006)

1. `GET /api/resources/{resolutor_b_id}/work-schedule` sin configuración previa →
   `is_default: true`, franjas lunes-viernes 08:00-17:00.
2. `PUT /api/resources/{resolutor_b_id}/work-schedule` con una franja distinta (ej. 06:00-14:00
   lunes a viernes en su `timezone`).
3. Repetir el Escenario 1 con "Resolutor B" a las 15:00 hora local → debe verse "No disponible:
   fuera de horario laboral" (ya con el horario custom, no el default).

## Verificación de contrato (opcional, vía curl/Swagger UI)

```bash
# Disponibilidad en el instante actual
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5000/api/resources/availability?resource_ids=$RESOURCE_ID"

# Crear solicitud de ausencia
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"absence_type_id":"'$ABSENCE_TYPE_ID'","start_date":"2026-08-01","end_date":"2026-08-05"}' \
  http://localhost:5000/api/absence-requests
```

**Resultado esperado**: `200`/`201` con las formas descritas en
[contracts/calendar-disponibilidad.md](contracts/calendar-disponibilidad.md).
