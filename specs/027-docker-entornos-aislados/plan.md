# Implementation Plan: Configuración de Entornos Aislados (Test y Producción) en Docker Compose

**Branch**: `develp_Jp` (sin rama de feature dedicada — convención del proyecto, ver `CLAUDE.md`) | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/027-docker-entornos-aislados/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Hoy `docker-compose.yml` (raíz del repo) es un único stack de desarrollo con nombres de
contenedor, puertos y variables fijos (`sywork_db:5432`, `sywork_backend:5000`,
`sywork_frontend:5173`, `sywork_redis:6379`, `sywork_worker`), leídos de un único `.env`. No hay
forma de correr dos copias de ese stack en el mismo host sin colisión de puertos, nombres de
contenedor y volúmenes.

Enfoque técnico: **parametrizar el `docker-compose.yml` existente** (no duplicarlo) para que
puertos publicados y nombres de contenedor se resuelvan desde variables de entorno con valores
por defecto que preservan el comportamiento actual de desarrollo. Dos archivos de entorno nuevos
(`.env.test`, `.env.prod`, ambos ignorados por git como ya lo es `.env`) fijan esos valores por
ambiente. El aislamiento de red y de volúmenes se logra reutilizando el mecanismo nativo de
Docker Compose de namespacing por **nombre de proyecto** (`-p` / `COMPOSE_PROJECT_NAME`), que ya
evita colisiones de red/volumen automáticamente en cuanto Test y Producción se levantan con
nombres de proyecto distintos — el único obstáculo real hoy es que `container_name` está
hardcodeado por servicio y por eso sí hay que parametrizarlo explícitamente. La documentación de
arranque/parada/logs por ambiente se agrega como sección nueva dentro de `README.md`.

Fuera de alcance (confirmado en `spec.md`): terminación TLS/HTTPS de Producción (pendiente del
`TODO(HOSTING)` de la Constitución) y cualquier cambio a los Dockerfiles de desarrollo
(`flask run --reload`, `vite dev`) hacia servidores de grado producción (gunicorn / build
estático) — ese trabajo ya está mapeado, sin implementar, en
`docs/GUIA_DESPLIEGUE_SYWORK_TICKETS.txt` (sección 4) y no es parte de esta feature.

## Technical Context

**Language/Version**: N/A — no se agrega ni modifica código de aplicación (Python 3.12 / TS ya
existentes no cambian). Cambios son de configuración: YAML de Docker Compose, archivos `.env.*` y
Markdown.

**Primary Dependencies**: Docker Engine + Docker Compose v2 (ya aprobados en la Constitución,
Principio V — "Infraestructura"). No se agrega ninguna dependencia nueva a
`requirements.txt`/`package.json`.

**Storage**: PostgreSQL 16 (sin cambios de esquema) — cada ambiente usa su propia instancia de
contenedor y su propio volumen nombrado (namespacing automático por nombre de proyecto de
Compose), no una base compartida con esquemas separados.

**Testing**: No aplica un framework de pruebas automatizadas para configuración de
infraestructura. Validación mediante `docker compose config` (valida sintaxis/interpolación) y
los pasos manuales de `quickstart.md` (arranque concurrente de ambos ambientes, verificación de
aislamiento de datos, logs y parada independiente). Consistente con el Principio VII (alcance de
sesión ultra-limitado): no se ejecuta la suite de pytest/tsc para este cambio, que no toca código
de aplicación.

**Target Platform**: Servidor Ubuntu (24.04 LTS recomendado, 22.04 LTS aceptado) — ya documentado
como plataforma objetivo en `docs/GUIA_DESPLIEGUE_SYWORK_TICKETS.txt` (sección 2). Docker Compose
es multiplataforma; los comandos de la documentación se dan en sintaxis `bash` para Ubuntu.

**Project Type**: Cambio de configuración/infraestructura sobre una aplicación web ya existente
(no es un proyecto nuevo). No introduce estructura de código nueva (`src/`, `backend/`,
`frontend/` no cambian).

**Performance Goals**: N/A — no hay objetivo de rendimiento de aplicación; el único requisito de
desempeño operativo es que ambos ambientes puedan correr simultáneamente en el hardware ya
dimensionado en la guía de despliegue (mínimo 2 vCPU/4 GB RAM, recomendado 4 vCPU/8 GB RAM),
notando que correr **dos** stacks completos duplica el consumo de RAM/CPU respecto a un solo
ambiente — se documenta como nota operativa en `quickstart.md`, no como un requisito nuevo a
diseñar.

**Constraints**: Los puertos por defecto de Test y Producción deben coincidir con los ejemplos
del requerimiento original y no colisionar entre sí en el mismo host; los archivos `.env.test`/
`.env.prod` nunca deben quedar versionados en git (Constitución, Principio IV).

**Scale/Scope**: Un solo host Ubuntu corriendo hasta 2 stacks Docker Compose completos en
paralelo (Test: 5 contenedores: db/backend/frontend/redis/worker; Producción: los mismos 5),
~10-30 usuarios internos según el dimensionamiento ya documentado.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Aplica | Evaluación |
|---|---|---|
| I. API-First y Dominio Primero | No | Esta feature no toca `backend/domain/`, `backend/api/` ni ningún contrato Swagger. Sin impacto. |
| II. Clean Architecture — 3 capas | No | No se agrega ni mueve código en `backend/domain/`, `backend/infra/`, `backend/api/` ni `frontend/src/`. Sin impacto. |
| III. Tipado estricto | No | No hay código TypeScript/Python nuevo. Sin impacto. |
| IV. Seguridad en profundidad (NON-NEGOTIABLE) | **Sí** | Dos sub-gates: (a) `.env.test`/`.env.prod` contienen secretos (credenciales BD, `JWT_SECRET`, credenciales SMTP/OAuth) → **deben** agregarse a `.gitignore` igual que `.env` — verificado como tarea explícita de Fase 1/implementación, no opcional. (b) HTTPS/TLS obligatorio en producción — la feature **no** viola este principio porque no expone Producción al usuario final directamente: los puertos de Compose son mapeo interno y la terminación TLS queda expresamente fuera de alcance y documentada como pendiente (`TODO(HOSTING)`), decisión ya confirmada por el usuario en `spec.md` (FR-011, Assumptions). PASA con la tarea de `.gitignore` como parte obligatoria de la implementación. |
| V. Gobernanza de librerías | Sí (verificación) | No se agrega ninguna dependencia a `requirements.txt` ni `package.json`. Docker/Docker Compose ya están en el "Stack completo aprobado > Infraestructura". PASA sin nuevas aprobaciones. |
| VI. AI-Native | No | Sin impacto — no toca endpoints de acción, comentarios ni Gold Standard Dataset. |
| VII. Alcance de sesión / testing ultra-limitado (NON-NEGOTIABLE) | **Sí** | El cambio se acota estrictamente a `docker-compose.yml`, `.gitignore`, `.env.test.example`/`.env.prod.example` (plantillas) y una sección nueva en `README.md` — ningún archivo de `backend/`/`frontend/` se toca. No se ejecuta la suite completa de tests (no aplica, no hay código de aplicación modificado). PASA. |

**Resultado**: PASA sin violaciones. No se requiere tabla de "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/027-docker-entornos-aislados/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output — sin entidades nuevas (feature de infraestructura)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── checklists/
    └── requirements.md  # Ya generado por /speckit-specify
```

No se genera `contracts/`: esta feature no expone ni modifica ninguna interfaz externa (API,
CLI, esquema) — es configuración de despliegue interna, consistente con la guía del template
("Skip if project is purely internal").

### Source Code (repository root)

Esta feature **no** introduce una estructura de código nueva. Los únicos archivos afectados están
en la raíz del repositorio y en documentación:

```text
TICKET_SYW/
├── docker-compose.yml         # MODIFICADO: puertos, container_name y VITE_API_URL parametrizados
│                               # por env vars (valores por defecto = los actuales, no rompe
│                               # `docker compose up` con el .env de desarrollo existente);
│                               # POSTGRES_DB/USER/PASSWORD/JWT_SECRET con ${VAR:?...} (fallo
│                               # explícito si faltan, ver research.md Decisiones 7 y 8)
├── .env.example                # SIN CAMBIOS (ya existe, plantilla de desarrollo)
├── .env.test.example           # NUEVO: plantilla trackeada en git (sin secretos reales)
├── .env.prod.example           # NUEVO: plantilla trackeada en git (sin secretos reales)
├── .env.test                   # NUEVO en el servidor Ubuntu — NUNCA en git (agregar a .gitignore)
├── .env.prod                   # NUEVO en el servidor Ubuntu — NUNCA en git (agregar a .gitignore)
├── .gitignore                  # MODIFICADO: agregar .env.test y .env.prod
└── README.md                   # MODIFICADO: nueva subsección "Entornos Test y Producción"
                                 # dentro de "Instalación y despliegue"

backend/    # sin cambios
frontend/   # sin cambios
```

**Structure Decision**: Un único `docker-compose.yml` parametrizado (no dos archivos compose
duplicados) + dos archivos de entorno (`.env.test`, `.env.prod`) + namespacing nativo de Docker
Compose por nombre de proyecto (`-p sywork_test` / `-p sywork_prod`). Ver `research.md` para la
comparación de alternativas consideradas y el detalle de qué variables se agregan.

## Complexity Tracking

*Sin violaciones de la Constitución — tabla no aplica.*
