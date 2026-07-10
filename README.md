# SyWork Desk

Sistema interno de ticketing y gestión de tareas para el equipo de consultoría Oracle ERP/CRM
de SyWork. Construido con metodología **SDD (Spec-Driven Development)** sobre **GitHub Spec Kit**.

> **Fase activa**: `Fase 3 — Tareas: ciclo de vida unificado, Listas y Subtareas` ✅ implementada y
> validada end-to-end contra Docker real (quickstart 0-6 · suite completa 332/332 · `tsc -b` sin
> errores) · Rama: `develp_Jp`

---

## Roadmap (SDD V3)

| Fase SDD V3 | Descripción | Estado |
|-------------|-------------|--------|
| **1a — Maestros** | Clientes, Proyectos, Recursos/Skills, Roles/Permisos, login dual, compensación protegida (spec `001`) | ✅ **Completa** |
| **1b — Tickets** | Ciclo de vida de 9 estados (FSM), comentarios tipificados con adjuntos, Triage Push + Gold Standard Dataset, Panel de Asignación, notificaciones, enforcement JWT total (spec `002`) | ✅ **Completa** (validación E2E 26/26) |
| **2 — Registro de tiempos** | Registro diario de tiempos por recurso (hora inicio/fin), rol Encargado (autoservicio con Cliente fijo), breadcrumbs de navegación, Encargado seleccionable/editable por Cliente en el ticket, "Mis Tareas" (specs `004`, `005`, `006`, `007`) | ✅ **Completa** |
| **3 — Tareas** | Tarea/Subtarea sobre la misma tabla de Ticket (jerarquía Cliente → Proyecto → Lista → Tarea → Subtarea), ciclo de vida unificado con Ticket (10 estados, transición libre + comentario), visibles en Kanban, Listas administrables tipo Teamwork/Asana, Subtareas con Encargado propio, fix de Registro de tiempo para creador de la Tarea (specs `008`, `009`) | ✅ **Completa** |
| 4 | SLAs por prioridad/cliente/proyecto con estados que pausan el contador | ⏳ Pendiente |
| 5 | Asignación por disponibilidad + calendarios por país/recurso | ⏳ Pendiente |
| 6 | Motor FSM automatizado + triggers de comentarios + Google Chat | ⏳ Pendiente |
| 7 | Focus Room + agente IA asistente (evaluar Triage Agent) | ⏳ Pendiente |
| 8 | Portal de clientes + integraciones + tickets por email | ⏳ Pendiente |

Fuentes de verdad: `docs/SDD V3.docx` (roadmap y alcances) y
`docs/Regla de actividad de estados.xlsx` (flujo de estados, codificado en
`backend/domain/fsm/ticket_fsm.py`).

---

## Estado actual — Fase 1 (Tickets) + Fase 2 (Tiempos y Encargados) + Fase 3 (Tareas)

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
- **Catálogos administrables**: herramientas, procesos, tipos de resolución (bloqueo por uso),
  tipo de registro dinámico.
- **Cierre controlado**: requiere aceptación del usuario (o 3+ días sin respuesta) + tipo
  de resolución + descripción de solución; notifica a Coordinador y QM.
- **Registro de tiempos** (Fase 2): registro manual estilo Teamwork desde el detalle del
  ticket (hora inicio/fin con duración calculada, o duración manual + nota), historial completo
  por ticket, Registro de Tiempos diario y Reporte de Tiempos agregados por recurso/cliente.
- **Rol Encargado**: usuario de cliente externo con alta simplificada (solo email/usuario,
  contraseña provisional), flujo de creación de ticket autoservicio restringido a su Cliente
  fijo, sin acceso a Maestros/Catálogos/Panel de Asignación.
- **Encargado solicitante asignable por Cliente**: al crear o editar un ticket, Coordinador/
  Resolutor pueden elegir el Encargado (contacto del Cliente) como solicitante desde una lista
  filtrada por Cliente; el campo se limpia si cambia el Cliente y queda bloqueado/no editable en
  tickets de autoservicio o en estados finales (Cerrado/Cancelado).
- **Mis Tareas** y **breadcrumbs de navegación** estilo Teamwork (Kanban → Detalle → Volver
  respeta el origen exacto).
- **Tareas y Subtareas** (Fase 3, misma tabla/entidad que Ticket, jerarquía Cliente → Proyecto →
  Lista → Tarea → Subtarea): mismo ciclo de 10 estados que el Ticket con **transición libre**
  (cualquier estado a cualquier otro, exige comentario) en vez de una FSM propia; mismos campos
  de clasificación (Tipo, Severidad, Herramienta, Proceso, Nivel de escalamiento) visibles y
  editables; aparecen en el **Kanban** junto a los Tickets con badge de tipo de registro.
- **Listas de tareas administrables**: entidad real por Proyecto (ya no texto libre), sidebar
  tipo Teamwork/Asana con conteo de tareas, creación y renombrado.
- **Subtareas** con Encargado y estado propios (no heredan el estado del padre), comentarios
  simples en Tarea/Subtarea sin cambio de estado.
- **Registro de tiempo sobre Tareas**: un recurso puede registrar tiempo sobre una Tarea/Subtarea
  que creó, sin exigir el historial formal de asignaciones de Triage (que solo aplica a Ticket).

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

- Tests de dominio + API contra Postgres real en Docker ✅ (suite dirigida por feature;
  la última incorporación — Encargado asignable por Cliente, spec `007` — 20/20 tests en verde)
- **Validación E2E** de la Fase 1 (6 escenarios del quickstart): 26/26 checks ✅
- **Validación E2E** de la Fase 2.2 (Encargado asignable por Cliente, spec `007`): 6/6
  escenarios del quickstart validados contra Docker real (creación con/sin Encargado,
  autoservicio inmutable, reasignación, bloqueo por estado, limpieza al cambiar Cliente,
  permiso de lectura para Resolutor)
- **Validación E2E** de la Fase 3 (Tareas, Listas y Subtareas, spec `009`): quickstart
  Escenarios 0-6 contra Docker real (migración de datos, registro de tiempo por creador,
  transición libre + Kanban, Listas administrables, Subtareas con Encargado propio, comentarios
  simples, regresión de Ticket sin cambios); suite completa `332/332` tests en verde
- **Performance** con 500+ tickets: panel 64 ms (SC < 2 s), listado 52 ms (SC < 1 s) ✅
- Typecheck frontend estricto sin errores ✅

---

## Stack Tecnológico

### Backend
- **Python 3.12** + **Flask 3.x** + **Flask-RESTX** (Swagger en `/swagger`)
- **python-transitions** (FSM del ciclo de vida — Capa 1, dominio puro)
- **SQLAlchemy 2.x** + **Alembic** (revisión `022` — dueño único del schema)
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
│   ├── entities/      # Ticket, Comment, Notification, Client, Project, Resource, User, Role,
│   │                  # ClientContact, WorkSession
│   ├── fsm/           # ticket_fsm.py — matriz de 16 transiciones (python-transitions)
│   └── services/      # ticket, comment, assignment, notification, compensation,
│                      # client_contact, work_session, ...
├── infra/             # Capa 2
│   ├── models/        # SQLAlchemy (tickets, comments, catalogs, notifications, maestros,
│   │                  # client_contacts, work_sessions, task_lists)
│   ├── repositories/  # paginación, filtros, historiales append-only
│   ├── storage/       # adjuntos en filesystem (uploads/tickets/{id}/)
│   └── migrations/    # Alembic 001..024
└── api/               # Capa 3
    ├── middleware/    # auth.py (JWT + usuario activo), rbac.py (@require_permission)
    └── routes/        # tickets, catalogs, notifications, assignment_panel, client_contacts,
                       # work_sessions, task_lists + maestros

frontend/src/
├── components/tickets/     # TicketStatusTag, AssignModal, CommentThread, CommentComposer,
│                           # TicketBreadcrumb, TaskStatusChanger, SubtaskList
├── components/worksessions/ # WorkSessionForm, TimeLogModal, TicketWorkSessions
├── components/common/      # NotificationBell, ProtectedRoute, ConfirmationModal, ...
├── pages/                  # TicketsPage, TicketDetailPage, AssignmentPanelPage, CatalogsPage,
│                           # MyTasksPage, WorkSessionsPage, TimeReportPage, ClientContactsPage,
│                           # ProjectListsPage, KanbanPage + maestros
├── services/                # ticketService, catalogService, notificationService,
│                            # clientContactService, workSessionService, taskListService + maestros
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
   (revisión `022`) y luego levanta el servidor en `:5000`.
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
docker exec sywork_backend python -m pytest tests/ -q     # suite completa
cd frontend && npx tsc -b                                  # typecheck estricto
docker exec sywork_backend python -m backend.scripts.seed_tickets 500   # datos de carga
```

> Nota: la suite completa acumula datos de prueba en la base (clientes/tickets sintéticos). En
> desarrollo, si el volumen de datos residuales afecta la UI (p. ej. selectores que paginan a
> 100 ítems), `docker compose down -v && docker compose up --build -d` reinicia la base desde
> cero (Alembic vuelve a aplicar todas las migraciones automáticamente).

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

| # | Spec | Alcance | Estado |
|---|------|---------|--------|
| `001` | [fase0-maestros](specs/001-fase0-maestros/spec.md) | Clientes, Proyectos, Recursos/Skills, Roles/Permisos, login dual | ✅ Completa |
| `002` | [fase1-tickets](specs/002-fase1-tickets/spec.md) | FSM de tickets, comentarios, Triage Push, Panel de Asignación | ✅ Completa — tasks 44/44 |
| `003` | [reseteo-contrasenas](specs/003-reseteo-contrasenas/spec.md) | Reseteo de contraseñas y credenciales semilla | ✅ Completa |
| `004` | [fase2-registro-tiempos](specs/004-fase2-registro-tiempos/spec.md) | Registro diario de tiempos por recurso | ✅ Completa |
| `005` | [ticket-tiempo-encargado-nav](specs/005-ticket-tiempo-encargado-nav/spec.md) | Registro de tiempo en el detalle, rol Encargado, breadcrumbs | ✅ Completa |
| `006` | [ticket-detalle-tiempo-ui](specs/006-ticket-detalle-tiempo-ui/spec.md) | Refactor visual/navegación del detalle del ticket | ✅ Completa |
| `007` | [ticket-encargado-cliente](specs/007-ticket-encargado-cliente/spec.md) | Encargado solicitante asignable por Cliente en el ticket | ✅ Completa — quickstart 6/6 |
| `008` | [fase3-tareas](specs/008-fase3-tareas/spec.md) | Tarea sobre la misma tabla de Ticket, campo "Tipo de registro"; decisiones de Lista texto libre y FSM propia reemplazadas por la spec `009` | ✅ Completa — tasks 31/31 |
| `009` | [tareas-listas-subtareas](specs/009-tareas-listas-subtareas/spec.md) | Listas administrables, Subtareas, ciclo de vida unificado con Ticket (10 estados, transición libre) y fix de Registro de tiempo | ✅ Completa — tasks 45/45, suite 332/332 |

Cada carpeta de spec sigue la misma estructura: `spec.md`, `plan.md`, `research.md`,
`data-model.md`, `contracts/`, `tasks.md`, `quickstart.md`.

**Transversales**: [Constitución v1.1.0](.specify/memory/constitution.md) ·
[MER actual](docs/MER.md) (maestros + tickets, generado del schema real)

## Pendientes conocidos

- Validación visual en navegador de la Fase 1 (la validación E2E original fue por API; las
  fases posteriores ya se validan con navegador real vía preview).
- Auditorías de Fase 0: sanitización XSS (T066), logs sin datos VPN (T067), exposición
  frontend (T071).
- El cifrado pgcrypto es placeholder de desarrollo → reemplazar por `pgp_sym_encrypt`
  antes de producción.
- Fase 4 (SLAs) y siguientes del roadmap SDD V3 aún no iniciadas.
