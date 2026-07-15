# Tasks: Accesos y conexiones múltiples del Cliente

**Input**: Design documents from `specs/018-cliente-accesos-conexiones/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos y **dirigidos** (Principio VII): un solo archivo de test nuevo
(`backend/tests/api/test_client_access_api.py`), ampliado incrementalmente por cada historia,
≤10 registros por caso.

**Restricción de alcance en pruebas/fixtures** (misma directriz de specs 015/016/017): fixtures
limitados a los Clientes que participan del flujo (creados mínimamente, sin datos de otros
maestros). Prohibido crear usuarios Resolutor adicionales como fixture o disparar el flujo de
correo de contraseña.

**Organización**: tareas agrupadas por User Story. Orden de ejecución: US1 (P1, registrar
accesos múltiples) → US2 (P1, aislamiento entre clientes) → US3 (P2, enmascarado por defecto).
Las tres comparten el modelo de datos y la migración de la fase Foundational.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias incompletas)
- **[Story]**: [US1] registrar accesos, [US2] aislamiento entre clientes, [US3] enmascarado por defecto

---

## Phase 1: Setup

**Purpose**: Sin dependencias nuevas que instalar (Constitución Principio V) — Ant Design
(`Tabs`, `Input.Password`) y SQLAlchemy/Alembic ya están aprobados y en uso en el repo.

- [X] T001 Confirmar que no se requieren cambios en `frontend/package.json` ni en
  `backend/requirements.txt` (plan.md, Constitution Check, Principio V) — sin acción de código,
  solo verificación antes de arrancar Foundational

**Checkpoint**: nada que instalar — se puede pasar directo a Foundational.

---

## Phase 2: Foundational (bloqueante para US1, US2 y US3)

**Purpose**: Modelo de datos, migración, generalización de adjuntos y capa de repositorio
compartidos por las tres historias — ninguna es usable sin esta fase.

- [X] T002 `backend/domain/entities/client.py`: agregar `@dataclass ClientAccess` (id, client_id,
  access_type, environment, username, password, host, notes, created_at, updated_at) — mismo
  estilo que `ClientSystem` (data-model.md)
- [X] T003 `backend/domain/entities/client.py`: agregar `@dataclass ClientAccessAttachment` (id,
  client_id, filename, content_type, size_bytes, storage_path, created_at) (depende de T002,
  mismo archivo)
- [X] T004 `backend/infra/models/client_model.py`: agregar `ClientAccessModel` (columnas de
  data-model.md, `password` cifrado con el mismo mecanismo que `vpn_credentials`,
  `to_entity(include_sensitive)`/`from_entity()`) (depende de T002)
- [X] T005 `backend/infra/models/client_model.py`: agregar `ClientAccessAttachmentModel`
  (columnas de data-model.md, `to_entity()`/`from_entity()`) (depende de T003, T004 — mismo
  archivo)
- [X] T006 [P] `backend/infra/storage/attachments.py`: generalizar `save()`/`open_path()` para
  aceptar un parámetro de tipo de entidad (`"tickets"` | `"clients"`) en vez de hardcodear
  `"tickets"` en la ruta — actualizar los call sites existentes de Tickets para pasar
  `"tickets"` explícito, sin cambiar su comportamiento (research.md Decisión 2)
- [X] T007 Migración `backend/infra/migrations/versions/030_client_access.py` (down_revision
  `"029"`): `CREATE TABLE client_access`, `CREATE TABLE client_access_attachments`; data
  migration en la misma transacción: por cada `clients` con `vpn_ips`/`vpn_credentials` no
  nulos, insertar un `client_access` tipo `vpn` (`host`=`vpn_ips` desencriptado,
  `password`=`vpn_credentials` desencriptado); `downgrade()` reconstruye ambas columnas desde el
  primer `client_access` tipo `vpn` de cada cliente y elimina las tablas (data-model.md, "Notas
  de migración") (depende de T004, T005)
- [X] T008 Migración `backend/infra/migrations/versions/031_client_access_rls.py`
  (down_revision `"030"`): habilitar RLS + policy `*_app_access` en `client_access` y
  `client_access_attachments`, mismo patrón que `020_client_contacts_rls.py` (research.md
  Decisión 5) (depende de T007)
- [X] T009 [P] `backend/infra/repositories/client_repo.py`: agregar
  `list_access/add_access/update_access/delete_access` — mismo patrón que
  `list_systems/add_system/delete_system` (depende de T004)
- [X] T010 `backend/infra/repositories/client_repo.py`: agregar
  `list_access_attachments/add_access_attachment/delete_access_attachment` (mismo archivo que
  T009, depende de T005, T006)
- [X] T011 [P] `frontend/src/types/client.ts`: agregar interfaces `ClientAccess`,
  `ClientAccessFormData`, `ClientAccessAttachment` (sin `any`)
- [X] T012 `frontend/src/services/clientService.ts`: agregar
  `listAccess/addAccess/updateAccess/deleteAccess/listAccessAttachments/uploadAccessAttachment/deleteAccessAttachment`
  (depende de T011)

**Checkpoint**: modelo, migración y capa de datos listos — las tres historias pueden empezar.

---

## Phase 3: User Story 1 - Registrar múltiples accesos y conexiones de un cliente (Priority: P1) 🎯 MVP

**Goal**: permitir crear, editar y eliminar múltiples registros de acceso (VPN / URL de sistema
/ Escritorio remoto) por cliente, con adjuntos, en una pestaña propia con tabla ancha horizontal
e independiente del guardado del resto de datos del cliente.

**Independent Test**: Escenarios 1 y 2 del quickstart — migración sin pérdida + alta de tres
tipos de acceso distintos con adjunto, persistiendo por separado.

### Tests for User Story 1

- [X] T013 [P] [US1] `backend/tests/api/test_client_access_api.py` (nuevo, ≤10 registros):
  crear 1 cliente, agregar 2-3 `client_access` de tipos distintos + 1 adjunto vía los endpoints
  de contracts/client-access.md, verificar `GET .../access` y `GET .../access-attachments`
  (fixtures: solo el cliente necesario, sin Resolutor ni email de contraseña)

### Implementation for User Story 1

- [X] T014 [US1] `backend/api/routes/clients.py`: `GET/POST /api/clients/{id}/access` (modelos
  Flask-RESTX + handlers; valida `access_type` del enum y que `environment` solo se acepte
  cuando `access_type='system_url'`) (depende de T009)
- [X] T015 [US1] `backend/api/routes/clients.py`: `PATCH/DELETE
  /api/clients/{id}/access/{access_id}` (mismo archivo, depende de T014)
- [X] T016 [US1] `backend/api/routes/clients.py`: `GET/POST /api/clients/{id}/access-attachments`
  + `GET/DELETE /api/clients/{id}/access-attachments/{attachment_id}` (mismo archivo, depende de
  T010, T006)
- [X] T017 [US1] `frontend/src/pages/ClientsPage.tsx`: agregar `Tabs` de Ant Design al modal de
  Detalle/Edición con pestañas "Datos generales" y "Accesos y conexiones"; ensanchar el `width`
  del modal para acomodar una tabla horizontal (research.md Decisión 6) (depende de T012)
- [X] T018 [US1] `frontend/src/pages/ClientsPage.tsx`: dentro de la pestaña "Accesos y
  conexiones", tabla (tipo/ambiente/usuario/host/notas) + formulario inline de alta (mismo
  patrón que `systemForm`/`systems`), con guardar/eliminar por registro independientes del botón
  "Guardar" principal del cliente (FR-012) (depende de T017)
- [X] T019 [US1] `frontend/src/pages/ClientsPage.tsx`: sección de adjuntos dentro de la misma
  pestaña — subir/listar/descargar/eliminar archivos vía `listAccessAttachments` /
  `uploadAccessAttachment` / `deleteAccessAttachment` (depende de T017)
- [X] T020 [US1] `frontend/src/pages/ClientsPage.tsx`: quitar los `Form.Item name="vpn_ips"` /
  `name="vpn_credentials"` del formulario de creación/edición del cliente (reemplazados por la
  pestaña nueva) (depende de T018)

**Checkpoint**: US1 funcional e independientemente probable (Escenarios 1 y 2 del quickstart).

---

## Phase 4: User Story 2 - Ver únicamente los accesos del cliente que se está editando (Priority: P1)

**Goal**: eliminar la fuga de datos entre clientes (`OBS-0008`) en el nuevo modelo de accesos.

**Independent Test**: Escenario 3 del quickstart — abrir edición del Cliente A, cerrar, abrir
edición del Cliente B, confirmar que B solo muestra sus propios accesos (repetir A→B→C).

### Tests for User Story 2

- [X] T021 [P] [US2] Ampliar `backend/tests/api/test_client_access_api.py` (mismo archivo de
  T013, ≤10 registros adicionales): dos clientes distintos, confirmar que `GET .../access` de
  uno nunca incluye filas del otro (aislamiento a nivel de query, `client_id` en el `WHERE`).
  Ya escrito en la pasada de T013 como `test_access_isolated_between_two_clients` — pasando.

### Implementation for User Story 2

- [X] T022 [US2] `frontend/src/pages/ClientsPage.tsx`: en `openEdit`/`openDetail`, resetear el
  estado de accesos (`setAccessList([])`) de inmediato, **antes** de esperar la respuesta de
  `listAccess`, para no mostrar residualmente los accesos del cliente anterior mientras carga.
  Nota de causa raíz: el `OBS-0008` original ocurría porque `openEdit` llamaba
  `form.setFieldsValue(c)` sin `form.resetFields()` previo, y `c` (fila de la lista) no incluye
  `vpn_ips`/`vpn_credentials` — el formulario conservaba los valores del cliente anteriormente
  editado. T020 ya elimina esos campos del `form`; este task cubre el mismo riesgo para el
  estado nuevo de accesos (depende de T018, T020)
- [X] T023 [US2] `frontend/src/pages/ClientsPage.tsx`: confirmar que `openCreate()` también
  limpia el estado de accesos (cliente nuevo arranca sin ningún acceso) (depende de T022).
  Estructuralmente satisfecho por diseño: `openCreate()` solo abre el modal de
  creación/edición (`formOpen`), que ya no tiene ninguna sección de accesos (T020) — la
  pestaña "Accesos y conexiones" vive exclusivamente en el modal de Detalle (`detailOpen`),
  así que no existe ruta de código por la que `openCreate()` pueda exponer `accessList`.

**Checkpoint**: US2 validado — verificado en Docker real (ver sesión de verificación) abriendo
Cliente A (con 1 acceso) → cerrar → abrir Cliente B (sin accesos): la pestaña de B mostró
"Sin accesos registrados", cero rastro de A.

---

## Phase 5: User Story 3 - Ocultar por defecto la información sensible de los accesos (Priority: P2)

**Goal**: enmascarar contraseñas por defecto en creación/edición, consistente con el detalle
(`OBS-0017`), gobernado por el permiso `include_sensitive` ya existente.

**Independent Test**: Escenario 4 del quickstart — contraseña enmascarada por defecto, control
de revelado, y usuario sin permiso no puede revelar usuario/contraseña.

### Tests for User Story 3

- [X] T024 [P] [US3] Ampliar `backend/tests/api/test_client_access_api.py` (mismo archivo,
  ≤5 registros adicionales): `GET .../access` sin `include_sensitive` no expone `password` ni
  `username`; con `include_sensitive` sí. Ya escrito en la pasada de T013 como
  `test_password_hidden_without_sensitive_permission` — pasando.

### Implementation for User Story 3

- [X] T025 [US3] `backend/api/routes/clients.py`: en el serializador de `access`, omitir
  `password`/`username` cuando `include_sensitive=False` — mismo patrón que `_client_to_dict`
  (depende de T014)
- [X] T026 [US3] `frontend/src/pages/ClientsPage.tsx`: el campo contraseña del formulario de
  alta/edición de acceso usa `Input.Password` (Ant Design, enmascarado nativo) (depende de T018)
- [X] T027 [US3] `frontend/src/pages/ClientsPage.tsx`: en la tabla de accesos, columna
  contraseña enmascarada (`••••••••`) con botón `EyeOutlined`/`EyeInvisibleOutlined` por fila,
  gobernado por `canSeeSensitive` ya existente en el archivo (depende de T018, T025)

**Checkpoint**: US3 validado — verificado en Docker real logueado como Resolutor (sin
`include_sensitive`): Tipo/Ambiente/Host visibles, Usuario y Contraseña muestran "—" en las 3
filas (el backend ni siquiera envía esos campos en la respuesta). Con Admin, los mismos campos
se ven enmascarados por defecto con control de revelado por fila. Las tres historias UAT
(`OBS-0001`, `OBS-0008`, `OBS-0017`) quedan cubiertas y verificadas end-to-end.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T028 [P] Ejecutar `quickstart.md` completo contra Docker real (los 4 escenarios) y
  documentar el resultado de cada uno

  **Resultado**:
  - **Escenario 1 (migración sin pérdida)**: `alembic current` confirma head en `031`
    (`030_client_access` + `031_client_access_rls` aplicadas sin error). Verificación directa en
    `sywork_db`/`sywork_tickets`: las columnas legacy `vpn_ips`/`vpn_credentials` siguen
    presentes en `clients` (no se eliminaron, según diseño) y **ningún** cliente en este entorno
    tenía datos no nulos en esas columnas al momento de migrar (`count(*) = 0`), por lo que no
    hay un caso real de dato legacy que migrar en este ambiente de desarrollo — la migración
    corrió sin filas afectadas por la parte de datos, lo cual es el comportamiento correcto dado
    el estado de la BD (nada que perder). La lógica de migración de datos en sí
    (`030_client_access.py`, `INSERT ... SELECT ... convert_from(vpn_ips, 'UTF8')` +
    `downgrade()` reversible) fue verificada por revisión de código (research.md Decisión 4,
    data-model.md "Notas de migración") ya que no hay dataset legacy disponible para un ensayo
    en vivo sin fabricar datos fuera del alcance de la sesión (Principio VII).
  - **Escenario 2 (alta de múltiples tipos + adjunto)**: validado en vivo durante US1 — 3 tipos
    de acceso (vpn/system_url/remote_desktop) + 1 adjunto persistidos por separado, sin usar el
    botón "Guardar" principal del cliente. Confirmado también por
    `test_add_multiple_access_types_and_attachment` (pytest, passing).
  - **Escenario 3 (aislamiento entre clientes)**: validado en vivo durante US2 — Cliente A → cerrar
    → Cliente B mostró únicamente sus propios accesos, cero rastro cruzado. Confirmado también por
    `test_access_isolated_between_two_clients` (pytest, passing).
  - **Escenario 4 (enmascarado por defecto)**: validado en vivo durante US3 — contraseña
    enmascarada con `Input.Password` + revelado por fila como Admin; como Resolutor (sin
    `include_sensitive`) el backend omite `username`/`password` de la respuesta por completo.
    Confirmado también por `test_password_hidden_without_sensitive_permission` (pytest, passing).

- [X] T029 Actualizar `UAT/02_Backlog/BACKLOG.md`: mover `OBS-0001`, `OBS-0008`, `OBS-0017` de
  `Abierta` a `Lista para Validar` (columna Estado), dejando `Iteración de cierre` en `—` hasta
  que el validador confirme en una iteración nueva (README.md, flujo del Desarrollador)

  **Resultado**: las tres filas actualizadas en `UAT/02_Backlog/BACKLOG.md` a estado
  `Lista para Validar`, `Iteración de cierre` sin tocar (`—`) — pendiente de que un validador
  confirme en una iteración futura.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede arrancar de inmediato (y es casi trivial, sin
  librerías nuevas).
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA las tres historias.
- **User Stories (Phase 3-5)**: dependen todas de Foundational. US1 debe completarse antes de
  US2/US3 en la práctica porque ambas dependen de UI introducida en T017/T018/T020 (aunque
  conceptualmente son historias independientes del spec).
- **Polish (Phase 6)**: depende de que las tres historias estén completas.

### Parallel Opportunities

- T002/T003 (mismo archivo `client.py`) — secuenciales, no paralelos.
- T004/T005 (mismo archivo `client_model.py`) — secuenciales.
- T006 (`attachments.py`) es paralelo a T002-T005 (archivo distinto, sin dependencia).
- T009 es paralelo a T006/T007/T008 (archivo distinto, solo depende de T004).
- T011 es paralelo a todo el bloque backend (archivo de tipos frontend, sin dependencias).
- Dentro de cada historia, las tareas de test ([T013], [T021], [T024]) son paralelas entre sí
  respecto a la implementación de su propia historia (archivo de test independiente de los
  archivos de producción que valida).

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1 (trivial) + Phase 2 (Foundational).
2. Completar Phase 3 (US1) → validar Escenarios 1 y 2 del quickstart.
3. Esto ya resuelve `OBS-0001` de punta a punta (con `OBS-0008`/`OBS-0017` todavía pendientes).

### Incremental Delivery

1. Foundational → US1 (MVP, resuelve `OBS-0001`) → validar → US2 (resuelve `OBS-0008`) →
   validar → US3 (resuelve `OBS-0017`) → validar → Polish (quickstart completo + BACKLOG.md).
