<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 → 1.2.0 (2026-07-10, directrices de alcance de sesion y testing para agentes IA)
Modified principles: N/A — principios I-VI sin cambios de fondo
Added sections:
  - Principio VII (NON-NEGOTIABLE): Alcance de Sesion, Testing Ultra-Limitado y Eficiencia de Tokens
Removed sections: N/A
Templates reviewed:
  - .specify/templates/*: compatibles, sin actualizaciones necesarias (el nuevo principio rige el
    comportamiento del agente durante la ejecucion, no la estructura de spec/plan/tasks)
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

### VII. Alcance de Sesion, Testing Ultra-Limitado y Eficiencia de Tokens (NON-NEGOTIABLE)

Aplica a todo agente IA que trabaje en este repositorio, en particular durante ejecucion de
codigo y pruebas.

- **Aislamiento de sesion**: cada sesion DEBE enfocarse unica y exclusivamente en los archivos y
  el contexto directo de la tarea solicitada en esa sesion. Prohibido realizar refactorizaciones
  externas, optimizaciones de codigo no solicitadas o inserciones en otros modulos ajenos al
  alcance pedido.
- **Restriccion de pruebas unitarias**: prohibido ejecutar la suite de pruebas unitarias de forma
  masiva o global. Solo se permite ejecutar el test especifico del modelo, controlador o
  componente modificado en la sesion actual. Las pruebas unitarias nuevas o modificadas DEBEN ser
  ultra-limitadas: no deben generar ni insertar mas de 5 a 10 registros de prueba/falsos en la
  base de datos por test.
- **Eficiencia de consumo**: las respuestas en consola DEBEN ser directas a la edicion del archivo
  o spec de SpecKit correspondiente, evitando explicaciones teoricas redundantes que consuman
  tokens innecesariamente.

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

**Fuente de verdad**: `docs/Regla de actividad de estados.xlsx` (SDD V3). Este flujo reemplaza
el flujo provisional de 6 estados de la v1.0.0.

```
NUEVO ──asignar resolutor──> CONTACTO ──"Confirmación de atención"──> EN ANÁLISIS
  │                             ▲                                        │
  └──asignar QM──> PRE-ANÁLISIS ┘                       "Termina análisis"
                        │                                                ▼
                        └───"Solicitud de información"──> PENDIENTE DE USUARIO <──┐
                                                              │ (respuesta)       │
                                                              ▼                   │
                                       EN EJECUCIÓN ──"Solicitud de información"──┘
                                          │    │
                                (EN PRUEBAS)   └──"Solicitud de cierre"──> RESUELTO
                                                     acepta usuario / 3 días ──> CERRADO
                                                     rechaza usuario ──> EN EJECUCIÓN
```

| Estado | Rol que atiende | Trigger de entrada | Campos bloqueados |
|--------|-----------------|--------------------|-------------------|
| NUEVO | Coordinador | Creacion manual o por integracion | ninguno |
| PRE-ANÁLISIS | QM | Coordinador asigna al QM | ninguno |
| CONTACTO | Resolutor | Coordinador/QM asigna resolutor | tiempo SLA, severidad, prioridad |
| EN ANÁLISIS | Resolutor | Comentario "Confirmación de atención" | se desbloquean tiempo estimado, severidad, prioridad |
| EN EJECUCIÓN | Resolutor | Comentario "Termina análisis" o respuesta del usuario | tiempo de resolucion |
| EN PRUEBAS | Resolutor | (pendiente de definicion en el SDD — marcado con "?") | tiempo de resolucion |
| PENDIENTE DE USUARIO | Usuario/N1/cliente | Comentario "Solicitud de información" o "Solicitud de cierre" | N.A. (SLA pausado) |
| RESUELTO | Usuario/cliente | Comentario "Solicitud de cierre" | N.A. |
| CERRADO | Resolutor | Usuario acepta resolucion, o 3+ dias sin respuesta | se habilita "Tipo de resolución" (obligatorio para cerrar) |

Reglas transversales del flujo:
- Los cambios de estado se disparan por **tipos de comentario estructurados** (Asignado,
  Pre-Análisis, Confirmación de atención, Solicitud de información, Termina análisis,
  Solicitud de cierre, Descripción solución) — nunca por texto libre (Principio VI).
- Cada transicion genera notificaciones (APP obligatoria; Google Chat deseable; email al
  usuario en comentarios externos).
- En Fase 1 los estados se actualizan manualmente por Coordinador/Resolutor; el motor FSM
  automatizado con `python-transitions` llega en la Fase 6 del roadmap, pero el catalogo de
  estados y tipos de comentario DEBE ser este desde Fase 1.
- Solo se permiten transiciones explicitamente definidas en la maquina de estados.

## Roadmap de Fases (SDD V3)

| Fase SDD V3 | Alcance | Equivalencia interna |
|-------------|---------|----------------------|
| 1 | Tickets + comentarios con adjuntos + ciclo de vida manual + pantallas de maestros (clientes, proyectos, recursos/skills, roles, datos sensibles) + Panel de Asignacion basico | `001-fase0-maestros` (maestros, hecho) + `002-fase1-tickets` (siguiente) |
| 2 | Registro diario de tiempos por recurso | futura |
| 3 | Manejo de Tareas (misma tabla que tickets, campo "Tipo de registro" + "Registro relacionado") | futura |
| 4 | SLAs por prioridad/cliente/proyecto con estados que pausan el contador | futura |
| 5 | Asignacion por disponibilidad + calendarios por pais/recurso + excepciones RRHH | futura |
| 6 | Motor FSM automatizado + motor de comentarios con triggers | futura |
| 7 | Focus Room + agente IA asistente del resolutor (evaluar Triage Agent) | futura |
| 8 | Portal de clientes + integraciones + creacion automatica de tickets | futura |

### Modelo de datos - Jerarquia de 5 niveles

```
clients           (RLS root, Nivel 1)
  projects        (FK: client_id, Nivel 2)
    task_lists    (FK: project_id, Nivel 3)
      tasks       (FK: task_list_id, FSM + SLA + comentarios, Nivel 4)
        subtasks  (autorreferencial FK: parent_task_id, sin SLA propio, Nivel 5)
```

**Maestros ampliados (SDD V3)** — los maestros DEBEN soportar, ademas de los datos base:
- **Clientes**: facturacion anual (USD) y portafolio de software del cliente
  (tipo ERP/WMS/CRM/etc., marca y version).
- **Proyectos**: overview, valores de venta (servicios, licencias, suscripciones) y
  componentes vendidos — historial completo de proyectos por cliente.
- **Recursos**: identificacion, nacionalidad, fecha de nacimiento, estado civil, tipo de
  contrato, pais/calendario de trabajo, nivel de estudios, especialidad, seniority,
  certificaciones, equipo y jefe (FK autorreferencial). Area protegida de compensacion
  (salario base, salario total con beneficios, overhead, costo hora calculado) cifrada y
  visible solo para roles con el permiso `compensation`.

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
- Todo PR/revision DEBE verificar conformidad con los principios I-VII antes de aprobarse.
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

**Version**: 1.2.0 | **Ratified**: 2026-06-29 | **Last Amended**: 2026-07-10
