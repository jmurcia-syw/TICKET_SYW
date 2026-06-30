# Tasks: Fase 0 — Maestros

**Input**: Design documents from `specs/001-fase0-maestros/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tareas agrupadas por User Story para implementacion y validacion independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias incompletas)
- **[Story]**: User Story a la que pertenece la tarea ([US1]..[US4])
- Cada tarea incluye la ruta de archivo exacta

---

## Phase 1: Setup (Infraestructura compartida)

**Purpose**: Inicializacion del proyecto y estructura base de directorios

- [ ] T001 Crear estructura de directorios backend segun plan.md: `backend/domain/entities/`, `backend/domain/services/`, `backend/infra/models/`, `backend/infra/repositories/`, `backend/infra/migrations/versions/`, `backend/api/middleware/`, `backend/api/routes/`, `backend/tests/domain/`, `backend/tests/infra/`, `backend/tests/api/`
- [ ] T002 Crear estructura de directorios frontend segun plan.md: `frontend/src/components/clients/`, `frontend/src/components/projects/`, `frontend/src/components/resources/`, `frontend/src/components/users/`, `frontend/src/services/`, `frontend/src/store/`, `frontend/src/types/`, `frontend/src/pages/`
- [ ] T003 [P] Habilitar extension pgcrypto en PostgreSQL y confirmar disponibilidad en `backend/infra/migrations/versions/000_enable_pgcrypto.py`
- [ ] T004 [P] Configurar Alembic con `env.py` apuntando a la URL de base de datos desde variable de entorno en `backend/infra/migrations/env.py`
- [ ] T005 [P] Definir tipos TypeScript compartidos base: `frontend/src/types/api.ts` con `PaginatedResponse<T>`, `ApiError`, y enums de `Role` y `ActiveStatus`

**Checkpoint**: Estructura de directorios lista. Alembic configurado. pgcrypto habilitado.

---

## Phase 2: Foundational (Prerequisitos bloqueantes)

**Purpose**: Infraestructura core que DEBE estar completa antes de cualquier User Story

**CRITICO**: Ningun trabajo de User Story puede comenzar hasta completar esta fase

- [ ] T006 Crear migracion de tabla `users` con roles y check de email @sywork.net en `backend/infra/migrations/versions/001_create_users.py`
- [ ] T007 Implementar entidad `User` con enum `Role` en `backend/domain/entities/user.py`
- [ ] T008 Implementar modelo SQLAlchemy `UserModel` mapeando tabla users en `backend/infra/models/user_model.py`
- [ ] T009 Implementar `UserRepository` con metodos `get_by_id`, `get_by_email`, `update_role`, `set_active` en `backend/infra/repositories/user_repo.py`
- [ ] T010 Implementar middleware `auth.py`: decodifica JWT Flask-JWT-Extended y verifica `users.active` en cada request, devuelve 401 si inactivo en `backend/api/middleware/auth.py`
- [ ] T011 Implementar decorador `@require_role(*roles)` para RBAC por endpoint en `backend/api/middleware/rbac.py`
- [ ] T012 Implementar callback Google OAuth2: validar dominio @sywork.net, rechazar sin crear usuario si dominio incorrecto, emitir JWT en `backend/api/routes/auth.py`
- [ ] T013 [P] Crear store de autenticacion Zustand con `user`, `role`, `token` y accion `logout` en `frontend/src/store/authStore.ts`
- [ ] T014 [P] Crear componente `ProtectedRoute` que lee rol del authStore y redirige si sin permiso en `frontend/src/components/common/ProtectedRoute.tsx`
- [ ] T015 [P] Configurar cliente Axios con interceptor JWT: agrega header Authorization y maneja 401→logout en `frontend/src/services/apiClient.ts`
- [ ] T016 [P] Configurar React Router con rutas protegidas por rol usando `ProtectedRoute` en `frontend/src/App.tsx`

**Checkpoint**: Auth completo. JWT + OAuth2 @sywork.net operativo. RBAC middleware activo. Frontend conectado con interceptor.

---

## Phase 3: User Story 1 — Gestión de Clientes (Priority: P1) MVP

**Goal**: Admin y Coordinador pueden crear, ver, editar y desactivar clientes. Datos sensibles
(VPN IPs/credenciales) almacenados cifrados con pgcrypto. Solo Admin/Coordinator los ve.

**Independent Test**: Crear cliente con datos VPN, verificar en DB que columnas son bytea cifrado,
verificar que Resolver recibe 403 al intentar obtener el cliente via API.

### Implementacion User Story 1

- [ ] T017 Crear migracion tabla `clients` con columnas `vpn_ips BYTEA` y `vpn_credentials BYTEA` cifradas via pgcrypto, constraint UNIQUE en `name`, habilitar RLS en `backend/infra/migrations/versions/002_create_clients.py`
- [ ] T018 Implementar entidad `Client` con campos y metodo `deactivate()` en `backend/domain/entities/client.py`
- [ ] T019 [P] [US1] Implementar `ClientService` con reglas: unicidad de nombre, validar impacto al desactivar (proyectos activos + tickets abiertos), cifrado/descifrado delegado a repo en `backend/domain/services/client_service.py`
- [ ] T020 [P] [US1] Implementar `ClientModel` SQLAlchemy con columnas BYTEA para vpn_ips/vpn_credentials; cifrado con `pgcrypto.encrypt` / descifrado con `pgcrypto.decrypt` en `backend/infra/models/client_model.py`
- [ ] T021 [US1] Implementar `ClientRepository` con metodos `list_paginated`, `get_by_id`, `create`, `update`, `deactivate`; descifra vpn_ips/vpn_credentials al leer en `backend/infra/repositories/client_repo.py`
- [ ] T022 [US1] Implementar endpoints Flask-RESTX: `GET /api/clients`, `GET /api/clients/{id}`, `POST /api/clients`, `PATCH /api/clients/{id}`, `PATCH /api/clients/{id}/deactivate`; aplicar `@require_role('admin','coordinator')` en `backend/api/routes/clients.py`
- [ ] T023 [P] [US1] Definir tipos TypeScript `Client`, `ClientListItem`, `ClientFormData`, `ClientDetail` en `frontend/src/types/client.ts`
- [ ] T024 [P] [US1] Implementar `clientService.ts` con funciones `listClients`, `getClient`, `createClient`, `updateClient`, `deactivateClient` usando apiClient en `frontend/src/services/clientService.ts`
- [ ] T025 [P] [US1] Crear store Zustand `clientStore.ts` con estado `clients`, `selectedClient`, acciones de CRUD en `frontend/src/store/clientStore.ts`
- [ ] T026 [US1] Implementar `ClientList.tsx`: Table Ant Design con columnas nombre/estado/acciones, busqueda por texto, paginacion server-side, badge Activo/Inactivo en `frontend/src/components/clients/ClientList.tsx`
- [ ] T027 [US1] Implementar `ClientForm.tsx`: Form Ant Design para crear/editar cliente; campos VPN visibles solo si rol Admin/Coordinator; validacion frontend en espanol en `frontend/src/components/clients/ClientForm.tsx`
- [ ] T028 [US1] Implementar `ClientDetail.tsx`: vista de detalle con datos sensibles visibles para Admin/Coordinator (no exportables), boton desactivar con confirmacion de impacto en `frontend/src/components/clients/ClientDetail.tsx`
- [ ] T029 [US1] Implementar pagina `ClientsPage.tsx` integrando ClientList + ClientForm + ClientDetail con rutas `/clients` y `/clients/:id` en `frontend/src/pages/ClientsPage.tsx`

**Checkpoint**: US1 completa. CRUD de clientes operativo. Cifrado VPN verificado en DB. Resolver bloqueado con 403.

---

## Phase 4: User Story 2 — Gestión de Proyectos (Priority: P1)

**Goal**: Admin y Coordinador pueden crear, ver, editar y desactivar proyectos asociados a clientes
existentes. Nombre unico por cliente. No se puede crear proyecto para cliente inactivo.

**Independent Test**: Crear proyecto para cliente activo, intentar crear para cliente inactivo
(debe fallar), intentar crear proyecto con nombre duplicado en mismo cliente (debe fallar).

### Implementacion User Story 2

- [ ] T030 Crear migracion tabla `projects` con FK `client_id`, constraint `UNIQUE(client_id, name)`, check de fechas, habilitar RLS en `backend/infra/migrations/versions/003_create_projects.py`
- [ ] T031 [P] [US2] Implementar entidad `Project` en `backend/domain/entities/project.py`
- [ ] T032 [P] [US2] Implementar `ProjectService` con reglas: cliente debe estar activo al crear, nombre unico por cliente, validar fechas (fin >= inicio) en `backend/domain/services/project_service.py`
- [ ] T033 [P] [US2] Implementar `ProjectModel` SQLAlchemy con FK a clients en `backend/infra/models/project_model.py`
- [ ] T034 [US2] Implementar `ProjectRepository` con metodos `list_paginated` (acepta filtro `client_id`), `get_by_id`, `create`, `update`, `deactivate` en `backend/infra/repositories/project_repo.py`
- [ ] T035 [US2] Implementar endpoints Flask-RESTX: `GET /api/projects`, `GET /api/projects/{id}`, `POST /api/projects`, `PATCH /api/projects/{id}`, `PATCH /api/projects/{id}/deactivate`; `@require_role('admin','coordinator')` en `backend/api/routes/projects.py`
- [ ] T036 [P] [US2] Definir tipos TypeScript `Project`, `ProjectListItem`, `ProjectFormData` en `frontend/src/types/project.ts`
- [ ] T037 [P] [US2] Implementar `projectService.ts` con `listProjects`, `getProject`, `createProject`, `updateProject`, `deactivateProject` en `frontend/src/services/projectService.ts`
- [ ] T038 [P] [US2] Crear store `projectStore.ts` con filtro por client_id en `frontend/src/store/projectStore.ts`
- [ ] T039 [US2] Implementar `ProjectList.tsx`: Table con columnas nombre/cliente/estado/fechas, filtro por cliente (Select Ant Design), paginacion en `frontend/src/components/projects/ProjectList.tsx`
- [ ] T040 [US2] Implementar `ProjectForm.tsx`: selector de cliente (solo activos), campos de fechas con DatePicker Ant Design, validacion fin >= inicio en espanol en `frontend/src/components/projects/ProjectForm.tsx`
- [ ] T041 [US2] Implementar pagina `ProjectsPage.tsx` integrando ProjectList + ProjectForm en `frontend/src/pages/ProjectsPage.tsx`

**Checkpoint**: US2 completa. Proyectos CRUD operativo. Reglas de cliente activo y unicidad de nombre verificadas.

---

## Phase 5: User Story 3 — Gestión de Recursos y Skills (Priority: P2)

**Goal**: Admin crea/edita recursos con skills asignados. QM ve lista completa (solo lectura).
Resolver ve y edita solo su propio perfil. Skills no eliminables si estan en uso.

**Independent Test**: Crear recurso con skills, filtrar lista por skill, intentar eliminar skill
en uso (debe fallar), acceder al recurso de otro como Resolver via API (debe dar 403).

### Implementacion User Story 3

- [ ] T042 Crear migraciones `skills`, `resources`, `resource_skills` con RLS; seed de skills iniciales (JDE_GL, API_REST, Oracle_Fusion, JDE_AP) en `backend/infra/migrations/versions/004_create_skills.py`, `005_create_resources.py`, `006_create_resource_skills.py`, `007_seed_skills.py`
- [ ] T043 [P] [US3] Implementar entidad `Resource` y entidad `Skill` en `backend/domain/entities/resource.py`
- [ ] T044 [P] [US3] Implementar `SkillService` con regla: no eliminar skill asignado a recursos activos; devolver conteo de recursos afectados en `backend/domain/services/skill_service.py`
- [ ] T045 [P] [US3] Implementar `ResourceService` con reglas: email unico, email @sywork.net, advertencia si sin skills; logica de acceso: Resolver solo puede editar `notes` de su propio recurso en `backend/domain/services/resource_service.py`
- [ ] T046 [P] [US3] Implementar `SkillModel` y `ResourceModel` SQLAlchemy con tabla de union `resource_skills` en `backend/infra/models/skill_model.py` y `backend/infra/models/resource_model.py`
- [ ] T047 [US3] Implementar `SkillRepository` y `ResourceRepository` con metodo `list_paginated` (acepta filtro `skill_code`) en `backend/infra/repositories/resource_repo.py`
- [ ] T048 [US3] Implementar endpoints Flask-RESTX para `/api/skills`: `GET`, `POST`, `DELETE /{id}` (DELETE falla con 409 si skill en uso); `@require_role('admin')` para POST/DELETE en `backend/api/routes/resources.py`
- [ ] T049 [US3] Implementar endpoints Flask-RESTX para `/api/resources`: `GET`, `GET /{id}`, `POST`, `PATCH /{id}`, `PATCH /{id}/skills`, `PATCH /{id}/deactivate`; Resolver bloqueado a ver/editar solo su propio recurso en `backend/api/routes/resources.py`
- [ ] T050 [P] [US3] Definir tipos TypeScript `Resource`, `Skill`, `ResourceFormData` en `frontend/src/types/resource.ts`
- [ ] T051 [P] [US3] Implementar `resourceService.ts` y `skillService.ts` en `frontend/src/services/resourceService.ts`
- [ ] T052 [P] [US3] Crear stores `resourceStore.ts` con filtro por skill y `skillStore.ts` en `frontend/src/store/resourceStore.ts`
- [ ] T053 [US3] Implementar `SkillSelector.tsx`: componente Select multiple con lista de skills activos para asignar a recurso en `frontend/src/components/resources/SkillSelector.tsx`
- [ ] T054 [US3] Implementar `ResourceList.tsx`: Table con columnas nombre/skills/estado, filtro por skill (Select), restringir a solo propio recurso si rol Resolver en `frontend/src/components/resources/ResourceList.tsx`
- [ ] T055 [US3] Implementar `ResourceForm.tsx`: Form con SkillSelector, campo email @sywork.net, advertencia si sin skills seleccionados en `frontend/src/components/resources/ResourceForm.tsx`
- [ ] T056 [US3] Implementar pagina `ResourcesPage.tsx` con seccion de administracion de skills (solo Admin) en `frontend/src/pages/ResourcesPage.tsx`

**Checkpoint**: US3 completa. CRUD recursos operativo. Filtro por skill funcional. Restriccion Resolver verificada via API.

---

## Phase 6: User Story 4 — Gestión de Roles y Seguridad (Priority: P2)

**Goal**: Admin cambia roles de usuarios y desactiva cuentas. Regla del ultimo Admin activa.
Usuario desactivado bloqueado en siguiente request aunque JWT sea valido.

**Independent Test**: Cambiar rol de usuario, cerrar sesion y verificar permisos cambiados.
Intentar desactivar/degradar al ultimo Admin (debe fallar con 409).

### Implementacion User Story 4

- [ ] T057 [P] [US4] Implementar `RoleService` con regla: verificar que no es el ultimo Admin activo antes de cambio de rol o desactivacion; devolver error de negocio `last_admin` en `backend/domain/services/role_service.py`
- [ ] T058 [US4] Implementar endpoints Flask-RESTX: `GET /api/users`, `GET /api/users/me`, `PATCH /api/users/{id}/role`, `PATCH /api/users/{id}/deactivate`; `GET /api/users` solo Admin en `backend/api/routes/users.py`
- [ ] T059 [P] [US4] Definir tipos TypeScript `UserAdmin`, `RoleChangeRequest` en `frontend/src/types/user.ts`
- [ ] T060 [P] [US4] Implementar `userService.ts` con `listUsers`, `getMe`, `changeRole`, `deactivateUser` en `frontend/src/services/userService.ts`
- [ ] T061 [P] [US4] Crear store `userStore.ts` (lista de usuarios para Admin) en `frontend/src/store/userStore.ts`
- [ ] T062 [US4] Implementar `UserList.tsx`: Table con columnas email/rol/estado/ultimo-login, acciones de cambio de rol y desactivacion solo para Admin en `frontend/src/components/users/UserList.tsx`
- [ ] T063 [US4] Implementar `RoleAssignment.tsx`: Select de rol con confirmacion de cambio; deshabilitar si es el ultimo Admin en `frontend/src/components/users/RoleAssignment.tsx`
- [ ] T064 [US4] Implementar pagina `UsersPage.tsx` integrando UserList + RoleAssignment con ruta `/users` (solo Admin) en `frontend/src/pages/UsersPage.tsx`

**Checkpoint**: US4 completa. Cambio de roles operativo. Regla ultimo Admin verificada. Usuario desactivado bloqueado en API.

---

## Phase 7: Polish y Preocupaciones Transversales

**Purpose**: Mejoras que afectan multiples User Stories; validacion E2E

- [ ] T065 [P] Habilitar RLS en tablas `clients`, `resources`, `users`: crear politicas PostgreSQL en `backend/infra/migrations/versions/008_enable_rls_policies.py`
- [ ] T066 [P] Agregar sanitizacion de inputs en todos los endpoints Flask-RESTX (prevenir XSS/injection): revisar `backend/api/routes/clients.py`, `projects.py`, `resources.py`, `users.py`
- [ ] T067 [P] Verificar que logs de aplicacion (Flask + SQLAlchemy) nunca incluyen `vpn_ips` ni `vpn_credentials` en texto plano: revisar configuracion de logging en `backend/app.py`
- [ ] T068 [P] Agregar paginacion consistente a todos los endpoints de lista que no la tengan; verificar parametros `page` y `page_size` (max 100) en `backend/api/routes/`
- [ ] T069 [P] Agregar mensajes de error en espanol en respuestas 400 de todos los endpoints de negocio en `backend/api/routes/`
- [ ] T070 [P] Implementar componente `ConfirmationModal` reutilizable (Ant Design Modal) para todas las acciones destructivas con descripcion de impacto en `frontend/src/components/common/ConfirmationModal.tsx`
- [ ] T071 [P] Verificar que ningun componente React expone datos sensibles a roles no autorizados; auditar `ClientDetail.tsx`, `ClientForm.tsx` en `frontend/src/components/clients/`
- [ ] T072 Ejecutar todos los escenarios del `quickstart.md` y marcar checklist de validacion completo en `specs/001-fase0-maestros/quickstart.md`
- [ ] T073 [P] Actualizar Swagger (Flask-RESTX) con descripciones de endpoints, esquemas de request/response y codigos de error en `backend/api/routes/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Sin dependencias — puede comenzar inmediatamente
- **Phase 2 (Foundational)**: Depende de Phase 1 — BLOQUEA todas las User Stories
- **Phase 3 (US1 Clientes)**: Depende de Phase 2 — puede ejecutarse en paralelo con US2
- **Phase 4 (US2 Proyectos)**: Depende de Phase 2 — puede ejecutarse en paralelo con US1
- **Phase 5 (US3 Recursos)**: Depende de Phase 2 — puede ejecutarse en paralelo con US1/US2
- **Phase 6 (US4 Roles)**: Depende de Phase 2 (T006-T012 ya crean la tabla users y el middleware); puede ejecutarse en paralelo con US1/US2/US3
- **Phase 7 (Polish)**: Depende de todas las User Stories deseadas

### User Story Dependencies (Data Model)

- **US1 (Clientes)**: Sin dependencias de otras US. Solo requiere Foundation.
- **US2 (Proyectos)**: Requiere que la tabla `clients` exista (T017). Si US1 no esta completa, al menos la migracion T017 debe estar ejecutada.
- **US3 (Recursos)**: Sin dependencias de US1/US2. Solo requiere Foundation.
- **US4 (Roles)**: La tabla `users` ya se crea en Foundation (T006). Solo extiende los endpoints de usuarios.

### Dentro de cada User Story

- Migraciones → Entidades de Dominio → Modelos SQLAlchemy → Repositorios → Servicios → Endpoints API → Tipos TS → Services TS → Store → Componentes → Pagina

---

## Parallel Example: User Story 1 (Clientes)

```bash
# Una vez Foundation completa, estos grupos pueden ejecutarse en paralelo:

# Grupo A — Backend (dependientes entre si, secuenciales):
T017 → T018 → T020 → T021 → T019 → T022

# Grupo B — Frontend (independiente del backend mientras API este definida):
T023 (tipos TS) → T024 (service) → T025 (store) → T026/T027/T028 (componentes) → T029 (pagina)

# Grupo A y Grupo B pueden ejecutarse en paralelo si hay dos desarrolladores
```

---

## Implementation Strategy

### MVP (Solo User Story 1 — Clientes)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRITICO — bloquea todo)
3. Completar Phase 3: User Story 1 (Clientes)
4. **PARAR y VALIDAR**: Escenarios 1, 2, 3 del quickstart.md
5. Demo con cliente real si esta listo

### Entrega Incremental

1. Setup + Foundation → Auth con Google OAuth2 operativo
2. US1 (Clientes) → Primer maestro validado independientemente
3. US2 (Proyectos) → Jerarquia cliente→proyecto lista
4. US3 (Recursos) → Skills y perfiles del equipo listos
5. US4 (Roles) → Panel de administracion de usuarios completo
6. Phase 7 (Polish) → RLS activado, validacion E2E completa → **Listo para Fase 1 (Tickets)**

### Estrategia de Equipo Paralelo

Con 2+ desarrolladores, una vez Phase 2 este completa:
- **Dev A**: US1 (Clientes — P1) + US2 (Proyectos — P1)
- **Dev B**: US3 (Recursos — P2) + US4 (Roles — P2)
- Ambos convergen en Phase 7 (Polish + validacion E2E)

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes — pueden ejecutarse en paralelo
- Cada User Story tiene su propio Checkpoint de validacion independiente
- Las migraciones de Alembic deben ejecutarse en orden numerico
- Ningun `any` en TypeScript; ningun campo sin type hint en funciones Python publicas
- pnpm exclusivamente para instalar dependencias frontend
- Datos VPN nunca en logs — verificar en T067 antes de cierre de fase
- Swagger debe estar actualizado antes de considerar la fase completa (T073)
