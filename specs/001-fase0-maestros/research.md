# Research: Fase 0 — Maestros

**Date**: 2026-06-29 | **Feature**: specs/001-fase0-maestros

---

## Decision 1: Cifrado de datos sensibles de clientes

**Decision**: pgcrypto (extension nativa de PostgreSQL) con AES-256 a nivel de columna, gestionado
en la Capa 2 (Infraestructura / SQLAlchemy). La clave de cifrado vive en variable de entorno del
backend, nunca en el repositorio ni en la base de datos.

**Rationale**: pgcrypto no agrega dependencias externas al proyecto (es una extension de PostgreSQL,
ya disponible en la imagen postgres:16-alpine). El cifrado en la Capa 2 significa que los datos
sensibles nunca llegan a la Capa 1 (Dominio) ni a la Capa 3 (API) en texto plano. Es transparente
para el resto de la aplicacion.

**Alternatives considered**:
- Cifrado en Capa 1 (Dominio): rechazado porque viola el principio de que el dominio no debe
  tener dependencias externas (la clave de cifrado es infraestructura, no dominio).
- SQLAlchemy-Utils EncryptedType: rechazado porque agrega una dependencia no aprobada en la
  Constitucion y hace el cifrado menos auditable.
- Vault / servicio externo de secretos: excesivo para esta escala y fase. Diferido a fase futura.

---

## Decision 2: Verificacion de estado activo del usuario en cada request JWT

**Decision**: Middleware `auth.py` en la Capa 3 (API) que, tras decodificar el JWT, consulta
`users.active` por el `user_id` del token. Si `active = false`, devuelve 401 y aborta el request.
La consulta se puede cachear en memoria por TTL corto (ej. 30 segundos) para no impactar
performance en endpoints de alta frecuencia.

**Rationale**: JWT sin estado por diseno no tiene mecanismo de revocacion. La verificacion en
middleware es el patron estandar para "soft invalidation" sin introducir una capa de sesiones.
El overhead es una consulta de primary key (O(1)), aceptable para la escala del proyecto.

**Alternatives considered**:
- Lista negra de tokens (blocklist): requiere Redis o tabla adicional y agrega complejidad.
  Rechazado en esta fase.
- Tokens de corta duracion (ej. 5 min) con refresh tokens: correcto en teoria, pero agrega
  complejidad de flujo de autenticacion. Diferido a revision de seguridad posterior.

---

## Decision 3: RBAC — Control de acceso basado en roles

**Decision**: Decorador `@require_role(*roles)` en `backend/api/middleware/rbac.py` aplicado
a cada endpoint de Flask-RESTX. El rol del usuario viene en el payload JWT. En frontend,
el componente `ProtectedRoute` en React lee el rol del store de autenticacion y redirige si
el rol no tiene acceso a la ruta.

**Rationale**: Centralizacion en la API (no en la UI) cumple con el Principio VI (AI-Native):
cualquier caller (humano via UI, agente IA, script interno) respeta las mismas reglas de acceso.
El frontend hace RBAC de navegacion para UX, pero nunca es la ultima linea de defensa.

**Alternatives considered**:
- RLS de PostgreSQL para RBAC: RLS es para aislamiento de datos por tenant/usuario, no para
  logica de roles de aplicacion. Se usa en combinacion, no como reemplazo.
- Middleware de RBAC en Capa 1 (Dominio): rechazado porque el rol es contexto de request
  (infraestructura), no logica de negocio pura.

---

## Decision 4: Unicidad de nombre de cliente y email de recurso

**Decision**: Restriccion UNIQUE en la base de datos (nivel PostgreSQL) mas validacion en
`domain/services/` antes del INSERT. La validacion en el servicio del dominio devuelve un
error de negocio descriptivo; la restriccion en DB es la red de seguridad.

**Rationale**: Doble validacion (dominio + DB) evita race conditions y da errores descriptivos
al usuario. La validacion en dominio puede ocurrir antes de abrir la transaccion.

---

## Decision 5: Regla del ultimo Admin

**Decision**: `role_service.py` en el dominio verifica, antes de ejecutar un cambio de rol o
desactivacion, si el usuario afectado es el unico Admin activo. Si es asi, la operacion es
rechazada con un error de negocio especifico.

**Rationale**: Esta es una regla de negocio pura (no de infraestructura), correctamente ubicada
en la Capa 1 (Dominio). No requiere logica adicional en la API ni en el frontend.

---

## Decision 6: Paginacion de listas

**Decision**: Paginacion server-side con parametros `page` (default 1) y `page_size` (default 20,
max 100). Los endpoints devuelven `{ items: [...], total: N, page: N, page_size: N }`.
El componente `Table` de Ant Design se conecta a esta paginacion nativamente.

**Rationale**: Con hasta 500 registros en esta fase, la paginacion es preventiva pero necesaria
para no degradar performance. Ant Design Table soporta paginacion server-side sin componentes
adicionales.

---

## Decision 7: Roles dinamicos y permisos granulares (FR-015, FR-015b)

**Decision**: Tablas `roles` y `permissions` (modulo + accion) con tabla puente `role_permissions`
many-to-many. `users.role_id` es FK a `roles.id` (no un enum fijo). Se siembran 4 roles iniciales
(Admin, Coordinador, QM, Resolutor) via migracion, pero Admin puede crear roles adicionales desde
`/api/roles` y ajustar permisos via `PUT /api/roles/{id}/permissions` (reemplazo total de la lista).
El rol Admin no puede desactivarse (`RoleAdminService.validate_deactivation`); un permiso no puede
eliminarse si esta asignado a algun rol (`validate_permission_delete`).

**Rationale**: FR-015/FR-015b exigen roles dinamicos, no una lista fija de 4. Modelar `role_id`
como FK desde el inicio evita una migracion de ruptura posterior cuando se agregue un quinto rol.
El middleware RBAC sigue centralizado en la API (Decision 3), solo cambia la fuente del rol: antes
un enum de 4 valores, ahora una fila de `roles` con su set de permisos.

**Alternatives considered**:
- Enum fijo de 4 roles con permisos hardcodeados en el decorador `@require_role`: rechazado porque
  no cumple FR-015 (roles dinamicos) ni FR-015b (permisos editables desde UI).

---

## Decision 8: Login provisional usuario/contraseña (FR-022b)

**Decision**: Endpoint `POST /api/auth/login` que acepta `username_or_email` + `password`,
verifica el hash (`AuthService.verify_password`) contra `users.password_hash`, y emite el mismo
JWT que `POST /api/auth/google`. Coexiste sin reemplazar el flujo OAuth2; un usuario puede no tener
`password_hash` (solo login Google) o tenerlo (ambos metodos disponibles). La respuesta de ambos
endpoints tiene la misma forma (`{ access_token, user }`) para que el frontend no distinga el origen
del login tras la autenticacion.

**Rationale**: Mismo contrato de respuesta para ambos metodos de login simplifica el frontend
(un solo `authStore`, sin lógica condicional post-login). El hash de contraseña vive solo en
`users.password_hash`, nunca en texto plano, cumpliendo FR-022b.

**Alternatives considered**:
- Tabla separada de credenciales provisionales: rechazado, agrega complejidad sin beneficio dado
  que `password_hash` nullable en `users` ya modela "login provisional opcional" correctamente.

---

## Decision 9: Eliminacion del bypass de autenticacion y datos semilla (FR-022c, FR-022d)

**Decision**: Se elimina el `DEV_SKIP_AUTH` que inyectaba un usuario Admin falso sin login real.
La migracion `009_roles_permissions_login.py` siembra los 4 roles y, ademas, 4 usuarios de prueba
(`admin@sywork.net`, `coordinador@sywork.net`, `qm@sywork.net`, `resolutor@sywork.net`) con una
contraseña provisional **compartida**, generada aleatoriamente con `secrets.token_urlsafe` en el
momento de correr la migracion e impresa una sola vez en el log — nunca persistida en el repo.

**Rationale**: Con login provisional real disponible (Decision 8), mantener un bypass de
desarrollo ya no tiene justificacion y viola FR-022c (ningun mecanismo debe omitir la
autenticacion). Generar la contraseña en el momento de la migracion (en vez de hardcodearla)
evita que una contraseña fija termine commiteada en el historial de git.

**Alternatives considered**:
- Contraseña fija documentada en un README de desarrollo: rechazado, es indistinguible de un
  secreto hardcodeado en el repo si el README se commitea.
- Una contraseña distinta por usuario semilla: mas seguro pero innecesario para datos de prueba
  de Fase 0 con ~4 cuentas; se documenta como limitacion aceptada, no como pendiente.
