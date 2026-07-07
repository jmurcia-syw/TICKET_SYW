# SyWork Desk

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

## Instalación y despliegue

### Requisitos previos

| Componente | Uso |
|------------|-----|
| **Docker Desktop** (o Docker Engine + Compose v2) | Orquesta los 3 servicios: `sywork_db`, `sywork_backend`, `sywork_frontend` |
| **Git** | Clonar el repositorio |
| Node.js 20+ y pnpm | Solo si vas a correr el frontend **fuera** de Docker |
| Python 3.12 | Solo si vas a correr el backend **fuera** de Docker |

Todo el stack corre en contenedores — no necesitas instalar PostgreSQL, Python ni Node
directamente en el host para levantar el servicio completo.

### 1. Clonar el repositorio

```bash
git clone https://github.com/jmurcia-syw/TICKET_SYW.git
cd TICKET_SYW
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con valores reales (nunca commitear este archivo):

```env
POSTGRES_DB=sywork_tickets
POSTGRES_USER=sywork
POSTGRES_PASSWORD=<contraseña fuerte>

JWT_SECRET=<cadena aleatoria de al menos 32 caracteres>

# console.cloud.google.com → APIs & Services → Credentials → OAuth 2.0 Client
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret

FLASK_ENV=production          # 'development' solo en entornos locales
FLASK_APP=backend/app.py
DEV_SKIP_AUTH=false           # SIEMPRE false: la API exige JWT en toda ruta (FR-022)
```

> `DEV_SKIP_AUTH` es una bandera heredada de versiones tempranas del proyecto — desde la
> Fase 1 el enforcement de JWT+permisos es real e incondicional en el backend, por lo que
> esta variable ya no tiene efecto y debe permanecer en `false`.

### 3. Levantar el stack

```bash
docker compose up --build -d
```

Esto construye las 3 imágenes y arranca, en orden:

1. **`sywork_db`** (Postgres 16) — espera a estar `healthy` antes de continuar.
2. **`sywork_backend`** (Flask) — corre `alembic upgrade head` automáticamente al iniciar
   (12 migraciones) y luego levanta el servidor en `:5000`.
3. **`sywork_frontend`** (Vite) — sirve la SPA en `:5173`.

```bash
docker compose ps                       # verificar que los 3 estén "Up"
docker compose logs -f backend           # seguir logs de arranque / migraciones
curl http://localhost:5000/health/       # {"status": "ok", "database": {"connected": true}}
```

- **App**: http://localhost:5173
- **Swagger / OpenAPI**: http://localhost:5000/swagger
- **Postgres** (para clientes externos como DBeaver/psql): `localhost:5432`

### 4. Primer login

En instalaciones de **Desarrollo** (`FLASK_ENV` distinto de `production`, el default), los 4
usuarios semilla quedan con una contraseña **fija** (la misma en cada instalación), documentada
en [`docs/credenciales_dev.txt`](docs/credenciales_dev.txt) (codificada en base64 — no es
cifrado, solo evita mostrarla a simple vista).

En instalaciones de **producción** (`FLASK_ENV=production`), el backend sigue **imprimiendo
una única vez** en el log una contraseña aleatoria compartida por los 4 usuarios semilla:

```bash
docker compose logs backend | grep -A2 "PROVISIONAL"
```

Usuarios semilla (`username` / dominio `@sywork.net`): `admin`, `coordinador`, `qm`,
`resolutor`. Cualquiera puede iniciar sesión por ese login provisional o por Google OAuth2
(si configuraste `GOOGLE_CLIENT_ID`/`SECRET`). Un Admin puede resetear la contraseña de
cualquier usuario (botón de llave en la pantalla de Usuarios) y dar de alta usuarios reales
desde ahí. Un usuario también puede recuperar su propia contraseña con el link "¿Olvidaste tu
contraseña?" en el login, si el backend tiene `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD`
configurados en `.env`.

### Detener / reiniciar

```bash
docker compose down              # detiene y elimina los contenedores (conserva datos)
docker compose down -v           # además borra el volumen de Postgres (⚠ pierde datos)
docker compose restart backend   # reiniciar solo un servicio tras editar código
```

### Despliegue en servidor (on-premise)

El proyecto está pensado para desplegarse on-premise vía Docker Compose, sin dependencias
de servicios cloud gestionados:

1. Provisionar un host Linux con Docker Engine + Compose v2 instalados.
2. Clonar el repo y configurar `.env` con secretos de producción (`JWT_SECRET` fuerte,
   credenciales de Postgres, credenciales OAuth reales, `FLASK_ENV=production`).
3. `docker compose up --build -d` — igual que en desarrollo; Alembic aplica las
   migraciones pendientes automáticamente en cada arranque, de forma idempotente.
4. Colocar un proxy inverso (nginx/Caddy) delante de `:5173` (frontend) y `:5000/api`
   (backend) para servir bajo un dominio único con TLS. *(Pendiente de definir en este
   repo — ver `TODO(HOSTING)` en la Constitución.)*
5. El volumen `postgres_data` persiste los datos entre despliegues; `uploads/` (adjuntos
   de tickets) también debe persistirse — verifica que el volumen bind `.:/repo` del
   backend incluya esa carpeta en el host.
6. Backups: `pg_dump` periódico del volumen `postgres_data` + copia de `uploads/`.

### Desarrollo sin Docker (opcional)

Si prefieres correr el backend o frontend directamente en el host (requiere Postgres
accesible por separado):

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
export DATABASE_URL=postgresql://sywork:changeme@localhost:5432/sywork_tickets
alembic upgrade head
flask run --host=0.0.0.0 --port=5000

# Frontend (en otra terminal)
cd frontend
pnpm install
pnpm dev   # http://localhost:5173, usa VITE_API_URL apuntando al backend
```

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
