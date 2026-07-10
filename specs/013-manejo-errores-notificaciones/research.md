# Research: Manejo Global de Errores y Notificaciones

**Feature**: 013-manejo-errores-notificaciones | **Date**: 2026-07-10

## Estado actual verificado en el código

- **Backend**: Flask + Flask-RESTX (`create_app()` en `backend/app.py`, ~17 namespaces en
  `backend/api/routes/`). Existe una convención de-facto: las rutas devuelven errores inline
  como `{"error": "<código_snake>", "message": "<texto>"}, <status>` (~285 ocurrencias en 17
  archivos). `backend/api/routes/_shared.py` ya expone `error_model()` (esquema Swagger
  `{error, message}`) y `server_error()` (500 genérico con logging).
- **Frontend**: `frontend/src/services/apiClient.ts` (axios) con interceptor de request (JWT)
  y de response que solo maneja 401 (logout + redirect a /login). Ant Design 5.24 con
  `ConfigProvider` en `App.tsx`. Algunas páginas leen `error.response?.data` manualmente,
  la mayoría no muestra nada.

## Decisión 1: Normalización backend vía hook global, no edición por endpoint

- **Decision**: Crear `backend/api/errors.py` con (a) un hook `after_request` que, para toda
  respuesta JSON con status ≥ 400, garantice los campos `success: false`, `message` y `code`
  (derivando `code` = campo `error` existente en UPPER_SNAKE, o un código por defecto según el
  status HTTP: `BAD_REQUEST`, `FORBIDDEN`, `NOT_FOUND`, `INTERNAL_ERROR`, etc.), conservando el
  campo legado `error`; y (b) manejadores globales de excepciones (`HTTPException` y
  `Exception`) que produzcan la misma estructura, con 500 genérico sin detalles internos.
  Ambos se registran en `create_app()`.
- **Rationale**: Cumple el alcance "todos los endpoints" con un único punto de cambio y
  respeta el Principio VII (los ~285 returns de error existentes quedan intactos). El
  manejador de `Exception` refuerza el Principio IV (nunca stack traces).
- **Alternatives considered**:
  - Editar cada return de error en los 17 módulos → rechazado: viola la directriz de no
    refactorizar controladores y es masivo/propenso a error.
  - Solo `@api.errorhandler` de Flask-RESTX → insuficiente: no intercepta los returns
    normales `(dict, status)` de las rutas, solo excepciones.

## Decisión 2: Estructura estándar como superconjunto retrocompatible

- **Decision**: La respuesta estándar es
  `{ "success": false, "message": "<texto es-ES>", "code": "<UPPER_SNAKE>", "error": "<snake legado>" }`.
  `code` es el contrato nuevo; `error` se conserva temporalmente para no romper las páginas
  que hoy leen `error.response?.data`.
- **Rationale**: Cero rupturas en frontend existente; migración transparente. El campo `code`
  estable en UPPER_SNAKE cumple el requerimiento del usuario y el Principio VI (máquina-legible).
- **Alternatives considered**: Reemplazar `error` por `code` de golpe → rechazado: requeriría
  tocar páginas fuera del alcance de la sesión.

## Decisión 3: Captura centralizada en el interceptor axios existente

- **Decision**: Extender el interceptor de response de `apiClient.ts`: para todo error con
  status ≠ 401, extraer `error.response?.data?.message` (string no vacío) y notificar; si no
  hay mensaje interpretable (error de red, cuerpo no JSON, campo ausente), notificar el
  genérico "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo". El 401 conserva
  exactamente su flujo actual (logout + redirect, sin toast). El interceptor sigue haciendo
  `Promise.reject(error)` para que los `catch` locales existentes sigan funcionando.
- **Rationale**: Un único punto de captura (FR-004) sin tocar páginas; las páginas que ya
  muestran mensajes propios no se rompen.
- **Alternatives considered**: Wrapper por servicio o error boundaries de React → rechazados:
  requieren cambios por pantalla y no capturan errores de datos asíncronos de forma uniforme.

## Decisión 4: Notificación con `message` de Ant Design 5 + montaje de `<App>`

- **Decision**: Crear `frontend/src/services/errorNotifier.ts` que muestre toasts de error
  usando el sistema de mensajes de antd 5. Para que la API de mensajes respete el tema/locale
  del `ConfigProvider`, se monta el componente `App` de antd (`<AntApp>`) dentro del
  `ConfigProvider` en `App.tsx` y el notifier usa la instancia estática registrada por él.
- **Rationale**: Reutiliza la librería aprobada (Principio V); toast es no intrusivo y visible
  de inmediato (SC-001/SC-003). El helper vive en `services/` (Principio II).
- **Alternatives considered**: `notification` de antd (más pesado, para contenido rico) o un
  banner propio → rechazados: `message` es el patrón estándar para feedback efímero de error.

## Decisión 5: Dedupe de notificaciones por contenido + ventana temporal

- **Decision**: El notifier colapsa duplicados usando el `key` de antd derivado del texto del
  mensaje más una ventana de supresión de ~3 segundos (un mapa `texto → timestamp` en el
  módulo). Mensajes idénticos dentro de la ventana se muestran una sola vez (FR-008).
- **Rationale**: Cubre el caso "dashboard con varias llamadas fallando a la vez" sin estado
  global nuevo (no requiere Zustand; es estado efímero de UI local al módulo).
- **Alternatives considered**: Store Zustand de notificaciones → rechazado: sobreingeniería
  para estado efímero de un solo módulo.

## Decisión 6: Testing ultra-limitado (Principio VII)

- **Decision**: Un archivo `backend/tests/api/test_error_contract.py` con tests del normalizador
  usando el test client de Flask sobre endpoints/handlers representativos: 400, 403, 404, 500
  (excepción no controlada) y verificación de no-exposición de detalles internos. Máximo 5-10
  casos/mocks en total; sin fixtures masivas de BD (el normalizador no toca BD). No se ejecuta
  la suite completa: solo `pytest tests/api/test_error_contract.py` (desde el contenedor).
- **Rationale**: Cumple la restricción constitucional y del spec; el normalizador es lógica
  pura de respuesta HTTP, no necesita datos reales.
- **Alternatives considered**: Tests e2e por módulo de rutas → rechazado: ejecución masiva
  prohibida; la verificación por módulo se hace manualmente vía quickstart (3 casos críticos).
