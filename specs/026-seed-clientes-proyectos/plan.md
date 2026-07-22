# Implementation Plan: Script de Datos Semilla — Clientes Aris y Vaxthera

**Branch**: `026-seed-clientes-proyectos` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/026-seed-clientes-proyectos/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Un único script Python, ejecutable con `docker exec sywork_backend python -m backend.scripts.seed_clients_aris_vaxthera`,
que crea (de forma idempotente, `get_or_create`) los clientes Aris (Colombia, `America/Bogota`) y
Vaxthera (Ecuador, `America/Guayaquil`), sus proyectos, los 3 usuarios "Usuario/cliente" con acceso
a esos proyectos, la matriz de SLA de 4 niveles del proyecto Soporte de Aris (Evolutivo/Preventa de
Aris y Soporte de Vaxthera quedan sin filas de SLA) y las Listas de Tareas de cada proyecto Soporte.
Sigue exactamente el patrón ya existente de `backend/scripts/seed_tickets.py` (repositorios de
dominio + `get_db()`/`close_db()`), sin migraciones de Alembic ni cambios de esquema.

## Technical Context

**Language/Version**: Python 3.12 (mismo runtime que `backend/`, sin dependencias nuevas)

**Primary Dependencies**: SQLAlchemy (repositorios ya existentes), `werkzeug.security.generate_password_hash`
(mismo mecanismo de hash que la migración `009_roles_permissions_login.py` y el flujo de reseteo de
spec 003) — ninguna dependencia nueva a `requirements.txt` (Principio V)

**Storage**: PostgreSQL 16 (contenedor `sywork_backend`/`sywork_db` vía Docker Compose), tablas ya
existentes (`clients`, `projects`, `users`, `project_members`, `sla_rules`, `task_lists`) — sin
migración de esquema nueva

**Testing**: Ejecución manual del script contra el entorno Docker de desarrollo + verificación visual
en Maestros > Clientes/Proyectos y en la pantalla de Listas de Tareas (Principio VII: sin suite de
pruebas unitarias masiva; el script en sí no crea más de los ~16 registros maestros aquí listados)

**Target Platform**: Backend Flask corriendo en el contenedor Docker `sywork_backend` (Linux)

**Project Type**: Script CLI interno de un solo uso (seeder), dentro del backend existente — no es
un servicio ni expone endpoint

**Performance Goals**: N/A (script de un solo uso, ~16 registros maestros en total)

**Constraints**: Debe ser re-ejecutable sin duplicar datos (FR-012); no debe tocar tablas
transaccionales (tickets/tareas/registros de tiempo, FR-013); no debe crear dependencias nuevas
(Principio V)

**Scale/Scope**: 2 clientes, 4 proyectos, 3 usuarios, 4 filas de SLA (solo Aris/Soporte), 13 listas
de tareas (8 + 5)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I/II (API-first, Clean Architecture)**: cumple — el script vive en `backend/scripts/`
  (mismo nivel que `seed_tickets.py`) y usa exclusivamente entidades de dominio (`backend/domain/`)
  y repositorios de infraestructura (`backend/infra/repositories/`) ya existentes; no añade lógica de
  negocio nueva ni expone un endpoint (no aplica: es una herramienta de datos, no una funcionalidad
  de producto).
- **Principio III (Tipado estricto)**: cumple — Python con type hints en las funciones del script,
  igual que `seed_tickets.py`; no hay código TypeScript involucrado.
- **Principio IV (Seguridad)**: cumple — las contraseñas iniciales se generan con
  `generate_password_hash` (nunca en texto plano en el script) y no se comitea ningún secreto; el
  script corre dentro del contenedor backend, nunca desde el navegador.
- **Principio V (Gobernanza de librerías)**: cumple — cero dependencias nuevas; reutiliza
  SQLAlchemy/Werkzeug ya aprobados.
- **Principio VII (Alcance de sesión y testing ultra-limitado)**: cumple — el script solo toca los
  ~16 registros maestros explícitamente listados en la spec, no ejecuta la suite de pruebas global, y
  la sesión se limita a este único archivo nuevo (sin refactors externos).

Sin violaciones. No aplica tabla de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/026-seed-clientes-proyectos/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No se genera `contracts/`: el script no expone una API ni una interfaz pública nueva — es una
herramienta interna de un solo uso invocada por línea de comandos dentro del contenedor backend.

### Source Code (repository root)

```text
backend/
├── scripts/
│   ├── seed_tickets.py                       # patrón existente que este script sigue
│   └── seed_clients_aris_vaxthera.py         # NUEVO — único archivo de código de esta feature
├── domain/entities/                          # sin cambios: Client, Project, User, SlaRule, TaskList
│   ├── client.py
│   ├── project.py
│   ├── user.py
│   ├── sla_rule.py
│   ├── project_member.py
│   └── task_list.py
└── infra/repositories/                       # sin cambios: repos ya existentes, reutilizados
    ├── client_repo.py
    ├── project_repo.py
    ├── user_repo.py
    ├── role_repo.py
    ├── project_member_repo.py
    ├── sla_rule_repo.py
    └── task_list_repo.py
```

**Structure Decision**: Un único archivo nuevo, `backend/scripts/seed_clients_aris_vaxthera.py`,
siguiendo al pie de la letra el patrón de `backend/scripts/seed_tickets.py` (mismo estilo de
`main()`, `get_db()`/`close_db()`, `get_by_x(...) or repo.create(Entity.create(...))` para
idempotencia). No se toca ninguna otra capa: no hay migración de Alembic nueva (no hay cambio de
esquema, solo de datos), no hay endpoint nuevo, no hay componente de frontend. Esto respeta el
Principio VII (alcance de sesión limitado a un archivo).

## Complexity Tracking

No aplica — el Constitution Check no reporta violaciones que requieran justificación.
