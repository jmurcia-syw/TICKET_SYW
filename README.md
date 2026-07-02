# SyWork Tickets

Sistema interno de ticketing y gestión de tareas para el equipo de consultoría Oracle ERP/CRM de SyWork.

> **Fase activa**: `Fase 0 — Maestros` · Rama: `develp_Jp`

---

## Roadmap

| Fase | Descripción | Estado |
|------|-------------|--------|
| **Fase 0** | Maestros — Clientes, Proyectos, Recursos/Skills, Roles/Seguridad | 🟡 En progreso |
| Fase 1 | Tickets — Ciclo de vida (FSM), SLA, comentarios, adjuntos, dashboards | ⏳ Pendiente |
| Fase 2 | Tareas — Subtareas por rol, motor FSM, SLA por cliente | ⏳ Pendiente |
| Fase 3 | Asignaciones con disponibilidad (Calendario) | ⏳ Pendiente |
| Fase 4 | Motor FSM completo para SLA | ⏳ Pendiente |
| Fase 5 | Focus Room | ⏳ Pendiente |

---

## Stack Tecnológico

### Backend
- **Python 3.12** + **Flask 3.x** + **Flask-RESTX** (Swagger en `/swagger`)
- **SQLAlchemy 2.x** + **Alembic** (migraciones — dueño único del schema)
- **PostgreSQL 16** on-premise con RLS y pgcrypto (AES-256 para datos VPN)
- **Flask-JWT-Extended** + **Google OAuth2** (dominio `@sywork.net`)

### Frontend
- **React 19** + **TypeScript strict** (prohibido `any`)
- **Ant Design 5** · **Zustand 5** · **React Router v6** · **Axios**
- **pnpm** exclusivamente (prohibido npm y yarn)
- **date-fns** (prohibido moment.js)

### Infraestructura
- **Docker** + **Docker Compose**
- `DEV_SKIP_AUTH=true` bypasea JWT en desarrollo

---

## Arquitectura (Clean Architecture — 3 capas)

```
backend/
├── domain/          # Capa 1 — Entidades, servicios de negocio, FSM
│   ├── entities/    # User, Client, Project, Resource, Skill
│   └── services/    # ClientService, ProjectService, SkillService, RoleService
├── infra/           # Capa 2 — Modelos SQLAlchemy, repositorios, migraciones
│   ├── models/      # UserModel, ClientModel, ProjectModel, ResourceModel
│   ├── repositories/
│   └── migrations/  # Alembic (versions/)
└── api/             # Capa 3 — Flask-RESTX namespaces, middleware
    ├── middleware/  # auth.py (JWT + DEV_SKIP_AUTH), rbac.py
    └── routes/      # clients, projects, resources, users, roles, permissions

frontend/src/
├── components/      # Componentes "tontos" — solo renderizan props
├── pages/           # ClientsPage, ProjectsPage, ResourcesPage, UsersPage…
├── services/        # Lógica de negocio y llamadas API (apiClient Axios)
├── store/           # Estado global con Zustand
└── types/           # Tipos TypeScript estrictos
```

---

## Fase 0 — Maestros: Estado actual

### ✅ Completado

#### Backend
- Migraciones Alembic: `users`, `clients`, `projects`, `skills`, `resources`, `resource_skills`
- Entidades de dominio con reglas de negocio encapsuladas
- Repositorios con paginación, búsqueda y filtros
- **Namespaces Flask-RESTX con Swagger completo** (25+ endpoints):
  - `GET/POST /api/clients` · `GET/PATCH /api/clients/{id}` · `/deactivate` · `/activate`
  - `GET/POST /api/projects` · `GET/PATCH /api/projects/{id}` · `/deactivate` · `/activate`
  - `GET/POST /api/skills` · `DELETE /api/skills/{id}`
  - `GET/POST /api/resources` · `GET/PATCH /api/resources/{id}` · `/skills` · `/deactivate` · `/activate`
  - `GET/POST /api/users` · `GET /api/users/{id}` · `/{id}/role` · `/deactivate` · `/activate`
  - `GET/POST /api/roles` · `GET/PATCH/DELETE /api/roles/{id}`
  - `GET/POST /api/permissions` · `DELETE /api/permissions/{id}`
- Docker + `DEV_SKIP_AUTH=true` para desarrollo sin OAuth

#### Frontend
- Páginas base: Clients, Projects, Resources, Skills, Users, Roles/Permissions
- DevLayout sin autenticación para modo desarrollo
- Tipos TypeScript: `Client`, `Project`, `Resource`, `Skill`, `User`, `Role`, `Permission`
- Servicios: `clientService`, `projectService`, `resourceService`, `userService`, `roleService`, `permissionService`, `authService`

### ❌ Pendiente para completar Fase 0

- [ ] RLS — políticas Row Level Security en PostgreSQL (`008_enable_rls_policies`)
- [ ] Cifrado VPN verificado en reposo (pgcrypto AES-256 en columnas `vpn_ips`/`vpn_credentials`)
- [ ] Componentes frontend completos (formularios, tablas con datos reales de la API)
- [ ] Auth real: Google OAuth2 + JWT activo (actualmente `DEV_SKIP_AUTH=true`)
- [ ] Validación E2E con escenarios del `quickstart.md`

---

## Quickstart — Desarrollo local

### Requisitos
- Docker Desktop
- Node.js 20+ y pnpm (`npm install -g pnpm`)

### Backend (Docker)

```bash
# Copiar variables de entorno
cp .env.example .env

# Levantar DB + backend (Alembic corre automáticamente al iniciar)
docker compose up --build

# Swagger UI disponible en:
http://localhost:5000/swagger

# Health check
curl http://localhost:5000/health/
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev

# App en http://localhost:5173
```

### Variables de entorno (`.env`)

```env
POSTGRES_DB=sywork_tickets
POSTGRES_USER=sywork_user
POSTGRES_PASSWORD=changeme
JWT_SECRET=changeme_jwt_secret_at_least_32_chars
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
FLASK_ENV=development
DEV_SKIP_AUTH=true
```

---

## Skills del proyecto (`.claude/skills/`)

Habilidades específicas del proyecto disponibles para Claude Code en esta sesión:

| Skill | Propósito |
|-------|-----------|
| `api-design-principles` | Guía de diseño REST: naming, status codes, paginación, errores |
| `error-handling-patterns` | Patrones de manejo de errores backend (Flask) y frontend (Axios) |
| `interface-design` | Principios de diseño de interfaces con Ant Design 5 |
| `vercel-react-best-practices` | Best practices React 19 + TypeScript strict |
| `speckit-implement` | Workflow de implementación guiada por spec (metodología SDD) |
| `speckit-tasks` | Generación de `tasks.md` desde artefactos de diseño |
| `speckit-clarify` | Clarificación de especificaciones antes de planificar |
| `speckit-plan` | Planificación técnica: research + contratos API + data model |

---

## Convenciones

| Contexto | Convención |
|----------|-----------|
| Componentes React | `PascalCase` (`ClientList.tsx`) |
| Funciones/utilidades | `camelCase` (`formatDate.ts`) |
| Columnas DB | `snake_case` (`created_at`, `client_id`) |
| Códigos de error API | `snake_case` (`not_found`, `already_inactive`) |
| Rama de desarrollo Fase 0 | `develp_Jp` |

---

## Especificación (Fase 0)

| Artefacto | Ruta |
|-----------|------|
| Spec | [`specs/001-fase0-maestros/spec.md`](specs/001-fase0-maestros/spec.md) |
| Plan técnico | [`specs/001-fase0-maestros/plan.md`](specs/001-fase0-maestros/plan.md) |
| Modelo de datos | [`specs/001-fase0-maestros/data-model.md`](specs/001-fase0-maestros/data-model.md) |
| Contratos API | [`specs/001-fase0-maestros/contracts/`](specs/001-fase0-maestros/contracts/) |
| Tasks | [`specs/001-fase0-maestros/tasks.md`](specs/001-fase0-maestros/tasks.md) |
| Quickstart | [`specs/001-fase0-maestros/quickstart.md`](specs/001-fase0-maestros/quickstart.md) |
| Constitución | [`.specify/memory/constitution.md`](.specify/memory/constitution.md) |
