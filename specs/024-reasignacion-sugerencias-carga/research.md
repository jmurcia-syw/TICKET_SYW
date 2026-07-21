# Research: Sugerencias de Carga y Disponibilidad en la Reasignación

## Decisión 1 — Extraer hook de datos + grid de tarjetas en vez de duplicar `AssignModal`

**Decisión**: Se extraen dos piezas nuevas de `frontend/src/components/tickets/AssignModal.tsx`
(spec 010, US2, ya en producción):
- `useResourceCandidates.ts`: hook que hace las mismas tres llamadas que hoy hace `AssignModal`
  en su `useEffect` (`resourceService.list({active:true, page_size:100})`,
  `ticketService.panel()` para el mapa de carga por recurso, y
  `calendarService.getAvailability()` para el mapa de disponibilidad), y devuelve
  `{resources, workload, availability}`.
- `ResourceCandidateGrid.tsx`: el grid de tarjetas clicables (avatar, nombre, skills, badge
  "Menor carga", barra de carga coloreada, etiqueta de no disponibilidad) que hoy está inline en
  el JSX de `AssignModal` (líneas ~132-199 de la versión actual).

`AssignModal` se refactoriza para consumir ambas piezas (mismo comportamiento, mismo output
visual — verificado manualmente); `ReassignModal` las reutiliza para cumplir FR-001 a FR-004 sin
reimplementar la lógica de orden/badge/etiqueta.

**Rationale**: La spec pide explícitamente "las mismas sugerencias... como la asignación
inicial". Copiar/pegar ~70 líneas de lógica de ordenamiento + tarjetas en `ReassignModal`
crearía dos fuentes de verdad que divergirían con el tiempo (p. ej. si mañana cambia el criterio
de "menor carga" solo se actualizaría un archivo). Extraer es el camino más simple que evita esa
divergencia sin tocar el backend ni el modelo de datos.

**Alternatives considered**:
- Duplicar la lógica directamente en `ReassignModal` (copy-paste) → descartado: es exactamente
  el tipo de duplicación que dos módulos con "las mismas sugerencias" tienden a desincronizar.
- Crear un directorio `hooks/` global nuevo a nivel de `frontend/src/` → descartado por ahora:
  la Constitución no lista `hooks/` en la convención de estructura vigente y con un solo caso de
  reutilización (2 consumidores, ambos en `components/tickets/`) no se justifica introducir una
  convención de carpetas nueva; el hook se coloca colocado junto a sus consumidores.
- Convertir `ResourceCandidateGrid` en un componente genérico reusable fuera de `tickets/` (p.
  ej. en un futuro selector de recursos en otras pantallas) → descartado por alcance: no hay hoy
  un segundo caso de uso fuera de asignación/reasignación de tickets; se puede promover más
  adelante si aparece.

## Decisión 2 — Sin backend nuevo, sin tests backend nuevos

**Decisión**: No se toca ningún endpoint ni repositorio de backend. Las tres fuentes de datos
(recursos activos, carga por recurso, disponibilidad) ya existen y ya están autorizadas/probadas
para la asignación inicial (specs 010, 020); esta feature solo cambia cómo se presentan en la
reasignación.

**Rationale**: Coherente con el Assumptions de la spec ("no se requiere ningún endpoint ni
cálculo de backend nuevo") y con el Principio VII (alcance acotado, sin tests innecesarios —
no hay lógica de dominio nueva que testear en Python).

**Alternatives considered**:
- Crear un endpoint agregado `/api/tickets/{id}/reassign-candidates` que combine las tres
  respuestas en una sola llamada → descartado por sobre-ingeniería: no hay problema de
  performance reportado y agregaría superficie de API nueva para un beneficio marginal (una
  llamada de red menos en un modal ya de por sí rápido).
