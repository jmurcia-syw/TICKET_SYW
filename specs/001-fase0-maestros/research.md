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
