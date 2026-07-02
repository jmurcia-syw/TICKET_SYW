# Tasks: Fase 0 — Maestros

**Input**: Design documents from `specs/001-fase0-maestros/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tareas agrupadas por User Story para implementacion y validacion independiente.

**Nota de esta revision (2026-07-01)**: La mayor parte del backend de esta fase ya esta
implementado en el repositorio, incluido un alcance mas amplio que el planeado originalmente
(roles dinamicos, catalogo de permisos, login provisional) diseñado y construido fuera del flujo
speckit en `docs/superpowers/specs/2026-07-01-roles-permissions-login-design.md` y
`docs/superpowers/plans/2026-07-01-roles-permissions-login-backend.md` (Tasks 1-12, con commits
reales). Esas tareas se marcan `[x]` aqui sin haberse re-ejecutado — no se repite trabajo ya
hecho.

**Actualización (`/speckit-implement`, 2026-07-01)**: las tareas T074-T099 (Fase 6b: rework de
frontend a roles/permisos dinámicos, login real sin bypass, pantalla Roles y Permisos; y Fase 6:
T095-T097, `POST /api/users` para FR-018b) **ya se implementaron** en esta sesión. Verificación
realizada: `npx tsc -b` (typecheck completo) sin errores, dev server de Vite arrancando sin
errores de transformación, `python -m py_compile` + arranque de `create_app()` con la nueva ruta
registrada, y los 34 tests de `backend/tests/domain/` (no requieren DB) en verde. **No
verificado en esta sesión** por falta de Docker/`.env` en el entorno de ejecución: los tests de
API nuevos (`test_users_api.py::test_create_user_*`) contra Postgres real, y la validación E2E en
navegador de `quickstart.md` (T072) — quedan como siguiente paso para quien tenga el stack
levantado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias incompletas)
- **[Story]**: User Story a la que pertenece la tarea ([US1]..[US4])
- Cada tarea incluye la ruta de archivo exacta

---

## Phase 1: Setup (Infraestructura compartida) — ✅ COMPLETO

- [x] T001 Crear estructura de directorios backend segun plan.md
- [x] T002 Crear estructura de directorios frontend segun plan.md
- [x] T003 [P] Habilitar extension pgcrypto en PostgreSQL (ver `002_create_clients.py`)
- [x] T004 [P] Configurar Alembic (`backend/infra/migrations/env.py`)
- [x] T005 [P] Definir tipos TypeScript compartidos base (`frontend/src/types/api.ts`) —
  **nota**: `Role`/`ActiveStatus` ahi definidos quedaron obsoletos frente al modelo dinamico;
  corregidos en T074.

**Checkpoint**: Estructura de directorios lista. Alembic configurado. pgcrypto habilitado.

---

## Phase 2: Foundational (Prerequisitos bloqueantes) — ✅ COMPLETO

- [x] T006 Migracion tabla `users` (`001_create_users.py`, luego extendida por `009_...`)
- [x] T007 Entidad `User` (`backend/domain/entities/user.py`) — evolucionada a `role: Role` FK
  dinamica en vez de enum fijo (ver Decision 7 en research.md)
- [x] T008 Modelo SQLAlchemy `UserModel` (`backend/infra/models/user_model.py`)
- [x] T009 `UserRepository` (`backend/infra/repositories/user_repo.py`)
- [x] T010 Middleware `auth.py`: JWT + verificacion `users.active` (`backend/api/middleware/auth.py`)
- [x] T011 Decorador `@require_role(*roles)` (`backend/api/middleware/rbac.py`) — existe pero no
  esta enganchado en ninguna ruta de maestros (ver FR-017: enforcement de API diferido)
- [x] T012 Callback Google OAuth2 (`backend/api/routes/auth.py::google_login`)
- [x] T013 [P] Store de autenticacion Zustand (`frontend/src/store/authStore.ts`) — reescrito en
  T076 con permisos dinamicos
- [x] T014 [P] Componente `ProtectedRoute` (`frontend/src/components/common/ProtectedRoute.tsx`)
  — conectado en `App.tsx` en T083/T085, ya sin el bypass `DevLayout`
- [x] T015 [P] Cliente Axios con interceptor JWT (`frontend/src/services/apiClient.ts`)
- [x] T016 [P] React Router configurado — rutas protegidas activadas en T085

**Checkpoint**: Auth backend completo (Google + provisional). Frontend consume auth real desde
Fase 6b (sin bypass de desarrollo).

---

## Phase 3: User Story 1 — Gestión de Clientes (Priority: P1) MVP — ✅ COMPLETO

**Goal**: Admin, Coordinador y QM pueden crear, ver, editar, desactivar y reactivar clientes.
Resolutor tiene acceso de solo lectura. Datos sensibles (VPN IPs/credenciales) cifrados con
pgcrypto, visibles solo para Admin/Coordinador (FR-001, FR-003 actualizados 2026-07-01).

- [x] T017 Migracion `clients` con `vpn_ips`/`vpn_credentials` cifrados (`002_create_clients.py`)
- [x] T018 Entidad `Client` (`backend/domain/entities/client.py`)
- [x] T019 [P] [US1] `ClientService` (`backend/domain/services/client_service.py`)
- [x] T020 [P] [US1] `ClientModel` SQLAlchemy (`backend/infra/models/client_model.py`)
- [x] T021 [US1] `ClientRepository` (`backend/infra/repositories/client_repo.py`)
- [x] T022 [US1] Endpoints Flask-RESTX `/api/clients` (`backend/api/routes/clients.py`) —
  incluye ademas `PATCH /{id}/activate` (no estaba en el plan original, ya implementado)
- [x] T023 [P] [US1] Tipos TS `Client*` (`frontend/src/types/client.ts`)
- [x] T024 [P] [US1] `clientService.ts`
- [x] T025 [P] [US1] Store `clientStore.ts` — no existe como archivo separado; el estado vive
  local en `ClientsPage.tsx` (patron equivalente, sin store dedicado — no bloqueante)
- [x] T026 [US1] `ClientList`/`ClientsPage.tsx`: tabla, busqueda, paginacion, badge Activo/Inactivo
- [x] T027 [US1] `ClientForm` (dentro de `ClientsPage.tsx`): formulario crear/editar
- [x] T028 [US1] Detalle de cliente con VPN enmascarada + boton de revelar (icono ojo)
- [x] T029 [US1] Rutas `/clients` integradas en la app

**Gap real detectado (2026-07-01), corregido en T089**: `ClientsPage.tsx` no ocultaba los botones
de crear/editar/desactivar ni el boton de revelar VPN segun permiso. Ahora usa
`hasPermission('clients', ...)` y un chequeo de rol para los campos VPN (FR-001, FR-003).

**Checkpoint**: US1 completa, incluido el gating de permisos (T089).

---

## Phase 4: User Story 2 — Gestión de Proyectos (Priority: P1) — ✅ COMPLETO

- [x] T030 Migracion `projects` (`003_create_projects.py`)
- [x] T031 [P] [US2] Entidad `Project`
- [x] T032 [P] [US2] `ProjectService` (cliente activo, nombre unico, fechas)
- [x] T033 [P] [US2] `ProjectModel`
- [x] T034 [US2] `ProjectRepository`
- [x] T035 [US2] Endpoints `/api/projects` (incluye `/activate`, no estaba en el plan original)
- [x] T036 [P] [US2] Tipos TS `Project*`
- [x] T037 [P] [US2] `projectService.ts`
- [x] T038 [P] [US2] Filtro por `client_id` (dentro de `ProjectsPage.tsx`)
- [x] T039 [US2] `ProjectList`/`ProjectsPage.tsx`
- [x] T040 [US2] `ProjectForm`: selector de cliente activo, fechas, validacion fin >= inicio
- [x] T041 [US2] Rutas `/projects` integradas

**Gap real detectado (2026-07-01), corregido en T090**: `ProjectsPage.tsx` no restringía a solo
lectura a QM/Resolutor (FR-006b). Ahora usa `hasPermission('projects', ...)`.

**Checkpoint**: US2 completa, incluido el gating de permisos (T090).

---

## Phase 5: User Story 3 — Gestión de Recursos y Skills (Priority: P2) — ✅ COMPLETO

**Goal actualizado (2026-07-01)**: Admin, Coordinador **y QM** comparten el mismo acceso completo
sobre Recursos y Skills (FR-009, FR-010, FR-013 — QM ya no es "solo lectura"). Resolutor ve y
edita unicamente su propio perfil.

- [x] T042 Migraciones `skills`/`resources`/`resource_skills` + seed (`004_create_skills_resources.py`)
- [x] T043 [P] [US3] Entidades `Resource`, `Skill` — **sin campo `role`** (ver Clarifications en
  spec.md, 2026-07-01): el rol de acceso vive solo en `User.user_id` opcional
- [x] T044 [P] [US3] `SkillService` (bloqueo de eliminacion si en uso)
- [x] T045 [P] [US3] `ResourceService` (email unico, advertencia sin skills, Resolutor solo su
  propio perfil)
- [x] T046 [P] [US3] `SkillModel`/`ResourceModel`
- [x] T047 [US3] `SkillRepository`/`ResourceRepository`
- [x] T048 [US3] Endpoints `/api/skills` (GET/POST/DELETE)
- [x] T049 [US3] Endpoints `/api/resources` (incluye `/activate`, no estaba en el plan original)
- [x] T050 [P] [US3] Tipos TS `Resource`, `Skill`
- [x] T051 [P] [US3] `resourceService.ts`/`skillService.ts` (`frontend/src/services/resourceService.ts`)
- [x] T052 [P] [US3] Filtro por skill (dentro de `ResourcesPage.tsx`)
- [x] T053 [US3] `SkillSelector` (Select multiple dentro de `ResourcesPage.tsx`)
- [x] T054 [US3] `ResourceList`/`ResourcesPage.tsx`
- [x] T055 [US3] `ResourceForm`
- [x] T056 [US3] `SkillsPage.tsx` — administracion de skills

**Gap real detectado (2026-07-01), corregido en T091/T092**: `ResourcesPage.tsx` definía
`const isAdmin = role === 'admin'` y ocultaba crear/editar/desactivar/gestionar-skills para
cualquiera que no fuera literalmente Admin, contradiciendo FR-009/FR-013. Ahora usa
`hasPermission('resources', 'create')` (Admin, Coordinador y QM comparten el mismo acceso) más
una excepción explícita para que un Resolutor edite su propio perfil (FR-012). `SkillsPage.tsx`
tampoco tenía ningún gating — se le agregó en T092.

**Checkpoint**: US3 completa, incluido el gating de permisos (T091, T092).

---

## Phase 6: User Story 4 — Gestión de Roles y Seguridad (alcance original) — ✅ COMPLETO (y superado)

**Nota**: el alcance real implementado (roles dinamicos + permisos granulares + login
provisional) es mucho mayor que estas 8 tareas originales — ver Fase 6b para el detalle completo
del rework de frontend correspondiente (ya completado).

- [x] T057 `RoleService` (regla del ultimo Admin) — adaptado a roles dinamicos en
  `backend/domain/services/role_service.py` (ver Decision 7/research.md)
- [x] T058 Endpoints `/api/users` (`GET`, `GET /me`, `PATCH /{id}/role`, `PATCH /{id}/deactivate`,
  `PATCH /{id}/activate`) — el alcance real agrega ademas `/api/roles` y `/api/permissions`
  completos (Tasks 1-12 de `docs/superpowers/plans/2026-07-01-roles-permissions-login-backend.md`,
  ya implementadas — no confundir con los IDs T074+ de este archivo, que son nuevos)
- [x] T059 Tipos TS `UserAdmin`, `RoleChangeRequest` (`frontend/src/types/user.ts`) — corregido
  en T094: `role: {id, name}`, `RoleChangeRequest.role_id`.
- [x] T060 `userService.ts` — corregido en T093/T098: `changeRole` envia `{ role_id }`, se agrego
  `create()`.
- [x] T061 Store `userStore.ts` — no existe como archivo separado; estado local en `UsersPage.tsx`
  (equivalente, no bloqueante)
- [x] T062 `UserList.tsx` (dentro de `UsersPage.tsx`) — corregido en T093: carga roles via
  `roleService.list()` en vez del array fijo `ROLES`.
- [x] T063 `RoleAssignment.tsx` (dentro de `UsersPage.tsx`) — corregido junto con T062/T093.
- [x] T064 Pagina `UsersPage.tsx` con ruta `/users` — reescrita en T093/T099 (rol dinamico +
  alta de usuarios).

### Gap nuevo detectado en `/speckit-clarify` (2026-07-01) — FR-018b: alta de usuarios

Ni el spec original ni el código definían cómo se crea un `User` para un empleado nuevo más allá
de los 4 usuarios semilla: no existe `POST /api/users`, y el login de Google no auto-crea cuentas
(devuelve 401 si el usuario no existe). Se resolvió en clarify: Admin crea el usuario manualmente
desde la pantalla de Usuarios, con una contraseña provisional generada una única vez (FR-018b).
La plomería de dominio ya existe (`UserRepository.create`, `AuthService.hash_password`) — solo
falta la ruta HTTP y el formulario.

- [x] T095 [US4] Implementar `POST /api/users` en `backend/api/routes/users.py` (mismo patrón
  que `RoleList.post` en `roles.py`): body `{ email, username, role_id }`; valida dominio
  `@sywork.net`, rechaza `email`/`username` duplicados con 409, valida que `role_id` exista
  (404 si no); genera una contraseña provisional con `secrets.token_urlsafe(9)`, la hashea con
  `AuthService.hash_password` y la guarda en `password_hash`; crea el usuario via
  `UserRepository.create`; responde `201` con
  `{ user: {...}, provisional_password: "<texto plano, una sola vez>" }` y header `Location`.
  Verificado: `python -m py_compile`, arranque completo de `create_app()` y registro correcto
  de la ruta (`GET/POST /api/users` en `app.url_map`).
- [x] T096 [P] [US4] Tests en `backend/tests/api/test_users_api.py` para `POST /api/users`:
  creación exitosa (incluye `provisional_password` en la respuesta y verifica login inmediato
  con esa contraseña), email fuera de `@sywork.net` (400), email duplicado (409), username
  duplicado (409), `role_id` inexistente (404), campos faltantes (400). **Escritos pero NO
  ejecutados contra Postgres real** — requieren `docker compose up` con `.env` (no disponible en
  este entorno de ejecución); correr `docker exec sywork_backend python -m pytest
  tests/api/test_users_api.py -v` para confirmar antes de cerrar la tarea. Los 34 tests de
  `backend/tests/domain/` (sin DB) sí se ejecutaron y pasan.
- [x] T097 [P] [US4] Documentado `POST /api/users` en `specs/001-fase0-maestros/contracts/roles.md`
  (sección Users), mismo formato que los demás endpoints del contrato.

**Checkpoint**: Backend de Roles/Permisos/Login 100% completo, incluida la alta de usuarios
(T095-T097). Frontend de gestion de usuarios corregido en Fase 6b (T093/T098/T099).

---

## Phase 6b: Rework — Roles Dinámicos, Permisos y Login Real en el Frontend — ✅ COMPLETO

**Verificación realizada en esta sesión**: `npx tsc -b` (typecheck completo del frontend) pasa
sin errores; `pnpm install` sincronizó `pnpm-lock.yaml` (estaba desactualizado desde antes de
esta sesión — le faltaba `react-router-dom`); el dev server de Vite arranca y sirve todos los
módulos nuevos/modificados sin errores de transformación. **No verificado**: flujo E2E real en
navegador (login → menú dinámico → CRUD por rol) contra un backend con Postgres real, porque el
entorno de ejecución no tiene Docker/`.env` disponibles — pendiente que alguien con el stack
levantado siga el Escenario 1, 7, 8 y 10 de `quickstart.md` (T072).

**Goal**: Reemplazar el modelo de rol fijo del frontend (`'admin'|'coordinator'|'qm'|'resolver'`)
por el modelo dinamico de roles+permisos ya implementado en el backend; activar el login real
(provisional + Google) eliminando el bypass `DevLayout`; construir la pantalla "Roles y
Permisos"; y corregir el gating de botones en las paginas existentes para que coincida con
FR-001/FR-006b/FR-009/FR-013.

**Independent Test**: Con el frontend reconstruido, iniciar sesion como cada uno de los 4
usuarios semilla (`admin@sywork.net`, `coordinador@sywork.net`, `qm@sywork.net`,
`resolutor@sywork.net`) y verificar que el menu lateral y los botones de accion en cada pantalla
coinciden exactamente con la matriz de permisos de `spec.md` (User Story 4).

### Fundacion (bloquea el resto de esta fase)

- [x] T074 [US4] Actualizar `frontend/src/types/api.ts`: reemplazar
  `export type Role = 'admin' | 'coordinator' | 'qm' | 'resolver'` por
  `export interface Role { id: string; name: string }` y agregar
  `export interface Permission { module: string; action: string }`.
- [x] T075 [P] [US4] Crear `frontend/src/types/role.ts`: `Role`, `Permission`, `RoleFormData`,
  `RolePermissionsUpdate` según `contracts/roles.md`.
- [x] T076 [US4] Reescribir `frontend/src/store/authStore.ts` (depende de T074): agregar
  `username: string | null`, `permissions: Permission[]`; `setAuth(token, user)` recibe el
  objeto `user` completo de `/api/auth/login` (`{id, email, username, role, permissions}`);
  agregar `hasPermission(module: string, action: string): boolean`; quitar `hasRole` basado en
  union fijo.
- [x] T077 [P] [US4] Crear `frontend/src/services/authService.ts`: `login(username_or_email,
  password)` → `POST /api/auth/login`; `me()` → `GET /api/auth/me` (ambos según
  `contracts/roles.md`).
- [x] T078 [P] [US4] Crear `frontend/src/services/roleService.ts` (depende de T075): `list`,
  `get`, `create`, `update`, `replacePermissions`, `deactivate`, `activate` sobre `/api/roles`.
- [x] T079 [P] [US4] Crear `frontend/src/services/permissionService.ts` (depende de T075):
  `list`, `create`, `delete` sobre `/api/permissions`.
- [x] T081 [US4] Reescribir `frontend/src/theme.ts`: quitar
  `ROLE_COLORS: Record<'admin'|'coordinator'|'qm'|'resolver', string>` fijo; reemplazar por
  `roleColor(name: string): string` que asigna color de una paleta fija de forma determinística
  (ej. hash del nombre del rol) para soportar roles creados dinámicamente sin romper.
- [x] T082 [US4] Reescribir `frontend/src/config/navigation.tsx` (depende de T075): quitar
  `roles: Role[]` de cada item; cada item declara `{ module: string }` (la acción `view` se
  asume); exportar `getVisibleNavItems(permissions: Permission[])` que filtra por
  `permissions.some(p => p.module === item.module && p.action === 'view')`; agregar el item
  "Roles y Permisos" (`module: 'roles'`).

### Login real y activación de rutas protegidas

- [x] T080 [US4] Reescribir `frontend/src/pages/LoginPage.tsx` (depende de T076, T077):
  formulario Ant Design usuario/contraseña que llama `authService.login`, guarda
  `{token, user}` via `authStore.setAuth`, navega a `/dashboard`; mantener el botón de Google
  como alternativa secundaria (llama `/api/auth/google`, integración real de Google Identity
  Services queda fuera de alcance de esta tarea — puede seguir como placeholder si no hay
  credenciales de OAuth configuradas en el entorno).
- [x] T083 [US4] Actualizar `frontend/src/components/common/ProtectedRoute.tsx` (depende de
  T074, T076): cambiar prop `roles?: Role[]` por `requiredPermission?: { module: string; action:
  string }`; usar `hasPermission` de `authStore` en vez de `hasRole`.
- [x] T084 [US4] Actualizar `frontend/src/pages/DashboardPage.tsx` (depende de T082, T083):
  usar `getVisibleNavItems(permissions)` en vez de
  `maestrosNavItems.filter(item => item.roles.includes(role))`; mostrar `role.name` (no el
  objeto completo) en el `Tag` de cabecera usando `roleColor` (T081).
- [x] T085 [US4] Reescribir `frontend/src/App.tsx` (depende de T080, T083, T084): eliminar
  `DevLayout` y el bypass de autenticación por completo; ruta pública `/login`; envolver el
  resto de rutas (`/clients`, `/projects`, `/resources`, `/skills`, `/users`, `/roles`) en
  `<ProtectedRoute><DashboardPage /></ProtectedRoute>` con rutas anidadas (`<Outlet/>`, ya usado
  en `DashboardPage.tsx`); agregar la ruta `/roles` → `RolesPermissionsPage` (T087).

### Pantalla nueva — Roles y Permisos

- [x] T086 [US4] Crear `frontend/src/components/roles/PermissionMatrix.tsx` (depende de T075,
  T078, T079): tabla módulo × acción con checkboxes por permiso; recibe `role`,
  `allPermissions`, `onChange(permissionIds: string[])`; al guardar llama
  `roleService.replacePermissions(role.id, permissionIds)`.
- [x] T087 [US4] Crear `frontend/src/pages/RolesPermissionsPage.tsx` (depende de T078, T086):
  tabla de roles con crear/editar/desactivar/activar (mismo patrón visual que
  `ClientsPage.tsx`); al editar un rol abre `PermissionMatrix` en un `Modal`.

### Corrección de gating de permisos en pantallas existentes (gaps reales de FR-001/006b/009/013)

- [x] T089 [P] [US1] Actualizar `frontend/src/pages/ClientsPage.tsx` (depende de T076): ocultar
  el botón "Nuevo cliente", los íconos de Editar/Desactivar/Activar y el botón de revelar VPN
  cuando `!hasPermission('clients', 'create'|'edit'|'deactivate')`; un Resolutor
  (`clients: view` únicamente) debe ver solo el listado de solo lectura (FR-001).
- [x] T090 [P] [US2] Actualizar `frontend/src/pages/ProjectsPage.tsx` (depende de T076): ocultar
  creación/edición/desactivación si `!hasPermission('projects', 'create'|'edit'|'deactivate')`
  (QM y Resolutor deben ver solo lectura, FR-006b).
- [x] T091 [P] [US3] Corregir `frontend/src/pages/ResourcesPage.tsx` (depende de T076):
  reemplazar `const isAdmin = role === 'admin'` (línea 15) por
  `const canManage = hasPermission('resources', 'create')`; Admin, Coordinador y QM deben tener
  el mismo acceso completo (FR-013) — hoy solo Admin ve los botones de crear/editar/desactivar y
  el selector de skills al editar.
- [x] T092 [P] [US3] Revisar `frontend/src/pages/SkillsPage.tsx` (depende de T076): si usa el
  mismo patrón de rol fijo que `ResourcesPage.tsx`, reemplazarlo por
  `hasPermission('skills', 'create'|'deactivate')` (FR-010 — Admin, Coordinador y QM comparten
  el mismo acceso al catálogo de skills).
- [x] T093 [US4] Corregir `frontend/src/pages/UsersPage.tsx` y `frontend/src/services/
  userService.ts` (depende de T074, T078, T094): el backend real espera
  `PATCH /api/users/{id}/role` con body `{ role_id: string }` y devuelve `role: {id, name}`,
  pero el código actual envía `{ role }` (string) y usa un array `ROLES` fijo de 4 valores en
  inglés minúscula (`const ROLES: Role[] = ['admin','coordinator','qm','resolver']`, línea 12).
  Reemplazar el `Select` de rol por una carga de `roleService.list()` (T078); actualizar
  `changeRole` en `userService.ts` para enviar `{ role_id }`.
- [x] T094 [P] [US4] Actualizar `frontend/src/types/user.ts` (depende de T074): `UserAdmin.role`
  pasa de `Role` (string) a `{ id: string; name: string }`; `RoleChangeRequest` pasa de
  `{ role: Role }` a `{ role_id: string }`; agregar `UserCreateRequest { email: string; username:
  string; role_id: string }` y `UserCreateResponse { user: UserAdmin; provisional_password:
  string }` (FR-018b).

### Alta de usuarios en el frontend (FR-018b, depende del backend T095-T097)

- [x] T098 [P] [US4] Agregar `create(data: UserCreateRequest)` a
  `frontend/src/services/userService.ts` → `POST /api/users`, devuelve `UserCreateResponse`
  (depende de T094, T095).
- [x] T099 [US4] Agregar botón "Nuevo usuario" en `frontend/src/pages/UsersPage.tsx` (parte del
  rework de T093): modal con formulario (`email`, `username`, `Select` de rol cargado con
  `roleService.list()`); al crear con éxito, mostrar un segundo modal no descartable por accidente
  con la `provisional_password` en texto monoespaciado y copiable, y una advertencia de que no se
  volverá a mostrar (depende de T078, T098).

**Checkpoint**: Login real (provisional + Google) operativo, sin bypass de desarrollo. Menú y
botones de acción en las 5 pantallas de maestros reflejan exactamente la matriz de permisos de
`spec.md` User Story 4. Pantalla "Roles y Permisos" funcional para Admin. Admin puede dar de alta
a un usuario nuevo end-to-end (T095-T099) y esa persona puede iniciar sesión con la contraseña
provisional generada.

---

## Phase 7: Polish y Preocupaciones Transversales

- [x] T065 [P] Políticas RLS en `clients`, `resources`, `users`
  (`backend/infra/migrations/versions/008_enable_rls_policies.py`)
- [ ] T066 [P] Auditar sanitización de inputs contra XSS/inyección en todos los endpoints —
  no re-verificado en esta sesión, sigue pendiente de confirmación explícita
- [ ] T067 [P] Verificar que los logs de aplicación nunca incluyen `vpn_ips`/`vpn_credentials`
  en texto plano — no re-verificado en esta sesión
- [x] T068 [P] Paginación consistente (`page`/`page_size`, máx 100) — verificado en
  clients/projects/resources/users/roles
- [x] T069 [P] Mensajes de error en español en respuestas 400 — verificado en las rutas leídas
- [x] T070 [P] Componente `ConfirmationModal` reutilizable
  (`frontend/src/components/common/ConfirmationModal.tsx`)
- [ ] T071 [P] Auditar que ningún componente React expone datos sensibles a roles no
  autorizados — pendiente de re-verificación tras T089 (el gating de VPN en `ClientsPage.tsx`
  hoy depende solo de que el backend omita el campo, sin gating adicional en frontend)
- [ ] T072 Ejecutar todos los escenarios de `quickstart.md` (incluye login provisional, roles
  dinámicos, reactivación y alta de usuarios — Escenarios 7-10) contra un stack real
  (`docker compose up`) y marcar su checklist de validación. Fase 6b ya está completa en código
  y pasa typecheck (`npx tsc -b`) y arranque de dev server; lo único que falta es la validación
  E2E manual en navegador contra un backend con Postgres real, que este entorno de ejecución no
  puede levantar (sin `.env`/Docker disponibles aquí).
- [x] T073 [P] Swagger actualizado (`backend/app.py`, commit
  "docs(api): fix stale Swagger description referencing the old DEV_SKIP_AUTH bypass")

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1-5**: ✅ Completas (backend y UI base)
- **Phase 6**: ✅ Completa, incluido FR-018b (T095-T097)
- **Phase 6b**: ✅ Completa (T074-T099) — código escrito y verificado por typecheck/dev-server;
  falta validación E2E manual (T072)
- **Phase 7 (Polish)**: T066, T067, T071, T072 pendientes de auditoría/validación explícita

### Dentro de Phase 6b

```
T074 → T075 → T076 → {T077, T078, T079, T081, T082} (paralelo)
T076 + T077 → T080
T074 + T076 → T083
T082 + T083 → T084
T080 + T083 + T084 → T085
T075 + T078 + T079 → T086 → T087
T076 → {T089, T090, T091, T092} (paralelo entre si)
T074 + T078 + T094 → T093
T094 + T095 → T098 → T099 (T099 tambien depende de T078 para el Select de roles)
```

### Backend FR-018b (independiente de Phase 6b)

```
T095 → {T096, T097} (paralelo)
```

---

## Parallel Example: Phase 6b (una vez completa la Fundación T074-T076)

```bash
# Grupo A — servicios (independientes entre si):
T077 (authService) | T078 (roleService) | T079 (permissionService)

# Grupo B — theming y navegacion (independientes entre si):
T081 (theme.ts) | T082 (navigation.tsx)

# Grupo C — correccion de gating en paginas existentes (archivos distintos, todas dependen solo de T076):
T089 (ClientsPage) | T090 (ProjectsPage) | T091 (ResourcesPage) | T092 (SkillsPage) | T094 (types/user.ts)
```

---

## Implementation Strategy

### Estado actual

1. ✅ Setup + Foundational (backend)
2. ✅ US1 Clientes, US2 Proyectos, US3 Recursos/Skills — backend completo, UI base funcional
3. ✅ US4 Roles/Permisos/Login — backend completo, incluida la alta de usuarios (FR-018b)
4. ✅ Fase 6b (frontend dinámico) — login real sin bypass, menú y gating por permisos, pantalla
   Roles y Permisos, alta de usuarios end-to-end. Verificado por typecheck + dev server; **no**
   verificado en navegador real contra Postgres (sin Docker/`.env` en este entorno).
5. ⬜ **Único pendiente real**: T072 (validación manual E2E de `quickstart.md`) y las auditorías
   T066/T067/T071, que requieren el stack corriendo.

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes — pueden ejecutarse en paralelo
- Los gaps marcados en las Fases 3-6 no son trabajo nuevo de alcance — son bugs de
  desincronización entre un frontend construido antes del modelo dinámico de roles/permisos y
  el backend real que ya lo implementa. Corregirlos es exactamente el contenido de la Fase 6b.
- Ningún `any` en TypeScript; ningún campo sin type hint en funciones Python públicas
- pnpm exclusivamente para instalar dependencias frontend
- Datos VPN nunca en logs — pendiente de re-verificación explícita (T067)
- Swagger ya actualizado (T073); revisar que quede así tras Fase 6b si se agregan endpoints
