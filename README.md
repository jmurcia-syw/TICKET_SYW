# SyWork Desk

Sistema interno de ticketing y gestión de tareas para el equipo de consultoría Oracle ERP/CRM
de SyWork. Construido con metodología **SDD (Spec-Driven Development)** sobre **GitHub Spec Kit**.

> **Fase activa**: `Festivos sincronizados por API, categorización visual y cumpleaños en el
> Calendario` (spec `021`) ✅ implementada — los festivos oficiales de cada país se sincronizan
> automáticamente desde una API pública (Nager.Date, con reintento y sin bloquear el sistema si
> falla), se categorizan como **Oficial** (afecta disponibilidad) o **Regional/Religioso** (solo
> informativo) con color/etiqueta propios, y la pestaña "Equipo" del calendario muestra el
> cumpleaños de cada Recurso como evento anual recurrente. Precedida por la Fase 5 SDD V3
> completa (spec `020`): calendarios multi-zona horaria por Cliente/Equipo, horario laboral
> semanal, vacaciones/permisos con doble aprobación (Jefe directo + rol RRHH) y alerta de
> disponibilidad (sin bloquear) al asignar tickets; por Accesos y conexiones múltiples del
> Cliente — VPN/URL por ambiente/Escritorio remoto (spec `018`); y por unidades de tiempo
> (minutos/horas/días) al configurar SLA (spec `019`). Rama: `develp_Jp`

---

## Roadmap (SDD V3)

| Fase SDD V3 | Descripción | Estado |
|-------------|-------------|--------|
| **1a — Maestros** | Clientes, Proyectos, Recursos/Skills, Roles/Permisos, login dual, compensación protegida (spec `001`) | ✅ **Completa** |
| **1b — Tickets** | Ciclo de vida de 9 estados (FSM), comentarios tipificados con adjuntos, Triage Push + Gold Standard Dataset, Panel de Asignación, notificaciones, enforcement JWT total (spec `002`) | ✅ **Completa** (validación E2E 26/26) |
| **2 — Registro de tiempos** | Registro diario de tiempos por recurso (hora inicio/fin), rol Usuario/cliente (autoservicio con Cliente fijo), breadcrumbs de navegación, Usuario/cliente seleccionable/editable por Cliente en el ticket, "Mis Tareas" (specs `004`, `005`, `006`, `007`) | ✅ **Completa** |
| **3 — Tareas** | Tarea/Subtarea sobre la misma tabla de Ticket (jerarquía Cliente → Proyecto → Lista → Tarea → Subtarea), ciclo de vida unificado con Ticket (10 estados, transición libre + comentario), visibles en Kanban, Listas administrables tipo Teamwork/Asana, Subtareas con Usuario/cliente propio, fix de Registro de tiempo para creador de la Tarea (specs `008`, `009`) | ✅ **Completa** |
| **4 — SLAs** | SLAs configurables por Proyecto × Prioridad, contador de 2 fases con pausa/reanudación según estado del ticket, indicadores en listado/dashboard y notificación proactiva de vencimientos vía Celery+Redis (spec `014`) | ✅ **Completa** |
| **5 — Calendarios y disponibilidad** | Calendarios multi-zona horaria por Cliente/Equipo, festivos por país sincronizados por API pública y categorizados (Oficial/Regional), horario laboral semanal, vacaciones/permisos con doble aprobación (Jefe directo + RRHH), cumpleaños del equipo y alerta de disponibilidad (sin bloquear) al asignar tickets (specs `020`, `021`) | ✅ **Completa** |
| 6 | Motor FSM automatizado + triggers de comentarios + Google Chat | ⏳ Pendiente |
| 7 | Focus Room + agente IA asistente (evaluar Triage Agent) | ⏳ Pendiente |
| 8 | Portal de clientes + integraciones + tickets por email | ⏳ Pendiente |

Fuentes de verdad: `docs/SDD V3.docx` (roadmap y alcances) y
`docs/Regla de actividad de estados.xlsx` (flujo de estados, codificado en
`backend/domain/fsm/ticket_fsm.py`).

> **Nota**: el renombre de rol Encargado → Usuario/cliente, su vínculo al Proyecto (en vez del
> Cliente), la sección "Personal del Proyecto" con subgrupos "Equipo" y la ampliación de Skills
> (spec `010`), el cronómetro manual de tiempo (spec `012`, provisional), las Skills requeridas
> del ticket (spec `011`) y el manejo global de errores (spec `013`) son cambios transversales
> sobre las Fases 1-3 ya completas, previos a la Fase 4 (SLAs, spec `014`) ya completada arriba.
> El Usuario/cliente en múltiples Proyectos y la corrección de su Cliente (specs `015`/`016`), el
> contenido enriquecido en tickets/comentarios (spec `017`), los accesos y conexiones múltiples
> del Cliente (spec `018`) y las unidades de tiempo del SLA (spec `019`) son cambios transversales
> posteriores a la Fase 4, previos a la Fase 5 (Calendarios y disponibilidad, specs `020`/`021`)
> ya completada arriba.

---

## Estado actual — Fase 1 (Tickets) + Fase 2 (Tiempos) + Fase 3 (Tareas) + Personal/Skills (spec `010`) + Cronómetro (spec `012`) + Manejo global de errores (spec `013`) + SLAs (spec `014`, Fase 4) + Usuario/cliente multi-Proyecto (spec `015`/`016`) + Contenido enriquecido (spec `017`) + Accesos del Cliente (spec `018`) + Unidades de tiempo SLA (spec `019`) + Calendarios/Vacaciones/Disponibilidad (spec `020`, Fase 5) + Festivos por API y cumpleaños (spec `021`)

### Funcionalidad operativa

- **Festivos sincronizados por API, categorización visual y cumpleaños** (spec `021`): una tarea
  Celery sincroniza los festivos oficiales de cada país desde la API pública Nager.Date (con
  reintento; si falla, el sistema sigue operando con los festivos ya cargados), categorizándolos
  como **Oficial** (afecta el cómputo de disponibilidad) o **Regional/Religioso** (solo
  informativo), cada uno con color/etiqueta propios sin colisionar entre sí. La pestaña "Equipo"
  del calendario muestra el cumpleaños de cada Recurso (`birth_date`) como evento anual
  recurrente. Corrige además el calendario colombiano, al que le faltaban el 20 de julio y los
  festivos móviles de la Ley Emiliani.
- **Calendarios, vacaciones y disponibilidad** (spec `020`, Fase 5 SDD V3): calendario
  multi-zona horaria por Cliente (huso/país) y por Equipo (zona por miembro), festivos por país,
  horario laboral semanal configurable por usuario, rol **RRHH** con solicitudes de ausencia
  (vacaciones/incapacidad/permiso) que exigen doble aprobación en cadena (Jefe directo + RRHH), y
  una alerta visual de disponibilidad (nunca bloqueante) al asignar un ticket a un recurso con
  ausencia o fuera de horario.
- **Unidades de tiempo en SLA** (spec `019`): al configurar el tiempo límite de
  Diagnóstico/Análisis/Ejecución de un SLA, el campo acepta minutos, horas o días y convierte
  internamente a minutos (el tiempo de Contacto sigue solo en minutos); no cambia el motor de
  cómputo de SLA de la spec `014`.
- **Accesos y conexiones múltiples del Cliente** (spec `018`): reemplaza los antiguos campos
  únicos de VPN del Cliente por múltiples registros de acceso/conexión (VPN, URL por ambiente
  DEV/TEST/PROD, Escritorio remoto), cada uno con usuario/contraseña y adjuntos propios y
  enmascarado de datos sensibles por defecto; corrige un bug de aislamiento de datos entre
  Clientes y resuelve las observaciones UAT OBS-0001/OBS-0008/OBS-0017.
- **Contenido enriquecido en tickets y comentarios** (spec `017`): la descripción de
  Ticket/Tarea y los comentarios admiten formato de texto (negrilla, cursiva, subrayado, listas,
  hipervínculos) vía un editor TipTap con toolbar; pegar contenido con formato (de un correo,
  Word o una web) conserva el formato compatible y las imágenes incrustadas se suben como
  adjuntos reales (no se pierden ni quedan como texto plano), igual que pegar directamente una
  captura de pantalla. La descripción también admite adjuntar archivos manualmente (paridad con
  los comentarios, spec 002). Todo el HTML se sanea en el servidor (`bleach`/`lxml`, lista
  blanca fija de tags/atributos) antes de persistir y de nuevo en el cliente (`DOMPurify`) antes
  de renderizar; las imágenes se muestran vía descarga autenticada (blob URL), nunca con un
  `<img src>` nativo que no podría mandar el header JWT.
- **Usuario/cliente en múltiples Proyectos** (spec `015`): un Usuario/cliente puede quedar
  vinculado a varios Proyectos del mismo Cliente (ya no solo uno) desde su alta o edición.
- **Corrección de Cliente de un Usuario/cliente** (spec `016`): si un Usuario/cliente queda con
  0 Proyectos (por ejemplo tras un error de alta), puede agregársele un Proyecto de **otro**
  Cliente para corregirlo; el selector de Proyecto muestra "Cliente — Proyecto" para desambiguar
  Proyectos homónimos entre distintos Clientes (ej. "SOPORTE" en dos clientes diferentes).
- **SLAs por Proyecto y Prioridad** (spec `014`, Fase 4 SDD V3): Admin/Coordinador configura
  reglas de SLA por combinación exacta Proyecto × Prioridad (sin reglas de respaldo/fallback),
  cada una con tiempo límite de Contacto y de Diagnóstico-Análisis-Ejecución. El ticket calcula
  su fase y consumo en tiempo real (sin persistir en cada lectura), pausa automáticamente en
  `pendiente_usuario` y reanuda sin reiniciar el contador, congela el resultado de Contacto al
  pasar a Ejecución. El listado y el dashboard muestran el estado agregado (`corriendo` /
  `pausado` / `vencido` / `sin_sla`) con filtros server-side y el stat "Vencen hoy". Una tarea
  periódica Celery (cada 5 min, sobre Redis) detecta vencimientos y notifica al Resolutor
  asignado y a los Coordinadores del proyecto. El cómputo de SLA nunca bloquea ni condiciona una
  transición del FSM (solo mide) y por ahora solo aplica a Tickets, no a Tareas/Subtareas.
- **Manejo global de errores y notificaciones** (spec `013`): toda respuesta de error de la
  API (todos los endpoints) sale con el contrato estándar `{success: false, message, code}`
  (+ campo legado `error`), aplicado por un normalizador global sin tocar las rutas; los 500
  no controlados nunca exponen detalles internos. El frontend captura todo error en el
  interceptor central de axios y muestra un toast (antd) con el mensaje del servidor o un
  genérico amigable, con dedupe de mensajes repetidos (~3 s); el 401 conserva la redirección
  a login sin toast.
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
- **Rol Usuario/cliente** (antes "Encargado", renombrado en spec `010` sin alterar permisos ni
  credenciales existentes): usuario de cliente externo con alta simplificada (solo email/usuario,
  contraseña provisional), flujo de creación de ticket autoservicio, sin acceso a Maestros/
  Catálogos/Panel de Asignación.
- **Usuario/cliente vinculado al Proyecto** (spec `010`, reemplaza el filtro por Cliente de la
  spec `007`): al crear o editar un ticket, Coordinador/Resolutor eligen el solicitante desde una
  lista filtrada por **Proyecto** (personal asignado a ese Proyecto); el campo se limpia si
  cambia el Proyecto y queda bloqueado/no editable en tickets de autoservicio o en estados
  finales (Cerrado/Cancelado). El autoservicio del Usuario/cliente queda acotado a los Proyectos
  a los que está vinculado (dentro de su Cliente fijo); la migración `025` conserva el histórico
  de solicitantes y backfillea las membresías desde los tickets existentes.
- **Personal del Proyecto y "Equipo"** (spec `010`, estilo Teamwork): sección "Asignar Personal"
  en la vista de edición del Proyecto (`/projects/:id/people`) para vincular cualquier usuario
  activo del sistema (Resolutor, Coordinador, QM, Usuario/cliente, Admin) con nombre/correo/tipo;
  subgrupos "Equipo" para agrupar personal ya asignado (una persona puede estar en varios); solo
  Coordinador/Admin (`projects:edit`) mutan, el resto consulta en solo lectura.
- **Skills con estructura** (spec `010`): cada Skill declara **tipo** obligatorio (funcional |
  técnico), **herramienta** y **proceso** opcionales (catálogos existentes); 10 skills semilla de
  referencia (JDE_GL, JDE_AP, JDE_MTC, BSFN, SQL_JDE, OIC, APEX, BI, JAVA/PYTHON/REACT, DBA) y
  backfill de tipo para las preexistentes.
- **Mis Tareas** y **breadcrumbs de navegación** estilo Teamwork (Kanban → Detalle → Volver
  respeta el origen exacto).
- **Tareas y Subtareas** (Fase 3, misma tabla/entidad que Ticket, jerarquía Cliente → Proyecto →
  Lista → Tarea → Subtarea): mismo ciclo de 10 estados que el Ticket con **transición libre**
  (cualquier estado a cualquier otro, exige comentario) en vez de una FSM propia; mismos campos
  de clasificación (Tipo, Severidad, Herramienta, Proceso, Nivel de escalamiento) visibles y
  editables; aparecen en el **Kanban** junto a los Tickets con badge de tipo de registro.
- **Listas de tareas administrables**: entidad real por Proyecto (ya no texto libre), sidebar
  tipo Teamwork/Asana con conteo de tareas, creación y renombrado.
- **Subtareas** con Usuario/cliente y estado propios (no heredan el estado del padre), comentarios
  simples en Tarea/Subtarea sin cambio de estado.
- **Registro de tiempo sobre Tareas**: un recurso puede registrar tiempo sobre una Tarea/Subtarea
  que creó, sin exigir el historial formal de asignaciones de Triage (que solo aplica a Ticket).
- **Cronómetro manual de tiempo** (spec `012`, provisional): en el detalle del ticket, el recurso
  asignado puede Iniciar/Pausar/Reanudar/Terminar un cronómetro propio; es personal (solo lo ve
  quien lo inició), persiste en backend (sobrevive recargas y cierres de sesión) y admite un solo
  cronómetro activo por recurso a la vez. Al "Terminar" genera un Registro de tiempo formal
  reutilizando `WorkSessionService.create()` sin duplicar sus reglas (bloquea en ticket cerrado,
  respeta el límite diario, exige un mínimo de 60 segundos acumulados).

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

- **Validación de las specs `020`/`021`** (Calendarios/Vacaciones/Disponibilidad + Festivos por
  API): 52/52 tareas de la spec `020` (7 fases: Setup, Foundational, US1-US4, Polish) y 27/27
  tareas de la spec `021` (6 fases) marcadas completas; el commit `26b4caf` corrige, tras
  validación, una colisión de colores entre categorías de festivo y peticiones duplicadas a la
  API de festivos.
- **Validación de las specs `018`/`019`** (Accesos del Cliente + unidades de tiempo de SLA):
  29/29 tareas de la spec `018` y 11/11 de la spec `019` marcadas completas.
- **Validación de las specs `015`/`016`** (Usuario/cliente multi-Proyecto + corrección de
  Cliente): 13/13 tests dirigidos en verde (`test_client_contacts_projects.py`), `tsc -b` sin
  errores, quickstart de ambas specs (Escenarios 1-4) validado contra Docker real.
- **Validación de la spec `017`** (Contenido enriquecido): 10/10 tests dirigidos en verde
  (`test_tickets_rich_content.py`, cubre US1 formato + US2 imágenes pegadas + US3 adjuntos
  manuales), `tsc -b` sin errores, y recorrido E2E de los 7 escenarios del quickstart contra
  Docker real. La validación en navegador encontró y corrigió dos bugs reales antes de cerrar la
  feature: (1) el backend saneaba el HTML (`bleach`) *antes* de resolver los `data-pending-id`
  de imágenes pegadas, despojando el atributo temporal antes de poder reescribirlo a la URL real
  del adjunto; (2) `RichTextViewer` pasaba un objeto nuevo a `dangerouslySetInnerHTML` en cada
  render, y cualquier re-render de la página (ej. el timer de la Sesión de Foco, que cambia de
  estado cada segundo) revertía el swap a blob URL de las imágenes ya cargadas.
- Tests de dominio + API contra Postgres real en Docker ✅ (suite dirigida por feature)
- **Validación E2E** de la Fase 1 (6 escenarios del quickstart): 26/26 checks ✅
- **Validación E2E** de la Fase 2.2 (Usuario/cliente asignable por Cliente, spec `007`): 6/6
  escenarios del quickstart validados contra Docker real (creación con/sin Usuario/cliente,
  autoservicio inmutable, reasignación, bloqueo por estado, limpieza al cambiar Cliente,
  permiso de lectura para Resolutor)
- **Validación E2E** de la Fase 3 (Tareas, Listas y Subtareas, spec `009`): quickstart
  Escenarios 0-6 contra Docker real (migración de datos, registro de tiempo por creador,
  transición libre + Kanban, Listas administrables, Subtareas con Usuario/cliente propio,
  comentarios simples, regresión de Ticket sin cambios); suite completa `332/332` tests en verde
- **Validación de la spec `010`** (Usuario/cliente por Proyecto, Personal y Skills): tests
  dirigidos en verde (`test_project_members.py`, `test_skills_structure.py`,
  `test_tickets_client_contact.py`, `test_tickets_encargado.py`,
  `test_ticket_service_client_contact.py`) + `tsc -b` sin errores; quickstart 0-6 según
  `tasks.md`. Por directriz explícita de la spec (FR-020) **no** se corrió la suite completa
  durante el desarrollo — pendiente confirmarla en verde tras este cambio.
- **Validación de la spec `012`** (Cronómetro manual de tiempo): 24/24 tests dirigidos en verde
  (`test_timer.py` + regresión de `work_sessions`), `tsc -b` sin errores, y recorrido E2E manual
  en navegador contra Docker real (ciclo completo iniciar → pausar → reanudar → terminar,
  persistencia entre recargas, bloqueo por duración mínima).
- **Performance** con 500+ tickets: panel 64 ms (SC < 2 s), listado 52 ms (SC < 1 s) ✅
- Typecheck frontend estricto sin errores ✅

---

## Stack Tecnológico

### Backend
- **Python 3.12** + **Flask 3.x** + **Flask-RESTX** (Swagger en `/swagger`)
- **python-transitions** (FSM del ciclo de vida — Capa 1, dominio puro)
- **SQLAlchemy 2.x** + **Alembic** (revisión `040` — dueño único del schema)
- **PostgreSQL 16** on-premise con RLS y pgcrypto
- **Flask-JWT-Extended** + login provisional usuario/contraseña + **Google OAuth2** (`@sywork.net`)
- **Celery 5.4** + **Redis 5.2**: tarea periódica de vencimientos de SLA (spec `014`) y
  sincronización de festivos por país (spec `021`)
- **`requests`** (spec `021`): cliente de la API pública de festivos Nager.Date

### Frontend
- **React 19** + **TypeScript strict** (prohibido `any`)
- **Ant Design 5** · **Zustand 5** · **React Router v6** · **Axios**
- **pnpm** exclusivamente · **date-fns**

### Infraestructura
- **Docker Compose**: `sywork_db` (5432) · `sywork_backend` (5000) · `sywork_frontend` (5173) ·
  `sywork_redis` (broker de Celery) · `sywork_worker` (Celery worker — vencimientos de SLA y
  sincronización de festivos)
- Adjuntos en volumen `uploads/` (fuera de git)

---

## Arquitectura (Clean Architecture — 3 capas)

```
backend/
├── domain/            # Capa 1 — sin imports de Flask/SQLAlchemy
│   ├── entities/      # Ticket, Comment, Notification, Client (+ ClientSystem, ClientAccess,
│   │                  # ClientAccessAttachment, spec 018), Project, Resource, User, Role,
│   │                  # ClientContact, WorkSession, ProjectMember, ProjectTeam, Calendar (+
│   │                  # Holiday, WorkSchedule, AbsenceRequest, spec 020/021)
│   ├── fsm/           # ticket_fsm.py — matriz de 16 transiciones (python-transitions)
│   └── services/      # ticket, comment, assignment, notification, compensation,
│                      # client_contact, work_session, project_member, skill,
│                      # rich_content (saneamiento HTML + resolución de imágenes pegadas),
│                      # absence_service, availability_service (spec 020),
│                      # holiday_sync_service (spec 021), ...
├── infra/             # Capa 2
│   ├── external/      # holiday_api_client.py — cliente de la API pública Nager.Date (spec 021)
│   ├── models/        # SQLAlchemy (tickets, comments, catalogs, notifications, maestros,
│   │                  # client_contacts, work_sessions, task_lists, project_member_model,
│   │                  # calendar_model — festivos/horarios/ausencias, spec 020/021)
│   ├── repositories/  # paginación, filtros, historiales append-only, calendar_repo
│   ├── storage/       # adjuntos en filesystem (uploads/tickets/{id}/)
│   └── migrations/    # Alembic 001..040
├── workers/           # celery_app.py, sla_tasks.py (spec 014), holiday_sync_tasks.py (spec 021)
└── api/               # Capa 3
    ├── middleware/    # auth.py (JWT + usuario activo), rbac.py (@require_permission)
    └── routes/        # tickets, catalogs, notifications, assignment_panel, client_contacts,
                       # work_sessions, task_lists, project_members, calendar (festivos,
                       # horarios, ausencias, disponibilidad — spec 020/021) + maestros

frontend/src/
├── components/tickets/     # TicketStatusTag, AssignModal, CommentThread, CommentComposer,
│                           # TicketBreadcrumb, TaskStatusChanger, SubtaskList,
│                           # RichTextEditor, RichTextViewer (TipTap + DOMPurify, spec 017)
├── components/worksessions/ # WorkSessionForm, TimeLogModal, TicketWorkSessions
├── components/sla/         # SlaRuleForm (selector de unidad minutos/horas/días, spec 019)
├── components/common/      # NotificationBell, ProtectedRoute, ConfirmationModal, ...
├── pages/                  # TicketsPage, TicketDetailPage, AssignmentPanelPage, CatalogsPage,
│                           # MyTasksPage, WorkSessionsPage, TimeReportPage, ClientContactsPage,
│                           # ProjectListsPage, ProjectPeoplePage, KanbanPage, SkillsPage,
│                           # SlaRulesPage, CalendarPage (festivos, horario, vacaciones, Equipo
│                           # con cumpleaños — spec 020/021) + maestros
├── services/                # ticketService, catalogService, notificationService,
│                            # clientContactService, workSessionService, taskListService,
│                            # projectMemberService, resourceService, slaService,
│                            # calendarService + maestros
├── store/               # authStore (Zustand: token, permisos, hasPermission)
└── types/               # tipos estrictos por dominio
```

---

## Instalación y despliegue

### Requisitos previos

| Componente | Uso |
|------------|-----|
| **Docker Desktop** (o Docker Engine + Compose v2) | Orquesta los 5 servicios: `sywork_db`, `sywork_backend`, `sywork_frontend`, `sywork_redis`, `sywork_worker` |
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

Esto construye las imágenes y arranca, en orden:

1. **`sywork_db`** (Postgres 16) — espera a estar `healthy` antes de continuar.
2. **`sywork_backend`** (Flask) — corre `alembic upgrade head` automáticamente al iniciar
   (revisión `040`) y luego levanta el servidor en `:5000`.
3. **`sywork_frontend`** (Vite) — sirve la SPA en `:5173`.
4. **`sywork_redis`** — broker de Celery.
5. **`sywork_worker`** (Celery) — vencimientos de SLA (spec `014`) y sincronización periódica
   de festivos por país (spec `021`).

```bash
docker compose ps                       # verificar que los 5 estén "Up"
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

### Entornos Test y Producción (aislados, mismo servidor)

Spec [`027`](specs/027-docker-entornos-aislados/spec.md): el mismo `docker-compose.yml` corre dos
veces en paralelo en el mismo host Ubuntu — una vez como ambiente de **Test** y otra como
**Producción** — diferenciados por puertos, nombre de proyecto Compose y archivo de variables,
sin tocar el flujo de desarrollo local (`docker compose up` sin flags sigue funcionando igual que
siempre, con los defaults de puerto `5173`/`5000`/`5432`/`6379`).

#### Ambiente de Test

```bash
cp .env.test.example .env.test
nano .env.test    # completar POSTGRES_PASSWORD, JWT_SECRET, etc. (nunca commitear este archivo)

docker compose -p sywork_test --env-file .env.test up --build -d
docker compose -p sywork_test --env-file .env.test ps
```

- **App**: http://localhost:8080
- **API**: http://localhost:3001 (`/swagger`, `/health/`)
- **Postgres**: `localhost:5433`

#### Ambiente de Producción

```bash
cp .env.prod.example .env.prod
nano .env.prod    # completar con secretos reales de producción (nunca commitear este archivo)

docker compose -p sywork_prod --env-file .env.prod up --build -d
docker compose -p sywork_prod --env-file .env.prod ps
```

- **App**: http://localhost:80
- **API**: http://localhost:3000 (`/swagger`, `/health/`)
- **Postgres**: `localhost:5432`

> Los puertos `80`/`3000` publicados por Docker Compose son el mapeo **interno**, no la
> exposición final HTTPS al usuario — la terminación TLS/proxy inverso sigue pendiente
> (`TODO(HOSTING)` en la Constitución, ver también sección "Despliegue en servidor" arriba).

Test y Producción pueden estar `Up` al mismo tiempo: cada uno usa su propio nombre de proyecto
Compose (`-p`), lo que namespacea automáticamente su red y su volumen de datos (`postgres_data`
queda completamente separado entre ambientes), y sus propios nombres de contenedor
(`sywork_db_test` / `sywork_db_prod`, etc.).

#### Logs y parada por ambiente

**Siempre nombrar el ambiente explícitamente** (`-p` + `--env-file`) al operar sobre Test o
Producción — omitirlos puede apuntar al stack equivocado y detener/afectar el ambiente incorrecto:

```bash
# Logs de un ambiente puntual (no se mezclan con el otro)
docker compose -p sywork_test --env-file .env.test logs -f backend
docker compose -p sywork_prod --env-file .env.prod logs -f backend

# Detener solo un ambiente (el otro sigue corriendo sin interrupción)
docker compose -p sywork_test --env-file .env.test down
docker compose -p sywork_prod --env-file .env.prod down
```

`down` (sin `-v`) conserva los datos de ese ambiente; agregar `-v` solo si se quiere descartar el
volumen de datos de ese ambiente en particular:

```bash
# Reinicio completo de un ambiente (borra su volumen de Postgres, uno a la vez)
# Test:
docker compose -p sywork_test --env-file .env.test down -v
docker compose -p sywork_test --env-file .env.test up --build -d

# Producción:
docker compose -p sywork_prod --env-file .env.prod down -v
docker compose -p sywork_prod --env-file .env.prod up --build -d
```

No afecta al stack de Desarrollo (`sywork_db`, sin `-p`) ni a su volumen `postgres_data` — son
proyectos Compose distintos. Detalle completo de variables, puertos y decisiones de diseño:
[`specs/027-docker-entornos-aislados/research.md`](specs/027-docker-entornos-aislados/research.md)
y [`quickstart.md`](specs/027-docker-entornos-aislados/quickstart.md).

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
| `010` | [proyecto-personal-skills](specs/010-proyecto-personal-skills/spec.md) | Renombre Encargado → Usuario/cliente, vínculo al Proyecto (en vez del Cliente), Personal del Proyecto + "Equipo" estilo Teamwork, Skills con tipo/herramienta/proceso y semillas | ✅ Completa — tasks 35/35, tests dirigidos en verde (suite completa no corrida, FR-020) |
| `011` | [ticket-skills-requeridas](specs/011-ticket-skills-requeridas/spec.md) | Skills opcionales en el ticket para identificar habilidades necesarias para resolverlo | ⏳ Spec lista, sin plan/tasks |
| `012` | [cronometro-manual-ticket](specs/012-cronometro-manual-ticket/spec.md) | Cronómetro manual de tiempo (provisional) en el detalle del ticket: iniciar/pausar/reanudar/terminar por recurso, genera Registro de tiempo formal | ✅ Completa — tasks 21/21, 24/24 tests, validado E2E en navegador |
| `013` | [manejo-errores-notificaciones](specs/013-manejo-errores-notificaciones/spec.md) | Normalizador global de errores de la API (`{success,message,code}`) + notificaciones toast en el frontend | ✅ Completa |
| `014` | [sla-tickets-tareas](specs/014-sla-tickets-tareas/spec.md) | SLAs configurables por Proyecto × Prioridad, contador de 2 fases, indicadores agregados y notificación proactiva de vencimientos vía Celery+Redis (Fase 4 SDD V3) | ✅ Completa — tasks 30/30, 63 tests dirigidos, suite 437/437, quickstart 3/3 validado contra Docker real |
| `015` | [encargado-multiples-proyectos](specs/015-encargado-multiples-proyectos/spec.md) | Un Usuario/cliente puede pertenecer a múltiples Proyectos del mismo Cliente, no solo uno | ✅ Completa — tasks 15/15, quickstart 4/4 |
| `016` | [corregir-cliente-encargado](specs/016-corregir-cliente-encargado/spec.md) | Corregir el Cliente de un Usuario/cliente agregando un Proyecto de otro Cliente cuando queda en 0 Proyectos; desambiguar Proyectos homónimos ("Cliente — Proyecto" en el selector) | ✅ Completa — tasks 10/10, quickstart 4/4 |
| `017` | [contenido-enriquecido-ticket](specs/017-contenido-enriquecido-ticket/spec.md) | Formato de texto enriquecido, pegado de contenido con imágenes incrustadas y adjuntos manuales en comentarios y en la descripción de Ticket/Tarea | ✅ Completa — tasks 37/37, 10 tests dirigidos, quickstart 7/7 validado contra Docker real |
| `018` | [cliente-accesos-conexiones](specs/018-cliente-accesos-conexiones/spec.md) | Múltiples registros de acceso/conexión del Cliente (VPN, URL por ambiente, Escritorio remoto) con adjuntos y enmascarado por defecto; corrige aislamiento entre clientes (OBS-0001/0008/0017) | ✅ Completa — tasks 29/29 |
| `019` | [sla-unidades-tiempo](specs/019-sla-unidades-tiempo/spec.md) | Selector de unidad (minutos/horas/días) en el tiempo límite de Diagnóstico/Análisis/Ejecución del SLA, con conversión interna a minutos | ✅ Completa — tasks 11/11 |
| `020` | [calendarios-vacaciones-disponibilidad](specs/020-calendarios-vacaciones-disponibilidad/spec.md) | Fase 5 SDD V3: calendarios multi-zona horaria, festivos por país, horario laboral semanal, vacaciones/permisos con doble aprobación (Jefe directo + RRHH) y alerta de disponibilidad al asignar tickets | ✅ Completa — tasks 52/52 (7 fases) |
| `021` | [festivos-api-cumpleanos](specs/021-festivos-api-cumpleanos/spec.md) | Festivos oficiales sincronizados por API pública (Nager.Date), categorización Oficial/Regional con color propio, y cumpleaños de Recursos en la pestaña "Equipo" del calendario | ✅ Completa — tasks 27/27 (6 fases) |

Cada carpeta de spec sigue la misma estructura: `spec.md`, `plan.md`, `research.md`,
`data-model.md`, `contracts/`, `tasks.md`, `quickstart.md`.

**Transversales**: [Constitución v1.3.0](.specify/memory/constitution.md) ·
[MER actual](docs/MER.md) (maestros + tickets, generado del schema real)

## Pendientes conocidos

- Validación visual en navegador de la Fase 1 (la validación E2E original fue por API; las
  fases posteriores ya se validan con navegador real vía preview).
- Auditorías de Fase 0: sanitización XSS (T066), logs sin datos VPN (T067), exposición
  frontend (T071).
- El cifrado pgcrypto es placeholder de desarrollo → reemplazar por `pgp_sym_encrypt`
  antes de producción.
- Fase 6 (motor FSM automatizado + triggers de comentarios + Google Chat) y siguientes del
  roadmap SDD V3 (Fases 7-8) aún no iniciadas.
- Spec `010`: correr la suite completa de tests (no ejecutada durante el desarrollo por
  directriz explícita FR-020) para confirmar ausencia de regresiones fuera de los archivos
  tocados.
- Spec `014` (SLAs): FR-011 (recalcular SLA al cambiar el Proyecto de un ticket) solo es
  parcialmente alcanzable — `project_id` no está hoy en los campos editables (`PATCHABLE_FIELDS`)
  de ningún endpoint, así que solo el cambio de Prioridad ejercita esa lógica en producción.
- Spec `011` (Skills requeridas en el ticket): la spec quedó redactada pero sin `plan.md`/
  `tasks.md` — no implementada aún.
