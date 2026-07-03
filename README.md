# SyWork Tickets

Sistema interno de ticketing y gestión de tareas para el equipo de consultoría Oracle ERP/CRM
de SyWork. Construido con metodología **SDD (Spec-Driven Development)** sobre **GitHub Spec Kit**.

> **Fase activa**: `Fase 1 — Tickets` ✅ implementada y validada (pendiente commit/merge) · Rama: `develp_Jp`

---

## Roadmap (SDD V3)

| Fase SDD V3 | Descripción | Estado |
|-------------|-------------|--------|
| **1a — Maestros** | Clientes, Proyectos, Recursos/Skills, Roles/Permisos, login dual, compensación protegida (spec `001`) | ✅ **Completa** |
| **1b — Tickets** | Ciclo de vida de 9 estados (FSM), comentarios tipificados con adjuntos, Triage Push + Gold Standard Dataset, Panel de Asignación, notificaciones, enforcement JWT total (spec `002`) | ✅ **Completa** (validación E2E 26/26) |
| 2 | Registro diario de tiempos por recurso + rentabilidad | ⏳ Siguiente |
| 3 | Tareas (misma tabla, campo "Tipo de registro" + registro relacionado) | ⏳ Pendiente |
| 4 | SLAs por prioridad/cliente/proyecto con estados que pausan el contador | ⏳ Pendiente |
| 5 | Asignación por disponibilidad + calendarios por país/recurso | ⏳ Pendiente |
| 6 | Motor FSM automatizado + triggers de comentarios + Google Chat | ⏳ Pendiente |
| 7 | Focus Room + agente IA asistente (evaluar Triage Agent) | ⏳ Pendiente |
| 8 | Portal de clientes + integraciones + tickets por email | ⏳ Pendiente |

Fuentes de verdad: `docs/SDD V3.docx` (roadmap y alcances) y
`docs/Regla de actividad de estados.xlsx` (flujo de estados, codificado en
`backend/domain/fsm/ticket_fsm.py`).

---

## Estado actual — Fase 1 Tickets

### Funcionalidad operativa

- **Tickets** (`TK-nnnnnn` consecutivo): creación con clasificación completa (tipo,
  prioridad, severidad, herramienta, proceso, escalamiento N1-N4, cliente/proyecto),
  listado con filtros combinables, detalle con historial completo.
- **Ciclo de vida de 10 estados** (NUEVO → PRE-ANÁLISIS/CONTACTO → EN ANÁLISIS →
  EN EJECUCIÓN ⇄ EN PRUEBAS → PENDIENTE DE USUARIO → RESUELTO → CERRADO, + CANCELADO):
  las transiciones se ejecutan **solo** vía comentarios tipificados y acciones de la matriz
  (máquina de estados `python-transitions` en el dominio — 16 transiciones, nada manual).
- **Comentarios tipificados con adjuntos** (10 tipos estructurados, visibilidad
  interno/externo, máx 10 MB por archivo, descarga autenticada).
- **Triage Push**: `POST /api/tickets/{id}/assign` independiente de la UI (Principio VI
  AI-Native); cada asignación registra el **Gold Standard Dataset** (skills del asignado,
  carga, prioridad, severidad — JSONB append-only) para el futuro Triage Agent.
- **Panel de Asignación**: matriz resolutor × estado + tickets NUEVOS asignables inline.
- **Notificaciones internas** con campana (polling 60 s): asignación, respuesta de usuario,
  rechazo de resolución, cierre.
- **Catálogos administrables**: herramientas, procesos, tipos de resolución (bloqueo por uso).
- **Cierre controlado**: requiere aceptación del usuario (o 3+ días sin respuesta) + tipo
  de resolución + descripción de solución; notifica a Coordinador y QM.

### Seguridad

- **Enforcement completo en la API**: TODAS las rutas exigen JWT + permiso módulo/acción
  (`@require_permission`). Públicas solo: `/api/auth/login`, `/api/auth/google`, `/health/`.
  *(El bypass `DEV_SKIP_AUTH` quedó eliminado del flujo — el login provisional
  usuario/contraseña y Google OAuth2 son los únicos accesos.)*
- **RBAC dinámico**: roles y permisos administrables (matriz módulo × acción); 4 roles seed
  (Admin, Coordinador, QM, Resolutor). Un Resolutor solo transiciona tickets asignados a él.
- **RLS** habilitado en tablas de maestros y tickets; datos sensibles cifrados
  (VPN de clientes, compensación de recursos — solo Admin).
- Pool de conexiones PostgreSQL dimensionado (10+20 overflow, sesión request-scoped con
  `teardown_appcontext`) — validado con 1.200 requests concurrentes sin errores.

### Verificación

- **155 tests** (dominio sin DB + API contra Postgres real en Docker) ✅
- **Validación E2E** de los 6 escenarios del quickstart: 26/26 checks ✅
- **Performance** con 500+ tickets: panel 64 ms (SC < 2 s), listado 52 ms (SC < 1 s) ✅
- Typecheck frontend estricto sin errores ✅

---

## Stack Tecnológico

### Backend
- **Python 3.12** + **Flask 3.x** + **Flask-RESTX** (Swagger en `/swagger`)
- **python-transitions** (FSM del ciclo de vida — Capa 1, dominio puro)
- **SQLAlchemy 2.x** + **Alembic** (12 migraciones — dueño único del schema)
- **PostgreSQL 16** on-premise con RLS y pgcrypto
- **Flask-JWT-Extended** + login provisional usuario/contraseña + **Google OAuth2** (`@sywork.net`)

### Frontend
- **React 19** + **TypeScript strict** (prohibido `any`)
- **Ant Design 5** · **Zustand 5** · **React Router v6** · **Axios**
- **pnpm** exclusivamente · **date-fns**

### Infraestructura
- **Docker Compose**: `sywork_db` (5432) · `sywork_backend` (5000) · `sywork_frontend` (5173)
- Adjuntos en volumen `uploads/` (fuera de git)

---

## Arquitectura (Clean Architecture — 3 capas)

```
backend/
├── domain/            # Capa 1 — sin imports de Flask/SQLAlchemy
│   ├── entities/      # Ticket, Comment, Notification, Client, Project, Resource, User, Role
│   ├── fsm/           # ticket_fsm.py — matriz de 16 transiciones (python-transitions)
│   └── services/      # ticket, comment, assignment, notification, compensation, ...
├── infra/             # Capa 2
│   ├── models/        # SQLAlchemy (tickets, comments, catalogs, notifications, maestros)
│   ├── repositories/  # paginación, filtros, historiales append-only
│   ├── storage/       # adjuntos en filesystem (uploads/tickets/{id}/)
│   └── migrations/    # Alembic 001..012
└── api/               # Capa 3
    ├── middleware/    # auth.py (JWT + usuario activo), rbac.py (@require_permission)
    └── routes/        # tickets, catalogs, notifications, assignment_panel + maestros

frontend/src/
├── components/tickets/  # TicketStatusTag, AssignModal, CommentThread, CommentComposer
├── components/common/   # NotificationBell, ProtectedRoute, ConfirmationModal, ...
├── pages/               # TicketsPage, TicketDetailPage, AssignmentPanelPage, CatalogsPage + maestros
├── services/            # ticketService, catalogService, notificationService + maestros
├── store/               # authStore (Zustand: token, permisos, hasPermission)
└── types/               # tipos estrictos por dominio
```

---

## Quickstart — Desarrollo local

### Requisitos
- Docker Desktop
- Node.js 20+ y pnpm (solo si corres el frontend fuera de Docker)

### Levantar todo

```bash
cp .env.example .env        # primera vez
docker compose up --build   # DB + backend (Alembic migra al iniciar) + frontend

# App:      http://localhost:5173
# Swagger:  http://localhost:5000/swagger
# Health:   curl http://localhost:5000/health/
```

### Login

Login provisional (usuario/contraseña) o Google OAuth2 (`@sywork.net`). Los 4 usuarios
semilla (`admin`, `coordinador`, `qm`, `resolutor`) comparten la contraseña provisional
que la migración imprime **una única vez** en el log del backend (rotable por Admin).

### Tests

```bash
docker exec sywork_backend python -m pytest tests/ -q     # suite completa (155 tests)
cd frontend && npx tsc -b                                  # typecheck estricto
docker exec sywork_backend python -m backend.scripts.seed_tickets 500   # datos de carga
```

---

## Convenciones

| Contexto | Convención |
|----------|-----------|
| Componentes React | `PascalCase` (`TicketDetailPage.tsx`) |
| Funciones/utilidades | `camelCase` |
| Columnas DB | `snake_case` (`ticket_number`, `assignee_id`) |
| Códigos de error API | `snake_case` (`invalid_transition`, `field_locked`) |
| Estados del ticket | `snake_case` en DB/API, etiquetas en español en UI |
| Skills | `UPPER_SNAKE` (`JDE_GL`, `ORACLE_FUSION`) |
| Ramas de feature | `###-nombre` (specs) · desarrollo actual: `develp_Jp` |

---

## Especificaciones (SDD / Spec Kit)

| Artefacto | Fase 0 — Maestros | Fase 1 — Tickets (activa) |
|-----------|-------------------|---------------------------|
| Spec | [`specs/001-fase0-maestros/spec.md`](specs/001-fase0-maestros/spec.md) | [`specs/002-fase1-tickets/spec.md`](specs/002-fase1-tickets/spec.md) |
| Plan técnico | [`plan.md`](specs/001-fase0-maestros/plan.md) | [`plan.md`](specs/002-fase1-tickets/plan.md) |
| Research | — | [`research.md`](specs/002-fase1-tickets/research.md) |
| Modelo de datos | [`data-model.md`](specs/001-fase0-maestros/data-model.md) | [`data-model.md`](specs/002-fase1-tickets/data-model.md) |
| Contratos API | [`contracts/`](specs/001-fase0-maestros/contracts/) | [`contracts/`](specs/002-fase1-tickets/contracts/) |
| Tasks | [`tasks.md`](specs/001-fase0-maestros/tasks.md) | [`tasks.md`](specs/002-fase1-tickets/tasks.md) — 44/44 ✅ |
| Quickstart de validación | [`quickstart.md`](specs/001-fase0-maestros/quickstart.md) | [`quickstart.md`](specs/002-fase1-tickets/quickstart.md) |

**Transversales**: [Constitución v1.1.0](.specify/memory/constitution.md) ·
[MER actual](docs/MER.md) (maestros + tickets, generado del schema real)

## Pendientes conocidos

- Validación visual en navegador de la Fase 1 (la validación E2E fue por API).
- Auditorías de Fase 0: sanitización XSS (T066), logs sin datos VPN (T067), exposición
  frontend (T071).
- El cifrado pgcrypto es placeholder de desarrollo → reemplazar por `pgp_sym_encrypt`
  antes de producción.
- Commit/merge del trabajo de las Fases 0-ampliación y 1 (rama `develp_Jp`).
