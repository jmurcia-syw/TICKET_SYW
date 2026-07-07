# API Contract: Reseteo de Contraseñas

**Auth**: `PATCH /api/users/{id}/reset-password` exige JWT Bearer + permiso `users:edit` (FR-022,
mismo enforcement que el resto de `/api/users`). `POST /api/auth/forgot-password` y
`POST /api/auth/reset-password` son **públicas** (sin JWT), igual que `POST /api/auth/login` —
el usuario todavía no está autenticado en ese punto del flujo.

---

## Reseteo por Admin

### PATCH /api/users/{id}/reset-password — permiso `users:edit`

Sin body. Genera una nueva contraseña temporal para el usuario `{id}` y la devuelve una única vez.

**Response 200**:
```json
{ "id": "uuid", "provisional_password": "texto-plano-temporal" }
```

**Response 404**: `{ "error": "not_found", "message": "Usuario no encontrado" }`

**Response 401/403**: payload genérico, mismo patrón que el resto de `/api/users` (FR-023).

---

## Auto-servicio "olvidé mi contraseña"

### POST /api/auth/forgot-password — pública

Body: `{ "email": "correo@sywork.net" }`

Si existe una cuenta **activa** con ese correo, genera un `reset_token` nuevo (invalida
cualquiera anterior de esa cuenta), lo guarda con expiración de 30 minutos, y envía un correo con
un enlace a `{FRONTEND_URL}/reset-password?token=...`.

**Response 200 (siempre, exista o no la cuenta, esté activa o no)**:
```json
{ "message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña." }
```

No hay respuesta 4xx para esta ruta salvo `400` si el body no trae `email`.

### POST /api/auth/reset-password — pública

Body: `{ "token": "...", "new_password": "..." }`

Si el token existe, no expiró y la cuenta asociada está activa: actualiza `password_hash`, borra
el `reset_token` (queda `NULL`) y responde `200`.

**Response 200**: `{ "message": "Contraseña actualizada correctamente" }`

**Response 400** (token inexistente, expirado, ya usado, o cuenta inactiva — mismo mensaje
genérico en los 4 casos, no se distingue el motivo):
```json
{ "error": "invalid_token", "message": "El enlace no es válido o ya expiró" }
```

---

## Enforcement (consistente con FR-022 / notifications-catalogs.md)

- `POST /api/auth/forgot-password` y `POST /api/auth/reset-password` se agregan a la lista de
  rutas públicas exceptuadas del JWT obligatorio (junto a `/api/auth/login`, `/api/auth/google`,
  `GET /health/`).
- `PATCH /api/users/{id}/reset-password` sigue el enforcement estándar ya vigente sobre
  `/api/users/*` — sin excepciones nuevas al mapa de permisos.
