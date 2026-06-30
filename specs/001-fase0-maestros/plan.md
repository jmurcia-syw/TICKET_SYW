# Implementation Plan: Fase 0 — Maestros

**Branch**: `001-fase0-maestros` | **Date**: 2026-06-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-fase0-maestros/spec.md`

---

## Summary

Implementar las cuatro pantallas de datos maestros prerequisito para Fase 1 (Tickets):
Clientes (con cifrado de credenciales VPN/IPs), Proyectos, Recursos/Skills y Roles/Seguridad.
Stack completo definido en la Constitucion v1.0.0: React 19 + Flask + PostgreSQL 16 con RLS,
RBAC de 4 roles, y middleware de verificacion de estado activo en cada request JWT.

---

## Technical Context

**Language/Version**: Python 3.12 (backend) + TypeScript 5.6 strict (frontend)

**Primary Dependencies**:
- Backend: Flask 3.1, Flask-RESTX 1.3, SQLAlchemy 2.x, Alembic, Flask-JWT-Extended,
  google-auth, psycopg2, pgcrypto (extension PostgreSQL para cifrado AES-256 de columnas)
- Frontend: React 19, Ant Design 5, Zustand 5, Axios 1.7, date-fns 4, pnpm

**Storage**: PostgreSQL 16 on-premise con Row Level Security habilitado en todas las tablas

**Testing**: pytest + pytest-flask (backend) — Vitest + React Testing Library (frontend)

**Target Platform**: Web app — Docker Compose on-premise, red interna SyWork

**Project Type**: Web application (SPA frontend + REST API backend)

**Performance Goals**:
- Listas de maestros cargan en menos de 1 segundo con hasta 500 registros
- Formularios de creacion/edicion responden en menos de 500ms
- Filtros y busqueda con debounce maximo de 300ms

**Constraints**:
- Single tenant, sin aislamiento multi-org en esta fase
- Credenciales VPN/IPs cifradas con pgcrypto AES-256 a nivel de columna PostgreSQL
- JWT sin estado: estado activo del usuario verificado via middleware en cada request a la API
- Prohibido `any` en TypeScript; type hints obligatorios en Python publico
- Sesion activa de usuario desactivado invalidada en la proxima llamada a API (no requiere
  revocacion de JWT, el middleware verifica `users.active` en cada request)

**Scale/Scope**: ~10-30 usuarios internos SyWork, ~50-200 clientes, ~100-500 proyectos

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Verificacion |
|-----------|--------|-------------|
| I. API-First: contrato Swagger antes de codigo | PASS | Contratos definidos en Phase 1 antes de tasks |
| I. Logica de negocio solo en domain/ | PASS | Reglas (unicidad, cascade, ultimo Admin) en domain/services/ |
| II. Clean Architecture 3 capas | PASS | domain/ — infra/ — api/ + frontend/src/ |
| II. Componentes React tontos | PASS | Logica y API calls en frontend/src/services/ |
| III. TypeScript strict, prohibido any | PASS | tsconfig con "strict": true ya configurado |
| III. Sin secretos en frontend | PASS | Solo VITE_API_URL como variable publica |
| IV. JWT + RLS doble proteccion | PASS | Middleware + RLS en todas las tablas sensibles |
| IV. Cifrado datos sensibles | PASS | pgcrypto AES-256 en columnas IPs/credenciales |
| V. pnpm exclusivo | PASS | Ya configurado en el proyecto |
| V. Ant Design para UI | PASS | Instalado; sin componentes custom innecesarios |
| V. Sin dependencias no aprobadas | PASS | pgcrypto es extension de PostgreSQL, sin nueva dep |
| VI. AI-Native: endpoints agnosticos al caller | PASS | RBAC centralizado en API, no acoplado a UI |

**Resultado**: TODAS las verificaciones pasan. Sin violaciones.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-fase0-maestros/
├── plan.md              este archivo
├── research.md          decisiones tecnicas Phase 0
├── data-model.md        entidades y relaciones Phase 1
├── quickstart.md        guia de validacion Phase 1
├── contracts/           contratos API Phase 1
│   ├── clients.md
│   ├── projects.md
│   ├── resources.md
│   └── roles.md
└── tasks.md             generado por /speckit-tasks
```

### Source Code

```text
backend/
├── domain/
│   ├── entities/
│   │   ├── client.py           entidad Client + reglas de negocio
│   │   ├── project.py          entidad Project
│   │   ├── resource.py         entidad Resource + Skills
│   │   └── user.py             entidad User + Role enum
│   └── services/
│       ├── client_service.py   unicidad nombre, cascade desactivacion
│       ├── project_service.py  validacion cliente activo, unicidad por cliente
│       ├── resource_service.py skill en uso, unicidad email
│       └── role_service.py     regla ultimo Admin, cambio de rol
├── infra/
│   ├── models/
│   │   ├── client_model.py     SQLAlchemy + pgcrypto columnas sensibles
│   │   ├── project_model.py
│   │   ├── resource_model.py
│   │   ├── skill_model.py
│   │   └── user_model.py
│   ├── repositories/
│   │   ├── client_repo.py
│   │   ├── project_repo.py
│   │   ├── resource_repo.py
│   │   └── user_repo.py
│   └── migrations/             Alembic versions/
├── api/
│   ├── middleware/
│   │   ├── auth.py             JWT decode + verificacion estado activo usuario
│   │   └── rbac.py             decorador @require_role(...)
│   └── routes/
│       ├── clients.py          /api/clients
│       ├── projects.py         /api/projects
│       ├── resources.py        /api/resources y /api/skills
│       └── users.py            /api/users (roles y estado)
└── tests/
    ├── domain/
    ├── infra/
    └── api/

frontend/src/
├── components/
│   ├── clients/
│   │   ├── ClientList.tsx
│   │   ├── ClientForm.tsx
│   │   └── ClientDetail.tsx
│   ├── projects/
│   │   ├── ProjectList.tsx
│   │   └── ProjectForm.tsx
│   ├── resources/
│   │   ├── ResourceList.tsx
│   │   ├── ResourceForm.tsx
│   │   └── SkillSelector.tsx
│   └── users/
│       ├── UserList.tsx
│       └── RoleAssignment.tsx
├── services/
│   ├── clientService.ts
│   ├── projectService.ts
│   ├── resourceService.ts
│   └── userService.ts
├── store/
│   ├── clientStore.ts
│   ├── projectStore.ts
│   ├── resourceStore.ts
│   └── userStore.ts
├── types/
│   ├── client.ts
│   ├── project.ts
│   ├── resource.ts
│   └── user.ts
└── pages/
    ├── ClientsPage.tsx
    ├── ProjectsPage.tsx
    ├── ResourcesPage.tsx
    └── UsersPage.tsx
```

**Structure Decision**: Web application. Frontend SPA en `frontend/src/`, backend Flask en
`backend/` con Clean Architecture estricta. Sin cambios a la estructura Docker Compose existente.

---

## Complexity Tracking

> Sin violaciones a la Constitucion — tabla vacia.
