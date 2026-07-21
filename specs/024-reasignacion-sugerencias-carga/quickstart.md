# Quickstart: Sugerencias de Carga y Disponibilidad en la Reasignación

## Prerrequisitos

- Stack levantado con Docker Compose (`docker compose up -d`).
- Un Ticket ya asignado a un Resolutor (para probar reasignación, spec 023).
- Al menos 2 Recursos activos adicionales con distinta carga de tickets abiertos entre sí.
- Idealmente, un Recurso actualmente fuera de horario, en festivo o con una ausencia aprobada
  vigente (para ver la etiqueta de no disponibilidad).

## Escenario 1 — Carga de trabajo visible al reasignar (US1)

1. Abrir el detalle del ticket y click en "Reasignar".
2. **Verificar**: cada candidato del selector muestra su cantidad de tickets abiertos.
3. **Verificar**: los candidatos aparecen ordenados de menor a mayor carga.
4. **Verificar**: el candidato con menor carga tiene el badge "Menor carga".
5. Comparar contra el modal de asignación inicial ("Asignar (Triage)" en un ticket sin asignar
   todavía) — el mismo recurso debe mostrar la misma carga y el mismo orden relativo en ambos
   modales.

## Escenario 2 — Disponibilidad visible al reasignar (US2)

1. Con un Recurso fuera de horario/festivo/ausente configurado, abrir "Reasignar".
2. **Verificar**: ese candidato muestra la etiqueta de no disponibilidad con el motivo correcto
   ("Fuera de horario", "Festivo" o "Ausencia aprobada").
3. Seleccionar igualmente ese candidato y confirmar la reasignación.
4. **Verificar**: la reasignación se completa con éxito (200) — la etiqueta no bloqueó la acción.

## Validación de código (alcance acotado, Principio VII)

- Frontend: verificación manual en navegador de ambos modales (Asignar y Reasignar) — sin
  suite de tests nueva (no hay lógica de dominio backend involucrada).
- Confirmar con `npx tsc -b --noEmit` que el refactor de `AssignModal.tsx` no rompe tipos.
