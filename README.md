# SYWork Tickets

Sistema de gestión de tickets de soporte técnico interno. Permite registrar, asignar y hacer seguimiento de incidencias con autenticación segura y una interfaz moderna.

---

## Tabla de contenidos

- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Requisitos previos](#requisitos-previos)
- [Configuración inicial](#configuración-inicial)
- [Comandos Docker](#comandos-docker)
- [URLs del proyecto](#urls-del-proyecto)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Skills instaladas](#skills-instaladas)

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENTE (Browser)                   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP :5173
┌──────────────────────▼──────────────────────────────────┐
│               FRONTEND  (sywork_frontend)                │
│          React 19 · TypeScript · Ant Design · Vite       │
│                      Puerto 5173                         │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API :5000
┌──────────────────────▼──────────────────────────────────┐
│               BACKEND   (sywork_backend)                 │
│         Flask · Flask-RESTX · JWT · Google OAuth         │
│                      Puerto 5000                         │
│                  Swagger en /swagger                     │
└──────────────────────┬──────────────────────────────────┘
                       │ PostgreSQL :5432
┌──────────────────────▼──────────────────────────────────┐
│               BASE DE DATOS  (sywork_db)                 │
│                  PostgreSQL 16 Alpine                    │
│                      Puerto 5432                         │
└─────────────────────────────────────────────────────────┘
```

Todos los servicios corren en contenedores Docker orquestados con `docker-compose`. El backend espera a que la base de datos esté **healthy** antes de arrancar.

---

## Stack tecnológico

### Frontend
| Tecnología | Versión | Propósito |
|---|---|---|
| React | 19.0 | UI framework |
| TypeScript | 5.6 | Tipado estático |
| Ant Design | 5.x | Componentes UI |
| Zustand | 5.x | Estado global |
| Vite | 6.x | Build tool / dev server |
| Axios | 1.7 | HTTP client |
| date-fns | 4.x | Manejo de fechas |
| @hello-pangea/dnd | 17.x | Drag & drop |

### Backend
| Tecnología | Versión | Propósito |
|---|---|---|
| Python | 3.12 | Runtime |
| Flask | 3.1 | Web framework |
| Flask-RESTX | 1.3 | REST API + Swagger |
| Flask-CORS | 5.0 | Cross-Origin |
| PyJWT | 2.10 | Autenticación JWT |
| Google Auth | 2.38 | OAuth con Google |
| psycopg2 | 2.9 | Driver PostgreSQL |
| transitions | 0.9 | Máquina de estados (tickets) |

### Infraestructura
| Tecnología | Propósito |
|---|---|
| Docker + Docker Compose | Orquestación de contenedores |
| PostgreSQL 16 Alpine | Base de datos relacional |

---

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- Archivo `.env` configurado en la raíz del proyecto (ver `.env.example` si existe)

### Variables de entorno requeridas (`.env`)

```env
POSTGRES_DB=sywork
POSTGRES_USER=tu_usuario
POSTGRES_PASSWORD=tu_password
JWT_SECRET=tu_jwt_secret_muy_seguro
GOOGLE_CLIENT_ID=tu_google_client_id
GOOGLE_CLIENT_SECRET=tu_google_client_secret
FLASK_ENV=development
```

> El archivo `.env` nunca se sube al repositorio (está en `.gitignore`). Crea uno local antes de ejecutar el proyecto.

---

## Comandos Docker

### Levantar el proyecto completo

```bash
docker compose up --build
```

> Reconstruye las imágenes y levanta todos los servicios. Usar la primera vez o cuando cambien dependencias.

### Levantar sin reconstruir (más rápido)

```bash
docker compose up
```

### Levantar en segundo plano (detached)

```bash
docker compose up -d
```

### Ver logs en tiempo real

```bash
# Todos los servicios
docker compose logs -f

# Solo el backend
docker compose logs -f backend

# Solo el frontend
docker compose logs -f frontend

# Solo la base de datos
docker compose logs -f postgres
```

### Detener los contenedores

```bash
docker compose down
```

### Detener y eliminar volúmenes (borra la base de datos)

```bash
docker compose down -v
```

> Usar solo si quieres reiniciar la base de datos desde cero.

### Ver estado de los contenedores

```bash
docker compose ps
```

### Reconstruir solo un servicio

```bash
docker compose up --build backend
docker compose up --build frontend
```

### Entrar a un contenedor

```bash
# Shell del backend
docker exec -it sywork_backend bash

# Shell de la base de datos
docker exec -it sywork_db psql -U tu_usuario -d sywork
```

---

## URLs del proyecto

| Servicio | URL | Descripción |
|---|---|---|
| Frontend | http://localhost:5173 | Interfaz de usuario |
| Backend API | http://localhost:5000 | REST API |
| Swagger UI | http://localhost:5000/swagger | Documentación interactiva de la API |
| PostgreSQL | localhost:5432 | Base de datos (acceso directo) |

---

## Estructura del proyecto

```
TICKET_SYW/
├── backend/
│   ├── app.py              # Punto de entrada Flask
│   ├── requirements.txt    # Dependencias Python
│   └── Dockerfile          # Imagen del backend
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Componente raíz
│   │   └── main.tsx        # Entry point React
│   └── package.json        # Dependencias Node
├── postgres/
│   └── init.sql            # Script de inicialización de la DB
├── docker-compose.yml      # Orquestación de servicios
├── .env                    # Variables de entorno (NO commitear)
├── .gitignore
└── README.md
```

---

## Skills instaladas

Este proyecto usa **Claude Code** con el sistema de skills **GSD (Get Stuff Done)** y **Superpowers** instaladas globalmente.

### Skills Superpowers (flujo de trabajo con Claude)

| Skill | Comando | Descripción |
|---|---|---|
| `using-superpowers` | automático | Punto de entrada — carga el sistema de skills al inicio de cada conversación |
| `brainstorming` | `/brainstorming` | Ideación estructurada antes de planificar |
| `writing-plans` | `/writing-plans` | Guía para crear planes de implementación claros |
| `executing-plans` | `/executing-plans` | Ejecución de planes con commits atómicos y manejo de desvíos |
| `systematic-debugging` | `/systematic-debugging` | Debugging científico con método reproducible |
| `test-driven-development` | `/tdd` | Flujo TDD: escribir tests antes que código |
| `verification-before-completion` | automático | Verifica que los cambios funcionen antes de marcar como hecho |
| `subagent-driven-development` | automático | Orquesta subagentes en paralelo para tareas complejas |
| `dispatching-parallel-agents` | automático | Lanza múltiples agentes en paralelo |
| `requesting-code-review` | `/code-review` | Solicita revisión de código del diff actual |
| `receiving-code-review` | automático | Procesa y aplica resultados de revisiones de código |
| `finishing-a-development-branch` | automático | Checklist de cierre de rama antes de hacer PR |
| `using-git-worktrees` | automático | Flujo de trabajo con git worktrees para trabajo en paralelo |
| `writing-skills` | `/writing-skills` | Crea nuevas skills personalizadas |

### Skills GSD (gestión de proyectos con IA)

#### Proyecto y planificación
| Skill | Comando | Descripción |
|---|---|---|
| `gsd-new-project` | `/gsd-new-project` | Inicializa un proyecto nuevo con contexto profundo y PROJECT.md |
| `gsd-new-milestone` | `/gsd-new-milestone` | Crea un nuevo hito con fases y roadmap |
| `gsd-phase` | `/gsd-phase` | Gestión completa de una fase (discuss → plan → execute) |
| `gsd-plan-phase` | `/gsd-plan-phase` | Genera el plan de implementación de una fase |
| `gsd-discuss-phase` | `/gsd-discuss-phase` | Recolecta contexto de una fase antes de planificar |
| `gsd-execute-phase` | `/gsd-execute-phase` | Ejecuta todos los planes de una fase |
| `gsd-spec-phase` | `/gsd-spec-phase` | Genera especificación técnica de una fase |
| `gsd-mvp-phase` | `/gsd-mvp-phase` | Ejecuta una fase en modo MVP (mínimo viable) |
| `gsd-ultraplan-phase` | `/gsd-ultraplan-phase` | Planificación ultra-detallada con análisis profundo |
| `gsd-autonomous` | `/gsd-autonomous` | Ejecuta todas las fases restantes de forma autónoma |

#### Calidad y revisión
| Skill | Comando | Descripción |
|---|---|---|
| `gsd-code-review` | `/gsd-code-review` | Revisa el código cambiado en una fase |
| `gsd-ui-review` | `/gsd-ui-review` | Auditoría visual de 6 pilares para frontend |
| `gsd-verify-work` | `/gsd-verify-work` | Verifica que una fase cumple su objetivo |
| `gsd-validate-phase` | `/gsd-validate-phase` | Valida que la fase está lista para ship |
| `gsd-secure-phase` | `/gsd-secure-phase` | Auditoría de seguridad de la fase implementada |
| `gsd-add-tests` | `/gsd-add-tests` | Genera tests basados en criterios UAT de la fase |
| `gsd-audit-fix` | `/gsd-audit-fix` | Pipeline autónomo: encuentra issues → clasifica → corrige → commitea |
| `gsd-audit-uat` | `/gsd-audit-uat` | Auditoría cruzada de todos los ítems UAT pendientes |

#### Debug y análisis
| Skill | Comando | Descripción |
|---|---|---|
| `gsd-debug` | `/gsd-debug` | Debugging sistemático con estado persistente |
| `gsd-forensics` | `/gsd-forensics` | Post-mortem para flujos GSD fallidos |
| `gsd-map-codebase` | `/gsd-map-codebase` | Análisis profundo del codebase |
| `gsd-explore` | `/gsd-explore` | Ideación socrática antes de comprometerse a un plan |
| `gsd-spike` | `/gsd-spike` | Investigación técnica rápida de una incógnita |

#### Flujo de trabajo diario
| Skill | Comando | Descripción |
|---|---|---|
| `gsd-progress` | `/gsd-progress` | Resumen del estado actual del proyecto |
| `gsd-update` | `/gsd-update` | Actualiza el estado de las fases |
| `gsd-health` | `/gsd-health` | Diagnóstica la salud del directorio `.planning/` |
| `gsd-resume-work` | `/gsd-resume-work` | Retoma el trabajo donde lo dejaste |
| `gsd-pause-work` | `/gsd-pause-work` | Guarda el estado para continuar después |
| `gsd-capture` | `/gsd-capture` | Captura ideas, tareas o notas rápidas |
| `gsd-fast` | `/gsd-fast` | Ejecuta una tarea trivial sin overhead de planificación |
| `gsd-quick` | `/gsd-quick` | Ejecución rápida de cambios pequeños |
| `gsd-manager` | `/gsd-manager` | Centro de comando interactivo para múltiples fases |
| `gsd-workspace` | `/gsd-workspace` | Gestión del espacio de trabajo GSD |

#### Ship y cierre
| Skill | Comando | Descripción |
|---|---|---|
| `gsd-ship` | `/gsd-ship` | Prepara y ejecuta el ship de la fase actual |
| `gsd-pr-branch` | `/gsd-pr-branch` | Crea rama y PR con formato correcto |
| `gsd-complete-milestone` | `/gsd-complete-milestone` | Archiva el hito completado y prepara el siguiente |
| `gsd-cleanup` | `/gsd-cleanup` | Archiva directorios de fases completadas |
| `gsd-undo` | `/gsd-undo` | Revierte la última acción GSD |
| `gsd-extract-learnings` | `/gsd-extract-learnings` | Extrae decisiones y lecciones de las fases completadas |
| `gsd-milestone-summary` | `/gsd-milestone-summary` | Resumen del hito completado |
| `gsd-audit-milestone` | `/gsd-audit-milestone` | Audita la completitud de un hito antes de archivarlo |

#### AI y documentación
| Skill | Comando | Descripción |
|---|---|---|
| `gsd-ai-integration-phase` | `/gsd-ai-integration-phase` | Genera AI-SPEC.md para fases con IA |
| `gsd-eval-review` | `/gsd-eval-review` | Audita la cobertura de evaluación de una fase IA |
| `gsd-docs-update` | `/gsd-docs-update` | Genera o actualiza documentación del proyecto |
| `gsd-ingest-docs` | `/gsd-ingest-docs` | Importa ADRs, PRDs y specs existentes al proyecto |
| `gsd-import` | `/gsd-import` | Importa planes externos con detección de conflictos |
| `gsd-review-backlog` | `/gsd-review-backlog` | Revisa el backlog de tareas pendientes |
| `gsd-inbox` | `/gsd-inbox` | Triages issues y PRs de GitHub |

### Skills de utilidad (Claude Code)

| Skill | Comando | Descripción |
|---|---|---|
| `code-review` | `/code-review` | Revisión del diff actual con distintos niveles de profundidad |
| `verify` | `/verify` | Verifica que un cambio funciona ejecutando la app y observando comportamiento |
| `run` | `/run` | Arranca la app y observa si el cambio funciona |
| `simplify` | `/simplify` | Refactoriza el código cambiado buscando simplificaciones y eficiencia |
| `update-config` | `/update-config` | Configura hooks, permisos y variables de entorno en `settings.json` |
| `keybindings-help` | `/keybindings-help` | Personaliza los atajos de teclado de Claude Code |
| `fewer-permission-prompts` | `/fewer-permission-prompts` | Escanea transcripts y agrega permisos para reducir prompts repetitivos |
| `loop` | `/loop` | Ejecuta un comando en intervalos recurrentes |
| `schedule` | `/schedule` | Programa agentes cloud en cron schedule |
| `claude-api` | `/claude-api` | Referencia de la API de Claude / SDK de Anthropic |
| `security-review` | `/security-review` | Auditoría de seguridad del código |
| `init` | `/init` | Inicialización de proyecto con Claude Code |
| `review` | `/review` | Revisión general del proyecto |

---

> Proyecto en desarrollo activo — v0.1.0
