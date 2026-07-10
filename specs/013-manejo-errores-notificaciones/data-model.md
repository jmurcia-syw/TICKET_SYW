# Data Model: Manejo Global de Errores y Notificaciones

**Feature**: 013-manejo-errores-notificaciones | **Date**: 2026-07-10

Esta feature **no crea ni modifica tablas ni migraciones**. Los "modelos" son contratos de
comunicación en memoria.

## ApiErrorBody (contrato de respuesta de error — backend → frontend)

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `success` | boolean | Sí | Siempre `false` en errores. |
| `message` | string | Sí | Texto legible en español, apto para mostrar al usuario final. |
| `code` | string | Sí | Identificador estable UPPER_SNAKE_CASE (p. ej. `TICKET_NOT_ASSIGNED`). Derivado del campo legado `error` o del status HTTP. |
| `error` | string | Sí (legado) | Código snake_case existente (p. ej. `not_found`). Se conserva por retrocompatibilidad; deprecado a futuro. |

**Reglas de validación / derivación** (aplicadas por el normalizador global):

- Si la respuesta de la ruta ya trae `error` → `code = error.upper()`.
- Si no trae `error` ni `code` → `code` por defecto según status HTTP:
  `400 → BAD_REQUEST`, `401 → UNAUTHORIZED`, `403 → FORBIDDEN`, `404 → NOT_FOUND`,
  `405 → METHOD_NOT_ALLOWED`, `409 → CONFLICT`, `422 → VALIDATION_ERROR`,
  `5xx → INTERNAL_ERROR`.
- Si no trae `message` → mensaje genérico en español según status.
- Respuestas 500 por excepción no controlada: `message` SIEMPRE genérico
  ("Ocurrió un error interno. Intenta de nuevo más tarde."), nunca el texto de la excepción.
- Solo se normalizan respuestas JSON con status ≥ 400; las respuestas de éxito no se tocan.

## Tipo TypeScript (frontend)

```ts
interface ApiErrorBody {
  success: false
  message: string
  code: string
  error?: string  // legado
}
```

## Notificación visual de error (estado efímero de UI)

| Atributo | Valor |
|----------|-------|
| Texto | el `message` recibido en el ApiErrorBody (incluido el genérico del backend para 500), o el genérico propio del frontend si NO llega ningún `message` interpretable (ver nota) |
| Severidad | error |
| Duración | ~4 s (default antd `message.error`) |
| Dedupe | mensajes idénticos dentro de una ventana de ~3 s se muestran una sola vez |

**Nota — dos genéricos distintos, intencional (no duplicación)**: existen dos textos "algo
salió mal" con disparadores mutuamente excluyentes:
- **Genérico del backend** ("Ocurrió un error interno. Intenta de nuevo más tarde."): lo emite
  la API en todo 500 no controlado. El frontend lo muestra tal cual porque SÍ es un `message`
  interpretable (FR-003 + FR-005).
- **Genérico del frontend** ("Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo."):
  lo genera el propio interceptor cuando NO llega ningún `message` del servidor — error de red,
  timeout, CORS, cuerpo no JSON (FR-006). Nunca compite con el del backend: si hay respuesta con
  `message`, ese es el que se muestra.

No se persiste; no interactúa con la entidad `Notification` existente del sistema (campanita),
que es un concepto distinto (notificaciones de negocio persistidas).
