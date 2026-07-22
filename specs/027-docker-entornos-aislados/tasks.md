---

description: "Task list for Configuración de Entornos Aislados (Test y Producción) en Docker Compose"
---

# Tasks: Configuración de Entornos Aislados (Test y Producción) en Docker Compose

**Input**: Design documents from `/specs/027-docker-entornos-aislados/`

**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (required for user stories), [research.md](research.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md)

**Tests**: No se generan tareas de test automatizado — esta feature es configuración de
infraestructura (Docker Compose + `.env.*` + docs), sin código de aplicación. La validación es
manual, vía los escenarios de `quickstart.md` (ver `plan.md`, Technical Context > Testing).

**Organization**: Tareas agrupadas por historia de usuario (US1/US2/US3, prioridad P1/P2/P3 de
`spec.md`) para permitir implementación y validación independiente de cada una.

> Revisado por `/speckit-analyze` (2026-07-22): se agregaron T004 y T005 en Foundational para
> cerrar dos hallazgos (E1 crítico: `VITE_API_URL` no estaba parametrizado; E2 alto: FR-010 no
> tenía cobertura para "variable obligatoria faltante", solo "archivo faltante"). Ver
> `research.md` Decisiones 7 y 8.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece la tarea (US1, US2, US3)
- Cada tarea incluye la ruta de archivo exacta

## Path Conventions

Esta feature no usa `src/`/`tests/` — los archivos afectados están en la raíz del repositorio
(`docker-compose.yml`, `.gitignore`, `.env.*.example`, `README.md`), consistente con
`plan.md` > Project Structure.

---

## Phase 1: Setup

**Purpose**: Establecer una línea base verificable antes de tocar `docker-compose.yml`

- [X] T001 Capturar la salida actual de `docker compose config` (con el `.env` de desarrollo tal
      cual existe hoy) sobre `docker-compose.yml`, para poder comparar después que el
      comportamiento por defecto no cambió (puertos `5173`/`5000`/`5432`/`6379`, nombres de
      contenedor `sywork_db`/`sywork_backend`/`sywork_frontend`/`sywork_redis`/`sywork_worker`,
      `VITE_API_URL=http://localhost:5000`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Mecanismo compartido del que dependen las 3 historias de usuario — parametrizar el
único `docker-compose.yml` y blindar el `.gitignore` antes de que exista ningún `.env.test`/
`.env.prod` real

**⚠️ CRITICAL**: Ninguna historia de usuario puede completarse hasta que esta fase termine

- [X] T002 Parametrizar los puertos publicados en `docker-compose.yml`: `${POSTGRES_PORT:-5432}:5432`
      (servicio `postgres`), `${BACKEND_PORT:-5000}:5000` (servicio `backend`),
      `${FRONTEND_PORT:-5173}:5173` (servicio `frontend`), `${REDIS_PORT:-6379}:6379` (servicio
      `redis`) — los defaults deben preservar exactamente el comportamiento actual
- [X] T003 Parametrizar `container_name` en `docker-compose.yml` para los 5 servicios
      (`postgres`, `backend`, `frontend`, `redis`, `worker`) usando `${CONTAINER_SUFFIX:-}`
      (ej. `container_name: sywork_db${CONTAINER_SUFFIX}`), de forma que con el default vacío los
      nombres actuales (`sywork_db`, `sywork_backend`, ...) no cambien
- [X] T004 Parametrizar `VITE_API_URL` en el servicio `frontend` de `docker-compose.yml`:
      cambiar el valor literal `http://localhost:5000` por
      `${VITE_API_URL:-http://localhost:5000}` (mismo default, no rompe desarrollo local) — sin
      esta tarea, el frontend de cualquier ambiente seguiría llamando siempre al puerto `5000` sin
      importar lo que diga `.env.test`/`.env.prod` (hallazgo `/speckit-analyze` E1, ver
      `research.md` Decisión 7)
- [X] T005 Convertir a sintaxis de fallo obligatorio (`${VAR:?mensaje}`) las variables sin default
      razonable en `docker-compose.yml`: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
      (servicio `postgres`) y `JWT_SECRET` (servicios `backend` y `worker`) — aplicar en **todas**
      las líneas donde aparecen, incluida la construcción de `DATABASE_URL` en `backend` y
      `worker` (hallazgo `/speckit-analyze` E2, FR-010, ver `research.md` Decisión 8)
- [X] T006 [P] Agregar `.env.test` y `.env.prod` a `.gitignore` en la raíz del repo (nunca deben
      quedar versionados — Constitución, Principio IV)
- [X] T007 Ejecutar `docker compose config` sobre el `docker-compose.yml` ya parametrizado, sin
      pasar `--env-file` ni `-p`, y confirmar que coincide con la línea base capturada en T001
      (regresión: el flujo de desarrollo local existente no debe verse afectado)

**Checkpoint**: El compose file soporta ambos ambientes por variables (puertos, nombre de
contenedor, `VITE_API_URL`) y falla explícitamente si faltan secretos obligatorios; las 3
historias de usuario pueden avanzar (US1 y US2 en paralelo si hay más de una persona; US3 depende
de tener al menos un ambiente arriba para validarse end-to-end, ver sección de Dependencias)

---

## Phase 3: User Story 1 - Levantar y validar el ambiente de Test sin afectar Producción (Priority: P1) 🎯 MVP

**Goal**: Un operador puede levantar el ambiente de Test con sus propios puertos y su propio
archivo de variables, sin tocar Producción.

**Independent Test**: Levantar únicamente el ambiente de Test (`docker compose -p sywork_test
--env-file .env.test up -d`) y confirmar que responde en sus puertos alternativos, usando solo
datos/configuración de `.env.test` — sin que Producción esté corriendo.

### Implementation for User Story 1

- [X] T008 [P] [US1] Crear `.env.test.example` en la raíz del repo (plantilla trackeada, sin
      secretos reales) con `FRONTEND_PORT=8080`, `BACKEND_PORT=3001`, `POSTGRES_PORT=5433`,
      `REDIS_PORT=6380`, `CONTAINER_SUFFIX=_test`, `VITE_API_URL=http://localhost:3001`, `TZ`, y
      placeholders para el resto de variables ya usadas por `docker-compose.yml` (`POSTGRES_DB`,
      `POSTGRES_USER`, `POSTGRES_PASSWORD`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`,
      `GOOGLE_CLIENT_SECRET`, `FLASK_ENV`, `DEV_SKIP_AUTH`, `FRONTEND_URL`, `SMTP_HOST`,
      `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`), siguiendo el mismo patrón que
      `.env.example`
- [X] T009 [US1] Agregar la subsección "Ambiente de Test" dentro de "Instalación y despliegue" en
      `README.md`, documentando `docker compose -p sywork_test --env-file .env.test up --build -d`
      y las URLs resultantes (app `:8080`, API `:3001`)
- [X] T010 [US1] Ejecutar el Escenario 1 de `quickstart.md` contra un host Docker real y confirmar
      que los 5 servicios de Test quedan `Up` respondiendo en sus puertos designados, **incluida**
      la verificación de que `VITE_API_URL` del frontend de Test apunta a `:3001` (no a `:5000`) —
      validado en vivo: `sywork_db_test`/`sywork_backend_test`/`sywork_frontend_test`/
      `sywork_redis_test`/`sywork_worker_test` `Up`, `/health/` reporta BD `sywork_tickets_test`
      aislada, frontend `HTTP 200` en `:8080`, `VITE_API_URL=http://localhost:3001` confirmado
      dentro del contenedor

**Checkpoint**: El ambiente de Test es completamente funcional y validable de forma independiente

---

## Phase 4: User Story 2 - Levantar el ambiente de Producción de forma aislada (Priority: P2)

**Goal**: Un operador puede levantar el ambiente de Producción con sus puertos principales y su
propio archivo de variables, sin que el estado de Test lo afecte.

**Independent Test**: Levantar únicamente el ambiente de Producción (`docker compose -p
sywork_prod --env-file .env.prod up -d`) y confirmar que responde en sus puertos principales,
usando solo datos/configuración de `.env.prod`, con o sin Test corriendo en paralelo.

### Implementation for User Story 2

- [X] T011 [P] [US2] Crear `.env.prod.example` en la raíz del repo (plantilla trackeada, sin
      secretos reales) con `FRONTEND_PORT=80`, `BACKEND_PORT=3000`, `POSTGRES_PORT=5432`,
      `REDIS_PORT=6379`, `CONTAINER_SUFFIX=_prod`, `VITE_API_URL=http://localhost:3000`, `TZ`, y
      el mismo conjunto de variables de aplicación que `.env.test.example` (T008)
- [X] T012 [US2] Agregar la subsección "Ambiente de Producción" dentro de "Instalación y
      despliegue" en `README.md`, documentando `docker compose -p sywork_prod --env-file
      .env.prod up --build -d`, las URLs resultantes (app `:80`, API `:3000`), y la nota explícita
      de que la terminación TLS/proxy inverso queda pendiente (`TODO(HOSTING)`, ver
      `docs/GUIA_DESPLIEGUE_SYWORK_TICKETS.txt`)
- [X] T013 [US2] Ejecutar los Escenarios 2 (levantar Producción con Test ya corriendo) y 3
      (crear un dato en Test y confirmar que no aparece en Producción) de `quickstart.md` contra
      un host Docker real, **incluida** la verificación de que `VITE_API_URL` del frontend de
      Producción apunta a `:3000` (independiente del de Test) — **nota**: validado solo vía
      `docker compose -p sywork_prod --env-file .env.prod config` (puertos `80`/`3000`/`5432`/
      `6379`, nombres `sywork_*_prod`, `VITE_API_URL=http://localhost:3000`, `TZ` propagado),
      **sin** `up` real, por decisión explícita del usuario: esta máquina de desarrollo ya tenía
      el stack de dev corriendo en los puertos `5432`/`6379` que Producción reutiliza a propósito
      (mismos "puertos principales"), y un `up` real habría colisionado con él. El aislamiento de
      datos (Escenario 3) queda demostrado estructuralmente por Test corriendo en paralelo con el
      stack de dev sin colisión (BD `sywork_tickets_test` vs `sywork_tickets`, contenedores y
      volumen namespaced distintos) — no por una comparación literal Test-vs-Prod en vivo. Repetir
      con un `up` real de `sywork_prod` en el servidor Ubuntu real (sin stack de dev de por medio)
      antes de dar la Delivery por cerrada.

**Checkpoint**: Test y Producción funcionan simultáneamente, cada uno de forma independiente

---

## Phase 5: User Story 3 - Detener y revisar logs de un ambiente específico de forma segura (Priority: P3)

**Goal**: Un operador puede detener y consultar logs de un ambiente puntual (Test o Producción)
de forma explícita, sin riesgo de afectar el otro por error.

**Independent Test**: Con ambos ambientes corriendo, ejecutar `logs`/`down` nombrando
explícitamente un ambiente y verificar que solo ese ambiente se ve afectado.

### Implementation for User Story 3

- [X] T014 [US3] Agregar la subsección "Logs y parada por ambiente" a `README.md`, documentando
      `docker compose -p <sywork_test|sywork_prod> --env-file <.env.test|.env.prod> logs -f
      [servicio]` y `... down`, con una advertencia explícita de que omitir `-p`/`--env-file`
      apunta al stack equivocado (mitiga el edge case de detener Producción por error)
- [X] T015 [US3] Ejecutar los Escenarios 4 (logs y parada aislados) y 5 (fallo explícito —
      5a archivo `.env.test` faltante, 5b variable obligatoria como `JWT_SECRET` faltante dentro
      de un archivo presente) de `quickstart.md` contra un host Docker real — validado: logs de
      `sywork_test` no se mezclan con el stack de dev; 5a falla con
      `couldn't find env file: .env.test`; 5b falla con `required variable JWT_SECRET is missing
      a value` citando la variable exacta — ningún contenedor arranca con secreto vacío en
      ninguno de los dos casos

**Checkpoint**: Las 3 historias de usuario son funcionales y validables de forma independiente

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consistencia documental y regresión final una vez completadas las 3 historias

- [X] T016 [P] Referenciar cruzadamente la nueva sección de `README.md` ("Entornos Test y
      Producción") desde `docs/GUIA_DESPLIEGUE_SYWORK_TICKETS.txt` (o viceversa), evitando
      duplicar la guía de Ubuntu/firewall/TLS ya existente en ese documento
- [X] T017 Ejecutar `quickstart.md` completo de punta a punta (Escenarios 1–5, incluidas las
      sub-verificaciones de `VITE_API_URL` y de variable obligatoria faltante) como regresión
      final una vez que T001–T015 están completas — completado dentro de T001-T015 (ver notas de
      T013/T015); stack de Test desmontado (`down`, sin `-v`) al terminar, stack de dev original
      confirmado intacto. **Pendiente**: repetir el Escenario 2/3 con un `up` real de
      `sywork_prod` en el servidor Ubuntu de destino (sin stack de dev de por medio) antes de
      aceptar esta feature como Delivery — ver nota en T013

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — puede iniciar de inmediato
- **Foundational (Phase 2)**: Depende de Setup (T001) — BLOQUEA las 3 historias de usuario
- **User Stories (Phase 3-5)**: Todas dependen de que Foundational (Phase 2) esté completo
  - US1 (T008-T010) y US2 (T011-T013) son independientes entre sí — pueden avanzar en paralelo
  - US3 (T014-T015) documenta el patrón de comandos con independencia de US1/US2, pero su
    **validación real** (T015, Escenario 4) requiere que Test y Producción ya estén arriba y
    funcionando — depende en la práctica de que T010 y T013 se hayan ejecutado antes
- **Polish (Phase 6)**: Depende de que las 3 historias estén completas (T001-T015)

### Within Each User Story

- US1: T008 (plantilla) antes de T009 (docs) antes de T010 (validación) — mismo orden lógico en
  US2 (T011 → T012 → T013) y US3 (T014 → T015)

### Parallel Opportunities

- T002, T003, T004 y T005 tocan el **mismo** `docker-compose.yml` — **no** son paralelas entre sí,
  deben aplicarse en secuencia
- T006 (`.gitignore`) puede correr en paralelo con T002-T005 (archivo distinto)
- T008 [US1] y T011 [US2] pueden correr en paralelo (archivos `.env.test.example` /
  `.env.prod.example` distintos, ambas solo dependen de Foundational)
- T009, T012 y T014 **no** son paralelas entre sí aunque pertenecen a historias distintas: las
  tres editan `README.md` (riesgo de conflicto de merge si se editan a la vez)
- Con más de una persona: US1 y US2 completas pueden trabajarse en paralelo por dos
  desarrolladores distintos una vez cerrado Foundational; US3 se documenta en paralelo pero su
  validación final espera a que ambas terminen

---

## Parallel Example: Foundational + User Stories 1 y 2

```bash
# Tras completar T001-T007 (Foundational):
Task: "Crear .env.test.example con valores de Test (T008)"
Task: "Crear .env.prod.example con valores de Producción (T011)"
# Ambas pueden lanzarse a la vez — archivos distintos, sin dependencia entre sí
```

---

## Implementation Strategy

### MVP First (User Story 1 solamente)

1. Completar Phase 1: Setup (T001)
2. Completar Phase 2: Foundational (T002-T007) — CRÍTICO, bloquea todo lo demás
3. Completar Phase 3: User Story 1 (T008-T010)
4. **STOP y VALIDAR**: correr el Escenario 1 de `quickstart.md` de forma aislada
5. Con esto ya hay un ambiente de Test operativo y aislado — valor entregable por sí solo

### Incremental Delivery

1. Setup + Foundational → mecanismo base listo (puertos, nombres, `VITE_API_URL` y fallo
   explícito de secretos ya parametrizados)
2. + User Story 1 → Test operativo → validar (MVP)
3. + User Story 2 → Producción operativa en paralelo con Test → validar
4. + User Story 3 → documentación de logs/parada segura por ambiente → validar
5. Polish → referencias cruzadas de documentación + regresión final de `quickstart.md`

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes
- [Story] mapea cada tarea a su historia de usuario para trazabilidad
- No hay tareas de test automatizado (feature de infraestructura, ver `plan.md`)
- Commitear tras cada tarea o grupo lógico de tareas
- Evitar editar `docker-compose.yml` o `README.md` desde dos tareas a la vez (riesgo de conflicto)
