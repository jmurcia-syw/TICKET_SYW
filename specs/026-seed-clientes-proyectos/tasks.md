---

description: "Task list template for feature implementation"
---

# Tasks: Script de Datos Semilla — Clientes Aris y Vaxthera

**Input**: Design documents from `/specs/026-seed-clientes-proyectos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: No se solicitaron tests automatizados en la spec (constitution Principio VII: sin suite
masiva). La validación de esta feature es manual, vía `quickstart.md`.

**Organization**: Todo el código de esta feature vive en un único archivo nuevo,
`backend/scripts/seed_clients_aris_vaxthera.py` (mismo patrón que `backend/scripts/seed_tickets.py`).
Las tareas están agrupadas por user story (spec.md) para que cada bloque de funcionalidad sea
identificable y verificable por separado, aunque se implementen secuencialmente en el mismo archivo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos o sin dependencias)
- **[Story]**: A qué user story pertenece (US1, US2, US3)
- Rutas de archivo exactas en cada descripción

## Path Conventions

Proyecto Web app existente (`backend/` + `frontend/`). Esta feature solo toca `backend/scripts/`.

---

## Phase 1: Setup

**Purpose**: Crear el archivo del script con la estructura base, siguiendo el patrón ya existente.

- [X] T001 Crear `backend/scripts/seed_clients_aris_vaxthera.py` con docstring de uso
  (`docker exec sywork_backend python -m backend.scripts.seed_clients_aris_vaxthera`), imports de
  `get_db`/`close_db` (`backend/infra/database.py`) y de los repositorios
  (`ClientRepository`, `ProjectRepository`, `UserRepository`, `RoleRepository`,
  `ProjectMemberRepository`, `SlaRuleRepository`, `TaskListRepository`), y esqueleto de `main()` +
  `if __name__ == "__main__": main()` (sin lógica todavía), igual que `backend/scripts/seed_tickets.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura mínima compartida por las 3 user stories dentro del mismo archivo.

**⚠️ CRITICAL**: Ninguna user story puede implementarse hasta completar esta fase.

- [X] T002 En `backend/scripts/seed_clients_aris_vaxthera.py`, dentro de `main()`, resolver el rol
  "Usuario/cliente" con `RoleRepository(db).get_by_name(USUARIO_CLIENTE_ROLE_NAME)` (constante
  importada de `backend.domain.entities.user`) y abortar con mensaje claro (`assert`) si no existe —
  precondición bloqueante para poder crear los 3 usuarios de las user stories siguientes
- [X] T003 En `backend/scripts/seed_clients_aris_vaxthera.py`, agregar un contador de resumen (dict
  `{"creados": [...], "omitidos": [...]}` o equivalente) que cada tarea de siembra posterior
  actualizará, para poder imprimir al final qué se creó y qué ya existía (FR-014)

**Checkpoint**: Con el rol resuelto y el contador listo, puede empezar la implementación de User Story 1.

---

## Phase 3: User Story 1 - Poblar un entorno nuevo con los datos reales de Aris y Vaxthera (Priority: P1) 🎯 MVP

**Goal**: Un solo comando crea los 2 clientes, sus 4 proyectos, los 3 usuarios "Usuario/cliente", la
matriz de SLA de Aris/Soporte y las 13 Listas de Tareas, tal como se especificó.

**Independent Test**: Ejecutar el script contra una base de datos limpia y verificar en Maestros >
Clientes/Proyectos y en Listas de Tareas que todo aparece exactamente como se pidió (Acceptance
Scenarios 1–6 de spec.md).

### Implementation for User Story 1

- [X] T004 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, sembrar cliente Aris
  (`name="Aris"`, `country="Colombia"`, `timezone="America/Bogota"`) vía
  `ClientRepository.get_by_name("Aris") or .create(Client.create(...))`
- [X] T005 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, sembrar cliente Vaxthera
  (`country="Ecuador"`, `timezone="America/Guayaquil"`) con el mismo patrón que T004
- [X] T006 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, sembrar los proyectos de Aris
  ("Evolutivo", "Preventa", "Soporte", `start_date=date.today()`) vía
  `ProjectRepository.get_by_client_and_name(client_id, name) or .create(Project.create(...))`
  (depende de T004)
- [X] T007 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, sembrar el proyecto "Soporte" de
  Vaxthera con el mismo patrón que T006 (depende de T005)
- [X] T008 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, sembrar usuarios
  `Eliseon@aris.ming.com` y `paulaBlanco@aris.ming.com` (rol resuelto en T002, `username` derivado
  del prefijo del email, `password_hash=generate_password_hash(secrets.token_urlsafe(12))`) vía
  `UserRepository.get_by_email(email) or .create(User(...))` (depende de T002)
- [X] T009 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, sembrar usuario
  `pablo@vaxthera.com` con el mismo patrón que T008 (depende de T002)
- [X] T010 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, asignar
  `Eliseon@aris.ming.com` y `paulaBlanco@aris.ming.com` a los 3 proyectos de Aris vía
  `ProjectMemberRepository.is_member(project_id, user_id)` antes de `.create(ProjectMember(...))`
  (depende de T006, T008)
- [X] T011 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, asignar `pablo@vaxthera.com` al
  proyecto Soporte de Vaxthera con el mismo patrón que T010 (depende de T007, T009)
- [X] T012 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, sembrar la matriz de SLA de 4
  niveles del proyecto Soporte de Aris (`critical` 120/240, `high` 240/480, `medium` 480/1440, `low`
  1440/2880 minutos, ver data-model.md) vía
  `SlaRuleRepository.find_by_project_priority(project_id, priority) or .create(...)` (depende de T006)
- [X] T013 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, sembrar las 8 Listas de Tareas
  del proyecto Soporte de Aris en el orden de data-model.md (Servicios Correctivos, Servicios
  Adaptativos, Servicios Evolutivos, Servicios Administrativos, Seguimiento, Coordinación, Servicios
  preventivos IT, Redwood) vía `TaskListRepository.get_by_project_and_name(...)` +
  `.next_position(project_id)` + `.create(TaskList(...))` (depende de T006)
- [X] T014 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, sembrar las 5 Listas de Tareas
  del proyecto Soporte de Vaxthera en el orden de data-model.md (Servicios Evolutivos, Servicios
  Administrativos, Servicios Correctivos, Servicios Adaptativos, Seguimiento (Completadas)) con el
  mismo patrón que T013 (depende de T007)
- [X] T015 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, al final de `main()`, imprimir el
  resumen de creados/omitidos (T003) y las contraseñas iniciales en texto plano una sola vez, y
  cerrar con `close_db()` (depende de T004–T014)

**Checkpoint**: User Story 1 completa — el script puede ejecutarse de punta a punta contra un
entorno limpio y producir todos los datos especificados.

---

## Phase 4: User Story 2 - Re-ejecutar el script sin duplicar datos (Priority: P2)

**Goal**: El mismo script puede volver a ejecutarse las veces que haga falta sin crear duplicados ni
pisar datos en conflicto.

**Independent Test**: Ejecutar el script dos veces seguidas y confirmar mismo conteo de registros
antes/después de la segunda ejecución (Acceptance Scenarios 1–2 de spec.md, User Story 2).

### Implementation for User Story 2

- [X] T016 [US2] En `backend/scripts/seed_clients_aris_vaxthera.py`, en T004/T005, si el cliente ya
  existe con `country`/`timezone` distinto al esperado, **forzar la convergencia**: actualizar esos
  campos al valor sembrado vía `ClientRepository.update(existing)` (partiendo de la entidad existente
  para no perder sus otros campos) y reportarlo como "actualizado" (revisado 2026-07-21: comportamiento
  original era solo advertir/omitir; ahora el seed es autoritativo)
- [X] T017 [US2] En `backend/scripts/seed_clients_aris_vaxthera.py`, en T008/T009, si el email ya
  existe pero con un rol distinto a "Usuario/cliente", **forzar la convergencia**: reasignar el rol vía
  `UserRepository.update_role(user_id, role_id)` y reportarlo como "actualizado" (revisado 2026-07-21,
  mismo criterio que T016)
- [X] T018 [US2] Ejecutar el script dos veces seguidas contra el entorno Docker
  (`docker exec sywork_backend python -m backend.scripts.seed_clients_aris_vaxthera`) y confirmar que
  la segunda ejecución reporta todo como "ya existía, omitido" sin crear filas nuevas — validación
  manual, quickstart.md paso 2 (depende de T004–T017)

**Checkpoint**: El script es seguro de re-ejecutar en cualquier momento del ciclo de vida del
entorno de desarrollo/pruebas.

---

## Phase 5: User Story 3 - Validar el motor de SLA con datos reales de estos clientes (Priority: P3)

**Goal**: Confirmar que el motor de SLA se comporta según lo esperado usando los proyectos recién
sembrados (con y sin SLA).

**Independent Test**: Crear un Ticket en cada proyecto Soporte y comparar el comportamiento del
indicador de SLA (Acceptance Scenarios 1–2 de spec.md, User Story 3).

### Implementation for User Story 3

- [ ] T019 [P] [US3] Crear un Ticket de prueba en el proyecto Soporte de Aris y confirmar en su
  detalle que se muestran los indicadores/countdown de SLA según la matriz de 4 niveles —
  validación manual, quickstart.md paso 4.1 (depende de T012)
- [ ] T020 [P] [US3] Crear un Ticket de prueba en el proyecto Soporte de Vaxthera y confirmar que su
  detalle NO muestra ningún indicador de SLA — validación manual, quickstart.md paso 4.2; eliminar
  ambos Tickets de prueba al terminar (FR-013: el script no debe dejar datos transaccionales)
  (depende de T007)

**No ejecutadas en esta sesión**: la solicitud original limitó explícitamente el alcance a "generar
el archivo del script y confirmar su ejecución", sin crear registros adicionales más allá de los
aquí listados. T019/T020 (crear Tickets de prueba) quedan como verificación manual opcional para
quien despliegue el script, documentada en quickstart.md paso 4.

**Checkpoint**: Los 4 proyectos sembrados quedan validados end-to-end frente al motor de SLA real
(pendiente de verificación manual opcional, ver nota arriba).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificación final de alcance y de la guía de validación completa.

- [X] T021 Ejecutar `quickstart.md` pasos 1–3 completos y confirmar visualmente en Maestros >
  Clientes, Maestros > Proyectos, la pantalla de Listas de Tareas y Maestros > Usuarios que todo
  coincide con data-model.md (depende de T015) — pasos 1 y 2 ejecutados vía Docker (33 creados, luego
  0 creados/33 omitidos); paso 3 verificado por consulta SQL directa a `sywork_db` (clientes,
  proyectos, sla_rules, task_lists, users y project_members) en vez de navegación UI manual — mismos
  datos que expone la UI, sin cambios de frontend involucrados en esta feature
- [X] T022 Confirmar con `git status`/`git diff` que el único archivo nuevo o modificado por esta
  sesión es `backend/scripts/seed_clients_aris_vaxthera.py` (alcance de sesión, constitution
  Principio VII) (depende de T001–T020) — confirmado: único archivo de código nuevo es
  `backend/scripts/seed_clients_aris_vaxthera.py`; el resto de cambios son artefactos de SpecKit
  (`specs/026-.../`, `CLAUDE.md`, `.specify/feature.json`)

---

## Phase 7: Corrección post-implementación — Encargados, no recursos/equipo (2026-07-21)

**Motivo**: verificación en base de datos real mostró que los 3 usuarios "Usuario/cliente" tenían
`project_members` pero ninguna fila en `client_contacts` — por eso no aparecían en Maestros >
Usuarios/clientes (Encargados) y solo eran visibles en el listado genérico de Personal/Equipo del
proyecto (el mismo donde aparecen los recursos), tal como reportó quien usa la feature.

- [X] T023 [US1] En `backend/scripts/seed_clients_aris_vaxthera.py`, importar `ClientContact`
  (`backend/domain/entities/client_contact.py`) y `ClientContactRepository`
  (`backend/infra/repositories/client_contact_repo.py`); para cada uno de los 3 usuarios, crear su
  `client_contacts` (`user_id`, `client_id`) vía
  `contacts.get_by_user_id(user.id) or contacts.create(ClientContact(...))`, replicando el mismo orden
  que `POST /api/client-contacts` (usuario → client_contact → project_members)
- [X] T024 Re-ejecutar el script contra el entorno Docker y confirmar por SQL directo que
  `client_contacts` tiene exactamente 3 filas (una por usuario, con el `client_id` correcto) y que una
  tercera ejecución consecutiva no crea ni actualiza nada (0 creados / 0 actualizados / 36 sin cambios)
- [X] T025 Simular un valor divergente (`UPDATE clients SET timezone=... WHERE name='Aris'`) y
  confirmar que la siguiente ejecución del script lo reporta como "actualizado" y lo corrige al valor
  sembrado — valida T016/T017 revisadas

**Checkpoint**: los 3 usuarios ahora tienen tanto `client_contacts` (Encargado del Cliente) como
`project_members` (acceso operativo al Proyecto); el script sigue siendo idempotente y ahora fuerza
la convergencia de los campos fijos por esta spec.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede empezar de inmediato
- **Foundational (Phase 2)**: depende de Setup — bloquea las 3 user stories
- **User Story 1 (Phase 3)**: depende de Foundational; es la base de datos de la que dependen US2 y US3
- **User Story 2 (Phase 4)**: depende de que existan T004–T015 (edita el mismo código de US1 para
  agregar manejo de conflictos) — no es independiente a nivel de archivo, pero sí a nivel de
  comportamiento verificable
- **User Story 3 (Phase 5)**: depende de que existan los proyectos Soporte de Aris (T006/T012) y
  Vaxthera (T007) — no requiere código nuevo, solo verificación manual
- **Polish (Phase 6)**: depende de que todas las user stories deseadas estén completas

### Parallel Opportunities

- T001 no tiene dependencias previas dentro de esta feature
- Dentro de Phase 3, T004 y T005 son independientes entre sí (clientes distintos) pero **no** se
  marcan `[P]` porque ambas editan el mismo archivo secuencialmente; igual para el resto de T004–T015
- T019 y T020 (Phase 5) sí se marcan `[P]`: son verificaciones manuales en proyectos distintos, sin
  edición de archivos ni dependencia entre sí

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup (T001)
2. Completar Phase 2: Foundational (T002–T003)
3. Completar Phase 3: User Story 1 (T004–T015)
4. **STOP y VALIDAR**: ejecutar el script una vez contra el entorno Docker y revisar la UI
   (quickstart.md pasos 1 y 3) — esto ya entrega el 100% del valor pedido en la solicitud original

### Incremental Delivery

1. Setup + Foundational + US1 → script funcional de punta a punta (MVP)
2. Agregar US2 (T016–T018) → confirmar re-ejecución segura
3. Agregar US3 (T019–T020) → confirmar comportamiento del motor de SLA con estos datos reales
4. Phase 6 (T021–T022) → cierre y verificación de alcance

---

## Notes

- Todas las tareas de código (T001–T017) tocan un único archivo nuevo:
  `backend/scripts/seed_clients_aris_vaxthera.py` — por eso casi ninguna se marca `[P]`.
- No ejecutar la suite de pruebas unitarias completa en ningún punto de esta feature (constitution
  Principio VII); la única verificación es manual, vía quickstart.md.
- Hacer commit al terminar Phase 3 (MVP) y, si se implementan, al terminar Phase 4 y Phase 5 por
  separado.
