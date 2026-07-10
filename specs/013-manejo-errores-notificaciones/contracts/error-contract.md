# Contract: Respuesta estándar de error de la API

**Feature**: 013-manejo-errores-notificaciones | **Alcance**: TODOS los endpoints de la API

## Estructura

Toda respuesta con status HTTP ≥ 400 emitida por la API tiene cuerpo JSON:

```json
{
  "success": false,
  "message": "El ticket no está asignado a este proyecto",
  "code": "TICKET_NOT_ASSIGNED",
  "error": "ticket_not_assigned"
}
```

- `success`: siempre `false`.
- `message`: texto en español apto para el usuario final. El frontend lo muestra tal cual.
- `code`: identificador estable UPPER_SNAKE_CASE, apto para lógica programática (Principio VI).
- `error`: código snake_case legado (retrocompatibilidad). Deprecado; no usar en código nuevo.

## Códigos de estado HTTP

| Status | Uso | `code` por defecto (si la ruta no especifica) |
|--------|-----|-----------------------------------------------|
| 400 | Validación de negocio / datos inválidos | `BAD_REQUEST` |
| 401 | Token ausente/expirado (flujo de re-login del frontend; sin toast) | `UNAUTHORIZED` |
| 403 | Usuario autenticado sin permiso | `FORBIDDEN` |
| 404 | Recurso inexistente (o ruta inexistente) | `NOT_FOUND` |
| 405 | Método no permitido | `METHOD_NOT_ALLOWED` |
| 409 | Conflicto de estado (p. ej. duplicado) | `CONFLICT` |
| 422 | Payload sintácticamente válido pero semánticamente inválido | `VALIDATION_ERROR` |
| 500 | Error interno no controlado | `INTERNAL_ERROR` |

## Garantías

1. **Cobertura total**: el contrato lo aplica un normalizador global registrado en la app;
   ninguna ruta puede emitir un error JSON fuera de este contrato.
2. **Sin fuga de detalles internos**: las respuestas 500 por excepción no controlada llevan
   `message` genérico. Nunca stack traces, texto de excepción, SQL ni rutas internas
   (Constitución, Principio IV).
3. **Retrocompatibilidad**: rutas existentes que devuelven `{"error", "message"}` siguen
   funcionando sin cambios; el normalizador les añade `success` y `code`.
4. **401 especial**: estructura estándar igual, pero el frontend NO muestra notificación:
   conserva logout + redirección a /login.

## Comportamiento del frontend (consumidor)

| Situación | Notificación mostrada |
|-----------|----------------------|
| Error con `message` string no vacío | El `message` exacto del servidor |
| Error de red / timeout / cuerpo no JSON / sin `message` (genérico del frontend, ningún `message` del servidor llega) | "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo" |
| 500 no controlado (genérico del backend, SÍ llega como `message`) | "Ocurrió un error interno. Intenta de nuevo más tarde." (se muestra tal cual, no el genérico del frontend) |
| Status 401 | Ninguna (redirección a login) |
| Mensajes idénticos en < ~3 s | Una sola notificación |
