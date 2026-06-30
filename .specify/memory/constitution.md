<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0 (initial ratification)
Modified principles: N/A — primera version
Added sections:
  - Core Principles (I-VI)
  - Stack Tecnologico y Gobernanza de Librerias
  - Convenciones de Nomenclatura y Estructura
  - Gobernanza
Templates reviewed:
  - .specify/templates/plan-template.md (compatible, sin actualizaciones necesarias)
  - .specify/templates/spec-template.md (compatible, sin actualizaciones necesarias)
  - .specify/templates/tasks-template.md (compatible, sin actualizaciones necesarias)
Deferred TODOs:
  - TODO(HOSTING): Definir entorno de hosting on-premise (servidor, SO, proxy inverso)
  - TODO(SSO_DETAIL): Detallar configuracion SSO si se extiende mas alla de @sywork.net
-->

# SyWork Tickets Constitution

## Core Principles

### I. API-First y Dominio Primero (NON-NEGOTIABLE)

La logica de negocio DEBE residir exclusivamente en la Capa 1 (Core/Dominio), libre de dependencias
externas. Todo acceso a funcionalidad de negocio desde el exterior DEBE pasar por un contrato de API
(Swagger/OpenAPI 3.0) definido antes de la implementacion.

- El dominio (FSM de tickets, reglas SLA, entidades) NO puede importar Flask, SQLAlchemy ni ningun
  framework externo.
- El contrato Swagger DEBE existir antes de escribir el codigo del endpoint.
- El endpoint `POST /api/tickets/{id}/assign` DEBE ser un endpoint de backend independiente, nunca
  acoplado a la pantalla del coordinador. Esta es la puerta de entrada para el futuro AI Dispatcher.
- Prohibido hardcodear logica de negocio en componentes React o en rutas Flask directamente.

### II. Clean Architecture - Tres Capas (NON-NEGOTIABLE)

El sistema se divide estrictamente en tres capas con dependencia unidireccional (externas a internas):

- **Capa 1 - Core/Dominio** (`backend/domain/`): FSM con `python-transitions`, motor SLA, entidades
  (`Ticket`, `Comment`, `User`, `WorkSession`). Sin imports de Flask, SQLAlchemy ni librerias externas.
- **Capa 2 - Datos/Infraestructura** (`backend/infra/`): Repositorios SQLAlchemy, cliente HTTP,
  modulos de reportes. Implementa interfaces definidas en Capa 1.
- **Capa 3 - Presentacion** (`backend/api/` y `frontend/src/`): Rutas Flask, componentes React.
  Solo orquesta y renderiza, nunca contiene logica de negocio.

La logica de negocio y llamadas API del frontend DEBEN vivir en `frontend/src/services/`.
Los componentes en `frontend/src/components/` DEBEN ser "tontos": solo reciben props y renderizan.

### III. Tipado Estricto y Seguridad de Tipos (NON-NEGOTIABLE)

- TypeScript: `"strict": true` en el compilador. **Prohibido usar `any`** sin justificacion
  documentada y aprobada en planificacion.
- Python: type hints obligatorios en funciones publicas del dominio y servicios.
- Ningun componente que corra en el navegador DEBE contener claves de API, cadenas de conexion a
  bases de datos o credenciales del servidor.
- El frontend solo interactua con el backend mediante JWT y la variable publica `VITE_API_URL`.

### IV. Seguridad en Profundidad - Doble Proteccion (NON-NEGOTIABLE)

- **Autenticacion**: JWT sin estado. SSO via Google OAuth2 restringido al dominio `@sywork.net`.
- **Autorizacion a nivel de datos**: Row Level Security (RLS) en PostgreSQL habilitado en todas
  las tablas con datos sensibles. Un usuario SOLO puede ver tickets que le corresponden, incluso
  si la API es comprometida.
- **Transporte**: HTTPS / TLS 1.3 obligatorio. No se acepta HTTP en produccion.
- **Secretos**: Variables de entorno en `.env` del backend (nunca comiteadas). `VITE_API_URL` es
  la unica variable publica permitida en el frontend.
- Prohibido exponer detalles de errores internos (stack traces, queries SQL) en respuestas de API.

### V. Gobernanza de Librerias - Zero Dependencias No Aprobadas

Ningun agente IA ni desarrollador puede anadir dependencias al `package.json` o `requirements.txt`
sin aprobacion previa documentada en el documento de Planificacion de la fase correspondiente.

Stack aprobado y obligatorio:

| Capa | Tecnologia aprobada | Prohibiciones explicitas |
|------|---------------------|--------------------------|
| Gestor paquetes JS | `pnpm` | `npm`, `yarn` |
| UI components | `Ant Design 5` | Crear componentes desde cero salvo necesidad estricta |
| Drag and drop | `@hello-pangea/dnd` | Cualquier alternativa |
| Estado global | `Zustand` | `Redux`, `Context API` para logicas complejas |
| Fechas | `date-fns` | `moment.js` (obsoleto, prohibido terminantemente) |
| FSM | `python-transitions` | Implementacion custom de maquinas de estado |
| ORM | `SQLAlchemy` + `Alembic` | ORM alternativo, migraciones manuales |
| Tareas async | `Celery` + `Redis` | — |

### VI. AI-Native - Preparacion para Agentes IA

La aplicacion DEBE ser disenada desde Fase 1 para que un agente IA pueda operar sus funciones
criticas en el futuro sin cambios de arquitectura.

- Las acciones del Coordinador humano (asignacion de tickets, cambios de estado) DEBEN crear un
  "Gold Standard Dataset": registros completos con contexto (skills del resolutor, carga de
  trabajo, severidad) para entrenamiento futuro del AI Dispatcher.
- Los endpoints de accion (`/assign`, `/status`) DEBEN ser agnosticos al caller (humano o IA).
- Los skills de resolutores DEBEN estar parametrizados con etiquetas estrictas
  (ej. `JDE_GL`, `API_REST`, `Oracle_Fusion`). La IA no puede asignar por "intuicion".
- El sistema de comentarios DEBE exponer tipos de comentario como datos estructurados (no texto
  libre) para facilitar el analisis automatico futuro.

## Stack Tecnologico y Gobernanza de Librerias

### Stack completo aprobado

**Frontend**
- React 19 + TypeScript strict
- Ant Design 5
- `@hello-pangea/dnd` (Kanban drag and drop)
- Zustand (estado global)
- `date-fns` (manejo de fechas)
- `pnpm` (gestor de paquetes)
- Vite 6 (build tool / dev server)
- Axios (cliente HTTP)

**Backend**
- Python 3.12 + Flask
- Flask-RESTX (Swagger / OpenAPI 3.0)
- `python-transitions` (FSM ciclo de vida del ticket)
- Flask-JWT-Extended
- SQLAlchemy + Alembic (ORM + migraciones)
- Celery + Redis (tareas async: notificaciones, SLA timers, emails automaticos)
- SLA Engine (custom, Capa 1)
- `google-auth` (OAuth2)

**Infraestructura**
- PostgreSQL 16 (on-premise, con RLS)
- Docker + Docker Compose (orquestacion)
- TODO(HOSTING): Definir servidor on-premise, SO, proxy inverso

### FSM - Estados y transiciones del ticket

```
nuevo -> asignado -> en_progreso <-> pendiente -> resuelto -> cerrado
```

| Estado | SLA activo | Trigger de entrada |
|--------|-----------|-------------------|
| nuevo | Si | estado inicial |
| asignado | Si | `asignar()` |
| en_progreso | Si | `iniciar()` |
| pendiente | No (pausado) | `pausar()` / `contactar_cliente()` |
| resuelto | Si | `resolver()` |
| cerrado | — (final) | `cerrar()` / auto-cierre configurable |

Solo se permiten transiciones explicitamente definidas en la maquina de estados.

### Modelo de datos - Jerarquia de 5 niveles

```
clients           (RLS root, Nivel 1)
  projects        (FK: client_id, Nivel 2)
    task_lists    (FK: project_id, Nivel 3)
      tasks       (FK: task_list_id, FSM + SLA + comentarios, Nivel 4)
        subtasks  (autorreferencial FK: parent_task_id, sin SLA propio, Nivel 5)
```

### Endpoints de API principales (contrato minimo Fase 1)

```
GET    /api/tickets                 lista paginada con filtros
POST   /api/tickets                 crear ticket
GET    /api/tickets/{id}            detalle
PATCH  /api/tickets/{id}/status     transicion FSM
POST   /api/tickets/{id}/assign     asignar resolutor (independiente del frontend)
POST   /api/tickets/{id}/comments   agregar comentario
GET    /api/users/{id}/workload     carga del resolutor
POST   /api/sessions/start          iniciar Work Session / Focus Mode
POST   /api/sessions/end            cerrar Work Session
```

## Convenciones de Nomenclatura y Estructura

### Nomenclatura

| Ambito | Convencion | Ejemplo |
|--------|-----------|---------|
| Componentes React | PascalCase | `TicketList.tsx`, `KanbanBoard.tsx` |
| Funciones / utilidades | camelCase | `formatDate.ts`, `calculateSla.ts` |
| Tablas y columnas DB | snake_case | `ticket_status`, `created_at`, `assignee_id` |
| Etiquetas de skills | UPPER_SNAKE | `JDE_GL`, `API_REST`, `Oracle_Fusion` |
| Ramas de feature | ###-feature-name | `001-ticket-crud` |

### Estructura de directorios

```
frontend/src/
  components/   UI "tontos" (Ant Design, Kanban cards)
  services/     Logica + llamadas API
  store/        Zustand stores
  types/        Interfaces TypeScript
  pages/        Vistas completas

backend/
  domain/       Capa 1: FSM, SLA Engine, entidades puras
  infra/        Capa 2: Repositorios SQLAlchemy, adaptadores
  api/          Capa 3: Rutas Flask, serializacion
```

## Governance

Esta Constitucion SUPERSEDE todas las practicas individuales, convenciones de equipo y decisiones
ad-hoc previas. Todo agente IA y todo desarrollador DEBEN leerla antes de tocar codigo.

**Reglas de cumplimiento:**
- Todo PR/revision DEBE verificar conformidad con los principios I-VI antes de aprobarse.
- Toda violacion de un principio NON-NEGOTIABLE DEBE documentarse en la tabla "Complexity Tracking"
  del `plan.md` de la fase, con justificacion y alternativa rechazada.
- Nuevas dependencias requieren aprobacion en el documento de Planificacion de la fase, no en PR.
- Los endpoints de accion critica (`/assign`, `/status`) NO pueden ser refactorizados para
  acoplarlos a la UI sin aprobacion explicita de arquitectura.

**Proceso de enmienda:**
1. Proponer cambio documentando: principio afectado, motivacion, impacto en fases existentes.
2. Revisar con el equipo.
3. Actualizar este archivo incrementando la version (MAJOR/MINOR/PATCH segun semver).
4. Propagar cambios a templates en `.specify/templates/`.
5. Actualizar `Last Amended`.

**Version**: 1.0.0 | **Ratified**: 2026-06-29 | **Last Amended**: 2026-06-29
