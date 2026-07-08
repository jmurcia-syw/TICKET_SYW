# Research: Refactorización visual y de navegación del detalle del Ticket

Todas las incógnitas de esta funcionalidad se resolvieron por inspección directa del código
existente (no requirió investigación externa) — se documentan aquí las decisiones y sus
alternativas descartadas.

## Decisión 1 — Cómo derivar la "Fecha de inicio"

- **Decision**: La fecha de inicio se calcula en el frontend como la fecha (`work_date` o
  `started_at`) del registro de tiempo más antiguo del ticket, a partir de la misma lista que ya
  consume `TicketWorkSessions` (`workSessionService.list({ ticket_id })`). No se agrega columna ni
  campo nuevo al ticket.
- **Rationale**: El usuario aclaró explícitamente que "la fecha de inicio... es cuando empezó a
  trabajársele [al ticket]", no la fecha de creación. El primer registro de tiempo cargado es la
  señal más directa y ya disponible de "cuándo empezó el trabajo real", sin tocar backend/DB
  (alineado con la restricción de alcance del usuario).
- **Alternatives considered**:
  - Nueva columna editable en `tickets` (fecha de inicio planificada) — descartada: requiere
    migración + endpoint, fuera del alcance pedido ("solo UI y lógica de tiempos").
  - Fecha de la transición a "En Ejecución" (histórico de `transitions`) — descartada: ya
    disponible en pantalla (`ticket.transitions`), pero el usuario fue explícito en que la fecha
    de inicio "está para registrar los tiempos", es decir, ligada a `work_sessions`, no al FSM.

## Decisión 2 — Revelado fluido (modal → resumen/comentarios/actividad) sin nueva dependencia

- **Decision**: Un único booleano de UI (`timeExpanded`, o similar) en `TicketDetailPage`,
  controlado por (a) el cierre del modal de tiempo (`onCancel`/`onClose` → colapsa) y (b) un
  listener de `scroll` sobre el contenedor de la página que detecta dirección de scroll (hacia
  arriba, cerca del tope) para volver a expandir. La transición visual usa CSS
  (`max-height`/`opacity` con `transition`), sin librería de animación nueva.
- **Rationale**: Ant Design y React ya cubren todo lo necesario; una librería de animación
  (framer-motion, react-spring) sería una dependencia nueva no aprobada (Principio V) para un
  efecto que un `transition` de CSS ya resuelve con solvencia.
- **Alternatives considered**:
  - `IntersectionObserver` sobre un marcador entre el resumen y los comentarios — más preciso para
    detectar "el usuario volvió arriba", pero más código para un beneficio marginal frente al
    listener de scroll con umbral simple; se deja como posible mejora futura si el comportamiento
    con scroll simple resulta insuficiente en la validación manual.
  - Librería de animación externa — descartada por gobernanza de dependencias.

## Decisión 3 — Filtros guardados: dónde y cómo persistir

- **Decision**: Nuevo store `frontend/src/store/savedFiltersStore.ts` con Zustand +
  `persist` (mismo patrón exacto que `authStore.ts`), namespaced en `localStorage` con una key
  distinta (p. ej. `sywork-saved-filters`) y los filtros propios indexados por `userId` (tomado de
  `useAuthStore`) para no mezclar filtros entre cuentas que compartan navegador. El filtro
  "Asignado a mí" se modela como un preset especial (`builtIn: true`) cuyo criterio de "asignado"
  se resuelve en el momento de aplicarlo (vía `resourceService.me()`), no como un `resource_id`
  guardado — así sigue siendo válido aunque cambie el recurso asociado al usuario.
- **Rationale**: Cumple el pedido de "guardar varios filtros" sin crear tabla ni endpoint nuevo en
  backend (alcance mínimo pedido explícitamente por el usuario); reutiliza un patrón ya aprobado y
  en uso (Zustand `persist`).
- **Alternatives considered**:
  - Persistencia en backend (nueva tabla `saved_filters` + endpoint) — descartada por ahora: mayor
    alcance (migración, API, RLS) no solicitado; queda anotada como posible iteración futura en
    Assumptions del spec si se necesita sincronizar entre dispositivos.
  - `localStorage` crudo sin Zustand — descartada: el proyecto ya estandarizó `persist` de Zustand
    para este tipo de estado (`authStore`), mantener un solo patrón es más consistente.

## Decisión 4 — Pantalla "Mis Tareas": de dónde sale "asignado a mí"

- **Decision**: Reutilizar `resourceService.me()` (ya usado exactamente para este propósito en
  `WorkSessionsPage.tsx:52`) para resolver el recurso del usuario autenticado, y
  `ticketService.list({ assignee_id: resource.id })` (mismo endpoint que ya usa `TicketsPage`) para
  traer sus tickets. No se necesita ningún endpoint nuevo.
- **Rationale**: Es el patrón ya validado y en producción en este mismo repositorio para resolver
  "tickets asignados al usuario actual".
- **Alternatives considered**: Ninguna — patrón ya establecido, sin ambigüedad.

## Decisión 5 — Evitar modal-dentro-de-modal en el flujo de registrar tiempo

- **Decision**: `WorkSessionForm` gana un prop opcional (p. ej. `embedded?: boolean`) para
  renderizar solo el `<Form>` sin su propio `<Modal>` envolvente cuando se usa dentro de
  `TimeLogModal` (que sí aporta el `<Modal>` único de la Historia 1). `WorkSessionsPage.tsx` (la
  pantalla global de registro de tiempos, fuera de alcance de esta funcionalidad) sigue
  invocándolo exactamente igual que hoy (con su propio `<Modal>`).
- **Rationale**: Ant Design permite modales apilados, pero apilar un modal de alta dentro del
  modal de historial degrada la experiencia (justo lo que esta funcionalidad busca evitar) y no es
  el patrón "limpio" que pide el usuario. Un prop `embedded` es el cambio más chico posible sobre
  un componente ya existente, sin duplicar el formulario.
- **Alternatives considered**: Duplicar el formulario en un componente nuevo — descartado, viola
  la directriz de no generar código innecesario cuando ya existe uno reutilizable.

## Decisión 6 — Umbrales de color para consumo estimado vs. real

- **Decision**: `< 80%` → `colorSuccess`; `80%–100%` (inclusive) → `colorWarning`; `> 100%` →
  `colorError` — tokens ya definidos en `theme.ts` (`palette.green600`/`amber600`/`red600`, ya
  mapeados a `colorSuccess`/`colorWarning`/`colorError` del `ThemeConfig`).
- **Rationale**: Ya definido como parte de las Assumptions del spec (confirmado con el usuario
  implícitamente al no objetar la propuesta); reutiliza tokens existentes, no amplía la paleta
  (pedido explícito del usuario).
- **Alternatives considered**: Gradiente continuo de color — descartado, más complejo de
  implementar y de interpretar de un vistazo que 3 estados discretos.

**Output**: Todas las incógnitas del Technical Context quedaron resueltas; no quedan
`NEEDS CLARIFICATION` pendientes para el diseño de Fase 1.
