# Feature Specification: Sugerencias de Carga y Disponibilidad en la Reasignación

**Feature Branch**: `024-reasignacion-sugerencias-carga`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "la reasignación debe contener la mismas sugerencias como la carga y disponibilidad, como la asignación inicial"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver carga de trabajo al elegir el nuevo resolutor (Priority: P1)

Como Jefe de equipo que reasigna un ticket (spec 023), quiero ver cuántos tickets abiertos tiene cada candidato a resolutor y cuál tiene la menor carga, igual que cuando hago la asignación inicial (Triage Push), para elegir un nuevo resolutor sin sobrecargar a nadie ni tener que consultar el Panel de Asignación por separado.

**Why this priority**: Es la ayuda que más directamente evita el problema que la reasignación busca resolver (error de asignación o escalamiento) — reasignar sin ver la carga puede simplemente trasladar el problema a otro resolutor ya sobrecargado.

**Independent Test**: Puede probarse abriendo el modal de reasignación de un ticket y verificando que cada candidato muestra su cantidad de tickets abiertos, ordenados de menor a mayor carga, y que el de menor carga está marcado visualmente — sin depender de la disponibilidad horaria.

**Acceptance Scenarios**:

1. **Given** un ticket en proceso de reasignación con varios recursos activos disponibles, **When** el usuario abre el selector de nuevo resolutor, **Then** cada candidato muestra su carga actual (cantidad de tickets abiertos) y la lista aparece ordenada de menor a mayor carga por defecto.
2. **Given** el selector de reasignación abierto, **When** el usuario lo revisa, **Then** el candidato con menor carga está identificado visualmente (mismo indicador "Menor carga" que usa la asignación inicial).

---

### User Story 2 - Ver disponibilidad horaria al elegir el nuevo resolutor (Priority: P2)

Como Jefe de equipo que reasigna un ticket, quiero ver si un candidato a resolutor está actualmente fuera de horario, de vacaciones/ausente o en un festivo, igual que en la asignación inicial, para evitar reasignar a alguien que no podrá atender el ticket de inmediato (aunque la reasignación no se bloquea por esto).

**Why this priority**: Complementa la carga con una segunda señal de contexto real; depende de los mismos datos que ya usa la asignación inicial, pero es un valor agregado secundario frente a ver la carga (US1).

**Independent Test**: Puede probarse abriendo el selector de reasignación con al menos un candidato actualmente fuera de horario/festivo/ausente, y verificando que ese candidato muestra la etiqueta de no disponible con el motivo correspondiente, mientras la reasignación sigue siendo posible.

**Acceptance Scenarios**:

1. **Given** un candidato a resolutor que está en una ausencia aprobada en este momento, **When** el usuario abre el selector de reasignación, **Then** ese candidato muestra una etiqueta de "no disponible" con el motivo "Ausencia aprobada".
2. **Given** un candidato fuera de su horario laboral o en un festivo de su país, **When** el usuario abre el selector, **Then** se muestra la etiqueta correspondiente ("Fuera de horario" o "Festivo").
3. **Given** un candidato marcado como no disponible, **When** el usuario lo selecciona y confirma la reasignación, **Then** la reasignación se completa igual (la disponibilidad es informativa, nunca bloquea — mismo criterio que la asignación inicial).

### Edge Cases

- ¿Qué pasa si un candidato no tiene país/huso horario configurado? No se muestra etiqueta de disponibilidad para ese candidato (sin datos suficientes para evaluarla), igual que en la asignación inicial.
- ¿Qué pasa si el servicio de disponibilidad falla o tarda? El selector de reasignación igual debe mostrar la carga y permitir reasignar; la disponibilidad es una mejora informativa que no debe bloquear ni impedir la acción principal.
- ¿Qué pasa si dos candidatos tienen la misma carga? Se muestra igualmente el orden ascendente estable; solo uno (el primero en ese orden) queda marcado como "Menor carga".
- El resolutor actualmente asignado al ticket ya no aparece en la lista de candidatos (regla existente de la reasignación, spec 023) — la carga/disponibilidad solo aplica a los candidatos restantes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El selector de nuevo resolutor en la reasignación DEBE mostrar, para cada candidato, su carga de trabajo actual (cantidad de tickets abiertos), con el mismo criterio de cálculo que usa la asignación inicial.
- **FR-002**: El selector de reasignación DEBE ordenar los candidatos de menor a mayor carga por defecto, igual que la asignación inicial.
- **FR-003**: El selector de reasignación DEBE marcar visualmente al candidato con menor carga (indicador "Menor carga"), igual que la asignación inicial.
- **FR-004**: El selector de reasignación DEBE mostrar una etiqueta de no disponibilidad (con motivo: fuera de horario, festivo o ausencia aprobada) para los candidatos que no estén disponibles en el momento de abrir el selector, igual que la asignación inicial.
- **FR-005**: La indicación de no disponibilidad NO DEBE bloquear la reasignación hacia ese candidato — es únicamente informativa, igual que en la asignación inicial.
- **FR-006**: El selector de reasignación DEBE seguir permitiendo buscar/filtrar candidatos por nombre.
- **FR-007**: El cálculo de carga y de disponibilidad NO DEBE duplicarse ni divergir del ya usado por la asignación inicial — misma fuente de datos y mismo criterio de vigencia (en el momento de abrir el selector).

### Key Entities

- No se introducen entidades nuevas. Esta feature reutiliza, en la reasignación (spec 023), los mismos datos de carga de trabajo (tickets abiertos por recurso) y disponibilidad (horario efectivo, festivos, ausencias) ya calculados y expuestos para la asignación inicial (specs 010 y 020).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede identificar al candidato con menor carga dentro del selector de reasignación en menos de 3 segundos, sin salir del diálogo ni consultar el Panel de Asignación por separado.
- **SC-002**: El 100% de los candidatos con carga registrada muestran su cantidad de tickets abiertos en el selector de reasignación.
- **SC-003**: El 100% de los candidatos actualmente no disponibles (fuera de horario, festivo o ausencia) muestran la etiqueta correspondiente cuando el dato de disponibilidad está disponible.
- **SC-004**: El 100% de las reasignaciones hacia un candidato marcado como no disponible se completan igualmente (la disponibilidad nunca bloquea la acción).

## Assumptions

- "Las mismas sugerencias" se interpreta como reutilizar tal cual la carga de trabajo y la disponibilidad ya mostradas en el modal de asignación inicial (Triage Push) — no se agregan señales nuevas (por ejemplo, no se incluye aquí una recomendación por IA/skills, que sigue fuera de alcance según la asignación inicial).
- No se requiere ningún endpoint ni cálculo de backend nuevo: la carga y la disponibilidad ya se calculan y exponen para la asignación inicial: esta feature es exclusivamente de reutilización en la interfaz de reasignación (spec 023).
- El resolutor actualmente asignado sigue excluido de la lista de candidatos de reasignación, regla ya vigente y fuera de alcance de este cambio.
