# Research: RRHH — Franjas Horarias, Calendario Superpuesto y Motor de SLA Dinámico

## Decisión 1 — Overlay del calendario de equipo sin nueva dependencia

**Decision**: La superposición de varios miembros del equipo en una misma vista se implementa
fusionando los eventos (festivos, cumpleaños, ausencias) de todos los recursos seleccionados en
una **única instancia de FullCalendar**, diferenciando cada recurso por color/etiqueta, usando los
plugins ya instalados `@fullcalendar/daygrid` (Mes) y `@fullcalendar/timegrid` (Semana/Día — ya en
`package.json`, aún no usado en `CalendarPage.tsx`).

**Rationale**: `frontend/src/pages/CalendarPage.tsx` hoy renderiza un `<HolidayCalendar>` **por
recurso** en una grilla CSS (no superpuestos entre sí). Fusionar los arrays de eventos en un solo
componente `<FullCalendar>` satisface literalmente el requisito ("superponer sus agendas en una
misma vista") sin instalar nada nuevo — `@fullcalendar/timegrid` ya está en el lockfile desde que
se agregó `@fullcalendar/core`/`daygrid`/`react` en spec 020.

**Alternatives considered**:
- `@fullcalendar/resource-timegrid` / `@fullcalendar/resource-daygrid` (swimlanes reales, una fila
  por recurso): rechazado — es parte de FullCalendar "Premium/Scheduler", requiere licencia
  comercial o clave GPL con condiciones no evaluadas; añadir esa dependencia necesitaría
  aprobación explícita de costo en Principio V, fuera del alcance ultra-limitado de esta fase.
- Librería de calendario alternativa (`react-big-calendar`, etc.): rechazado de plano — viola
  Principio V (dependencia no aprobada) sin necesidad, ya que FullCalendar cubre el caso de uso.

## Decisión 2 — Franja Horaria global vs. horario por recurso (herencia)

**Decision**: Se introduce una tabla nueva `work_hour_templates` (+ `work_hour_template_slots`,
mismo shape que `WorkScheduleSlot`: un slot por día de la semana) como la plantilla global por
país. `Resource` gana `schedule_mode` (`heredado` | `personalizado`) y `work_hour_template_id`
(nullable). Cuando `schedule_mode == "heredado"`, el horario efectivo del recurso se resuelve en
tiempo de lectura a partir de los slots de su plantilla (no se copian filas); cuando es
`personalizado`, se usan sus propias filas de `work_schedules` (tabla ya existente, sin cambios de
esquema). `availability_service.compute_availability` **no cambia su firma** — sigue recibiendo
`work_schedule_slots: list[WorkScheduleSlot]` ya resueltos; solo cambia qué le resuelve el llamador
(repositorio/ruta) según el `schedule_mode` del recurso.

**Rationale**: minimiza el cambio de superficie (Principio VII) reutilizando la función pura ya
validada de spec 020 sin tocarla, y evita duplicar datos (la plantilla se edita una vez, todo
recurso heredado la sigue automáticamente por join en lectura, no por copia).

**Alternatives considered**:
- Copiar los slots de la plantilla a cada recurso al asignarla: rechazado — requeriría
  re-sincronizar filas en cada edición de la plantilla (más código, más riesgo) en vez de un join
  de lectura; contradice el patrón de "cálculo perezoso" ya establecido en esta misma fase.

## Decisión 3 — Migración de recursos con horario individual ya existente

**Decision**: Migración de datos (Alembic) que marca `schedule_mode = 'personalizado'` para todo
recurso que ya tenga al menos una fila en `work_schedules` al momento del despliegue; el resto
nace `schedule_mode = 'heredado'` sin plantilla asignada (equivalente al default actual de
`availability_service`: L-V 08:00-17:00) hasta que RRHH le asigne una Franja Horaria de país.

**Rationale**: decisión ya confirmada explícitamente con el usuario durante `/speckit-specify`
(ver Assumptions de spec.md) — preserva el comportamiento actual sin pérdida de datos ni necesidad
de revisión manual caso por caso.

## Decisión 4 — SLA dinámico: "hacia adelante" sale gratis del modelo de acumulación existente

**Decision**: `sla_service` ya acumula el consumo como `sla_consumed_seconds` (base persistida) +
`(now - sla_last_resume_at)` (delta desde la última reanudación) — ver `compute_consumed_seconds`.
El motor dinámico solo reemplaza el cálculo del **delta** por una suma de intervalos disponibles
entre `sla_last_resume_at` y `now` (consultando horario efectivo + festivos + ausencias, incluidas
las parciales por horas), dejando `sla_consumed_seconds` (la base ya congelada en cada pausa/
transición previa) completamente intacto.

**Rationale**: esto satisface "hacia adelante únicamente" (decisión confirmada con el usuario) sin
ningún flag de corte ni recalculo retroactivo — es una propiedad emergente del modelo de
acumulación por fases que ya existía desde spec 014, no una migración de datos nueva.

**Alternatives considered**:
- Recalcular `sla_consumed_seconds` completo desde `created_at` con la nueva lógica al desplegar:
  rechazado explícitamente por el usuario (podría "revivir" tickets ya marcados vencidos).

## Decisión 5 — Pausa/reanudación automática sin proceso en segundo plano nuevo

**Decision**: No se necesita una tarea Celery que "flip" el estado a las 18:00 en punto. El nuevo
cálculo de segundos disponibles (Decisión 4) ya devuelve el valor correcto sin importar cuándo se
consulte (cálculo perezoso, igual que hoy) — si son las 23:00 y el horario terminó a las 18:00, la
función simplemente no suma esas horas. La tarea periódica existente
(`backend/workers/sla_tasks.py: check_sla_breaches`) solo se actualiza para invocar la nueva
función de cómputo en vez de la de reloj de pared puro.

**Rationale**: consistente con el principio de "cálculo perezoso, no se persiste nada" ya
documentado en `sla_service.compute_state`; evita introducir un nuevo mecanismo de scheduling
(menor superficie, Principio VII).

**Alternatives considered**: tarea Celery adicional que materialice pausas/reanudaciones exactas
por recurso — rechazada por complejidad innecesaria frente al cálculo perezoso ya suficiente.

## Decisión 6 — Estado visual de "pausado por disponibilidad" vs. pausado por estado del ticket

**Decision**: `compute_state()` (lectura) gana una distinción visual — cuando el ticket está en
fase activa de SLA pero el recurso asignado no está disponible *en este instante* (fuera de
horario/festivo/ausencia), el estado mostrado se anota como "pausado" con motivo `outside_hours`/
`holiday`/`absence` (mismos `reason` que ya devuelve `Availability`, spec 020), en vez de mostrar
"corriendo" de forma engañosa cuando el contador no está avanzando. El campo persistido
`sla_status` (`corriendo`/`pausado`/`vencido`/`detenido`/`sin_sla`) no cambia sus valores
posibles — solo se enriquece el resultado de lectura con el motivo de la pausa cuando aplique.

**Rationale**: transparencia para el Coordinador sin tocar el contrato de datos persistido ni la
máquina de estados del ticket (Principio I: el dominio de tickets no se toca).

## Decisión 7 — Ausencia parcial por horas: mismo flujo de doble aprobación

**Decision**: `AbsenceRequest` gana `start_time`/`end_time` opcionales (ambos `NULL` = día
completo, comportamiento actual sin cambios; ambos presentes = rango horario dentro de
`start_date`, que debe igualar `end_date`). La validación de solape (`assert_no_overlap`) se
extiende para comparar también el rango horario cuando ambas solicitudes son parciales el mismo
día. La cadena de aprobación (Jefe directo + RRHH) no cambia.

**Rationale**: reutiliza el 100% del flujo de aprobación ya construido y probado en spec 020;
decisión confirmada con el usuario ("sin pasos adicionales para quien la solicita").

## Decisión 8 — Prioridad/Severidad: mapeo de "P1/P2/S1/S2" a los valores reales del sistema

**Decision**: La vista diaria y el resaltado de criticidad usan los valores reales ya existentes
en `Ticket` (`priority`: `critical`/`high`/`medium`/`low`; `severity`: `s1`-`s4`), mapeando
"P1/P2" del enunciado a prioridad `critical`+`high` y "S1/S2" directamente a severidad `s1`/`s2`.

**Rationale**: no existe un campo "P1-P4" literal en el sistema (confirmado por exploración de
`backend/domain/entities/ticket.py`); se documenta el mapeo en vez de introducir un campo/enum
paralelo redundante.

## Decisión 9 — Endpoint de carga de trabajo ("workload")

**Decision**: se expone `GET /api/resources/{id}/workload` (no `/api/users/{id}/workload`) —
calcula en tiempo de lectura la suma de tiempo de SLA comprometido de los tickets con SLA
asignados al recurso frente a su disponibilidad real restante del día (o rango consultado), sin
persistir el resultado. Permiso: `resources:view` (mismo `enforce_module("resources")` ya
aplicado a `ResourceList`/`ResourceDetail` en `backend/api/routes/resources.py` para peticiones
GET) — se añade al mismo endpoint nuevo `ResourceWorkload` en ese archivo, dentro del mismo grupo
de enforcement.

**Rationale**: la carga de trabajo es un concepto de **Recurso** (skills, calendario, horario),
no de **Usuario** (login/roles) — son entidades distintas en este dominio
(`backend/domain/entities/resource.py` vs `user.py`). `constitution.md` anticipa
`GET /api/users/{id}/workload` en su tabla ilustrativa de "Endpoints de API principales" (Fase 1,
pensado en su momento para un futuro Focus Room del propio usuario), pero esta feature necesita
leer datos de calendario/horario que solo existen en `Resource`. Se documenta aquí como una
divergencia **intencional** frente a esa tabla ilustrativa (no es un requisito NON-NEGOTIABLE de
los Principios I-VII, por lo que no requiere entrada en Complexity Tracking) — una futura
enmienda de la constitución podría actualizar ese ejemplo a `resources/{id}/workload`.

## Decisión 10 — Cómo se alimenta de datos reales el motor de SLA dinámico

**Decision**: `sla_service.compute_state` y `compute_consumed_seconds` ganan parámetros opcionales
(`resource`, `holidays`, `schedule_slots`, `absences`, todos `None` por defecto). Cuando vienen
informados, el cálculo del delta usa `compute_available_seconds` (Decisión 4); cuando no vienen
(valor por defecto), se preserva el comportamiento wall-clock puro actual — esto evita romper
otros llamadores no identificados y permite una migración incremental. Los **tres** puntos de
la Capa 3 que hoy invocan estas funciones se actualizan para resolver y pasar ese contexto antes
de llamarlas:

1. `backend/api/routes/tickets.py:358` (`TicketDetail`/listado — `compute_state(ticket, now)`).
2. `backend/api/routes/tickets.py:454` (detalle de ticket — mismo patrón).
3. `backend/workers/sla_tasks.py: check_sla_breaches` (tarea periódica Celery) — hoy no importa
   nada de calendario/festivos/horario/ausencias; pasa a resolver el mismo contexto por cada
   ticket con SLA corriendo antes de invocar `sla_service.is_breach`/`compute_state`.

Resolver el contexto en cada punto significa: `ResourceRepository.get_by_id(ticket.assignee_id)`
→ resolver los slots efectivos del recurso (Decisión 2: propios si `personalizado`, de la
plantilla si `heredado`, vía la nueva `WorkHourTemplateRepository`) → `HolidayRepository
.list_by_country(resource.calendar_country)` (ya existente, sin cambios — la función de dominio
sigue filtrando por fecha internamente, igual que hoy) → la nueva `AbsenceRequestRepository
.list_approved_between(resource_id, from_date, to_date)` (ver Decisión 11).

**Rationale**: sin este cableado explícito, las funciones nuevas de `sla_service` quedan sin
ningún llamador real — es el hallazgo crítico de la revisión de consistencia (`/speckit-analyze`,
C1). Hacerlo con parámetros opcionales (no obligatorios) evita tener que auditar y tocar cada
llamador existente de golpe, y hace explícito en la firma qué datos hacen falta.

## Decisión 11 — Consulta de ausencias aprobadas por rango (nueva, ranged)

**Decision**: se agrega `AbsenceRequestRepository.list_approved_between(resource_id, start_date,
end_date)` en `backend/infra/repositories/calendar_repo.py` — devuelve solo solicitudes con
`manager_status="approved"` **y** `hr_status="approved"` que se solapan con `[start_date,
end_date]`. El método ya existente `get_active_absence(resource_id, on_date)` (consulta puntual
de un solo día, usada hoy por el endpoint de disponibilidad) no alcanza para sumar segundos
disponibles a lo largo de un rango multi-día (`sla_last_resume_at` → `now`) — es la brecha
concreta señalada por C1. `list_overlapping` (ya existente) es parecido pero incluye solicitudes
`pending` (solo excluye `rejected`), lo cual no sirve para el cálculo de disponibilidad real, que
exige aprobación de ambos lados.

**Rationale**: reutilizar el mismo criterio de "ambos lados aprobados" que ya usa
`get_active_absence`, evitando duplicar semántica de negocio con nombres o comportamientos
distintos entre los dos métodos.

Los festivos **no** requieren un método ranged nuevo: `HolidayRepository.list_by_country`/
`list_by_countries` (ya existentes) devuelven todos los festivos activos del país sin filtrar por
fecha a nivel SQL — `compute_available_seconds` filtra día por día internamente, igual que ya
hace hoy `_has_holiday_today` dentro de `compute_availability`.

## Decisión 12 — Franja Horaria: persistencia en un repositorio nuevo, no en el "servicio" de dominio

**Decision**: `work_hour_template_service.py` (Capa 1, dominio puro) contiene **solo** validación
(timezone IANA válida, `end_time > start_time` por slot) — nunca toca la base de datos, igual que
`absence_service.py` hoy. La persistencia (crear/editar/listar Franjas y sus slots, y resolver a
qué recurso pertenece cada una) vive en una `WorkHourTemplateRepository` **nueva** en
`backend/infra/repositories/calendar_repo.py` (mismo archivo que `HolidayRepository`/
`WorkScheduleRepository`/`AbsenceRequestRepository`), invocada directamente desde las rutas de
`backend/api/routes/calendar.py` — igual patrón que ya usan los festivos y las ausencias hoy.

**Rationale**: `plan.md` (Project Structure) describía este archivo de forma ambigua como si
hiciera "CRUD" — un servicio de Capa 1 con imports de SQLAlchemy violaría el Principio I. Se
corrige aquí para que el diseño sea consistente con el patrón ya establecido en el resto de la
Fase 5 (`absence_service.py` valida, `calendar.py` orquesta contra los repositorios).
