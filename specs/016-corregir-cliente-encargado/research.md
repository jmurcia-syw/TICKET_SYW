# Research: Corregir el Cliente de un Usuario/cliente y desambiguar Proyectos homónimos

**Feature**: `016-corregir-cliente-encargado` · **Date**: 2026-07-14

No hay `[NEEDS CLARIFICATION]` pendientes del spec — este documento registra las decisiones de
diseño, verificadas contra el código de spec 015 escrito en la sesión anterior (no se asumió).

## Decisión 1 — Dónde vive el bug reportado

**Hallazgo** (verificado en código): `client_contacts.client_id` se fija en el alta y nunca se
actualiza después. El endpoint `POST /api/client-contacts/{contact_id}/projects`
(`backend/api/routes/client_contacts.py:296-...`) siempre exige que el Proyecto a agregar
resuelva al mismo `client_id` ya guardado en el contacto (`resolve_common_client` seguido de
comparación estricta), **sin excepción** aunque el contacto tenga 0 Proyectos activos en ese
momento. El frontend (`ClientContactsPage.tsx`, selector "Agregar proyecto") refuerza esto
filtrando `projects.filter(p => p.client_id === managingContact.client_id)` — con 0 Proyectos
asignados, ese filtro sigue acotado al Cliente original, dejando al Admin sin salida.

**Decisión**: relajar la regla **solo** cuando el contacto tiene 0 membresías de Proyecto
activas en el momento de agregar uno: en ese caso, el Proyecto agregado puede ser de cualquier
Cliente, y ese Cliente pasa a ser el nuevo `client_id` del contacto. Con 1+ Proyectos ya
asignados, la regla estricta de spec 015 (mismo Cliente) se mantiene sin cambios.

**Alternativas consideradas**:
- Permitir editar el Cliente directamente en un campo separado (sin pasar por Proyecto) —
  rechazada: rompe el patrón ya establecido (spec 010/015) de que el Cliente siempre se deriva
  de los Proyectos asignados; introduciría una segunda fuente de verdad.
- Permitir "forzar" un cambio de Cliente aunque haya Proyectos activos de otro Cliente (con
  confirmación) — rechazada por alcance: el spec deliberadamente solo cubre el caso de 0
  Proyectos (ver Assumptions), que es exactamente el escenario reportado (el Admin ya quitó el
  Proyecto equivocado antes de intentar corregir).

## Decisión 2 — Cómo determinar "0 Proyectos" en el backend

**Decisión**: reutilizar `ProjectMemberRepository.list_project_ids_by_user(contact.user_id)`
(ya existe, spec 010) dentro del endpoint de agregar Proyecto — si la lista viene vacía, se
habilita la corrección de Cliente; si no, se mantiene la validación estricta actual.

**Rationale**: evita una consulta nueva; el método ya existe y es exactamente lo que se
necesita (ignora si el Proyecto de origen sigue activo o no — cualquier membresía cuenta).

## Decisión 3 — Persistir la corrección de Cliente

**Decisión**: nuevo método `ClientContactRepository.update_client_id(contact_id, client_id)`
(`UPDATE client_contacts SET client_id = ...`), invocado por el endpoint de agregar Proyecto
justo antes de crear la membresía, solo cuando el contacto tenía 0 Proyectos y el Proyecto
agregado resuelve a un Cliente distinto del actual.

## Decisión 4 — Mostrar el Cliente en el selector de "agregar Proyecto"

**Hallazgo**: el selector de creación (`Form.Item name="project_ids"`) ya construye la etiqueta
como `` `${p.client_name} — ${p.name}` `` (spec 015) — el problema reportado es específico del
selector de **agregar Proyecto** dentro del modal "Gestionar proyectos", que hoy usa solo
`p.name` (`ClientContactsPage.tsx` ~línea 219).

**Decisión**: usar la misma construcción de etiqueta (`Cliente — Proyecto`) en ese selector,
sin importar si está acotado a un Cliente o abierto a todos (consistencia, US2 escenario 2).

## Decisión 5 — Refetch tras agregar el primer Proyecto

**Hallazgo**: `handleAddProject` (`ClientContactsPage.tsx` ~línea 82) recarga la lista filtrando
por `client_id: managingContact.client_id` (el Cliente **anterior**) para releer el contacto
actualizado — si el Cliente cambió, ese filtro ya no encuentra la fila y el modal no refleja la
corrección.

**Decisión**: refetchear filtrando por `email` del contacto (único, estable) en lugar de por
`client_id`, para que el refetch funcione sin importar si el Cliente cambió.
