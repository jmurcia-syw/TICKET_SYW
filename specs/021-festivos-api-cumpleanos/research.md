# Research — Festivos sincronizados por API, categorización visual y cumpleaños

No quedaron `NEEDS CLARIFICATION` en el Technical Context del plan. Se documentan igual como
research formal porque cada decisión tenía más de una alternativa razonable.

## Decisión 1 — Fuente externa de festivos: Nager.Date (nueva integración, Principio V)

- **Decisión**: consumir la API pública y gratuita `https://date.nager.at` (endpoint
  `GET /api/v3/PublicHolidays/{year}/{countryCode}`), sin API key. Usa códigos ISO 3166-1 alpha-2
  — el mismo formato ya usado por `calendar_country`/`country` en Cliente y Recurso, y por el
  catálogo curado `frontend/src/data/countries.ts`. El cliente HTTP es `requests` (Python), **ya
  presente en `backend/requirements.txt` desde antes de esta fase** (no se agrega línea nueva al
  archivo de dependencias) aunque hasta ahora no tenía ningún uso real en el código — esta es su
  primera materialización. **Aprobación documentada aquí, per Principio V.**
- **Rationale**: no requiere credenciales (evita el problema de manejo de secretos para una
  integración de solo lectura de datos públicos), respuesta JSON simple, cobertura amplia de
  países (~100+), y cada festivo trae un campo `counties` (subdivisión regional, si aplica) y
  `global` (si aplica a todo el país) que sirve como señal adicional pero no se usa para la
  categorización Oficial/Regional de esta fase (ver Decisión 4 — esa distinción la decide un
  humano, no la API).
- **Alternativas consideradas**: (a) `python-holidays` (librería de cálculo algorítmico offline) —
  rechazada, es una dependencia nueva no aprobada y el usuario pidió explícitamente una fuente "en
  línea"/conectada, no un cálculo local; (b) Calendarific — rechazada, requiere API key (choca con
  Principio IV: "Secretos en `.env`... nunca comiteados" agrega superficie de gestión de
  credenciales para un dato no sensible); (c) Abstract API — rechazada, capa gratuita limitada en
  volumen de llamadas, sin ventaja sobre Nager.Date para este caso de uso.

## Decisión 2 — Sincronización: tarea periódica Celery Beat + intento inline en primer uso

- **Decisión**: dos mecanismos complementarios, mismo patrón que `check_sla_breaches`
  (`backend/workers/sla_tasks.py`, spec 014):
  1. **Tarea periódica** `backend/workers/holiday_sync_tasks.py::sync_holidays` registrada en
     `celery_app.conf.beat_schedule` (ej. diaria, `crontab(hour=3, minute=0)` — los festivos no
     cambian con la frecuencia de un SLA, no se justifica una cadencia de minutos). Recorre los
     países realmente en uso (`SELECT DISTINCT country FROM clients UNION SELECT DISTINCT
     calendar_country FROM resources`, ambos no nulos) y sincroniza año actual + siguiente para
     cada uno.
  2. **Intento inline en primer uso**: si `GET /api/holidays?country=X` no encuentra ningún
     registro con `source='api'` para ese país (o no existe fila en `holiday_sync_status`), el
     propio endpoint dispara un intento síncrono único de sincronización (timeout corto, ~3s)
     antes de responder — cumple el edge case del spec ("no debe esperar una tarea programada").
     Si falla, responde con lo que haya en base (posiblemente vacío) y deja el reintento al job
     periódico.
- **Rationale**: reutiliza la infraestructura Celery+Redis ya aprobada y ya materializada en el
  proyecto (Principio V), sin introducir un scheduler nuevo. El intento inline solo corre una vez
  por país (gracias al registro en `holiday_sync_status`), evitando que cada `GET` dispare una
  llamada HTTP externa.
- **Alternativas consideradas**: sincronizar únicamente vía tarea periódica sin intento inline —
  rechazada, un país configurado por primera vez quedaría con el calendario vacío hasta la
  siguiente corrida programada (hasta 24h), violando el edge case explícito del spec.

## Decisión 3 — Modelo de datos: extender `holidays` + nueva tabla `holiday_sync_status`

- **Decisión**: agregar a la tabla `holidays` existente (spec 020) dos columnas:
  `category` (`'oficial' | 'regional_religioso'`, default `'oficial'`) y
  `source` (`'api' | 'manual'`, default `'manual'`). Nueva tabla `holiday_sync_status`
  (`country`, `year`, `last_synced_at`, `success`, `error_message`, unique `(country, year)`) para
  registrar el estado de cada intento de sincronización y decidir cuándo reintentar.
- **Rationale**: extender la tabla existente evita duplicar el modelo de festivo (país, fecha,
  nombre, activo) ya usado por el calendario y por `availability_service.py`; las dos columnas
  nuevas son suficientes para resolver tanto la categorización visual (Decisión 4) como el
  bloqueo de sobrescritura tras edición manual (Decisión 5). `holiday_sync_status` es una tabla
  puramente operativa (no la consume el frontend), separada de `holidays` para no mezclar el
  registro de "intentos de sincronización" con los festivos mismos.
- **Alternativas consideradas**: tabla `holidays` separada por origen (`holidays` vs.
  `holidays_api_cache`) con proceso de "promoción" a la tabla visible — rechazada, añade
  complejidad de sincronización entre dos tablas sin necesidad; un simple flag `source` alcanza.

## Decisión 4 — Categorización visual: campo `category` + color por tipo en el frontend

- **Decisión**: `CalendarPage.tsx` colorea los eventos de FullCalendar según `holiday.category`
  (oficial = color ya usado hoy, naranja; regional/religioso = un segundo color distintivo, ej.
  púrpura) con una leyenda simple sobre el calendario. El backend expone `category` en
  `GET /api/holidays` (ya existente, se extiende el modelo Swagger `_holiday_out`).
- **Rationale**: cambio de bajo riesgo — FullCalendar ya soporta `color` por evento
  individualmente (`events` acepta ese campo por ítem), no requiere plugin nuevo.
- **Alternativas consideradas**: ninguna — es la extensión mínima natural del componente ya
  existente.

## Decisión 5 — Disponibilidad (spec 020) solo considera festivos "Oficial"

- **Decisión**: `availability_service.py::_has_holiday_today` (y el repo que le da la lista de
  festivos) filtran por `category == 'oficial'` antes de evaluar si el recurso está disponible.
  Los festivos "Regional/Religioso" nunca entran a ese cálculo — cumple FR-007.
- **Rationale**: es el único punto del dominio que necesita distinguir categoría; el resto del
  sistema (calendario visual) simplemente muestra ambas categorías con color distinto. Cambio
  aislado a una función pura ya cubierta por test unitario existente
  (`backend/tests/domain/test_availability_service.py`), se agregan casos nuevos ahí mismo.
- **Alternativas consideradas**: filtrar en el repositorio (SQL `WHERE category = 'oficial'`) en
  vez del dominio — rechazada, `compute_availability` ya es la función pura testeada que decide
  reglas de negocio (Principio I); mover el filtro a SQL dispersaría la regla fuera del dominio.

## Decisión 6 — Edición manual bloquea sobrescritura futura vía el campo `source`

- **Decisión**: cualquier operación de escritura sobre un festivo hecha por un Admin desde
  Maestros (crear, editar campos, activar/desactivar) fija `source='manual'` en esa fila. La
  tarea de sincronización **nunca** actualiza una fila con `source='manual'` — solo inserta
  festivos nuevos que no colisionen por `(country, holiday_date, name)` con uno ya existente, y
  solo actualiza/reinstala filas que ella misma creó (`source='api'`) previamente.
- **Rationale**: cumple FR-009 con un único flag, sin necesitar un historial de ediciones. Reusa
  el mismo criterio de "colisión" que ya usa `HolidayRepository.exists()` (spec 020, T037) para
  evitar duplicados al crear festivos manualmente.
- **Alternativas consideradas**: tabla de auditoría de cambios por festivo — rechazada, over-
  engineering para lo que pide el spec (solo "no sobrescribir lo editado a mano").

## Decisión 7 — Cumpleaños: computados en frontend desde `Resource.birth_date`, sin tabla ni
dependencia nueva

- **Decisión**: no se persiste ningún registro nuevo. `CalendarPage.tsx` (pestaña Equipo), que ya
  carga la lista de `Resource` completa (incluye `birth_date`, campo ya expuesto por
  `GET /api/resources`), genera del lado del cliente un evento de FullCalendar por cada año
  visible en una ventana razonable (año actual ± 2) a partir del día/mes de `birth_date` de cada
  recurso seleccionado, con color/ícono propio (🎂) distinto de los festivos. Sin backend nuevo.
- **Rationale**: `birth_date` ya es un dato existente del Recurso (Constitución, sección
  "Recursos"); no hay necesidad de tocar el dominio ni la base de datos. Generar instancias para
  una ventana de años fija es suficientemente simple para el patrón de navegación mes-a-mes de
  FullCalendar `dayGridMonth`, sin agregar el plugin `@fullcalendar/rrule` (evento recurrente
  "de verdad").
- **Alternativas consideradas**: agregar `@fullcalendar/rrule` para eventos recurrentes nativos —
  rechazada por Principio V (nueva dependencia sin necesidad real: la ventana de años fija ya
  resuelve el caso de uso de navegar el calendario sin tener que sincronizar cumpleaños en cada
  cambio de mes); persistir cumpleaños como filas de `holidays` — rechazada, un cumpleaños no es
  un festivo de país, es un evento por Recurso, mezclarlo violaría el modelo `holidays`
  (país-céntrico) y su relación con disponibilidad/festivos oficiales.

## Decisión 8 — RLS: `holiday_sync_status` sin RLS, igual que `holidays`

- **Decisión**: `holiday_sync_status` no lleva Row Level Security, igual que `holidays` y
  `work_schedules` (spec 020, Decisión 6 de su research.md).
- **Rationale**: es una tabla puramente operativa (estado de sincronización por país/año), no
  contiene datos sensibles ni pertenece a un usuario específico — no aplica el criterio de
  Principio IV que exige RLS en tablas con datos sensibles.
- **Alternativas consideradas**: ninguna — mismo precedente ya fijado en spec 020.
