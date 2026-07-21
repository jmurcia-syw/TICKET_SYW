# Implementation Plan: Actualización Integral del Manual de Usuario

**Branch**: `025-manual-usuario-integral` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/025-manual-usuario-integral/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Producir un manual de usuario actualizado (`docs/Manual_de_Usuario.md`, listo para exportar a
Word/PDF) que documente, en lenguaje no técnico, el sistema SyWork Tickets tal como quedó tras las
fases 0-5 SDD V3 (specs 001-024): resumen arquitectónico orientado a usabilidad, tres diagramas
Mermaid (ciclo de vida del Ticket, aprobación de vacaciones/permisos, regla de pausa/reanudación de
SLA), guía paso a paso de las vistas principales con marcadores `[INSERTAR CAPTURA: ...]`, tablas de
ayuda rápida y bloques de nota/advertencia. Es una sesión 100% de documentación: no se toca código
de `backend/` ni `frontend/`, y no se ejecuta la suite de pruebas (Principio VII de la Constitución).

## Technical Context

**Language/Version**: N/A — el entregable es documentación en Markdown (GitHub-Flavored Markdown +
bloques ```mermaid), no código ejecutable.

**Primary Dependencies**: Ninguna dependencia de software nueva. Se reutiliza la sintaxis Mermaid ya
usada en la documentación del proyecto (compatible con Word/PDF vía conversión posterior, ej.
Pandoc o la skill `docx`).

**Storage**: N/A — el único artefacto persistente es el archivo `docs/Manual_de_Usuario.md` (y, en
una sesión posterior fuera de este alcance, su conversión a `docs/Manual_de_Usuario.docx`).

**Testing**: N/A — no aplica suite de pruebas automatizada. La validación es una revisión de
contenido contra `quickstart.md` (checklist de lectura) y contra el catálogo de estados/roles de
`.specify/memory/constitution.md`.

**Target Platform**: Documento Markdown legible en cualquier visor estándar (GitHub, VS Code,
editores Markdown) y convertible a Word/PDF.

**Project Type**: Documentación (no aplica la clasificación library/cli/web-service de proyectos de
código).

**Performance Goals**: N/A.

**Constraints**: 
- No modificar código de `backend/` ni `frontend/` (alcance estrictamente documental).
- No ejecutar pruebas unitarias ni de integración.
- No escanear el repositorio de forma masiva; solo inspeccionar los modelos/rutas/componentes de UI
  estrictamente necesarios para describir cada flujo/vista con precisión.
- Mantener consistencia terminológica exacta con la Constitución y las specs 001-024 (nombres de
  estado, roles, campos visibles).

**Scale/Scope**: Un único documento (`docs/Manual_de_Usuario.md`) con ~8-10 secciones principales:
resumen arquitectónico, 3 diagramas de flujo, y guía paso a paso de 6 vistas (Dashboard, Kanban, Mis
Tareas, Detalle de Ticket, Vista del Cliente/Encargado, Módulo de RRHH).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Aplica a esta feature | Evaluación |
|-----------|------------------------|------------|
| I. API-First y Dominio Primero | No (no se crean/modifican endpoints) | PASS — el manual solo describe endpoints/contratos ya existentes, no los cambia |
| II. Clean Architecture 3 capas | No (no se toca código) | PASS — sin impacto, no se crean componentes ni servicios |
| III. Tipado estricto | No (no hay código TS/Python nuevo) | PASS |
| IV. Seguridad en profundidad | No directamente, pero el manual NO debe filtrar secretos, credenciales ni detalles internos de seguridad (variables `.env`, JWT interno) | PASS — se documentará solo la experiencia de usuario (login SSO, roles), sin exponer configuración de seguridad |
| V. Gobernanza de librerías | No (no se añade ninguna dependencia a `package.json`/`requirements.txt`) | PASS |
| VI. AI-Native | No directamente aplicable, pero el manual debe usar la misma nomenclatura de skills/roles/tipos de comentario estructurados que exige este principio | PASS — FR-012 exige consistencia terminológica |
| VII. Alcance de sesión, testing ultra-limitado y eficiencia de tokens | **Sí, es el principio rector de esta sesión** | PASS — el plan confirma: sin refactors externos, sin ejecución de pruebas, lectura acotada a lo necesario para describir el flujo de usuario |

No hay violaciones. No se requiere tabla de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/025-manual-usuario-integral/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
docs/
├── Manual_de_Usuario.md    # Entregable principal de esta feature (nuevo/actualizado)
├── Manual_de_Usuario.docx  # Documento binario existente; su actualización queda como paso
│                            # manual/posterior (conversión desde el .md), fuera de esta sesión
└── MER.md                  # Referencia existente de modelo de datos (fuente para el resumen
                             # arquitectónico, solo lectura)
```

**Structure Decision**: Documentación pura dentro de `docs/`. No se crea estructura de código nueva
(no aplica `src/`, `backend/`, `frontend/` para esta feature). El único artefacto de código fuente
tocado es el archivo Markdown del manual; no se generan contratos de API ni componentes.

## Complexity Tracking

*No aplica — sin violaciones de la Constitution Check.*
