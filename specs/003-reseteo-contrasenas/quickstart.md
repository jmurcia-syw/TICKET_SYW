# Quickstart: Reseteo de Contraseñas y Credenciales Semilla Estables

**Prerequisitos**: `docker compose up -d` (Postgres + backend + frontend), migración
`014_password_reset_tokens.py` aplicada, variables `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/
`SMTP_PASSWORD`/`SMTP_FROM` configuradas en `.env` (para el Escenario 3). Referencias:
[contracts/auth-password-reset.md](contracts/auth-password-reset.md),
[data-model.md](data-model.md).

Verificación rápida del arranque:

```bash
docker exec sywork_backend alembic current          # → 014 (head)
docker exec sywork_backend python -m pytest tests/ -q
```

---

## Escenario 1 — Credenciales semilla estables en Desarrollo (US2)

1. `docker compose down -v && docker compose up --build` en dos máquinas/entornos distintos con
   `FLASK_ENV` sin definir o distinto de `production`.
2. Confirmar que `admin` / `coordinador` / `qm` / `resolutor` inician sesión con la misma
   contraseña en ambos entornos (la documentada en `docs/credenciales_dev.txt`, decodificando el
   base64).
3. Repetir con `FLASK_ENV=production` → la contraseña impresa en el log del backend debe ser
   distinta en cada corrida (aleatoria), nunca la fija de Desarrollo.

## Escenario 2 — Reseteo de contraseña por Admin (US1)

1. Login como `admin`. Ir a la pantalla de Usuarios.
2. Sobre un usuario real (no semilla) activo, usar la acción "Resetear contraseña" → confirmar.
3. Verificar: aparece el modal con la nueva contraseña temporal, con la advertencia de que no se
   vuelve a mostrar.
4. Cerrar sesión, iniciar sesión como ese usuario con la contraseña mostrada → acceso exitoso.
5. Repetir el reseteo apuntando a un `id` de usuario inexistente vía `curl` directo a
   `PATCH /api/users/{id}/reset-password` → `404`.

## Escenario 3 — Auto-recuperación por email (US3)

1. Desde `/login`, click en "¿Olvidaste tu contraseña?", ingresar el correo de una cuenta activa
   existente.
2. Verificar: la respuesta en pantalla es el mensaje genérico de éxito.
3. Repetir con un correo que no existe en el sistema → mismo mensaje genérico, sin diferencia
   observable.
4. Abrir el correo recibido, seguir el enlace a `/reset-password?token=...`, definir una
   contraseña nueva → confirmar redirección a `/login` e inicio de sesión exitoso con la
   contraseña nueva.
5. Reutilizar el mismo enlace una segunda vez → rechazado (`400`, mensaje genérico).
6. Solicitar un enlace nuevo, desactivar la cuenta antes de usarlo (como Admin), luego intentar
   completar el cambio de contraseña con el enlace aún vigente → rechazado.
