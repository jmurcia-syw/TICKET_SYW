# Quickstart — Validación de RRHH, Franjas Horarias, Calendario Superpuesto y SLA Dinámico

Valida las 4 historias de usuario de `spec.md`. Ver contrato en
[contracts/rrhh-calendario-sla-dinamico.md](contracts/rrhh-calendario-sla-dinamico.md) y modelo en
[data-model.md](data-model.md).

## Prerrequisitos

- Entorno Docker Compose levantado (`sywork_db`, `sywork_backend`, `sywork_frontend`,
  `sywork_worker`), con `alembic upgrade head` aplicando las migraciones `041` a `044` de esta
  fase.
- Un usuario con rol RRHH (seed ya existente desde spec 020) y un usuario Resolutor/Coordinador
  para probar la asignación de tickets.
- Al menos un país con Recursos ya configurados (ej. `CO`, ya usado en specs 020/021).
- Una regla de SLA vigente (spec 014) para el Proyecto/Prioridad del ticket de prueba.

## Escenario 1 — Franjas Horarias globales y modo Personalizado (US1, FR-001 a FR-005)

1. Iniciar sesión como RRHH. **Resultado esperado**: aparece el menú desplegable "RRHH" con
   "Calendario" y "Permisos", con el mismo estilo visual que "Maestros".
2. `POST /api/work-hour-templates` creando una Franja Horaria para `CO` (ej. L-V 08:00-17:00,
   huso `America/Bogota`).
3. Verificar que un recurso de `CO` sin horario propio configurado (o recién migrado) queda
   `schedule_mode: "heredado"` — asignarle la plantilla vía
   `PATCH /api/resources/{id}/work-hour-template`.
4. `PATCH /api/work-hour-templates/{id}` cambiando el horario a 09:00-18:00. **Resultado
   esperado**: `GET /api/resources/availability` para ese recurso refleja la nueva ventana sin
   ninguna otra llamada.
5. Iniciar sesión como ese mismo recurso y editar su horario desde su Perfil
   (`PUT /api/resources/{id}/work-schedule`). **Resultado esperado**: el recurso pasa a
   `schedule_mode: "personalizado"`; repetir el paso 4 con otra edición de la plantilla y
   confirmar que este recurso **ya no** cambia.
6. Como RRHH, `GET /api/work-hour-templates/personalized`. **Resultado esperado**: el recurso del
   paso 5 aparece listado.

## Escenario 2 — Motor de SLA Dinámico (US2, FR-006 a FR-010)

1. Con un recurso cuya Franja Horaria es 08:00-18:00 (ajustar el reloj del entorno de prueba o
   usar un caso ya en curso), asignar un ticket con SLA a las 17:00 con la regla de SLA
   correspondiente.
2. `GET /api/tickets/{id}` una hora después (18:00). **Resultado esperado**: `sla.consumed_seconds
   ≈ 3600` (1 hora) y `sla.status: "pausado"`, `sla.pause_reason: "outside_hours"`.
3. Consultar de nuevo al día siguiente a las 08:00. **Resultado esperado**: `sla.status:
   "corriendo"` de nuevo, sin haber requerido ninguna acción manual.
4. Repetir el paso 1 con un ticket que entra completamente fuera de horario (ej. las 20:00).
   **Resultado esperado**: `consumed_seconds` no crece hasta la siguiente ventana disponible.
5. Aprobar una ausencia (día completo) para el recurso asignado a un ticket con SLA corriendo.
   **Resultado esperado**: el tiempo de esos días no se descuenta del SLA.
6. Sobre un ticket que ya estaba abierto **antes** de aplicar las migraciones de esta fase,
   verificar que su `consumed_seconds` previo no cambió tras el despliegue — solo el tiempo
   adicional desde entonces usa la lógica dinámica.

## Escenario 3 — Calendario de Equipo Superpuesto y ausencias parciales (US3, FR-011 a FR-014)

1. Abrir `/calendar`, pestaña Equipo, y seleccionar varios miembros (o "Seleccionar todo").
   **Resultado esperado**: una sola vista muestra los festivos/cumpleaños/días especiales de
   todos los seleccionados, diferenciados por color/etiqueta (no un calendario separado por
   persona).
2. Alternar entre las vistas Mes, Semana y Día. **Resultado esperado**: la selección de miembros
   se mantiene y la información se reorganiza según la vista.
3. `POST /api/absence-requests` con `start_time`/`end_time` (ej. cita médica de 2 horas).
   **Resultado esperado**: `201`, mismo flujo de doble aprobación (Jefe directo + RRHH) que una
   ausencia de día completo.
4. Tras aprobar ambas partes, verificar en `GET /api/resources/availability` que, dentro del rango
   horario de la ausencia, el recurso aparece no disponible (`reason: "absence"`), y disponible
   fuera de ese rango el mismo día.
5. `GET /api/resources/{id}/workload`. **Resultado esperado**: refleja el tiempo comprometido por
   tickets con SLA frente a la disponibilidad restante del día, descontando la ausencia parcial.

## Escenario 4 — Vista Diaria priorizada (US4, FR-015 a FR-016)

1. Asignar a un mismo Resolutor varios tickets el mismo día con distintas combinaciones de
   Prioridad/Severidad (ej. uno `low`/`s4`, uno `critical`/`s1`).
2. Abrir la vista de Día del calendario para ese Resolutor. **Resultado esperado**: el ticket
   `critical`/`s1` aparece primero y resaltado visualmente; el `low`/`s4` aparece al final sin
   resaltar.

## Verificación de contrato (opcional, vía curl/Swagger UI)

```bash
# Crear una Franja Horaria
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"country":"CO","name":"Colombia — Estándar","timezone":"America/Bogota",
       "slots":[{"weekday":0,"start_time":"08:00","end_time":"17:00"}]}' \
  http://localhost:5000/api/work-hour-templates

# Consultar la carga de trabajo de un recurso
curl -H "Authorization: Bearer $TOKEN" "http://localhost:5000/api/resources/$RESOURCE_ID/workload"
```

**Resultado esperado**: `200`/`201` con las formas descritas en
[contracts/rrhh-calendario-sla-dinamico.md](contracts/rrhh-calendario-sla-dinamico.md).

## Alcance de pruebas automatizadas (directriz explícita del usuario / Principio VII)

La suite de tests de esta fase se limita a un archivo dirigido al cálculo de SLA dinámico (ej.
`test_sla_dynamic_availability.py`), con 5-10 registros dummy (festivos, slots de Franja,
ausencias parciales) cubriendo el escenario estricto del enunciado (Escenario 2 arriba). No se
ejecuta la suite global de integración como parte de la validación de esta fase.
