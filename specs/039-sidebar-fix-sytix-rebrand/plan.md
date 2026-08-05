# Implementation Plan: Corrección de Layout del Menú Lateral (Sidebar Estático) y Rebranding a SYTIX

**Branch**: `039-sidebar-fix-sytix-rebrand` | **Date**: 2026-08-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/039-sidebar-fix-sytix-rebrand/spec.md`

## Summary

Dos bugs de layout del sidebar de `DashboardPage.tsx` — el bloque del logo no reacciona al
`collapsed` del `Sider` (queda con padding/tamaño fijo y se superpone a los íconos) y dos
disparadores (`onMouseEnter` del `Sider`, `onClick` del `Menu`) fuerzan la re-expansión sin que
el usuario lo pida — más un rebranding puramente textual de "SyWork"/"SyWork Desk" a "SYTIX"
(con eslogan "Systems | Innovation | Xcellence" donde ya hay espacio de marca completa). Enfoque:
hacer que el logo del `Sider` lea el `collapsed` ya existente para renderizar su variante
compacta centrada; eliminar los dos disparadores de re-expansión, dejando el `onCollapse` nativo
del `Sider` (ligado a su botón/flecha de alternar) como único punto de control; reemplazar los
literales de texto de marca en los 3 archivos donde son visibles al usuario
(`DashboardPage.tsx`, `AuthLayout.tsx`, `index.html`). Sin cambios de backend, sin dependencias
nuevas, sin migración, sin suite de pruebas (Principio VII + instrucción explícita del usuario).

## Technical Context

**Language/Version**: TypeScript 5 estricto / React 19 (frontend). Sin cambios de backend.

**Primary Dependencies**: Ant Design 5 (`Layout.Sider`, `Layout.Header`, `Menu`, `Typography`) —
todas ya usadas en los mismos componentes. **Sin dependencias nuevas** (Principio V).

**Storage**: N/A — sin cambios de esquema ni de API.

**Testing**: `tsc -b` (frontend) como único chequeo técnico. **Sin ejecución de suite de
pruebas** — prohibido explícitamente para esta sesión (Principio VII + instrucción del usuario);
validación manual en navegador contra Docker real siguiendo `quickstart.md`.

**Target Platform**: Web app on-premise (Docker Compose), navegador de escritorio en múltiples
resoluciones.

**Project Type**: Web application (cambio acotado exclusivamente a `frontend/`).

**Performance Goals**: N/A — ajuste de estilos/estado local y reemplazo de texto, sin fetch ni
cómputo adicional.

**Constraints**: Principio VII (alcance de sesión acotado únicamente a componentes de layout —
Header/Sidebar/Layout principal — y constantes de nombre; prohibido tocar controladores o lógica
de backend, prohibido correr la suite de pruebas). Principio V (cero dependencias nuevas). No se
agregan archivos de imagen de logo nuevos (FR-008) — se reutiliza `logo-sywork.jpg` existente.

**Scale/Scope**: 3 archivos frontend tocados (`frontend/src/pages/DashboardPage.tsx`,
`frontend/src/components/common/AuthLayout.tsx`, `frontend/index.html`), ~20-30 líneas
modificadas en total. Ningún archivo de backend, ninguna migración, ninguna prueba nueva.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (API-First y Dominio Primero)**: Cumple — no se toca ningún endpoint ni lógica
  de negocio; es un ajuste de presentación puro.
- **Principio II (Clean Architecture)**: Cumple — cambio contenido en Capa 3
  (`frontend/src/pages/`, `frontend/src/components/common/`), sin lógica de negocio nueva; los
  componentes tocados siguen siendo de presentación/layout, no "servicios" con lógica.
- **Principio III (Tipado estricto)**: Cumple — no se introduce ningún `any`; el estado
  `collapsed` ya está tipado (`boolean`, `useState`) desde spec 038.
- **Principio IV (Seguridad en profundidad)**: Sin impacto — no se toca autenticación,
  autorización, RLS ni transporte; no se expone ningún dato nuevo.
- **Principio V (Gobernanza de librerías)**: Cumple — cero dependencias nuevas (ver Decisión 1 de
  `research.md`, que descarta explícitamente `@ant-design/pro-layout`).
- **Principio VI (AI-Native)**: Sin impacto — no se tocan endpoints de acción ni el modelo de
  comentarios/skills.
- **Principio VII (Alcance de sesión y testing ultra-limitado)**: Cumple — alcance restringido a
  los 3 archivos de layout/branding listados arriba, ninguna refactorización externa, cero
  ejecución de suite de pruebas (ver Decisión 4 de `research.md`).

**Resultado**: PASS, sin violaciones. Tabla de Complexity Tracking no aplica.

## Project Structure

### Documentation (this feature)

```text
specs/039-sidebar-fix-sytix-rebrand/
├── plan.md              # Este archivo
├── research.md          # Fase 0 — decisiones (fix de logo colapsado, hover, alcance de branding)
├── data-model.md        # Fase 1 — confirma que no hay cambios de esquema/tipos
├── quickstart.md        # Fase 1 — validación manual end-to-end
└── tasks.md             # Fase 2 (/speckit-tasks — no generado por este comando)
```

No se genera `contracts/` — esta feature no agrega ni modifica ningún endpoint ni interfaz
externa (Decisión 1/3 de `research.md`); es un cambio de presentación puro.

### Source Code (repository root)

```text
frontend/
├── index.html                              # <title> "SyWork Desk" → "SYTIX"
└── src/
    ├── pages/
    │   └── DashboardPage.tsx                # Sider: logo collapse-aware, quitar onMouseEnter
    │                                         #   y el setCollapsed(false) del onClick del Menu;
    │                                         #   Header: texto de marca → "SYTIX"
    └── components/common/
        └── AuthLayout.tsx                   # Panel de marca (Login/Reset): "SYTIX" + eslogan
```

**Structure Decision**: 3 archivos tocados dentro de la estructura frontend ya vigente
(`frontend/index.html`, `frontend/src/pages/`, `frontend/src/components/common/`). No se crean
directorios ni componentes nuevos — se reutiliza el `Sider`/`Menu`/`Header` de Ant Design y el
`AuthLayout` compartido ya existentes, ajustando su estado/estilos y literales de texto.
Ningún archivo de `backend/` se toca, consistente con la restricción explícita del alcance.

## Complexity Tracking

> No aplica — Constitution Check sin violaciones.
