# Tasks: Corregir el Cliente de un Usuario/cliente y desambiguar Proyectos homónimos

**Input**: Design documents from `specs/016-corregir-cliente-encargado/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos y **dirigidos** (Principio VII): se agregan al archivo ya existente
`backend/tests/api/test_client_contacts_projects.py` (spec 015) — sin archivo nuevo, sin
fixtures de Resolutor, sin disparo de correo (misma restricción de spec 015).

**Restricción de alcance** (misma directriz de spec 015, 2026-07-14): fixtures limitados a
Clientes y Proyectos ya existentes o creados mínimamente; prohibido crear usuarios Resolutor o
disparar el flujo de correo de contraseña.

**Organización**: tareas agrupadas por User Story. Orden de ejecución: US1 (P1, corregir Cliente
con 0 Proyectos) → US2 (P1, mostrar Cliente en el selector). Sin migraciones ni endpoints nuevos
— ambas historias modifican los mismos 3 archivos que tocó spec 015.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] corregir Cliente con 0 Proyectos, [US2] desambiguar Proyectos homónimos en
  el selector

---

## Phase 1: Setup

- [X] T001 Confirmar que no se requieren dependencias nuevas (Principio V): sin cambios en
  `backend/requirements.txt` ni `frontend/package.json` (ver plan.md Technical Context)

**Checkpoint**: sin cambios de dependencias.

---

## Phase 2: User Story 1 — Corregir el Cliente con 0 Proyectos asignados (Priority: P1) 🎯 MVP

**Goal**: cuando un Usuario/cliente queda con 0 Proyectos, el Admin puede agregarle un Proyecto
de cualquier Cliente y ese Cliente pasa a ser el del contacto (corrigiendo un alta equivocada).

**Independent Test**: Escenarios 1 y 2 del quickstart. Puede probarse íntegramente contra la API
(`POST /api/client-contacts/{id}/projects` con un Proyecto de otro Cliente, contacto en 0
Proyectos → 201 y Cliente corregido) sin depender de los cambios de etiqueta de US2.

### Implementation for User Story 1

- [X] T002 [US1] `backend/infra/repositories/client_contact_repo.py` += método
  `update_client_id(contact_id: uuid.UUID, client_id: uuid.UUID) -> None` (`UPDATE
  client_contacts SET client_id = :client_id WHERE id = :contact_id`, commit incluido)
- [X] T003 [US1] `backend/api/routes/client_contacts.py`, método `ClientContactProjects.post`:
  antes de la comparación estricta de Cliente, obtener `existing_project_ids =
  ProjectMemberRepository(db).list_project_ids_by_user(contact.user_id)`; si viene vacía,
  **omitir** el rechazo 400 por Cliente distinto y en su lugar, si `resolved_client_id !=
  contact.client_id`, llamar `ClientContactRepository(db).update_client_id(contact.id,
  resolved_client_id)` y actualizar `contact.client_id = resolved_client_id` en memoria antes de
  continuar; si la lista NO viene vacía, mantener el rechazo 400 actual (spec 015, sin cambios).
  Actualizar también los textos de `@ns.response(400, ...)` y el docstring del método para
  reflejar la nueva condición (depende de T002)
- [X] T004 [P] [US1] `frontend/src/pages/ClientContactsPage.tsx`: en el `<Select>` de "agregar
  Proyecto" del modal "Gestionar proyectos", el `.filter(...)` deja de exigir `p.client_id ===
  managingContact.client_id` cuando `managingContact.projects.length === 0` (en ese caso, se
  ofrecen Proyectos activos de **cualquier** Cliente); cuando `managingContact.projects.length >
  0`, se mantiene el filtro acotado al Cliente actual (comportamiento de spec 015 sin cambios)
- [X] T005 [US1] `frontend/src/pages/ClientContactsPage.tsx` (mismo archivo que T004,
  secuencial): en `handleAddProject`, el refetch tras agregar cambia de
  `clientContactService.list({ page_size: 200, client_id: managingContact.client_id })` a
  `clientContactService.list({ page_size: 200, email: managingContact.email })`, para que la
  búsqueda encuentre al contacto aunque su Cliente haya cambiado (depende de T004, mismo
  archivo)
- [X] T006 [US1] `backend/tests/api/test_client_contacts_projects.py` += (mismos fixtures que
  spec 015, sin Resolutor ni correo): `test_add_project_different_client_when_zero_projects_corrects_client`
  — contacto creado con `project_a`, se quita ese Proyecto (0 Proyectos), se agrega
  `project_other_client` → 201; `GET /api/client-contacts?client_id=<other_client>` incluye
  ahora al contacto y `?client_id=<ticket_client>` ya no. Confirmar (sin duplicar) que
  `test_add_project_different_client_returns_400` (ya existente, contacto con 1 Proyecto) sigue
  en verde — valida que la regla estricta de spec 015 no cambió con 1+ Proyectos. Correr solo
  este archivo: `docker exec sywork_backend pytest tests/api/test_client_contacts_projects.py -v`
  (depende de T003)

**Checkpoint US1**: Escenarios 1 y 2 del quickstart ejecutables end-to-end.

---

## Phase 3: User Story 2 — Mostrar el Cliente junto al Proyecto en el selector (Priority: P1)

**Goal**: el selector de "agregar Proyecto" distingue Proyectos homónimos de Clientes distintos
(ej. dos "SOPORTE"), mostrando siempre "Cliente — Proyecto".

**Independent Test**: Escenario 3 del quickstart. Probable de forma independiente inspeccionando
el texto de las opciones del selector, sin importar si el filtro está acotado a un Cliente o
abierto a todos (US1).

### Implementation for User Story 2

- [X] T007 [US2] `frontend/src/pages/ClientContactsPage.tsx` (mismo archivo que T005,
  secuencial): las opciones del `<Select>` de "agregar Proyecto" pasan de `label: p.name` a
  `label: p.client_name ? \`${p.client_name} — ${p.name}\` : p.name` (mismo formato que el
  selector de alta, spec 015); actualizar el placeholder del selector (ya no dice "mismo
  Cliente" de forma incondicional, dado que con 0 Proyectos puede ser cualquiera) (depende de
  T005, mismo archivo)

**Checkpoint US2**: Escenario 3 del quickstart ejecutable end-to-end.

---

## Phase 4: Polish y validación transversal

- [X] T008 [P] Swagger revisado contra `contracts/client-contacts-delta.md`: descripciones de
  `POST /api/client-contacts/{id}/projects` reflejan la condición de "0 Proyectos ⇒ cualquier
  Cliente"
- [X] T009 Ejecutar `quickstart.md` (Escenarios 1-4) contra Docker real
- [X] T010 Validación dirigida de cierre (NUNCA la suite completa — Principio VII): `docker exec
  sywork_backend pytest tests/api/test_client_contacts_projects.py -v`; `cd frontend && npx tsc
  -b` → sin errores

**Checkpoint Final**: quickstart completo en verde y tests dirigidos en verde.

---

## Dependencies & Execution Order

```
Phase 1 (T001)
→ Phase 2 / US1 (T002 → T003 → T006; T004[P] → T005)
→ Phase 3 / US2 (T007 [mismo archivo que T005, tras T005])
→ Phase 4 (T008[P], T009, T010)
```

- T004/T005/T007 son el mismo archivo (`ClientContactsPage.tsx`) — dependencia de archivo, no de
  dominio: T004 (US1, desbloquear filtro) y T007 (US2, etiqueta) son cambios independientes en
  el mismo bloque de JSX, aplicados secuencialmente para evitar conflictos de edición.
- US1 es funcionalmente completa sin US2 (se puede corregir el Cliente aunque el selector no
  muestre el Cliente de cada opción); US2 mejora la usabilidad y reduce el riesgo de repetir el
  error, pero no bloquea a US1.

## Parallel Example: User Story 1

```bash
# En paralelo tras Phase 1:
Task: "update_client_id en client_contact_repo.py"        # T002 (backend)
Task: "Desbloquear filtro en ClientContactsPage.tsx"       # T004 (frontend, archivo distinto)
```

---

## Implementation Strategy

1. **MVP = Phase 1 + Phase 2 (US1)** — resuelve el bloqueo reportado (Cliente irrecorregible)
   sin necesidad todavía de las etiquetas de desambiguación.
2. Incremento 1: US2 (etiqueta Cliente — Proyecto) — cierra el riesgo de repetir el error al
   corregir, especialmente con Proyectos homónimos entre Clientes.
3. Sin riesgo de migración ni de endpoints nuevos: todo el cambio es lógica de aplicación sobre
   los mismos 3 archivos de spec 015.

## Notes

- [P] = archivos distintos, sin dependencias incompletas
- Commitear después de cada tarea o grupo lógico
- Detenerse en cada checkpoint para validar la story de forma independiente
- **Directriz estricta**: no tocar archivos fuera de los listados y no ejecutar la suite
  completa de tests durante el desarrollo (Principio VII)
