# Implementation Plan: Reseteo de Contraseñas y Credenciales Semilla Estables

**Branch**: `003-reseteo-contrasenas` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-reseteo-contrasenas/spec.md`

## Summary

Tres piezas relacionadas, todas sobre el módulo de usuarios/autenticación ya existente
(`backend/api/routes/users.py`, `backend/api/routes/auth.py`, `backend/domain/services/auth_service.py`):

1. La migración semilla (009) deja de generar una contraseña aleatoria distinta en cada
   instalación de Desarrollo; usa una constante fija, documentada en un `.txt` versionado.
2. Un Admin puede resetear la contraseña de cualquier usuario real desde la UI existente de
   gestión de usuarios, reutilizando el patrón de "contraseña provisional mostrada una vez"
   que ya existe para la creación de usuarios.
3. Un usuario puede recuperar su propia contraseña por correo (token de un solo uso, 30 min
   de expiración), sin depender de un Admin.

## Technical Context

**Language/Version**: Python 3.12 + Flask (backend, ya en uso) / React 19 + TypeScript strict (frontend, ya en uso)

**Primary Dependencies**: Flask-RESTX, Flask-JWT-Extended, SQLAlchemy + Alembic, `werkzeug.security`
(hash ya usado por `AuthService`), `secrets` (stdlib), `smtplib` + `email.mime` (stdlib — **sin
dependencia nueva que aprobar**, Principio V)

**Storage**: PostgreSQL 16 — 2 columnas nuevas en `users` (`reset_token`, `reset_token_expires_at`)
vía migración Alembic; sin tablas nuevas

**Testing**: `pytest` (mismo patrón que `backend/tests/domain/` y `backend/tests/api/` ya existente)

**Target Platform**: Docker Compose on-premise (igual que el resto del proyecto)

**Project Type**: Web application (backend Flask + frontend React, estructura ya establecida)

**Performance Goals**: N/A — operaciones puntuales de bajo volumen (reseteo de contraseña, envío de un correo), no hay meta de throughput específica

**Constraints**: El envío de correo no debe bloquear la respuesta al usuario más de lo que tarda un `smtplib.send_message` normal (segundos, no hay SLA estricto en esta fase — ver Complexity Tracking sobre por qué no se usa Celery todavía)

**Scale/Scope**: 3 endpoints nuevos/modificados en `users.py`/`auth.py`, 1 migración de datos (seed fijo) + 1 migración de esquema (columnas de token), 2 pantallas frontend nuevas/ampliadas (`UsersPage.tsx`, `LoginPage.tsx` + pantalla `ResetPasswordPage.tsx`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumple | Notas |
|---|---|---|
| I. API-First y Dominio Primero | Sí | Contratos documentados en `contracts/` antes de implementar; reglas de expiración/uso único del token viven en `backend/domain/services/auth_service.py` (Capa 1), no en las rutas |
| II. Clean Architecture 3 capas | Sí | Reutiliza `AuthService` (dominio), `UserRepository` (infra), rutas Flask (presentación) — mismo patrón que login/creación de usuario existentes |
| III. Tipado estricto | Sí | Sin `any` nuevo en frontend; type hints en los métodos nuevos de `AuthService`/`UserRepository` |
| IV. Seguridad en Profundidad | Sí, con una excepción documentada | `forgot-password`/`reset-password` son rutas públicas (igual que `/login`) — no llevan JWT porque el usuario aún no está autenticado, es el propósito del flujo. `reset_token` se guarda en texto plano en `users` (no hasheado): es de un solo uso, expira en 30 min y se borra al usarse, perfil de riesgo comparable al de una sesión corta, no al de una contraseña. La contraseña semilla fija de Desarrollo (`SyWork_Dev2026!`) documentada en `docs/credenciales_dev.txt` es una **excepción explícita y deliberada** a "prohibido exponer secretos", acotada a **NO-producción** (ver Complexity Tracking) |
| V. Cero dependencias no aprobadas | Con desviación documentada | `smtplib`/`email.mime` son stdlib, no requieren aprobación de dependencia nueva. Pero la tabla de stack aprobado declara `Celery + Redis` como obligatorio para "emails automaticos" — **esta fase no lo usa** (ver Complexity Tracking) |
| VI. AI-Native | N/A | Esta feature no toca acciones de Coordinador/Resolutor ni el Gold Standard Dataset |

## Project Structure

### Documentation (this feature)

```text
specs/003-reseteo-contrasenas/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── auth-password-reset.md
└── tasks.md             # Phase 2 output (/speckit-tasks, no creado aún)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   └── services/
│       └── auth_service.py        # + generación/validación de reset_token, generación de contraseña temporal
├── infra/
│   ├── migrations/versions/
│   │   ├── 009_roles_permissions_login.py   # modificar: password semilla fija si no es producción
│   │   └── 014_password_reset_tokens.py     # nueva: columnas reset_token, reset_token_expires_at
│   └── repositories/
│       └── user_repo.py           # + set_password, set_reset_token, get_by_reset_token, clear_reset_token
├── api/
│   └── routes/
│       ├── users.py                # + PATCH /api/users/{id}/reset-password
│       └── auth.py                 # + POST /api/auth/forgot-password, POST /api/auth/reset-password
└── tests/
    ├── domain/
    │   └── test_auth_service.py    # + casos de reset_token (expiración, un solo uso)
    └── api/
        ├── test_users_api.py       # + reseteo por Admin (200/404/403)
        └── test_auth_login_api.py  # + forgot-password/reset-password (200 genérico, 400, inactivo)

frontend/
├── src/
│   ├── pages/
│   │   ├── UsersPage.tsx           # + botón "Resetear contraseña" (reutiliza modal existente)
│   │   ├── LoginPage.tsx           # + link "¿Olvidaste tu contraseña?"
│   │   └── ResetPasswordPage.tsx   # nueva: lee ?token=, formulario de nueva contraseña
│   └── services/
│       ├── userService.ts          # + resetPassword(id)
│       └── authService.ts          # + forgotPassword(email), resetPassword(token, newPassword)

docs/
└── credenciales_dev.txt            # nuevo: tabla de credenciales semilla (contraseña en base64)
```

**Structure Decision**: Reutiliza la estructura de 3 capas ya establecida (`backend/domain` /
`backend/infra` / `backend/api`) y la organización por página/servicio del frontend. No se crean
directorios ni módulos nuevos de alto nivel — todo cuelga de archivos ya existentes, salvo la
migración nueva, la pantalla `ResetPasswordPage.tsx` y el `.txt` de credenciales.

## Complexity Tracking

> Violaciones de principios NON-NEGOTIABLE que requieren justificación explícita (Governance, `.specify/memory/constitution.md`)

| Violación | Por qué es necesaria ahora | Alternativa más simple descartada porque |
|---|---|---|
| Envío de correo síncrono vía `smtplib` en vez de tarea async con Celery + Redis (Principio V exige Celery+Redis para "emails automaticos") | Celery/Redis no están desplegados en este proyecto todavía (no existen en `docker-compose.yml`); levantarlos solo para este correo puntual es una inversión de infraestructura fuera del alcance que el usuario aprobó en el diseño de esta feature | Levantar Celery+Redis ahora, antes de que el roadmap (Fase 2+, notificaciones/SLA) los necesite de todas formas, es sobre-ingeniería para un solo correo de bajo volumen; se migra cuando se implemente el motor de notificaciones real |
| Contraseña fija conocida (`SyWork_Dev2026!`) documentada en texto (base64) en `docs/credenciales_dev.txt`, versionado en Git (Principio IV prohíbe exponer secretos) | Decisión explícita del usuario para eliminar la fricción de reinstalar el proyecto en equipos nuevos y perder la contraseña generada en logs; se le informó que base64 no es cifrado y que `docs/` queda en el historial de Git, y confirmó que la quiere así | Mantener la generación aleatoria (alternativa "segura") es precisamente el problema que motivó esta feature — la alternativa fue evaluada y rechazada por el usuario en brainstorming previo |

**Mitigación aplicada a ambas**: acotadas explícitamente a **Desarrollo** — en producción
(`FLASK_ENV=production`) la migración semilla sigue generando una contraseña aleatoria única
(nunca la fija), y nada impide migrar el envío de correo a Celery más adelante sin cambiar el
contrato público (`POST /api/auth/forgot-password`).
