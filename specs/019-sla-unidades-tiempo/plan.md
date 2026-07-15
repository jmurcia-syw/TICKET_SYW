# Implementation Plan: Unidades de tiempo (minutos/horas/días) al configurar SLA

**Branch**: `develp_Jp` (sin rama dedicada por feature en este repo) | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/019-sla-unidades-tiempo/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Agregar, exclusivamente al campo "Tiempo límite de diagnóstico, análisis y ejecución" del
formulario de reglas de SLA (`SlaRuleForm.tsx`), un selector de unidad (minutos / horas / días)
que convierte el valor ingresado a minutos antes de guardar — sin tocar el modelo de datos, el
contrato de API ni el motor de cómputo de SLA (spec 014-sla-tickets-tareas), que siguen operando
exclusivamente sobre `execution_minutes` en minutos enteros. El campo "Tiempo límite de contacto"
no cambia. Es una funcionalidad **100% frontend**, acotada a un componente y un ajuste mínimo en
su contenedor.

## Technical Context

**Language/Version**: TypeScript 5 (strict) sobre React 19, sin cambios de versión.

**Primary Dependencies**: Ant Design 5 (`InputNumber`, `Select`, `Space.Compact`, `Form`) —
componentes ya usados en el propio `SlaRuleForm.tsx`; ninguna dependencia nueva (Principio V).

**Storage**: N/A — sin migraciones ni cambios de esquema. `execution_minutes` sigue siendo la
misma columna entera en `sla_rules` (`backend/infra/models/sla_rule_model.py`); la conversión de
unidades ocurre enteramente en el cliente antes de enviar el `PATCH`/`POST` ya existente.

**Testing**: El frontend no tiene suite de tests automatizados configurada (mismo hallazgo que la
spec 006-ticket-detalle-tiempo-ui): no hay Vitest/Jest en `package.json`. La validación es
`npx tsc -b` (typecheck) + verificación manual guiada por `quickstart.md`. No aplica pytest porque
no se toca el backend.

**Target Platform**: Navegador web (misma SPA existente).

**Project Type**: Web application (frontend + backend ya detectados) — esta funcionalidad solo
toca `frontend/`.

**Performance Goals**: Sin objetivo nuevo; la conversión de unidades es aritmética trivial en
cliente (multiplicaciones/divisiones simples), sin impacto perceptible.

**Constraints**: Cero cambios de contrato de API, de dominio (`sla_service.py`) o de base de datos
(FR-002/FR-007 del spec). Alcance mínimo explícitamente pedido por el usuario ("NO es necesario
ajustar toda la estructura"): solo `SlaRuleForm.tsx` y un ajuste mínimo en `SlaRulesPage.tsx` para
forzar la reinicialización del estado local de unidad al abrir el formulario (ver research.md
Decisión 4).

**Scale/Scope**: 1 componente modificado (`SlaRuleForm.tsx`), 1 ajuste mínimo en su contenedor
(`SlaRulesPage.tsx`). Ningún archivo de `backend/` ni de `types/sla.ts` cambia (el shape de
`SlaRuleFormData` permanece igual: `execution_minutes: number`, siempre en minutos).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I (API-First / Dominio primero)**: N/A — no se toca dominio, `sla_service.py` ni se
  agrega/modifica ningún endpoint; el contrato `contracts/sla-contract.md` (spec 014) no cambia.
  **PASS**.
- **Principio II (Clean Architecture 3 capas)**: El cambio vive exclusivamente en
  `frontend/src/components/sla/SlaRuleForm.tsx` (componente de presentación) y un ajuste mínimo de
  estado en `frontend/src/pages/SlaRulesPage.tsx`. La conversión de unidades es lógica de
  presentación (formato de entrada), no lógica de negocio de SLA — el dominio del SLA
  (`sla_service.py`) sigue operando exclusivamente en minutos. **PASS**.
- **Principio III (Tipado estricto)**: Todo el código nuevo en TypeScript strict, sin `any`. El
  tipo `SlaRuleFormData` no cambia (sigue siendo `execution_minutes: number`). **PASS**.
- **Principio IV (Seguridad en profundidad)**: Sin cambios de autenticación/autorización; se
  reutiliza el permiso `sla_rules:manage` ya vigente que controla quién ve el formulario. **PASS**.
- **Principio V (Gobernanza de librerías)**: No se agrega ninguna dependencia nueva; se reutilizan
  `InputNumber`, `Select` y `Space.Compact` de Ant Design 5, ya presentes en el proyecto. **PASS**.
- **Principio VI (AI-Native)**: N/A — no hay endpoints de acción crítica ni datos de entrenamiento
  involucrados en este cambio puramente de presentación. **PASS**.
- **Principio VII (Alcance de sesión / testing ultra-limitado)**: El cambio se acota estrictamente
  a los 2 archivos identificados arriba; no se ejecuta ninguna suite de tests global (no existe
  suite de frontend en este repo) y no se toca el backend. **PASS**.

**Resultado**: Sin violaciones. No se requiere entrada en "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/019-sla-unidades-tiempo/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No se genera carpeta `contracts/`: esta funcionalidad no agrega ni modifica ningún endpoint ni
contrato de API (ver Constitution Check, Principio I) — el contrato de reglas de SLA ya documentado
en `specs/014-sla-tickets-tareas/contracts/sla-contract.md` no cambia.

### Source Code (repository root)

Proyecto tipo "Web application" ya establecido (`backend/` + `frontend/`). Esta funcionalidad solo
toca `frontend/src/`:

```text
frontend/src/
├── components/
│   └── sla/
│       └── SlaRuleForm.tsx   # MODIFICADO: el campo "Tiempo límite de diagnóstico, análisis y
│                              # ejecución" pasa de un único InputNumber (minutos) a un
│                              # InputNumber + Select de unidad (minutos/horas/días), con un
│                              # Form.Item oculto (`execution_minutes`) que sigue siendo la
│                              # fuente de verdad en minutos consumida por onFinish. El campo
│                              # "Tiempo límite de contacto" no cambia.
└── pages/
    └── SlaRulesPage.tsx      # MODIFICADO MÍNIMO: agrega un contador incremental
                               # (`formResetToken`) usado como `key` de `SlaRuleForm`, para forzar
                               # que el componente reinicialice su estado local de unidad/monto
                               # cada vez que se abre para crear o editar una regla.
```

**Structure Decision**: Se mantiene la estructura ya vigente del proyecto
(`components/sla/`, `pages/`). No se crean carpetas ni archivos nuevos; el cambio es una
modificación acotada de un componente existente y un ajuste mínimo de su contenedor. No hay
cambios en `backend/` ni en `frontend/src/types/sla.ts` o `frontend/src/services/slaService.ts`.

## Complexity Tracking

*Sin violaciones de la Constitution Check — tabla no aplica.*
