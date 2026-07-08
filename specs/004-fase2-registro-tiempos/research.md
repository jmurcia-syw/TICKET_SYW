# Research: Fase 2 — Registro diario de tiempos por recurso

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

No quedaron marcadores `NEEDS CLARIFICATION` en el Technical Context del plan — el stack, la
arquitectura de tres capas y las convenciones de nomenclatura ya están fijados por la Constitución
y por el precedente de `002-fase1-tickets`. Este documento resuelve las decisiones de diseño
propias de esta fase que no estaban predeterminadas por el spec.

## Decisión 1: Unidad de almacenamiento del tiempo

- **Decision**: Persistir el tiempo como `duration_minutes` (entero, minutos), no como horas
  decimales ni como intervalo `start`/`end`.
- **Rationale**: El spec (US1) pide "horas/minutos" como entrada de usuario, pero minutos enteros
  evitan errores de redondeo de punto flotante en la suma diaria (FR-003/FR-004) y simplifican la
  validación de "máx. 24h/día" (FR-004) a una comparación entera (`SUM(duration_minutes) <= 1440`).
  La UI convierte horas:minutos → minutos al guardar y viceversa al mostrar.
- **Alternatives considered**:
  - *Horas decimales (`NUMERIC`)*: más natural para reportes, pero introduce redondeo al sumar
    fracciones repetidas; se descarta por el requisito exacto de "no superar 24h".
  - *Timestamps `start`/`end` (como sugieren los endpoints `/api/sessions/start`/`/end` listados en
    la Constitución para "Work Session / Focus Mode")*: ese patrón corresponde a un timer en vivo
    (Focus Mode, Fase 7 del roadmap), no a la carga manual retroactiva que pide esta fase. Se
    descarta para no adelantar alcance de Fase 7; el modelo de datos de `work_sessions` queda
    abierto a incorporar `started_at`/`ended_at` en Fase 7 sin romper esta fase (ver Fase futura
    en Assumptions del spec).

## Decisión 2: Historial de ediciones auditable

- **Decision**: Tabla append-only `work_session_edits` (una fila por creación/edición/borrado),
  igual patrón que `ticket_assignments` y `ticket_status_transitions` en `002-fase1-tickets`.
- **Rationale**: FR-012/FR-013 exigen que el historial de ediciones sea auditable y que el
  registro no pierda el autor original. Un log append-only evita sobrescribir datos (a diferencia
  de un simple `updated_by`/`updated_at` en la fila principal) y reutiliza un patrón ya validado y
  familiar para el equipo.
- **Alternatives considered**: Versionado con `SQLAlchemy-Continuum` u otra librería de auditoría
  automática — rechazado por Principio V (cero dependencias nuevas sin aprobación); una tabla
  append-only manual con SQLAlchemy plano es suficiente y consistente con lo ya construido.

## Decisión 3: Enforcement de la ventana de edición (7 días)

- **Decision**: Se valida en `WorkSessionService` (Capa 1, dominio), comparando
  `date.today() - work_session.work_date <= 7 días`, no como constraint de base de datos.
- **Rationale**: Principio I exige que la lógica de negocio viva en el dominio; una ventana de
  tiempo relativa a "hoy" no es expresable como `CHECK constraint` está fuera del dominio y sería
  difícil de mantener. El dominio ya sigue este patrón para las transiciones de FSM de tickets.
- **Alternatives considered**: Trigger de PostgreSQL — descartado, misma razón (lógica de negocio
  fuera de la Capa 1, más difícil de testear con `pytest`).

## Decisión 4: Autorización de visibilidad (recurso propio vs. Coordinador/QM/Admin)

- **Decision**: Igual que `tickets` (`012_tickets_rls.py`): RLS a nivel de tabla habilitado como
  red de seguridad de datos (policy permisiva para la sesión autenticada de la app), y la
  restricción real de "un recurso ve solo lo suyo salvo Coordinador/QM/Admin" (FR-010) se aplica
  en el dominio + capa API (filtro por `resource_id` según el rol del caller), consistente con
  cómo ya se documentó la separación de responsabilidades para tickets.
- **Rationale**: Mantener un único patrón de autorización en todo el sistema reduce superficie de
  error; replicar RLS granular por fila (usando `current_setting('app.user_id')`) requeriría
  primero instrumentar esa variable de sesión en el middleware, algo que hoy no está conectado ni
  siquiera para `notifications` (única tabla con policy por owner) de forma consistente — quedaría
  fuera de alcance de esta fase tocar esa infraestructura transversal.
- **Alternatives considered**: RLS estricto por `resource_id` vía `current_setting` — se deja
  como mejora futura transversal (afecta a todas las tablas, no solo `work_sessions`), no
  bloqueante para esta fase.

## Decisión 5: Reporte agregado y "días sin registro" (US3)

- **Decision**: El endpoint de reporte (`GET /api/work-sessions/summary`) calcula la agregación en
  el repositorio con SQL (`GROUP BY resource_id, work_date`), y el servicio de dominio rellena en
  memoria los días del rango consultado que no aparecen en el resultado con `total_minutes = 0` /
  `sin_registro = true`, en vez de usar `generate_series` de PostgreSQL.
- **Rationale**: Mantiene la lógica de "qué es un día sin registro" en el dominio (testeable con
  `pytest` sin base de datos), y evita acoplar el dominio a una función específica de PostgreSQL.
- **Alternatives considered**: `generate_series` + `LEFT JOIN` en SQL — más eficiente en volumen
  alto, pero el volumen esperado (Scale/Scope del plan) no lo justifica; se prefiere simplicidad y
  testabilidad sobre optimización prematura.

## Decisión 6: Nuevo permiso de autorización

- **Decision**: Se agregan los permisos `work_sessions:view_own`, `work_sessions:view_all` y
  `work_sessions:manage` al catálogo de permisos existente (mismo mecanismo que
  `tickets:view`/`tickets:create` de Fase 1), asignados por rol en la migración correspondiente
  (Coordinador/QM/Admin obtienen `view_all`; todos los roles internos obtienen `view_own` y
  `manage` sobre sus propios registros).
- **Rationale**: Reutiliza el sistema de roles/permisos ya construido en `001-fase0-maestros`, sin
  crear un mecanismo de autorización paralelo.
- **Alternatives considered**: Hardcodear el chequeo de rol en el endpoint — rechazado, viola el
  patrón ya establecido de permisos parametrizados por rol (y el espíritu del Principio VI de
  reglas explícitas y no ad-hoc).
