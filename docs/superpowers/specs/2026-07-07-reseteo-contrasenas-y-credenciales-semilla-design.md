# Reseteo de Contraseñas y Credenciales Semilla — Diseño

**Fecha**: 2026-07-07
**Estado**: Aprobado, pendiente de plan de implementación

## Contexto

Al instalar el proyecto en un equipo nuevo, la migración [009_roles_permissions_login.py](../../../backend/infra/migrations/versions/009_roles_permissions_login.py) genera una contraseña provisional **aleatoria** (`secrets.token_urlsafe(9)`) compartida por los 4 usuarios semilla (`admin`, `coordinador`, `qm`, `resolutor`) y la imprime una única vez en el log del contenedor `backend`. Si esos logs se pierden o rotan, la contraseña es irrecuperable (el hash `scrypt` guardado en `users.password_hash` no es reversible).

Esto motivó tres piezas relacionadas, decididas en conjunto:

1. Que las credenciales semilla dejen de cambiar en cada instalación (Desarrollo).
2. Que un Admin pueda resetear la contraseña de cualquier usuario **real** (no semilla) sin depender de logs.
3. Que a futuro el propio usuario pueda recuperar su contraseña por correo, sin depender de un Admin.

## Decisiones de alcance (confirmadas con el usuario)

- La contraseña semilla fija es **solo para Desarrollo**; en producción (`FLASK_ENV=production`) la migración sigue generando una aleatoria por instalación, como hoy.
- Las credenciales semilla (usuario/email/rol/contraseña en base64) se documentan en un `.txt` bajo `docs/`, **con conocimiento explícito de que quedará versionado en Git** — decisión del usuario, no un descuido: se le informó que base64 no es cifrado y que `docs/` está bajo control de versiones, y confirmó que quiere subirlo así de todas formas.
- El reseteo por Admin sigue el mismo patrón ya existente de "contraseña provisional mostrada una sola vez" (usado hoy al crear un usuario).
- El auto-servicio por email usa SMTP con una cuenta personal/provisional del usuario (no un servicio transaccional de pago), configurado por variables de entorno — las credenciales reales de esa cuenta se configuran directo en `.env` al implementar, nunca se documentan en archivos versionados.
- Mientras se trabaja en el endpoint `/api/users`, se usa el flag `DEV_SKIP_AUTH=true` ya existente en [auth.py](../../../backend/api/middleware/auth.py) — sin cambios de código para desactivar el enforcement.

## 0. Contraseña fija para usuarios semilla (Desarrollo)

- En la migración 009, `provisional_password = secrets.token_urlsafe(9)` pasa a ser condicional:
  ```python
  import os
  SEED_PASSWORD_DEV = "SyWork_Dev2026!"
  provisional_password = SEED_PASSWORD_DEV if os.environ.get("FLASK_ENV") != "production" else secrets.token_urlsafe(9)
  ```
- El resto de la migración (hash, insert, print) no cambia.
- Se crea `docs/credenciales_dev.txt` con la tabla de los 4 usuarios semilla, contraseña codificada en base64 (`SyWork_Dev2026!` → `U3lXb3JrX0RldjIwMjYh`):

  ```
  Usuario/email                         | Rol          | Contraseña (base64)
  admin / admin@sywork.net              | Admin        | U3lXb3JrX0RldjIwMjYh
  coordinador / coordinador@sywork.net  | Coordinador  | U3lXb3JrX0RldjIwMjYh
  qm / qm@sywork.net                    | QM           | U3lXb3JrX0RldjIwMjYh
  resolutor / resolutor@sywork.net      | Resolutor    | U3lXb3JrX0RldjIwMjYh
  ```

## 1. Reseteo de contraseña por Admin

- Nuevo endpoint `PATCH /api/users/<id>/reset-password` en [users.py](../../../backend/api/routes/users.py), agregado a la lista de clases con `enforce_module("users")` (línea ~297) — igual que `/role`, `/deactivate`, `/activate`. Como el método es `PATCH` y la ruta no termina en `/activate`/`/deactivate`, el enforcement existente lo mapea automáticamente a la acción `edit` (mismo permiso que cambiar de rol, sin nueva acción que dar de alta).
- Lógica: genera `secrets.token_urlsafe(9)`, lo hashea con `AuthService.hash_password` (ya existente), actualiza `password_hash` del usuario vía `UserRepository`, responde `{"id": ..., "provisional_password": "..."}` — mismo shape que la creación de usuario.
- No hay invalidación de tokens JWT existentes (son *stateless*; expiran solos a las 8h, igual que ya ocurre al desactivar un usuario).

### Frontend
- Nuevo botón de acción (icono llave) en la columna "Acciones" de [UsersPage.tsx](../../../frontend/src/pages/UsersPage.tsx:139), visible con el mismo permiso `users:edit` que ya controla `canChangeRole`.
- Confirmación previa reutilizando `ConfirmationModal` (mismo patrón que "Desactivar").
- Al confirmar, se reutiliza el modal "Contraseña provisional generada" que ya existe (líneas 186-203) seteando `provisionalPassword` con la respuesta del nuevo endpoint — sin UI nueva que construir.

## 2. Auto-servicio "olvidé mi contraseña"

### Backend
- Nueva migración: agrega a `users` las columnas `reset_token` (text, nullable, único) y `reset_token_expires_at` (timestamptz, nullable).
- `POST /api/auth/forgot-password` (pública, sin JWT): recibe `{email}`. Si existe un usuario activo con ese email, genera un token de un solo uso (`secrets.token_urlsafe`), lo guarda con expiración de 30 minutos, y envía un correo con un link `https://.../reset-password?token=...`. **Responde siempre el mismo mensaje de éxito genérico**, exista o no la cuenta, para no filtrar qué correos están registrados.
- `POST /api/auth/reset-password` (pública, sin JWT): recibe `{token, new_password}`. Si el token es válido y no expiró, actualiza `password_hash`, invalida el token (lo borra) y responde `200`. Si el token no existe o expiró: `400` genérico.
- Envío de correo vía `smtplib` estándar de Python, configurado con variables de entorno: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. Sin librería nueva de terceros.

### Frontend
- Link "¿Olvidaste tu contraseña?" en [LoginPage.tsx](../../../frontend/src/pages/LoginPage.tsx:76), debajo del formulario de login.
- Formulario simple (solo email) que llama a `/api/auth/forgot-password` y muestra el mensaje genérico de éxito.
- Pantalla nueva en la ruta `/reset-password` que lee `?token=` de la URL, pide la nueva contraseña (con confirmación) y llama a `/api/auth/reset-password`; en éxito redirige a `/login`.

## Manejo de errores y casos borde

- Reseteo por Admin sobre un usuario inexistente → `404`, mismo patrón que las demás rutas de `users`.
- `forgot-password` con email inexistente → `200` genérico igualmente (no se revela si el correo existe).
- `reset-password` con token expirado o ya usado → `400` genérico, sin distinguir el motivo.
- Un usuario desactivado no puede completar `reset-password` aunque el token sea válido (se valida `user.active` igual que en login).
- La contraseña semilla fija (`SyWork_Dev2026!`) nunca se usa si `FLASK_ENV=production` — la migración sigue generando aleatoria en ese caso, evitando que una instalación productiva quede con credenciales públicas conocidas.

## Testing

Mismo patrón que la suite ya existente en `backend/tests/`:
- **Unitarios de dominio**: generación/verificación de hash, validación de expiración de `reset_token`.
- **Integración de API**: reseteo por Admin (200, 404, permisos), `forgot-password` (siempre 200, con y sin email existente), `reset-password` (200 con token válido, 400 con token expirado/inexistente/ya usado, rechazo si el usuario está inactivo).

## Fuera de alcance (explícito)

- Servicio transaccional de email de pago (SendGrid/SES) — se deja como posible mejora futura, hoy es SMTP simple.
- Rate limiting sobre `forgot-password` — no se implementa en esta fase (riesgo de abuso queda documentado, no mitigado).
- Invalidación activa de JWTs existentes al resetear contraseña — quedan vigentes hasta su expiración natural (8h), igual que al desactivar un usuario hoy.
- Cambiar el mecanismo de auth de Google OAuth — no se toca.
