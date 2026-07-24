# Quickstart: Configuración de Entornos Aislados (Test y Producción) en Docker Compose

Guía de validación manual — confirma que Test y Producción corren simultáneamente en el mismo
servidor Ubuntu, aislados en puertos, variables y datos, y que se pueden operar (arrancar,
detener, ver logs) de forma independiente. No requiere pytest/tsc (esta feature no toca código de
aplicación — ver `plan.md`, Technical Context > Testing).

## Prerrequisitos

- Servidor Ubuntu (o entorno local equivalente) con Docker Engine + Docker Compose v2 instalados
  (`docker --version`, `docker compose version`).
- Repositorio clonado, en la raíz del repo.
- `.env.test` creado a partir de `.env.test.example` (valores reales de Test).
- `.env.prod` creado a partir de `.env.prod.example` (valores reales de Producción).
- Ambos archivos **no** deben aparecer en `git status` como trackeados (verificar que
  `.gitignore` los cubre).

## Escenario 1 — Levantar Test sin afectar Producción (US1)

```bash
docker compose -p sywork_test --env-file .env.test up --build -d
docker compose -p sywork_test --env-file .env.test ps
curl -I http://localhost:8080          # Frontend/App de Test
curl -I http://localhost:3001/health/  # Backend de Test
docker exec sywork_frontend_test env | grep VITE_API_URL   # debe apuntar a :3001, no a :5000
```

**Esperado**: los 5 servicios de Test quedan `Up`, responden en los puertos de `.env.test`, y (si
Producción no está corriendo aún) esto no falla por conflicto de puertos/nombres. El frontend de
Test tiene `VITE_API_URL` apuntando a **su propio** backend (`:3001`), no al puerto `5000` fijo
(ver `research.md`, Decisión 7).

> **Acceso remoto (navegador en otra máquina que el servidor Docker)**: `VITE_API_URL` se sirve al
> navegador y se ejecuta ahí, no dentro del contenedor — si el valor es `http://localhost:3001` y
> el usuario abre la app desde `http://<IP-del-servidor>:8080` en otra PC, "localhost" resuelve a
> su propia máquina y el login falla con `ERR_CONNECTION_REFUSED` (aunque Swagger, probado
> directo contra el servidor, funcione). En `.env.test`/`.env.prod` del servidor real, `VITE_API_URL`
> debe apuntar a la IP/host públicamente alcanzable del servidor (ej. `http://16.0.0.159:3001`), no
> a `localhost`. Como el frontend corre `pnpm run dev --host` (Vite dev server, ver
> `frontend/Dockerfile`), basta con corregir la variable y recrear el contenedor — no requiere
> `--build`: `docker compose -p sywork_test --env-file .env.test up -d --force-recreate frontend`.

## Escenario 2 — Levantar Producción en paralelo (US2)

```bash
docker compose -p sywork_prod --env-file .env.prod up --build -d
docker compose -p sywork_prod --env-file .env.prod ps
curl -I http://localhost:80            # Frontend/App de Producción
curl -I http://localhost:3000/health/  # Backend de Producción
docker exec sywork_frontend_prod env | grep VITE_API_URL   # debe apuntar a :3000, no a :5000 ni a Test
```

**Esperado**: los 5 servicios de Producción quedan `Up` en paralelo con los de Test (verificar con
`docker ps` que existen ambos juegos de contenedores, con nombres distintos, ej. `sywork_db_test`
y `sywork_db_prod`), sin que arrancar uno haya reiniciado o detenido el otro. El `VITE_API_URL` de
Producción apunta a su propio backend (`:3000`), independiente del de Test.

## Escenario 3 — Aislamiento de datos (US1 + US2, SC-003)

```bash
# Crear un dato de prueba en Test (ejemplo vía API o UI en :8080)
curl -X POST http://localhost:3001/api/... -d '...'   # cualquier escritura de ejemplo en Test

# Verificar que NO aparece en Producción
curl http://localhost:3000/api/...                     # el registro creado en Test no debe existir aquí
```

**Esperado**: cero cambios observables en Producción como resultado de la acción en Test (SC-003).

## Escenario 4 — Logs y parada aislados por ambiente (US3)

```bash
docker compose -p sywork_test --env-file .env.test logs -f backend    # solo logs de Test
docker compose -p sywork_test --env-file .env.test down               # detiene solo Test

docker compose -p sywork_prod --env-file .env.prod ps                 # Producción sigue "Up"
```

**Esperado**: los logs de Test no se mezclan con los de Producción; detener Test no afecta a
Producción (SC-005).

## Escenario 5 — Fallo explícito por configuración faltante (Edge case, FR-010)

**5a — Archivo de ambiente completo faltante**:

```bash
mv .env.test .env.test.bak
docker compose -p sywork_test --env-file .env.test up -d
```

**Esperado**: el comando falla de forma clara (Compose reporta el archivo faltante) en vez de
levantar servicios con variables vacías. Restaurar con `mv .env.test.bak .env.test` al terminar.

**5b — Archivo presente pero le falta una variable obligatoria**:

```bash
cp .env.test .env.test.bak2
grep -v '^JWT_SECRET=' .env.test.bak2 > .env.test   # simula JWT_SECRET faltante
docker compose -p sywork_test --env-file .env.test up -d
```

**Esperado**: el comando falla explícitamente citando `JWT_SECRET` (sintaxis `${JWT_SECRET:?...}`
en `docker-compose.yml`, ver `research.md` Decisión 8) — **no** debe arrancar ningún contenedor
con el secreto vacío. Repetir opcionalmente con `POSTGRES_PASSWORD`/`POSTGRES_USER`/`POSTGRES_DB`.
Restaurar con `mv .env.test.bak2 .env.test` al terminar.

## Limpieza

```bash
docker compose -p sywork_test --env-file .env.test down
docker compose -p sywork_prod --env-file .env.prod down
```

`down` (sin `-v`) conserva los volúmenes de datos de cada ambiente; agregar `-v` solo si se quiere
descartar los datos de ese ambiente en particular.

## Referencias

- Detalle de variables y puertos por ambiente: [research.md](research.md), Decisiones 3, 4, 7 y 8.
- Configuración de servidor Ubuntu, Docker, systemd y backups (aplica a ambos ambientes por
  igual, fuera del alcance de esta feature): `docs/GUIA_DESPLIEGUE_SYWORK_TICKETS.txt`.
