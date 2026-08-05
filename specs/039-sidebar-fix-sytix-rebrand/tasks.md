---

description: "Task list for 039-sidebar-fix-sytix-rebrand"
---

# Tasks: Corrección de Layout del Menú Lateral (Sidebar Estático) y Rebranding a SYTIX

**Input**: Design documents from `/specs/039-sidebar-fix-sytix-rebrand/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md)

**Tests**: no aplica — sin cambios de backend, y prohibido explícitamente ejecutar la suite de pruebas en esta sesión (Principio VII + instrucción del usuario, ver `research.md` Decisión 4). Validación manual en Docker real siguiendo `quickstart.md`.

**Organización**: 3 historias de usuario (US1/US2 en `frontend/src/pages/DashboardPage.tsx`, US3 repartida entre ese mismo archivo, `AuthLayout.tsx` e `index.html`). US1 y US2 tocan el mismo bloque `<Sider>` del mismo archivo — se ejecutan en secuencia, no en paralelo entre sí. Dentro de US3, la edición de `index.html` y de `AuthLayout.tsx` son archivos distintos entre sí y pueden hacerse en paralelo; la edición de `DashboardPage.tsx` (texto del header) comparte archivo con US1/US2 y va después de esas dos.

## Path Conventions

Web app existente: `frontend/src/pages/`, `frontend/src/components/common/`, `frontend/index.html` (ver Project Structure de [plan.md](plan.md)). Sin cambios de backend.

---

## Phase 1: Setup

No aplica — sin dependencias nuevas (Principio V), sin estructura de proyecto nueva.

## Phase 2: Foundational

No aplica — los 3 archivos a modificar, el estado `collapsed` y el logo (`logo-sywork.jpg`) ya existen; ninguna infraestructura nueva que preparar antes de las historias.

---

## Phase 3: User Story 1 - Menú lateral colapsado usable en cualquier resolución (Priority: P1) 🎯 MVP

**Goal**: Al colapsar el sidebar, el logo se muestra en su versión compacta, centrada dentro del ancho colapsado, sin superponerse a los íconos, en cualquier resolución.

**Independent Test**: Colapsar el menú lateral con la ventana en 3 anchos distintos (1920px, 1366px, 1024px) y confirmar visualmente que el logo compacto queda centrado sin desbordes ni superposición.

### Implementation for User Story 1

- [X] T001 [US1] En `frontend/src/pages/DashboardPage.tsx`, en el `<div style={{ padding: '20px 24px 16px' }}>` que envuelve el `<img>` del logo dentro del `<Sider>` (línea ~112-114), hacer que el padding y la alineación dependan de `collapsed`: cuando `collapsed` es `true`, usar padding horizontal reducido (o `0`) y `display: 'flex', justifyContent: 'center'` para centrar el `<img>` dentro del ancho colapsado del `Sider` (`collapsedWidth` por defecto de Ant Design, 80px); cuando `collapsed` es `false`, mantener el padding/alineación actuales (research.md Decisión 1). No modificar el logo del `<Header>` superior (líneas ~67-77), que está fuera del `Sider` y no colapsa.
- [X] T002 [US1] Verificación manual contra Docker real siguiendo `quickstart.md` Escenario 1 (colapsar el menú y confirmar el logo centrado sin superposición en 1920px, 1366px y 1024px)

**Checkpoint**: El sidebar colapsado se ve correcto en cualquier resolución probada, sin afectar el header superior ni el comportamiento de expansión existente.

---

## Phase 4: User Story 2 - El menú lateral solo cambia de estado por clic explícito (Priority: P1)

**Goal**: El menú lateral colapsado permanece fijo ante el paso del cursor o la navegación por sus opciones; solo cambia de estado con un clic explícito en su control de alternar.

**Independent Test**: Con el menú colapsado, pasar el cursor repetidamente sobre el sidebar sin clic (permanece colapsado) y luego navegar a otra pantalla haciendo clic en una opción del menú (permanece colapsado tras la navegación); confirmar que el clic en el botón/flecha de alternar sigue expandiendo/colapsando normalmente.

### Implementation for User Story 2

- [X] T003 [US2] En `frontend/src/pages/DashboardPage.tsx`, eliminar el atributo `onMouseEnter={() => { if (collapsed) setCollapsed(false) }}` del `<Sider>` (línea ~109) y eliminar `setCollapsed(false)` del `onClick={({ key }) => { navigate(key); setCollapsed(false) }}` del `<Menu>` (línea ~121), dejando únicamente `onClick={({ key }) => navigate(key)}`. El único disparador de cambio de `collapsed` que debe quedar es el `onCollapse={setCollapsed}` nativo del `Sider`, ya ligado a su control de alternar por defecto de Ant Design (research.md Decisión 2).
- [X] T004 [US2] Verificación manual contra Docker real siguiendo `quickstart.md` Escenario 2 (≥20 pasadas de cursor sin clic con el menú colapsado → permanece colapsado; clic en el control de alternar → expande/colapsa; clic en una opción del menú colapsado → permanece colapsado tras navegar)

**Checkpoint**: El sidebar solo cambia de estado colapsado/expandido por clic explícito en su control de alternar; el hover y la navegación por sus opciones dejan de forzar la expansión.

---

## Phase 5: User Story 3 - La aplicación se identifica como SYTIX (Priority: P2)

**Goal**: Todas las menciones visibles al usuario de "SyWork"/"SyWork Desk" (header, sidebar, panel de login, título de pestaña) pasan a "SYTIX", con el eslogan "Systems | Innovation | Xcellence" donde ya se muestra la marca completa, sin agregar archivos de imagen nuevos.

**Independent Test**: Recorrer login, header autenticado y título de la pestaña del navegador y confirmar que ninguno muestra "SyWork" ni "SyWork Desk", y que el panel de login muestra el eslogan junto a "SYTIX".

### Implementation for User Story 3

- [X] T005 [P] [US3] En `frontend/index.html`, cambiar `<title>SyWork Desk</title>` (línea 7) por `<title>SYTIX</title>`.
- [X] T006 [P] [US3] En `frontend/src/components/common/AuthLayout.tsx`: cambiar el `<Title level={2}>SyWork Desk</Title>` (línea ~34) por `<Title level={2}>SYTIX</Title>` y agregar el eslogan "Systems | Innovation | Xcellence" en la línea de `<Text>` secundaria existente (línea ~35, hoy "Tickets, tiempos y equipo de soporte en un solo lugar.") — combinando ambos textos o agregando el eslogan como línea adicional dentro del mismo bloque de marca; cambiar los dos `alt="SyWork"` de esa pantalla (líneas ~32 y ~48) por `alt="SYTIX"`. No tocar el `src={logo}` (mismo archivo `logo-sywork.jpg`, FR-008).
- [X] T007 [US3] En `frontend/src/pages/DashboardPage.tsx`: cambiar el texto `SyWork Desk` del header (línea ~75) por `SYTIX`, y los dos `alt="SyWork"` (líneas ~72 y ~113) por `alt="SYTIX"`. No agregar el eslogan aquí (el header compacto no tiene espacio para una segunda línea, research.md Decisión 3) ni tocar `src={logo}`. Ejecutar después de T001/T003 (mismo archivo).
- [X] T008 [US3] Verificación manual contra Docker real siguiendo `quickstart.md` Escenario 3 (login muestra "SYTIX" + eslogan; header autenticado muestra "SYTIX"; título de pestaña dice "SYTIX"; ninguna de las 3 pantallas muestra "SyWork"/"SyWork Desk")

**Checkpoint**: Ninguna pantalla visible al usuario muestra "SyWork"/"SyWork Desk"; el logo gráfico existente no cambió.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T009 Ejecutar `tsc -b` en `frontend/` y confirmar cero errores
- [X] T010 Actualizar `CLAUDE.md` (bloque "Active feature") con el resultado de la validación end-to-end de las 3 historias

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup / Foundational**: no aplica
- **US1 (Phase 3)**: sin dependencias — MVP, primer incremento entregable
- **US2 (Phase 4)**: sin dependencia funcional de US1, pero comparte archivo (`DashboardPage.tsx`) — se ejecuta después de US1 para evitar tocar el mismo archivo en paralelo
- **US3 (Phase 5)**: sin dependencia funcional de US1/US2; T005/T006 pueden hacerse en cualquier momento, T007 comparte archivo con US1/US2 y va después de ambas
- **Polish (Phase 6)**: depende de que US1, US2 y US3 estén completas

### Parallel Opportunities

- T005 (`index.html`) y T006 (`AuthLayout.tsx`) pueden ejecutarse en paralelo entre sí y respecto de T001-T004 (archivos distintos)
- T001-T004 y T007 comparten `DashboardPage.tsx` — ejecución secuencial entre ellas, no en paralelo

---

## Parallel Example: User Story 3

```bash
# T005 y T006 son archivos distintos, sin dependencia entre sí:
Task: "Cambiar <title> en frontend/index.html"
Task: "Cambiar texto de marca + eslogan + alt en frontend/src/components/common/AuthLayout.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 3 (US1) — corrige la superposición visual del logo colapsado, el bug más disruptivo reportado.
2. **STOP and VALIDATE**: Escenario 1 de `quickstart.md` en 3 resoluciones.

### Incremental Delivery

1. US1 → validar → el sidebar colapsado ya no se ve roto (MVP).
2. US2 → validar → el sidebar deja de auto-expandirse por hover/navegación.
3. US3 → validar → la app se identifica como SYTIX en toda pantalla visible.
4. Phase 6 (Polish) → `tsc -b` + actualización de `CLAUDE.md`.
