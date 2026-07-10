# Tasks: Manejo Global de Errores y Notificaciones (API a Frontend)

**Input**: Design documents from `/specs/013-manejo-errores-notificaciones/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/error-contract.md, quickstart.md

**Tests**: Incluidos SOLO los pedidos por el spec: un test backend del normalizador con ≤ 5-10
casos/mocks. Prohibido ejecutar la suite completa (Principio VII); único comando permitido:
`pytest tests/api/test_error_contract.py` (desde el contenedor `sywork_backend`, working dir
`/repo/backend`) — el archivo vive en `backend/tests/api/` porque colocarlo directamente en
`backend/tests/` producía un `INTERNALERROR` de pytest por conflicto de rutas con el paquete
`backend` (ver research.md, Decisión 6).

**Organization**: Tareas agrupadas por historia de usuario. US1 (frontend) y US2 (backend) son
independientes y paralelizables; US3 valida ambas de punta a punta.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1, US2, US3)

## Path Conventions

Web app existente: `backend/` (Flask) y `frontend/src/` (React). Rutas exactas según plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

Sin tareas — proyecto existente, cero dependencias nuevas (Principio V); no hay inicialización
ni configuración previa requerida.

---

## Phase 2: Foundational (Blocking Prerequisites)

Sin tareas — US1 y US2 no comparten prerequisitos: US1 funciona con el mensaje genérico aunque
US2 no exista, y US2 es verificable por curl sin US1.

---

## Phase 3: User Story 1 - Alerta visual inmediata ante errores de API (Priority: P1) 🎯 MVP

**Goal**: Todo fallo de API (≠ 401) produce un toast inmediato con el `message` del servidor o
el genérico; la UI nunca queda congelada sin feedback.

**Independent Test**: Con el backend actual (sin US2), provocar un error de API desde la UI y
ver el toast; detener el backend y ver el mensaje genérico (quickstart, Validación 3).

- [X] T001 [P] [US1] Montar el componente `App` de antd (`<AntApp>`) dentro del `ConfigProvider` en `frontend/src/App.tsx` para habilitar la API de mensajes con tema/locale correctos
- [X] T002 [P] [US1] Crear `frontend/src/services/errorNotifier.ts`: tipo `ApiErrorBody` (según data-model.md), función `notifyApiError(error: AxiosError)` que extrae `response.data.message` (string no vacío) o usa el genérico "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo", con dedupe por texto en ventana de ~3 s (FR-005, FR-006, FR-008). Sin `any` (Principio III)
- [X] T003 [US1] Extender el interceptor de response en `frontend/src/services/apiClient.ts`: para errores con status ≠ 401 (o sin response), llamar a `notifyApiError`; conservar intacto el flujo 401 (logout + redirect, sin toast) y el `Promise.reject(error)` final (FR-004, FR-007)
- [ ] T004 [US1] Validación manual de casos borde según `quickstart.md` Validación 3: error de red → genérico sin loading infinito; 401 → redirect sin toast; dedupe con llamadas simultáneas fallando *(PENDIENTE — requiere validación visual manual; `tsc --noEmit` OK y Vite sin errores)*

**Checkpoint**: MVP entregable — el usuario ya recibe feedback visual de todo fallo.

---

## Phase 4: User Story 2 - Estructura estándar de error en TODOS los endpoints (Priority: P2)

**Goal**: Toda respuesta ≥ 400 de la API sale con `{success: false, message, code}` (+ `error`
legado), con el status HTTP correcto y sin fuga de detalles internos en 500.

**Independent Test**: curl a endpoints con errores conocidos (404/403/400) y excepción forzada
(500) verificando la estructura (quickstart, Validación 1), sin necesidad del frontend.

- [X] T005 [US2] Crear `backend/api/errors.py`: hook `after_request` que normaliza toda respuesta JSON con status ≥ 400 (añade `success: false`; deriva `code` desde el campo `error` existente en UPPER_SNAKE o desde el status HTTP según la tabla de data-model.md; garantiza `message`; conserva `error` legado) + manejadores globales de `HTTPException` y `Exception` con 500 genérico sin stack traces (FR-001, FR-002, FR-003; research.md Decisiones 1-2). Type hints obligatorios
- [X] T006 [US2] Registrar el normalizador y los manejadores en `create_app()` en `backend/app.py` (sin tocar ningún módulo de `backend/api/routes/` — Principio VII)
- [X] T007 [P] [US2] Crear `backend/tests/api/test_error_contract.py` con ≤ 5-10 casos usando el test client de Flask: 400 con `error` propio → `code` derivado; 403; 404 (recurso y ruta inexistente); excepción no controlada → 500 genérico sin texto de la excepción; respuesta de éxito no alterada. Ejecutar SOLO `pytest tests/api/test_error_contract.py` *(8/8 pasan en el contenedor `sywork_backend`)*
- [X] T008 [US2] Validación por curl contra Docker real según `quickstart.md` Validación 1 *(verificado: 400 validación, 403 sin permiso, 404 recurso "Proyecto no encontrado", 404 ruta y 405 en español, todos con `success`/`message`/`code`)*

**Checkpoint**: Contrato de error garantizado en los ~17 módulos de rutas sin editarlos.

---

## Phase 5: User Story 3 - Casos críticos muestran su mensaje específico (Priority: P3)

**Goal**: Los 3 errores críticos del negocio llegan del servidor con su mensaje específico y se
ven como toast inmediato en la UI (FR-009).

**Independent Test**: Reproducir cada caso desde el navegador (quickstart, Validación 2).
Depende de US1 + US2 completadas.

- [ ] T009 [US3] Verificar en UI el caso "ticket no asignado a este proyecto": provocar la operación y confirmar toast con el mensaje específico del servidor; si el mensaje del endpoint no es apto para usuario final, ajustar SOLO ese texto en la ruta correspondiente de `backend/api/routes/` (cambio de string, no de lógica) *(PENDIENTE visual — lado servidor verificado por curl: errores de negocio 400 salen con mensaje específico y contrato estándar)*
- [ ] T010 [US3] Verificar en UI el caso "usuario sin permisos": con rol limitado (p. ej. Resolutor en acción restringida), confirmar toast 403 con mensaje entendible y pantalla no congelada *(PENDIENTE visual — lado servidor verificado: 403 Resolutor → "Acceso denegado" con contrato estándar)*
- [ ] T011 [US3] Verificar en UI el caso "proyecto no encontrado": operar sobre proyecto inexistente/eliminado y confirmar toast 404 con mensaje específico *(PENDIENTE visual — lado servidor verificado: 404 → "Proyecto no encontrado" con contrato estándar)*

**Checkpoint**: SC-002 verificado — los 3 casos críticos muestran mensaje específico, no genérico.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T012 [P] Actualizar `error_model()` en `backend/api/routes/_shared.py` para que el esquema Swagger documente también `success` y `code` (solo el modelo de documentación; sin cambios de comportamiento)
- [X] T013 [P] Actualizar `README.md` (estado del proyecto) reflejando la feature 013 completada, siguiendo el patrón de commits `docs(readme)` del repositorio

---

## Dependencies

```text
Phase 1, 2: vacías
US1 (T001→T003→T004; T001‖T002)  ──┐
                                    ├──> US3 (T009, T010, T011) ──> Polish (T012 ‖ T013)
US2 (T005→T006→{T007‖T008})      ──┘
US1 ‖ US2 (archivos disjuntos: frontend/ vs backend/)
```

- T003 depende de T001 y T002 (usa el notifier y el `<AntApp>` montado).
- T006 depende de T005; T007 y T008 dependen de T006.
- US3 requiere US1 + US2 completas.

## Parallel Execution Examples

- **Entre historias**: US1 (frontend) y US2 (backend) completas en paralelo — cero archivos
  compartidos.
- **Dentro de US1**: T001 y T002 en paralelo (App.tsx vs errorNotifier.ts).
- **Dentro de US2**: T007 (test) y T008 (curl) en paralelo tras T006.
- **Polish**: T012 y T013 en paralelo.

## Implementation Strategy

1. **MVP = US1** (4 tareas): con solo el interceptor + notifier, el usuario ya deja de ver la
   app "congelada" — todo error muestra al menos el mensaje genérico, y los endpoints que ya
   traen `message` muestran el texto real.
2. **Incremento 2 = US2**: el normalizador global garantiza `message`/`code` consistentes en el
   100% de los endpoints, elevando la calidad de los toasts sin tocar el frontend de nuevo.
3. **Incremento 3 = US3 + Polish**: verificación end-to-end de los 3 casos críticos contra
   Docker real y documentación (Swagger/README).

**Restricciones transversales (Constitución v1.2.0, Principio VII)**: no refactorizar
controladores (solo T009 permite ajustar strings de mensaje); no ejecutar la suite de tests
masivamente (solo `test_error_contract.py`); tests con ≤ 5-10 mocks; sin trabajo fuera del
alcance de esta feature.
