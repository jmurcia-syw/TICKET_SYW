# Implementation Plan: Manejo Global de Errores y Notificaciones (API a Frontend)

**Branch**: `develp_Jp` | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-manejo-errores-notificaciones/spec.md`

## Summary

Hoy los fallos de la API no producen feedback visual en el frontend. La solución tiene dos
piezas, ambas centralizadas para cubrir TODOS los endpoints sin refactorizar controladores
(Principio VII):

1. **Backend**: un normalizador global de respuestas de error (hook `after_request` +
   manejadores de excepciones no controladas a nivel de aplicación Flask) que garantiza que
   toda respuesta 4xx/5xx salga con la estructura estándar
   `{ "success": false, "message": <texto>, "code": <CÓDIGO> }`, aprovechando la convención
   de-facto ya existente `{error, message}` presente en los ~17 módulos de rutas
   (se conserva el campo legado `error` por compatibilidad).
2. **Frontend**: extensión del interceptor de respuestas de `apiClient.ts` (axios) para
   capturar todo error ≠ 401, extraer `message` (o usar el genérico) y mostrarlo con el
   sistema de notificaciones de Ant Design 5, con colapso de duplicados.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript strict + React 19 (frontend)

**Primary Dependencies**: Flask + Flask-RESTX (backend, ya aprobados); axios + Ant Design 5
(frontend, ya aprobados). **Cero dependencias nuevas** (Principio V).

**Storage**: N/A — esta feature no persiste datos ni toca el modelo de datos.

**Testing**: pytest (backend: test del normalizador de errores); no se añade infraestructura
de testing frontend nueva. Restricción Principio VII: solo tests de lo modificado, máx. 5-10
mocks por test, sin ejecución masiva de la suite.

**Target Platform**: Web (frontend Vite/React servido en navegador; backend Flask en Docker).

**Project Type**: Web application (backend + frontend existentes).

**Performance Goals**: El normalizador `after_request` añade procesamiento solo a respuestas
de error (status ≥ 400); impacto nulo en respuestas exitosas.

**Constraints**:
- NO refactorizar la lógica interna de los controladores (Principio VII / directriz del spec):
  el normalizador opera sobre la respuesta ya construida; los ~285 `return {"error":...}` de
  las rutas quedan intactos.
- Conservar el comportamiento 401 actual (logout + redirección a /login) sin toast adicional.
- Errores 500 nunca exponen stack traces ni detalles internos (Principio IV).

**Scale/Scope**: ~17 módulos de rutas backend cubiertos por un único normalizador; 1 archivo
de interceptor + 1 helper de notificación en frontend; verificación end-to-end en 3 casos
críticos (ticket no asignado, sin permisos, proyecto no encontrado).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|-----------|-----------|--------|
| I. API-First | El contrato de error se documenta en `contracts/error-contract.md` antes de implementar. No se altera lógica de negocio ni contratos de éxito. | ✅ PASS |
| II. Clean Architecture | Normalizador vive en Capa 3 (`backend/api/`), no toca dominio ni infra. Interceptor y notificador en `frontend/src/services/`; componentes siguen "tontos". | ✅ PASS |
| III. Tipado estricto | Tipos TS explícitos para la respuesta de error (`ApiErrorBody`); se usa `AxiosError` tipado, sin `any`. Type hints en el normalizador Python. | ✅ PASS |
| IV. Seguridad en profundidad | La feature REFUERZA este principio: manejador global de excepciones garantiza 500 sin stack traces/SQL en todos los endpoints. RLS/JWT sin cambios. | ✅ PASS |
| V. Gobernanza de librerías | Cero dependencias nuevas: axios y antd 5 ya aprobados; backend usa solo Flask stdlib. | ✅ PASS |
| VI. AI-Native | Campo `code` estable en UPPER_SNAKE (derivado del `error` snake_case existente) hace los errores máquina-legibles para agentes futuros. | ✅ PASS |
| VII. Alcance de sesión y testing | Enfoque "wrap, don't refactor": controladores intactos. Tests nuevos limitados al normalizador/interceptor con ≤ 5-10 mocks; sin ejecución masiva de suite. | ✅ PASS |

**Post-Phase 1 re-check**: ✅ PASS — el diseño final (research.md Decisiones 1-5) no introduce
violaciones; no se requiere Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/013-manejo-errores-notificaciones/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones de diseño
├── data-model.md        # Fase 1: contrato de error (sin entidades de BD)
├── quickstart.md        # Fase 1: guía de validación end-to-end
├── contracts/
│   └── error-contract.md  # Fase 1: contrato estándar de error de la API
└── tasks.md             # Fase 2 (/speckit-tasks — no creado por /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── api/
│   ├── errors.py            # NUEVO: normalizador after_request + handlers globales
│   └── routes/
│       └── _shared.py       # Sin cambios de comportamiento (server_error() se conserva)
├── app.py                   # MODIFICADO: registrar normalizador/handlers en create_app()
└── tests/
    └── api/
        └── test_error_contract.py  # NUEVO: test del normalizador (≤ 5-10 mocks)

frontend/src/
├── services/
│   ├── apiClient.ts         # MODIFICADO: interceptor de errores centralizado
│   └── errorNotifier.ts     # NUEVO: helper de toast antd con dedupe
└── App.tsx                  # MODIFICADO: montar <AntApp> para el sistema de mensajes
```

**Structure Decision**: Web application existente (backend Flask + frontend React). Todo el
trabajo backend se concentra en un archivo nuevo (`backend/api/errors.py`) más su registro en
`create_app()`; todo el trabajo frontend en `apiClient.ts` + un helper nuevo. Ningún módulo de
rutas ni página se refactoriza.

## Complexity Tracking

Sin violaciones a la constitución — tabla no requerida.
