# Research: Script de Datos Semilla — Clientes Aris y Vaxthera

## Decisión 1: Patrón de script a reutilizar

- **Decision**: Nuevo módulo `backend/scripts/seed_clients_aris_vaxthera.py`, ejecutable con
  `docker exec sywork_backend python -m backend.scripts.seed_clients_aris_vaxthera`, siguiendo
  exactamente la estructura de `backend/scripts/seed_tickets.py`: `get_db()`/`close_db()` de
  `backend/infra/database.py`, repositorios de dominio importados directamente, función `main()`
  con `if __name__ == "__main__":`, y un print de resumen final.
- **Rationale**: Es el único precedente de seeding en el repo; reutilizarlo evita introducir un
  segundo patrón (por ejemplo, una migración de datos de Alembic) para un caso que ya tiene
  solución establecida. Cumple Principio VII (alcance mínimo, un solo archivo nuevo).
- **Alternatives considered**:
  - *Migración de Alembic con `bind.execute(INSERT ...)`* (patrón usado en `013_dynamic_record_type.py`
    y `009_roles_permissions_login.py` para catálogos): rechazada porque esos casos seedean
    catálogos/roles que son parte del **esquema base** de toda instalación; los datos de Aris/Vaxthera
    son datos de negocio específicos de dos clientes reales, no un catálogo del sistema, y deben poder
    ejecutarse/re-ejecutarse a demanda sin acoplarse al historial de migraciones (`alembic upgrade head`).
  - *Endpoint de API temporal*: rechazado — violaría el alcance (Principio VII) y no aporta valor
    reutilizable frente a un script directo.

## Decisión 2: Idempotencia + convergencia forzada (re-ejecución segura, FR-012)

- **Decision**: Para cada entidad, usar el patrón `repo.get_by_x(...) or repo.create(Entity.create(...))`
  ya usado en `seed_tickets.py`:
  - Cliente: `ClientRepository.get_by_name(name)`
  - Proyecto: `ProjectRepository.get_by_client_and_name(client_id, name)`
  - Usuario: `UserRepository.get_by_email(email)`
  - Contacto de cliente (Encargado): `ClientContactRepository.get_by_user_id(user_id)` antes de `.create(...)`
  - Membresía de proyecto: `ProjectMemberRepository.is_member(project_id, user_id)` antes de `.create(...)`
  - Lista de tareas: `TaskListRepository.get_by_project_and_name(project_id, name)`
  - Regla de SLA: `SlaRuleRepository.find_by_project_priority(project_id, priority)` (o `exists_active`)
    antes de `.create(...)`

  A diferencia de la primera versión de esta feature, cuando el registro **ya existe pero con un
  valor distinto** en un campo que esta spec fija (país/zona horaria del Cliente, rol del Usuario),
  el script ya no solo advierte y omite: actualiza ese campo al valor sembrado
  (`ClientRepository.update(...)`, `UserRepository.update_role(...)`) y lo reporta como
  "actualizado". Decisión revisada 2026-07-21 a pedido explícito: estos valores son fijos y deben
  converger sin importar el estado previo ni que el proceso implique reiniciar servicios — pero el
  `update(client)` siempre parte de la entidad existente (no de una nueva con campos en blanco) para
  no perder el resto de sus datos (contacto, VPN, facturación, notas), y el alcance se mantiene
  acotado a los 2 clientes y 3 emails explícitamente listados en esta spec.
- **Rationale**: Todos estos métodos de lookup/actualización ya existen en los repositorios actuales
  — no requiere añadir ningún método nuevo a la capa de infraestructura.
- **Alternatives considered**: `ON CONFLICT DO NOTHING` a nivel SQL (usado en la migración de roles):
  rechazada porque el script opera vía capa de dominio/repositorios, no con SQL crudo, y los
  repositorios ya ofrecen los métodos de búsqueda/actualización necesarios. Dejar el conflicto como
  advertencia manual (comportamiento original): rechazada tras la corrección — el pedido explícito
  fue que el seed force la convergencia, no que la señale para revisión.

## Decisión 3: Valores de la matriz de SLA (Aris / Soporte)

- **Decision**: Usar los valores sugeridos por quien solicitó la feature, convertidos a minutos para
  `SlaRule.create(project_id, priority, contact_minutes, execution_minutes)`:

  | Prioridad (`SlaRule.priority`) | Contacto | Ejecución |
  |---|---|---|
  | `critical` | 2 h → `120` min | 4 h → `240` min |
  | `high` | 4 h → `240` min | 8 h → `480` min |
  | `medium` | 8 h → `480` min | 24 h → `1440` min |
  | `low` | 24 h → `1440` min | 48 h → `2880` min |

- **Rationale**: `SlaRule` (spec 014) ya modela exactamente 4 prioridades (`critical/high/medium/low`)
  con dos tiempos en minutos cada una (`contact_minutes`, `execution_minutes`) — no existe un tercer
  campo de "diagnóstico" separado, así que los tiempos indicados en la solicitud mapean 1:1 a
  contacto/ejecución.
- **Alternatives considered**: N/A — spec.md ya documenta estos valores como Assumption (no quedó
  como `[NEEDS CLARIFICATION]`).

## Decisión 4: Alta de usuarios y contraseña inicial

- **Decision**: Crear los 3 usuarios (`Eliseon@aris.ming.com`, `paulaBlanco@aris.ming.com`,
  `pablo@vaxthera.com`) con `UserRepository.create(User(...))`, rol resuelto vía
  `RoleRepository.get_by_name(USUARIO_CLIENTE_ROLE_NAME)` (constante ya definida en
  `backend/domain/entities/user.py`), y contraseña inicial generada con
  `werkzeug.security.generate_password_hash(secrets.token_urlsafe(12))`, imprimiendo la contraseña
  en texto plano una sola vez por consola al finalizar (mismo criterio que el flujo de producción de
  spec 003 — nunca se persiste en texto plano ni se comitea).
- **Rationale**: No existe un servicio reutilizable único de "crear usuario + password" en el dominio;
  los dos precedentes (migración `009_roles_permissions_login.py` y el flujo de reseteo de spec 003)
  llaman `generate_password_hash` directamente antes de `UserRepository.create`/`.set_password`. Seguir
  el mismo criterio evita introducir un patrón nuevo.
- **Alternatives considered**: Dejar `password_hash=None` y forzar reseteo por email: rechazada porque
  el entorno de siembra (desarrollo/pruebas) normalmente no tiene un servidor de correo saliente
  configurado; imprimir la contraseña en consola es consistente con `docs/credenciales_dev.txt` ya
  documentado para otros usuarios semilla.

## Decisión 4a: `ClientContact` obligatorio — Encargado, no recurso/equipo (revisada 2026-07-21)

- **Decision**: Además del `User` y de sus filas en `project_members`, el script crea una fila en
  `client_contacts` (`ClientContactRepository.get_by_user_id(user.id) or .create(ClientContact(...))`)
  por cada uno de los 3 usuarios, replicando exactamente lo que hace `POST /api/client-contacts`
  (`backend/api/routes/client_contacts.py:206-220`): crea el `User`, luego el `ClientContact`
  (`user_id`, `client_id`), y solo después las membresías de proyecto.
- **Rationale**: La primera versión de este script solo creaba `project_members`, sin
  `client_contacts`. Se verificó en la base de datos real que, sin esa fila, los 3 usuarios no
  aparecían en absoluto en `GET /api/client-contacts` (la pantalla Maestros > Usuarios/clientes,
  `ClientContactsPage.tsx`) — `ClientContactRepository.list_paginated(project_id=...)` hace `JOIN`
  contra `client_contacts`, así que sin esa fila el usuario es invisible ahí aunque sí tenga
  `project_members`. Solo aparecían en el listado genérico de "Personal"/equipo del proyecto
  (`ProjectMemberRepository.list_by_project`), que es el mismo listado donde aparecen los recursos —
  exactamente el problema reportado ("son encargados de los proyectos, NO recursos o parte del
  equipo"). `client_contacts.user_id` es `UNIQUE`, así que la comprobación de idempotencia es
  `get_by_user_id`.
- **Alternatives considered**: Quitar la membresía de `project_members`: rechazada — esa fila sigue
  siendo necesaria (es la que da acceso operativo al Proyecto y la que usa
  `ClientContactRepository.list_paginated(project_id=...)` para filtrar); el problema no era que
  `project_members` sobrara, sino que faltaba `client_contacts`.

## Decisión 5: "Seguimiento (Completadas)" como nombre literal de lista

- **Decision**: Crear la lista con el nombre literal `"Seguimiento (Completadas)"` vía
  `TaskListRepository.create(TaskList(...))`, igual que cualquier otra lista.
- **Rationale**: `TaskList` (spec 009) solo tiene `id, project_id, name, position` — no existe un
  concepto de "lista completada" en el dominio actual; el paréntesis proviene del sistema origen
  (Teamwork) donde task lists completas se agrupan aparte, pero aquí es simplemente un nombre de texto.
  Confirmado en spec.md (sección Assumptions).
- **Alternatives considered**: Marcar la lista con algún flag "completada": rechazada porque
  requeriría un cambio de esquema en `TaskList`, fuera del alcance de este script (constitution
  Principio VII, "no modificar arquitectura de tablas existentes salvo FK directa").

## Decisión 6: Orden y `position` de las Listas de Tareas

- **Decision**: Asignar `position` incremental en el orden exacto listado en la spec, usando
  `TaskListRepository.next_position(project_id)` antes de cada `create(...)` (mismo método ya usado
  por la API para nuevas listas), de modo que la UI las muestre en el orden solicitado.
- **Rationale**: `next_position` ya existe y es el único punto de verdad para el orden secuencial;
  reutilizarlo evita calcular posiciones a mano.
