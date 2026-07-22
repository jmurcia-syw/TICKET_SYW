# Phase 0 Research: Configuración de Entornos Aislados (Test y Producción) en Docker Compose

No quedaron `[NEEDS CLARIFICATION]` en `spec.md` (la única duda, alcance de TLS, ya se resolvió
con el usuario — ver Assumptions y FR-011). Las decisiones de esta fase son técnicas (el "cómo"),
no de alcance.

## Decisión 1 — Un `docker-compose.yml` parametrizado, no dos archivos duplicados

**Decisión**: Parametrizar el `docker-compose.yml` único existente con variables de entorno para
puertos publicados y `container_name`, en vez de mantener `docker-compose.test.yml` +
`docker-compose.prod.yml` como archivos separados.

**Rationale**: El repo ya tiene un solo `docker-compose.yml` de referencia para los 5 servicios
(`postgres`, `backend`, `frontend`, `redis`, `worker`). Duplicarlo en dos archivos obligaría a
mantener sincronizados manualmente cualquier cambio futuro de imagen base, volúmenes o
`healthcheck` en dos lugares — alto riesgo de "drift" entre Test y Producción, justo lo opuesto a
lo que un ambiente de Test debe garantizar (que valida lo mismo que correrá en Producción). Un
solo archivo + interpolación de variables (`${VAR:-default}`) es el patrón idiomático de Docker
Compose para este caso exacto.

**Alternatives considered**:
- *Dos `docker-compose.*.yml` completos*: rechazado por duplicación y riesgo de drift.
- *`docker-compose.override.yml` + Compose merge*: más complejo de razonar para un cambio que es,
  en esencia, solo "puertos y nombres distintos"; el mecanismo de interpolación de variables ya
  resuelve el caso sin una segunda capa de merge de YAML.
- *Compose "profiles"*: profiles controla qué **servicios** arrancan (ej. incluir/excluir
  `worker`), no para qué ambiente corren — no resuelve el problema real (puertos/nombres/env).

## Decisión 2 — Aislamiento de red/volumen: namespacing nativo por nombre de proyecto

**Decisión**: Levantar cada ambiente con un nombre de proyecto Compose distinto
(`docker compose -p sywork_test ...` / `docker compose -p sywork_prod ...`, o equivalente vía
`COMPOSE_PROJECT_NAME` en el archivo de entorno). Docker Compose ya prefija automáticamente redes
y volúmenes **sin nombre explícito** con el nombre de proyecto (ej. `postgres_data` del compose
actual pasa a `sywork_test_postgres_data` / `sywork_prod_postgres_data`), sin necesidad de tocar
la sección `volumes:` del compose.

**Rationale**: Es el mecanismo nativo de Compose para exactamente este escenario (mismo compose
file, múltiples instancias aisladas en el mismo host) — cero código nuevo, cero riesgo de
colisión de volumen si cada ambiente usa su propio nombre de proyecto de forma consistente.

**Alternatives considered**:
- *Nombrar volúmenes/redes explícitamente por ambiente en el YAML* (`name: sywork_test_pgdata`):
  rechazado — requeriría además parametrizar esos nombres con variables (mismo resultado que el
  namespacing automático, con más líneas de configuración que mantener).

**Excepción real encontrada**: `container_name` **sí** está hardcodeado hoy para los 5 servicios
(`sywork_db`, `sywork_backend`, `sywork_frontend`, `sywork_redis`, `sywork_worker`) — Compose NO
aplica el prefijo de proyecto sobre un `container_name` explícito, así que sin cambiarlo ambos
ambientes competirían por el mismo nombre de contenedor y el segundo `up` fallaría. **Se
parametriza** `container_name` con la variable `CONTAINER_SUFFIX` (ej.
`container_name: sywork_db${CONTAINER_SUFFIX}`, con default `${CONTAINER_SUFFIX:-}` vacío para no
alterar los nombres actuales en desarrollo), preservando nombres legibles (referenciados en varios
docs del repo: `GUIA_DESPLIEGUE_SYWORK_TICKETS.txt`, `README.md`) en vez de dejar que Compose
genere nombres autoincrementales genéricos.

## Decisión 3 — Puertos por ambiente

**Decisión**: Se introducen variables de puerto con valores por defecto iguales a los actuales
(para no romper el flujo de desarrollo existente con el `.env` de hoy, que no pasa `-p` ni
`--env-file`), sobrescritas por cada archivo de ambiente:

| Variable | Default (dev actual, sin cambios) | `.env.prod` | `.env.test` |
|---|---|---|---|
| `FRONTEND_PORT` | `5173` | `80` | `8080` |
| `BACKEND_PORT` | `5000` | `3000` | `3001` |
| `POSTGRES_PORT` | `5432` | `5432` | `5433` |
| `REDIS_PORT` | `6379` | `6379` | `6380` |
| `COMPOSE_PROJECT_NAME` (flag `-p`) / `CONTAINER_SUFFIX` | (sin usar) / `` (vacío) | `sywork_prod` / `_prod` | `sywork_test` / `_test` |

**Rationale**: El requerimiento original da `8080` **o** `3001` como ejemplos para "Test" y `80`
**o** `3000` para "Producción", sin distinguir a qué servicio aplica cada uno. Se interpretan como
un par (no alternativas excluyentes): el puerto "clásico" de cada categoría (`80`/`8080`) para el
Frontend/App público, y el puerto "alto" (`3000`/`3001`) para el Backend/API — mismo patrón que ya
usa el propio ejemplo del usuario (`8080` guarda la misma relación con `80` que `3001` con
`3000`). `POSTGRES_PORT`/`REDIS_PORT` no estaban en el requerimiento explícito, pero **sí** son
necesarios para que ambos stacks convivan sin colisión (FR-001, FR-008) — se les asigna un puerto
secundario consecutivo, siguiendo la pista textual del propio requerimiento ("BD en puerto
secundario si aplica").

**Alternatives considered**:
- *No exponer Postgres/Redis fuera de Docker en ningún ambiente* (más seguro, ya recomendado para
  Producción en `docs/GUIA_DESPLIEGUE_SYWORK_TICKETS.txt` sección 4): se deja como **nota
  operativa** en `quickstart.md`/README (recomendar no publicar `POSTGRES_PORT` hacia afuera del
  firewall en Producción) en vez de forzarlo en el compose — el requerimiento original sí pide
  contemplar un puerto de BD ("si aplica"), así que la capacidad de exponerlo queda disponible
  pero el hardening de firewall sigue siendo responsabilidad operativa documentada, no un cambio
  de código.

## Decisión 4 — Variables cubiertas por `.env.test` / `.env.prod`

**Decisión**: Cada archivo de ambiente cubre el mismo conjunto de variables que ya usa
`docker-compose.yml` hoy (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `JWT_SECRET`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FLASK_ENV`, `DEV_SKIP_AUTH`, `FRONTEND_URL`,
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `VITE_API_URL`) más las
variables nuevas de puerto/proyecto de la Decisión 3. Para "configuración regional" (pedida
explícitamente en el requerimiento) se agrega `TZ` (zona horaria del contenedor) — hoy no existe
una variable de entorno regional dedicada; la app ya maneja zona horaria por Cliente/Calendario a
nivel de datos (Fase 5, specs `020`/`021`), independiente del ambiente de despliegue, así que
`TZ` a nivel de contenedor es el único knob "regional" que aplica en esta capa.

**Rationale**: Reutilizar el contrato de variables ya validado en producción (mismo
`docker-compose.yml`, mismas claves) minimiza sorpresas; no se inventa un esquema de
configuración paralelo.

**Nota de implementación**: para evitar repetir el mismo gap que la Decisión 7 (`VITE_API_URL`
documentado pero no interpolado), `TZ` se conectó explícitamente como
`TZ: ${TZ:-America/Bogota}` en los servicios `postgres`, `backend` y `worker` de
`docker-compose.yml` (no solo listado en los `.env.*.example`).

## Decisión 5 — `.gitignore` debe cubrir `.env.test` y `.env.prod`

**Decisión**: Agregar explícitamente `.env.test` y `.env.prod` a `.gitignore`. Se agregan además
`.env.test.example` y `.env.prod.example` (sin secretos reales, con placeholders) como plantillas
trackeadas en git, replicando el patrón ya usado por `.env.example`.

**Rationale**: Hallazgo directo al revisar `.gitignore` — hoy cubre `.env`, `.env.local` y
`.env.*.local`, pero **no** cubre `.env.test` ni `.env.prod` (el patrón `.env.*.local` no
matchea esos nombres). Sin este cambio, un `git add .` accidental commitearía secretos de
Test/Producción — violación directa del Principio IV (NON-NEGOTIABLE) de la Constitución.

## Decisión 6 — Dockerfiles de desarrollo se mantienen sin cambios en ambos ambientes

**Decisión**: Tanto Test como Producción, en el alcance de esta feature, siguen corriendo
`backend/Dockerfile` (`flask run --reload`) y `frontend/Dockerfile` (`vite dev`) — no se
introduce un Dockerfile de producción (gunicorn / build estático + nginx) como parte de este
trabajo.

**Rationale**: Ya está confirmado en `spec.md` (Assumptions) que el ciclo de vida de contenido de
prueba y el hardening de runtime quedan fuera de alcance — esta feature es exclusivamente
aislamiento de puertos/variables/datos entre ambientes, no maduración del stack de despliegue.
`docs/GUIA_DESPLIEGUE_SYWORK_TICKETS.txt` (sección 4 y 12) ya deja mapeado, sin implementar, el
trabajo pendiente de Dockerfiles de producción reales — se referencia desde el README como
siguiente paso, no se duplica aquí.

**Alternatives considered**: Construir ya los Dockerfiles de producción como parte de esta
feature — rechazado por alcance: el requerimiento original y la spec resultante piden
específicamente aislamiento de ambientes, no maduración del runtime; mezclar ambos esfuerzos
haría la feature más difícil de revisar y de revertir de forma independiente.

## Decisión 7 — `VITE_API_URL` del frontend también debe parametrizarse

**Decisión**: El servicio `frontend` de `docker-compose.yml` hoy fija
`VITE_API_URL: http://localhost:5000` como valor literal (no interpolado). Se cambia a
`VITE_API_URL: ${VITE_API_URL:-http://localhost:5000}`, con el mismo default que el valor actual
(no rompe desarrollo local), y cada `.env.test`/`.env.prod` fija su propio valor apuntando al
`BACKEND_PORT` de ese ambiente (ej. `http://localhost:3001` en Test, `http://localhost:3000` en
Producción).

**Rationale**: Hallazgo de `/speckit-analyze` (E1, CRÍTICO) — la Decisión 4 ya listaba
`VITE_API_URL` como parte del contrato de variables por ambiente, pero ninguna decisión anterior
cubría el cambio real en `docker-compose.yml` necesario para que ese valor tuviera efecto. Sin
este cambio, el frontend de **cualquier** ambiente seguiría llamando al backend en el puerto
`5000` fijo, sin importar qué diga `.env.test`/`.env.prod` — rompiendo en silencio el aislamiento
que es el propósito central de la feature (FR-005, SC-002).

## Decisión 8 — Variables sin default deben fallar explícitamente si faltan

**Decisión**: Las variables que no tienen (ni deben tener) un valor por defecto razonable —
`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `JWT_SECRET` — se interpolan en
`docker-compose.yml` con la sintaxis de fallo obligatorio de Compose, `${VAR:?mensaje}`, en
**todas** las líneas donde aparecen (`postgres.environment`, `backend.environment` +
`backend`'s `DATABASE_URL`, `worker.environment` + su propio `DATABASE_URL`), no solo en la
primera ocurrencia.

**Rationale**: Hallazgo de `/speckit-analyze` (E2, ALTO) — FR-010 exige que el sistema falle de
forma explícita si el archivo de ambiente existe pero le faltan variables obligatorias, no solo si
el archivo completo falta. Hoy `${VAR}` sin modificador, cuando la variable no está definida en el
`--env-file` usado, hace que Compose emita solo una **advertencia** y sustituya un string vacío —
los contenedores arrancan igual con un secreto en blanco (ej. `JWT_SECRET=""`), que es exactamente
el escenario que FR-010 pide evitar. `${VAR:?mensaje}` fuerza a Compose a abortar el `up` con un
error legible en ese caso.

**Alternatives considered**: Un script de pre-flight separado (`check-env.sh`) que valide el
archivo antes de invocar `docker compose up` — rechazado por ahora: agrega un artefacto nuevo
(script) a mantener y a documentar como paso adicional, cuando la sintaxis nativa de Compose ya
resuelve el mismo caso sin código extra. Se puede reconsiderar si en el futuro se necesita
validar reglas más complejas que un simple "está vacío o no".

## Resultado

Todas las decisiones técnicas quedaron resueltas sin `[NEEDS CLARIFICATION]` pendientes. Fase 1
(data-model.md, quickstart.md) puede proceder.
