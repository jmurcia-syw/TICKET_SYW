# Data Model: Reseteo de Contraseñas y Credenciales Semilla Estables

## `users` (modificación de tabla existente)

Se agregan 2 columnas nuevas vía migración `014_password_reset_tokens.py` (revisión posterior a
`013_dynamic_record_type.py`). No se elimina ni renombra ninguna columna existente.

| columna | tipo | notas |
|---|---|---|
| `reset_token` | text, nullable, único | Token de un solo uso para recuperación de contraseña. `NULL` cuando no hay una solicitud activa. Se genera con `secrets.token_urlsafe(32)`. Se limpia (`NULL`) al usarse con éxito o al emitirse una solicitud nueva para la misma cuenta (invalida la anterior). |
| `reset_token_expires_at` | timestamptz, nullable | Momento a partir del cual `reset_token` deja de ser válido (emisión + 30 minutos). `NULL` junto con `reset_token`. |

Columnas ya existentes relevantes para esta feature (sin cambios): `password_hash` (text,
nullable — se sobreescribe tanto en el reseteo por Admin como en la recuperación por email),
`active` (boolean — una cuenta inactiva no puede completar la recuperación aunque el token siga
vigente), `email` (text, único).

### Reglas de validez de `reset_token` (viven en `AuthService`, Capa 1 — Principio I)

Un `reset_token` es válido para completar una recuperación si, y solo si:
1. Coincide exactamente con el `reset_token` guardado para esa cuenta.
2. `reset_token_expires_at` es posterior al momento actual.
3. La cuenta (`users.active`) está activa.

Si cualquiera de las 3 condiciones falla, la recuperación se rechaza con el mismo error genérico
(sin distinguir cuál falló, mismo patrón que el login con credenciales inválidas).

## Sin tablas nuevas

Se evaluó una tabla separada `password_reset_requests` (con historial de solicitudes) y se
descartó — ver `research.md` § 4. Una cuenta solo necesita, como máximo, una solicitud de
recuperación activa a la vez.

## Datos semilla (modificación de la migración 009 existente)

No se agregan filas nuevas. Se modifica el valor de la contraseña generada para las 4 filas
semilla ya existentes (`admin`, `coordinador`, `qm`, `resolutor`) — ver `research.md` § 2.
