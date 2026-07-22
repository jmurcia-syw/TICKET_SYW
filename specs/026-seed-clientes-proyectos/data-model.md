# Data Model: Script de Datos Semilla — Clientes Aris y Vaxthera

Ninguna entidad, tabla o columna nueva. Este documento mapea exactamente qué filas se insertan en
las tablas ya existentes, usando las entidades y repositorios de dominio/infraestructura actuales.
No hay migración de Alembic asociada a esta feature.

## Entidades reutilizadas (sin cambios de esquema)

| Entidad (dominio) | Archivo | Repositorio | Campos relevantes para esta siembra |
|---|---|---|---|
| `Client` | `backend/domain/entities/client.py` | `ClientRepository` (`client_repo.py`) | `name`, `country`, `timezone` |
| `Project` | `backend/domain/entities/project.py` | `ProjectRepository` (`project_repo.py`) | `client_id`, `name`, `start_date` |
| `User` | `backend/domain/entities/user.py` | `UserRepository` (`user_repo.py`) | `email`, `username`, `role_id`, `password_hash` |
| `Role` (lookup) | `backend/domain/entities/role.py` | `RoleRepository` (`role_repo.py`) | `get_by_name("Usuario/cliente")` — usar constante `USUARIO_CLIENTE_ROLE_NAME` |
| `ClientContact` | `backend/domain/entities/client_contact.py` | `ClientContactRepository` (`client_contact_repo.py`) | `user_id` (UNIQUE), `client_id` — **obligatoria**: es lo que marca a un `User` con rol Usuario/cliente como Encargado de un Cliente (spec 010/015); sin esta fila el usuario no aparece en Maestros > Usuarios/clientes aunque tenga `project_members` |
| `ProjectMember` | `backend/domain/entities/project_member.py` | `ProjectMemberRepository` (`project_member_repo.py`) | `project_id`, `user_id` — vínculo operativo Encargado↔Proyecto (spec 010/015), no confundir con pertenencia al equipo/recursos del proyecto |
| `SlaRule` | `backend/domain/entities/sla_rule.py` | `SlaRuleRepository` (`sla_rule_repo.py`) | `project_id`, `priority`, `contact_minutes`, `execution_minutes` |
| `TaskList` | `backend/domain/entities/task_list.py` | `TaskListRepository` (`task_list_repo.py`) | `project_id`, `name`, `position` |

## Filas a sembrar

### Clientes

| name | country | timezone |
|---|---|---|
| Aris | Colombia | `America/Bogota` |
| Vaxthera | Ecuador | `America/Guayaquil` |

### Proyectos (`client_id` = FK al cliente anterior)

| Cliente | Proyecto | SLA |
|---|---|---|
| Aris | Evolutivo | sin filas en `sla_rules` |
| Aris | Preventa | sin filas en `sla_rules` |
| Aris | Soporte | 4 filas en `sla_rules` (ver abajo) |
| Vaxthera | Soporte | sin filas en `sla_rules` (explícito, FR-009) |

`start_date` (campo obligatorio de `Project`, sin equivalente en la solicitud original): usar la
fecha de ejecución del script (`date.today()`) como valor por defecto razonable — no es un dato de
negocio crítico para esta siembra y no fue provisto por quien la solicitó.

### Usuarios ("Usuario/cliente" = Encargados de sus proyectos, no recursos/equipo)

| email | Cliente (`ClientContact`) | Proyectos con `ProjectMember` |
|---|---|---|
| `Eliseon@aris.ming.com` | Aris | Evolutivo, Preventa, Soporte |
| `paulaBlanco@aris.ming.com` | Aris | Evolutivo, Preventa, Soporte |
| `pablo@vaxthera.com` | Vaxthera | Soporte |

`username`: derivado del prefijo local del email (parte antes de `@`), único campo requerido por
`User` sin equivalente explícito en la solicitud.

Cada usuario se siembra con **dos** vínculos, replicando exactamente el flujo de alta de
`POST /api/client-contacts` (`backend/api/routes/client_contacts.py`):
1. Una fila en `client_contacts` (`user_id`, `client_id`) — es lo que lo identifica como Encargado
   del Cliente en Maestros > Usuarios/clientes.
2. Una fila en `project_members` por cada proyecto de la tabla de arriba — es lo que le da acceso
   operativo a esos proyectos.

Sin (1), el usuario solo tendría (2) y aparecería únicamente en el listado genérico de "Personal"
de cada proyecto (`ProjectMemberRepository.list_by_project`, usado también para recursos/equipo),
sin distinguirse como Encargado — de ahí que ambas filas sean obligatorias, no solo la membresía.

### Matriz de SLA — Aris / Soporte (`sla_rules`, una fila por prioridad)

| priority | contact_minutes | execution_minutes |
|---|---|---|
| critical | 120 | 240 |
| high | 240 | 480 |
| medium | 480 | 1440 |
| low | 1440 | 2880 |

### Listas de Tareas — Aris / Soporte (`position` 0..7, en este orden)

1. Servicios Correctivos
2. Servicios Adaptativos
3. Servicios Evolutivos
4. Servicios Administrativos
5. Seguimiento
6. Coordinación
7. Servicios preventivos IT
8. Redwood

### Listas de Tareas — Vaxthera / Soporte (`position` 0..4, en este orden)

1. Servicios Evolutivos
2. Servicios Administrativos
3. Servicios Correctivos
4. Servicios Adaptativos
5. Seguimiento (Completadas)

## Reglas de validación (heredadas, no nuevas)

- Nombre de Lista de Tareas único por proyecto — ya impuesto por `TaskListRepository.get_by_project_and_name`
  (usado para el chequeo de idempotencia, doble propósito).
- Un email de usuario es único en todo el sistema (`users.email` ya es `UNIQUE`) — si alguno de los
  3 emails ya existe, el script lo omite y lo reporta (edge case de spec.md), no lo reasigna.
- `SlaRule` no tiene fallback: cada `(project_id, priority)` es independiente (ya documentado en
  spec 014) — de ahí que "sin SLA" simplemente signifique cero filas para ese `project_id`.
