# Research: Reseteo de Contraseñas y Credenciales Semilla Estables

Sin `[NEEDS CLARIFICATION]` pendientes en `spec.md` — las decisiones de alcance ya se validaron
con el usuario en la sesión de brainstorming previa a este plan. Este documento fija las
decisiones técnicas concretas que implementan esas decisiones de alcance.

## 1. Contraseña temporal para reseteo por Admin

**Decision**: Reutilizar exactamente el mismo mecanismo ya usado al crear un usuario
(`backend/api/routes/users.py:149`): `secrets.token_urlsafe(9)`, hasheado con
`AuthService.hash_password` (scrypt vía `werkzeug.security.generate_password_hash`).

**Rationale**: Cero código nuevo de generación/hash; el frontend ya tiene el modal "Contraseña
provisional generada" listo para reutilizar sin cambios.

**Alternatives considered**: Generar una contraseña "memorable" (palabras+número) — rechazado,
no aporta valor sobre el patrón ya validado y usado hoy en producción.

## 2. Contraseña fija para usuarios semilla en Desarrollo

**Decision**: Constante `SEED_PASSWORD_DEV = "SyWork_Dev2026!"` en la migración 009, usada
cuando `os.environ.get("FLASK_ENV") != "production"`; en producción se mantiene
`secrets.token_urlsafe(9)` sin cambios.

**Rationale**: Es la causa raíz reportada por el usuario (contraseña distinta e irrecuperable en
cada instalación de Desarrollo). Condicionar por `FLASK_ENV` reutiliza una variable que el
proyecto ya define y pasa por `docker-compose.yml` (`environment: FLASK_ENV`), sin agregar una
variable nueva solo para esto.

**Alternatives considered**: Nueva variable de entorno `SEED_ADMIN_PASSWORD` configurable —
evaluada y descartada por el usuario a favor de un valor fijo "quemado" en el código, para que no
dependa de que alguien configure el `.env` correctamente en cada instalación nueva.

## 3. Documentación de credenciales semilla

**Decision**: `docs/credenciales_dev.txt`, tabla con columnas Usuario/email, Rol, Contraseña
(base64). Contraseña codificada con `base64.b64encode` estándar de Python
(`SyWork_Dev2026!` → `U3lXb3JrX0RldjIwMjYh`).

**Rationale**: Formato solicitado explícitamente por el usuario, con conocimiento expreso de que
base64 no es cifrado y de que el archivo queda versionado en Git (ver Complexity Tracking en
`plan.md`).

**Alternatives considered**: Guardar la contraseña real (sin codificar) — rechazada por el propio
usuario a favor de al menos una capa de ofuscación visual. Guardar solo en `.env` (no
versionado) — rechazada porque el usuario quiere que quede documentada "para subirlo a futuro".

## 4. Token de recuperación por email

**Decision**: Columna `reset_token` (texto, único, nullable) + `reset_token_expires_at`
(timestamptz, nullable) directamente en `users`, generado con `secrets.token_urlsafe(32)`.
Expiración: 30 minutos desde su emisión. Se borra (`NULL`) al usarse con éxito o al emitirse uno
nuevo (una solicitud nueva invalida cualquier token anterior de esa cuenta).

**Rationale**: Un usuario solo necesita un token de recuperación activo a la vez — no hace falta
una tabla aparte con historial. Guardar en texto plano (no hasheado) es aceptable porque es de
un solo uso, expira en 30 min, y su exposición no compromete la contraseña real del usuario
(distinto del `password_hash`, que sí exige hash irreversible).

**Alternatives considered**: JWT autocontenido como token de recuperación (sin persistir en DB)
— rechazado porque no permite invalidarlo server-side al usarlo una vez ni al desactivar la
cuenta a mitad de camino, que son requisitos explícitos de la spec (FR-009, FR-012). Tabla
separada `password_reset_requests` con historial — rechazada por sobre-ingeniería frente al
único caso de uso (un token activo por usuario).

## 5. Envío de correo

**Decision**: `smtplib.SMTP` + `email.mime.text.MIMEText` (stdlib de Python, sin dependencia
nueva), configurado con variables de entorno `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD`, `SMTP_FROM` — mismo mecanismo de configuración que `GOOGLE_CLIENT_ID`/
`JWT_SECRET` ya usan en `docker-compose.yml`. Envío síncrono dentro del request de
`POST /api/auth/forgot-password`.

**Rationale**: Cumple la decisión del usuario de usar una cuenta de correo personal/provisional
(Gmail u otro proveedor SMTP estándar) sin dar de alta un servicio transaccional de pago. Es
stdlib, por lo que no requiere aprobación de dependencia nueva (Principio V).

**Alternatives considered**: Celery + Redis (ya declarado como stack aprobado del proyecto para
"emails automaticos") — evaluado, mejor arquitectura a largo plazo, pero requiere levantar
infraestructura (Redis, worker) que hoy no existe en `docker-compose.yml`; queda documentado como
desviación aceptada en `plan.md` § Complexity Tracking, migrable después sin romper el contrato
público. Servicio transaccional (SendGrid/SES) — rechazado por el usuario, quiere evitar altas de
cuenta en un proveedor de pago para esta fase.

## 6. Enforcement del endpoint de reseteo por Admin

**Decision**: `PATCH /api/users/<id>/reset-password`, agregado a la lista de clases decoradas
con `enforce_module("users")` en `users.py:297`. El mapeo existente de `_action_for_request()`
(`backend/api/middleware/rbac.py:54`) ya traduce `PATCH` (sin sufijo `/activate`/`/deactivate`) a
la acción `edit` — mismo permiso que cambiar de rol (`/role`), sin necesidad de dar de alta una
acción de permiso nueva.

**Rationale**: Cero cambios al modelo de permisos/roles; el rol Admin ya tiene `users:edit`
sembrado en la migración 009.

**Alternatives considered**: Acción de permiso dedicada `users:reset_password` — rechazada por
innecesaria, ya que en este proyecto "quién puede resetear contraseña" siempre coincide con
"quién puede editar usuarios" (mismos 4 roles semilla, mismo perfil de permisos).
