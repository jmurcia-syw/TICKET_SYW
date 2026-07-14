# Plan de pruebas — SyWork Desk (alpha)

> Bitácora personal de QA sobre la app en etapa alpha.
> Feature activa: [spec 009 — Listas, Subtareas, ciclo unificado y fix de tiempos](specs/009-tareas-listas-subtareas/spec.md).
> Última actualización: _(pendiente)_

---

## 0. Entorno

| Ítem | Valor |
|------|-------|
| Rama | `main` |
| Último commit probado | `ae4f590` (merge Fase 3 Tareas) |
| Alembic head esperado | `024` |
| Stack | Docker Compose (`sywork_db:5432`, `sywork_backend:5000`, `sywork_frontend:5173`) |
| URL frontend | http://localhost:5173 |
| URL API | http://localhost:5000 |
| Swagger | http://localhost:5000/swagger |

### Levantar entorno
```bash
docker compose up -d
docker exec sywork_backend alembic upgrade head   # confirmar → 024 (head)
docker exec sywork_backend pytest -q              # baseline 331 tests verde
```

### Regenerar entorno limpio (para probar Escenario 0 de migración)
```bash
docker compose down -v          # ⚠ borra volumen de Postgres
docker compose up -d
# NO correr upgrade todavía: crear datos de spec 008 primero, luego migrar
```

---

## 1. Roles y credenciales de dev

Contraseña común (base64 `U3lXb3JrX0RldjIwMjYh`): **`SyWork_Dev2026!`**

| Usuario | Rol | Alcance esperado |
|---------|-----|------------------|
| `admin@sywork.net` | Admin | Todo, incluye compensación cifrada y Roles/Permisos |
| `coordinador@sywork.net` | Coordinador | Triage, reasignación, catálogos |
| `qm@sywork.net` | QM | Aceptación de cierre, auditoría |
| `resolutor@sywork.net` | Resolutor | Solo tickets asignados a él |
| _(crear)_ | Encargado | Solo autoservicio de su Cliente |

Fuente: `docs/credenciales_dev.txt`.

---

## 2. Smoke test (≤ 5 min)

Se ejecuta al inicio de cada sesión de pruebas para confirmar que el stack está sano.

- [x] Login con cada uno de los 4 roles seed
- [x] `GET /health/` responde 200
- [x] Crear un Ticket nuevo (rol Coordinador)
- [x] Crear una Tarea nueva (rol Resolutor)
- [x] Registrar 30 min sobre esa Tarea desde su detalle
- [x] Cerrar el Ticket con comentario tipificado
- [x] Campana de notificaciones muestra evento reciente

**Resultado**: ✅ Completado — 2026-07-14, build `866b223`. Stack sano, los 7 checks pasan.

---

## 3. Quickstart spec 009 — Listas, Subtareas y ciclo unificado

Fuente: [`specs/009-tareas-listas-subtareas/quickstart.md`](specs/009-tareas-listas-subtareas/quickstart.md).

### Validación dirigida (pytest)
```bash
docker exec sywork_backend pytest \
  tests/domain/test_ticket_service_free_transition.py \
  tests/domain/test_work_session_service_tasks.py \
  tests/api/test_tickets_status_transition.py \
  tests/api/test_task_lists.py \
  tests/api/test_tickets_subtasks.py \
  tests/api/test_work_sessions_tasks.py \
  tests/api/test_tickets_tasks.py -v
cd frontend && npx tsc -b
```
- [ ] Backend suite dirigida verde
- [ ] `npx tsc -b` sin errores
- [ ] `pytest -q` completo verde (331 tests)

### Escenario 0 — Migración de datos ⚠ una sola oportunidad
- [ ] Antes de migrar: anotar 2-3 Tareas de spec 008 con estado y `list_name`
- [ ] `alembic upgrade head` corre sin error
- [ ] Mapeo de estado: `pendiente→Nuevo`, `en_progreso→En Ejecución`, `hecha→Cerrado`, `cancelado` sin cambio
- [ ] `list_name` migrado a Lista real, misma etiqueta
- [ ] `GET /api/projects/{id}/task-lists` devuelve las Listas con `task_count` correcto

### Escenario 1 (US1) — Fix de Registro de tiempo
- [ ] Creador de una Tarea registra tiempo → 201 (era 403)
- [ ] Creador de Tarea padre registra tiempo sobre Subtarea asignada a otro → permitido
- [ ] Recurso ajeno intenta registrar tiempo → 403 `not_assigned`
- [ ] Ticket con assignee formal: registro sigue funcionando igual

### Escenario 2 (US2) — Ciclo unificado libre en Tarea
- [ ] Tarea: `PATCH /status` Nuevo→Cerrado con comentario → 200
- [ ] Historial de estados registra la transición
- [ ] `PATCH /status` sin `comment` → 400 `validation_error`
- [ ] Retroceso Cerrado→Nuevo permitido
- [ ] Ticket: `PATCH /status` → 409 `not_a_task`
- [ ] Detalle de Tarea muestra Tipo, Severidad, Herramienta, Proceso, Nivel de escalamiento editables
- [ ] Kanban muestra Tarea con tag "Tarea"
- [ ] Drag de Tarea a cualquier columna: pide comentario y mueve
- [ ] Drag de Ticket: sigue validando `getKanbanTransition`

### Escenario 3 (US3) — Listas administrables
- [ ] Sidebar de Listas visible en Proyecto (según `docs/mockup.html` id `s-lista`)
- [ ] Crear Lista → aparece con conteo 0
- [ ] Asociar Tarea → conteo sube a 1
- [ ] Asociar Tarea a Lista de otro Proyecto → 409 `list_mismatch`

### Escenario 4 (US4) — Subtareas con Encargado propio
- [ ] Dos Subtareas con Encargados distintos, distintos del padre
- [ ] Cada Subtarea muestra badge de estado y avatar propios
- [ ] Cambiar estado de una Subtarea no afecta a la Tarea padre ni a la otra Subtarea
- [ ] Encargado de Subtarea la ve en "Mis Tareas" y Kanban
- [ ] Crear Subtarea dentro de Subtarea → 409 `nested_subtask_not_allowed`

### Escenario 5 (US5) — Comentarios simples
- [ ] Comentario en Tarea sin cambio de estado → aparece en historial, sin fila en "Historial de estados"
- [ ] Comentario en Subtarea → aparece solo en su historial, no en el del padre

### Escenario 6 — Regresión de Ticket
- [ ] Ticket transitado Triage → cierre funciona igual
- [ ] `ticket_fsm.py` sigue siendo única fuente de verdad para Ticket

---

## 4. Regresión de specs anteriores

Cada uno tiene su propio `quickstart.md` — correr al menos una vez sobre este build.

- [ ] [`002 — Fase 1 Tickets`](specs/002-fase1-tickets/quickstart.md) (6 escenarios, 26 checks)
- [ ] [`004 — Registro de tiempos`](specs/004-fase2-registro-tiempos/quickstart.md)
- [ ] [`005 — Encargado y navegación`](specs/005-ticket-tiempo-encargado-nav/quickstart.md)
- [ ] [`006 — Detalle de ticket UI`](specs/006-ticket-detalle-tiempo-ui/quickstart.md)
- [ ] [`007 — Encargado por Cliente`](specs/007-ticket-encargado-cliente/quickstart.md) (6 escenarios)
- [ ] [`008 — Fase 3 Tareas`](specs/008-fase3-tareas/quickstart.md)

---

## 5. Exploración de bordes (más allá del quickstart)

### 5.1 Permisos por rol
- [ ] Encargado NO ve Maestros, Panel de Asignación, Catálogos
- [ ] Encargado solo crea tickets de su Cliente fijo
- [ ] Resolutor NO transiciona Ticket ajeno (403 aunque UI lo permita)
- [ ] Pegar directo a `/api/tickets/{id}/assign` con token de Resolutor → 403
- [ ] QM cierra tickets, Coordinador reasigna, ambos NO editan compensación

### 5.2 FSM Ticket vs transición libre Tarea
- [ ] Cambiar `tipo_registro` de un Ticket cerrado a Tarea vía SQL: ¿corrompe historial?
- [ ] Kanban: mover Ticket a columna inválida vs mover Tarea a la misma → comparar mensajes
- [ ] Cierre de Tarea sin `tipo_resolucion` → ¿se permite?
- [ ] Cierre de Ticket sin `tipo_resolucion` → debe rechazar

### 5.3 Jerarquía 5 niveles
- [ ] Subtarea de subtarea → 409
- [ ] Lista cross-project → 409
- [ ] Cambiar Proyecto de Tarea con Lista asociada: ¿qué pasa con la Lista?
- [ ] `task_count` con 5 tareas: 3 cerradas, 1 cancelada → ¿cuenta abiertas o todas?

### 5.4 Registro de tiempo (bordes)
- [ ] Creador registra tiempo tras reasignación a otro
- [ ] `hora_inicio > hora_fin` → validar rechazo
- [ ] Registro cruzando medianoche
- [ ] Dos registros solapados del mismo recurso el mismo día
- [ ] Registrar tiempo sobre Tarea CANCELADA
- [ ] Registrar tiempo sobre Tarea CERRADA

### 5.5 Concurrencia
- [ ] Dos usuarios cambian estado de la misma Tarea a la vez
- [ ] Dos pestañas del mismo usuario reciben notificación: marcar leída en una, verificar la otra
- [ ] Panel de Asignación con 500+ tickets < 100 ms

### 5.6 Adjuntos
- [ ] Subir archivo de 10 MB exactos → OK
- [ ] Subir archivo de 10 MB + 1 byte → rechazo
- [ ] Nombre con Unicode, `../`, `.exe`
- [ ] URL directa al archivo sin JWT → 401

### 5.7 Autenticación
- [ ] JWT expirado → 401 y redirección a login
- [ ] Login Google OAuth con dominio distinto a `@sywork.net` → rechazo
- [ ] Reseteo de contraseña (spec 003)

---

## 6. Hallazgos

> El detalle completo de cada hallazgo vive en **[HALLAZGOS.md](HALLAZGOS.md)** (con template, pasos, causa raíz y fix propuesto). Aquí queda solo el resumen de estado.

**Total**: 17 hallazgos · **Alto ×5** · Medio ×8 · Bajo ×3 · Mixto ×1

| # | Título | Severidad | Estado |
|---|--------|-----------|--------|
| [H-001](HALLAZGOS.md#h-001) | JWT inválido devuelve 500 en vez de 401 en maestros | Alto | Abierto |
| [H-002](HALLAZGOS.md#h-002) | Nombre de cliente sin validación de caracteres | Bajo | Abierto |
| [H-003](HALLAZGOS.md#h-003) | Email solo valida formato, no existencia | Medio | Abierto (producto) |
| [H-004](HALLAZGOS.md#h-004) | Teléfono sin selector de código de país | Medio | Abierto |
| [H-005](HALLAZGOS.md#h-005) | Teléfono sin longitud máxima | Medio | Abierto |
| [H-006](HALLAZGOS.md#h-006) | Campos VPN visibles en texto plano al crear/editar | Alto | Abierto |
| [H-007](HALLAZGOS.md#h-007) | Falta feedback claro cuando la validación falla | Medio | Abierto (ver spec 013) |
| [H-008](HALLAZGOS.md#h-008) | Editar Proyecto ignora el cambio de Cliente en silencio | Alto | Abierto (producto) |
| [H-009](HALLAZGOS.md#h-009) | Identificación acepta cualquier carácter y longitud | Medio | Abierto |
| [H-010](HALLAZGOS.md#h-010) | Nacionalidad es input libre en vez de lista de países | Medio | Abierto |
| [H-011](HALLAZGOS.md#h-011) | Fecha de nacimiento sin validación de edad mínima | Medio | Abierto |
| [H-012](HALLAZGOS.md#h-012) | Nivel de estudios es input libre en vez de catálogo | Bajo | Abierto |
| [H-013](HALLAZGOS.md#h-013) | Equipo es input libre en vez de catálogo administrable | Bajo | Abierto |
| [H-014](HALLAZGOS.md#h-014) | Matriz de permisos omite 9 permisos reales | Alto | Abierto |
| [H-015](HALLAZGOS.md#h-015) | Ticket se puede cerrar sin tiempo registrado | Alto | Abierto (producto) |
| [H-016](HALLAZGOS.md#h-016) | Múltiples usuarios simultáneos en el mismo navegador | Medio/Alto | Abierto (producto) |
| [H-017](HALLAZGOS.md#h-017) | Listados de tickets sin ordenamiento útil | Medio | Abierto (producto) |

### H-001 — JWT inválido / usuario inexistente devuelve 500 en vez de 401 en todos los maestros
- **Severidad**: Alto
- **Módulo**: Auth · Maestros (Clients, Projects, Resources, Users, Roles, Permissions)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12
- **Build/commit**: `ae4f590`

**Pasos**
1. `docker compose down -v` (entorno limpio, BD nueva).
2. `docker compose up -d` + `alembic upgrade head`.
3. Con el navegador conservando el JWT del entorno anterior, entrar a Clientes y pulsar "Nuevo cliente" → Guardar.

**Esperado**: 401 limpio y el frontend redirige a login (o `message.error` claro de sesión expirada).
**Observado**: 500 opaco. En UI, el botón "Guardar" no reacciona visiblemente. Backend log:
```
TypeError: Object of type Response is not JSON serializable
POST /api/clients HTTP/1.1 500
```
También ocurre en `GET /api/clients` y `GET /api/projects`.

**Causa raíz**:
- [auth.py:43](backend/api/middleware/auth.py) `jwt_required_active` retorna `jsonify({...}), 401` — `jsonify()` devuelve un `Response`.
- [rbac.py:97-101](backend/api/middleware/rbac.py) `enforce_module` recibe ese `Response` como `denied` y lo re-retorna a Flask-RESTX.
- Flask-RESTX intenta serializar el `Response` como JSON → `TypeError` → 500.

**Impacto**:
- El frontend no puede detectar sesión expirada y redirigir a login.
- Cualquier JWT con `user_id` inexistente o usuario desactivado produce el mismo 500 opaco.
- Ensucia logs con tracebacks que parecen bugs reales.

**Workaround**: cerrar sesión / limpiar `authStore` en Local Storage y volver a loguear.

**Fix propuesto**: en `auth.py:43` reemplazar `return jsonify({...}), 401` por `return {"error": "unauthorized", "message": "Acceso denegado"}, 401` (dict tuple, no Response).

**Referencia**: enforcement JWT total, spec 002.
**Estado**: Abierto

---

### H-002 — Campo "Nombre" del cliente sin validación de caracteres
- **Severidad**: Bajo
- **Módulo**: Maestros · Clientes (formulario de creación/edición)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Menú Clientes → Nuevo cliente.
2. En "Nombre" escribir cadena con símbolos raros o solo emojis / signos (`!@#$%^&*` o `😀😀`) y guardar.

**Esperado**: al menos rechazar cadenas que no contengan ninguna letra/número (un nombre de empresa debería exigir carácter alfanumérico) y limitar longitud razonable (≤ 120).
**Observado**: se acepta cualquier cadena, incluso solo símbolos.
**Referencia**: [ClientsPage.tsx:165](frontend/src/pages/ClientsPage.tsx) — regla actual solo `required`.
**Estado**: Abierto

---

### H-003 — Email de contacto solo valida formato, no existencia real
- **Severidad**: Medio
- **Módulo**: Maestros · Clientes
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Nuevo cliente → email `pepito@noexiste.zzz` → Guardar.

**Esperado**: (opción A) validar dominio contra MX record al menos best-effort en backend; (opción B) enviar email de verificación al contacto. Como mínimo, dejarlo documentado como "el email no se verifica" en el placeholder.
**Observado**: cualquier cadena con formato `a@b.c` se acepta como email válido.
**Nota**: es un compromiso de negocio, no un bug puro. Discutir con producto antes de fixear.
**Referencia**: [ClientsPage.tsx:169](frontend/src/pages/ClientsPage.tsx) — solo `{ type: 'email' }`.
**Estado**: Abierto (a discutir con producto)

---

### H-004 — Teléfono sin selector de código de país
- **Severidad**: Medio
- **Módulo**: Maestros · Clientes (UX)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Nuevo cliente → campo Teléfono.

**Esperado**: componente con dropdown de código de país (bandera + `+57`, `+1`, etc.) y campo separado para el número local. Estándar E.164.
**Observado**: input de texto libre. El usuario puede escribir "número al azar" sin formato ni indicación de país.
**Sugerencia técnica**: `react-phone-number-input` o `antd-country-phone-input`. Guardar en formato E.164 (`+573001234567`).
**Referencia**: [ClientsPage.tsx:170](frontend/src/pages/ClientsPage.tsx).
**Estado**: Abierto

---

### H-005 — Teléfono sin longitud máxima
- **Severidad**: Medio
- **Módulo**: Maestros · Clientes (validación)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Nuevo cliente → Teléfono → escribir 40+ dígitos → Guardar.

**Esperado**: rechazar si supera longitud E.164 (máx 15 dígitos incluyendo código de país) o bloquear input al llegar al máximo.
**Observado**: acepta cualquier cantidad de caracteres. Un teléfono no tiene 40 dígitos.
**Fix propuesto**: `Input maxLength={20}` + regla `{ pattern: /^\+?[0-9\s\-()]{7,20}$/ }` como parche mínimo, o resolver junto con [[H-004]] usando componente E.164.
**Referencia**: [ClientsPage.tsx:170](frontend/src/pages/ClientsPage.tsx).
**Estado**: Abierto

---

### H-006 — Campos VPN (IPs y Credenciales) visibles en texto plano al crear/editar
- **Severidad**: Alto
- **Módulo**: Maestros · Clientes (seguridad UX)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Nuevo cliente → escribir en "IPs VPN" y "Credenciales VPN".

**Esperado**: los campos sensibles deben renderizarse como `<Input.Password>` con toggle "ojito" para revelar bajo demanda, igual que se hace en el modal de Detalle (que sí oculta con `••••••••` y botón `EyeOutlined`).
**Observado**: en el formulario de creación/edición ambos campos son `<Input.TextArea>` plano — cualquiera detrás del hombro los ve. Inconsistente con la protección del modal de detalle.
**Fix propuesto**: reemplazar `Input.TextArea` por `Input.Password` (o un textarea custom con toggle) en las líneas 174-175. Mantener `include_sensitive` en API.
**Referencia**: [ClientsPage.tsx:174-175](frontend/src/pages/ClientsPage.tsx). Contraste con el modal de detalle (líneas 187-198) que sí enmascara.
**Estado**: Abierto

---

### H-007 — Falta feedback claro cuando la validación falla (transversal)
- **Severidad**: Medio
- **Módulo**: Global (Clientes, Proyectos, Recursos, Usuarios, Roles, Tickets, Tareas — todo formulario)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Crear un cliente con un nombre que ya existe → Guardar.
2. Repetir en Proyectos, Recursos, Usuarios con otro campo duplicado o inválido.

**Esperado**:
- Mensaje inline junto al campo problemático (Ant Design: `Form.Item` con `validateStatus="error"` + `help="Ya existe un cliente con ese nombre"`).
- El modal se queda abierto sobre el campo en falta.
- Distinguir visualmente:
  - **Duplicado** (`name_duplicate`, 409) → "Ya existe un cliente con ese nombre".
  - **Validación de campo** (400) → mensaje específico del campo.
  - **Sin permisos** (403) → "No tienes permiso para esta acción".
  - **Sesión expirada** (401) → redirigir a login.
  - **Error del servidor** (500) → toast rojo "Error interno, inténtalo más tarde" + reportar.
**Observado**:
- El backend sí devuelve mensajes tipados y específicos (`ClientBusinessError("name_duplicate", "Ya existe un cliente con ese nombre")` — [client_service.py:16](backend/domain/services/client_service.py)).
- El frontend los captura, pero solo los muestra vía **toast fugaz** de Ant Design (`message.error(msg)`) en la esquina superior, sin marcar el campo ni impedir cerrar el modal.
- Cuando ocurre un 500 (ver [[H-001]]), el mensaje se pierde y solo aparece "Error al guardar" genérico o nada.

**Impacto**: el usuario no sabe qué campo corregir; en muchos casos parece que "el botón no hace nada" (síntoma inicial del reporte de este entorno).

**Fix propuesto** (dos capas):
1. Introducir helper `mapApiErrorToFormFields(err, form)` que traduzca `err.response.data.error` a `form.setFields([{ name, errors: [msg] }])` para pintar inline.
2. Mantener toast como respaldo solo para errores no asociados a un campo (500, 403, red caída).

**Referencia**: [ClientsPage.tsx:87-102](frontend/src/pages/ClientsPage.tsx) — patrón actual. Se repite igual en [ProjectsPage.tsx](frontend/src/pages/ProjectsPage.tsx), [ResourcesPage/TeamPage.tsx](frontend/src/pages/TeamPage.tsx), etc.
**Estado**: Abierto

---

### H-008 — Editar Proyecto permite cambiar el Cliente pero el backend lo ignora silenciosamente
- **Severidad**: Alto
- **Módulo**: Maestros · Proyectos
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Menú Proyectos → editar un proyecto existente.
2. Cambiar el "Cliente" a otro cliente activo del combo → Guardar.
3. Observar toast: "Proyecto actualizado" ✅.
4. Revisar la fila en el listado / reabrir el proyecto.

**Esperado**: el proyecto queda asociado al nuevo cliente, o el frontend debería deshabilitar el campo Cliente en modo edición si el diseño no permite mover proyectos entre clientes.
**Observado**: la UI reporta éxito pero el cliente sigue siendo el original. El cambio se pierde en silencio (peor que un rechazo — el usuario cree que se aplicó).

**Causa raíz**:
- Frontend: [ProjectsPage.tsx:160-162](frontend/src/pages/ProjectsPage.tsx) muestra el Select de Cliente también en modo edición y envía `client_id` en el payload.
- Backend: el schema `_project_update` en [projects.py:54-64](backend/api/routes/projects.py) **no incluye `client_id`**, y el handler PATCH ([projects.py:264-268](backend/api/routes/projects.py)) solo aplica `for field in ("name", "description", "overview", "components_sold")` — ignora `client_id` sin devolver error.

**Impacto**:
- Data integrity: el usuario cree que reasignó el proyecto y no ocurrió.
- Tickets, tareas, tiempos y facturación siguen apuntando al cliente equivocado desde la perspectiva del usuario.
- Combina mal con [[H-007]]: no hay feedback de "campo no editable".

**Decisión de producto pendiente** (elegir una):
- **Opción A — Permitir reasignar Cliente**: backend acepta `client_id` en PATCH (agregar al schema + al `for field in ...`), validando que el cliente destino exista y esté activo. Contemplar el impacto en tickets/tareas/tiempos existentes (¿migran? ¿se bloquea si tiene tickets abiertos?).
- **Opción B — Prohibir reasignación**: frontend deshabilita el Select de Cliente en modo edición (mostrarlo como texto o con `disabled`), y explicar que para mover un proyecto se cancela y se crea uno nuevo.

**Referencia**: [ProjectsPage.tsx:66-70, 160-162](frontend/src/pages/ProjectsPage.tsx), [projects.py:246-274](backend/api/routes/projects.py).
**Estado**: Abierto (requiere decisión de producto antes del fix)

---

### H-009 — Identificación acepta cualquier carácter y longitud
- **Severidad**: Medio
- **Módulo**: Equipo · Perfil extendido (SDD V3)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Menú Equipo → Nuevo integrante → expandir "Perfil extendido (SDD V3)".
2. En "Identificación" escribir símbolos, letras y números mezclados (por ejemplo `AB#12!@$99...`) → Guardar.

**Esperado**: solo dígitos, longitud acotada según país (Colombia CC 6-10, cédula extranjería 6-7, pasaporte alfanumérico 6-12). Como mínimo `pattern: /^[0-9]{6,15}$/` o similar y `maxLength`.
**Observado**: input libre, acepta cualquier símbolo y cualquier longitud.
**Sugerencia técnica**: si va a soportar pasaporte alfanumérico, agregar un Select "Tipo de documento" (CC / CE / Pasaporte / NIT) y validar el patrón según tipo.
**Referencia**: [TeamPage.tsx:348](frontend/src/pages/TeamPage.tsx).
**Estado**: Abierto

---

### H-010 — Nacionalidad es input libre en vez de lista de países
- **Severidad**: Medio
- **Módulo**: Equipo · Perfil extendido (SDD V3)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Nuevo integrante → Perfil extendido → "Nacionalidad" → escribir `asdasd` → Guardar.

**Esperado**: `<Select>` con lista ISO 3166-1 de países (con búsqueda por nombre). Guardar el código ISO alpha-2 (`CO`, `AR`, `EC`, ...) en BD.
**Observado**: `<Input>` texto libre. Acepta cualquier cadena como "nacionalidad" — rompe reportes agregados y filtros.
**Inconsistencia**: en el mismo formulario "País calendario" sí es Select ([TeamPage.tsx:356-358](frontend/src/pages/TeamPage.tsx)); nacionalidad debería serlo por el mismo criterio.
**Referencia**: [TeamPage.tsx:349](frontend/src/pages/TeamPage.tsx).
**Estado**: Abierto

---

### H-011 — Fecha de nacimiento sin validación de edad mínima
- **Severidad**: Medio
- **Módulo**: Equipo · Perfil extendido (SDD V3)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Nuevo integrante → Perfil extendido → "Fecha de nacimiento" → poner `2020-01-01` (un niño) → Guardar.

**Esperado**:
- `max` en el `<Input type="date">` = fecha de hoy - 18 años (persona mayor de edad).
- `min` razonable (por ejemplo hoy - 100 años).
- Validación en backend replicando la regla.
**Observado**: acepta cualquier fecha reciente, incluso futura.
**Fix propuesto**: calcular `max = format(subYears(new Date(), 18), 'yyyy-MM-dd')` y pasarlo al Input, más regla `Form.Item` que compare.
**Referencia**: [TeamPage.tsx:350](frontend/src/pages/TeamPage.tsx).
**Estado**: Abierto

---

### H-012 — Nivel de estudios es input libre en vez de catálogo
- **Severidad**: Bajo
- **Módulo**: Equipo · Perfil extendido (SDD V3)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Nuevo integrante → Perfil extendido → "Nivel de estudios" → escribir `abc123` → Guardar.

**Esperado**: `<Select>` con niveles estándar: Bachiller, Técnico, Tecnólogo, Pregrado, Especialización, Maestría, Doctorado, Otro.
**Observado**: `<Input>` texto libre. Cada usuario puede escribir variantes distintas ("Universitario", "Ingeniero", "profesional"), rompe agrupaciones en reportes.
**Inconsistencia**: "Especialidad" y "Seniority" adyacentes ya son Select ([TeamPage.tsx:361-366](frontend/src/pages/TeamPage.tsx)).
**Referencia**: [TeamPage.tsx:360](frontend/src/pages/TeamPage.tsx).
**Estado**: Abierto

---

### H-013 — Equipo es input libre en vez de catálogo administrable
- **Severidad**: Bajo
- **Módulo**: Equipo · Perfil extendido (SDD V3)
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Nuevo integrante → Perfil extendido → "Equipo" → escribir `xyz` → Guardar.

**Esperado**: `<Select>` administrable desde Catálogos (Oracle EBS, Oracle Fusion, Data & Analytics, Infraestructura, etc.), con opción "Otro" para casos no cubiertos. Alinear con la nomenclatura oficial del equipo SyWork.
**Observado**: `<Input>` texto libre. Riesgo de que cada admin cree una variante distinta del mismo equipo real.
**Referencia**: [TeamPage.tsx:368](frontend/src/pages/TeamPage.tsx).
**Estado**: Abierto

---

### H-014 — Matriz de permisos en Roles muestra celdas vacías y omite 9 permisos reales
- **Severidad**: Alto
- **Módulo**: Roles y Permisos
- **Rol usado**: Admin
- **Fecha**: 2026-07-12

**Pasos**
1. Menú Roles → Nuevo rol "TestQA" → Guardar.
2. Editar "TestQA" → observar la matriz "módulo × acción".
3. Comparar con lo que devuelve `SELECT module, action FROM permissions`.

**Esperado**: la matriz muestra TODAS las combinaciones `(módulo, acción)` que existen en la BD, y solo esas. Las celdas donde no existe la combinación deben quedar visualmente distintas (por ejemplo con "—" o gris deshabilitado) para que el usuario entienda que no es un permiso ausente sino inexistente.
**Observado (dos problemas)**:

**(a) Celdas vacías sin explicación** — la matriz siempre renderiza 4 columnas fijas `['view', 'create', 'edit', 'deactivate']` ([PermissionMatrix.tsx:6](frontend/src/components/roles/PermissionMatrix.tsx)). Para módulos donde no existen esas acciones (ej. `assignment_panel` solo tiene `view`, `catalogs` no tiene `edit`), las celdas quedan en blanco sin indicar por qué. Ese es el síntoma que reportaste: "cosas para chulear que no existen".

**(b) Bug funcional grave** — 9 permisos existentes en la BD **nunca se muestran en la UI**, por lo que no se pueden asignar desde la pantalla de Roles:

| Módulo | Permisos ocultos |
|--------|------------------|
| `client_contacts` | `manage` |
| `tickets` | `assign`, `cancel`, `transition`, `view_own` |
| `work_sessions` | `manage`, `manage_all`, `view_all`, `view_own` |

Los roles seed (Admin, Coordinador, QM, Resolutor) tienen algunos de estos permisos porque las migraciones los sembraron por SQL directo. Pero **un admin que crea un rol nuevo desde la UI NO puede darle permiso de transicionar tickets, asignar, cancelar, ni gestionar sesiones de trabajo**.

**Causa raíz**: [PermissionMatrix.tsx:6](frontend/src/components/roles/PermissionMatrix.tsx):
```typescript
const ACTIONS = ['view', 'create', 'edit', 'deactivate'] as const
```
Las columnas están hardcodeadas y no reflejan el catálogo dinámico.

**Impacto**:
- Cualquier rol personalizado creado desde la UI carece de las acciones específicas del dominio (Tickets, Work Sessions, Contactos de cliente).
- Se rompe el principio "RBAC dinámico administrable" declarado en el README ("roles y permisos administrables (matriz módulo × acción)").

**Fix propuesto**:
1. Calcular las columnas dinámicamente: `const ACTIONS = Array.from(new Set(allPermissions.map(p => p.action))).sort()`.
2. Para módulos donde `byAction[action]` es `undefined`, renderizar un guión gris ("—") en lugar de nada, para distinguir "no existe" de "no chuleado".
3. Agregar `ACTION_LABELS` para las nuevas acciones: `assign`, `cancel`, `transition`, `manage`, `manage_all`, `view_all`, `view_own`, más el fallback genérico.

**Referencia**: [PermissionMatrix.tsx:6-58](frontend/src/components/roles/PermissionMatrix.tsx), tabla de permisos actuales verificada con `SELECT module, action FROM permissions`.
**Estado**: Abierto

---

### H-015 — Un ticket se puede cerrar sin tiempo registrado (cronómetro sin efecto sobre el cierre)
- **Severidad**: Medio (impacto de producto), Alto (invalida el valor del feature "Cronómetro" de spec 012)
- **Módulo**: Tickets · Cierre · Cronómetro (spec 012)
- **Rol usado**: Admin / Resolutor
- **Fecha**: 2026-07-12
- **Build/commit**: `866b223` (post spec 012 mergeada)

**Pasos**
1. Crear un ticket nuevo → asignarlo a un usuario (Resolutor).
2. Transicionarlo hasta "Resuelto" sin correr el cronómetro ni registrar ninguna sesión de trabajo.
3. Confirmar el cierre (aceptación del usuario o esperar los 3+ días).
4. `POST /api/tickets/{id}/close` con `resolution_type_id` y `body` → devuelve 200 y el ticket queda cerrado.
5. Verificar `SELECT SUM(duration_minutes) FROM work_sessions WHERE ticket_id = ...` → `0` o `NULL`.

**Esperado**: el cierre debería validar que el ticket tiene al menos algún tiempo registrado (vía `work_sessions` o vía cronómetro cerrado), EXCEPTO para tipos de resolución que semánticamente no requieren trabajo (Duplicado, No aplica, Reasignado a otro sistema, etc.).

**Observado**: el endpoint [tickets.py:1006-1066](backend/api/routes/tickets.py) NO consulta `work_sessions` ni el timer en ningún momento. Un ticket se puede llevar a "Cerrado" con 0 minutos registrados. El cronómetro entregado en spec 012 termina siendo decorativo — no afecta el cierre ni queda como requisito.

**Causa raíz**: el flujo de cierre nunca se actualizó cuando se mergeó spec 012 (Cronómetro). El servicio `ticket_timer_service.py` existe y el endpoint `timer.py` está registrado, pero ninguna de sus salidas alimenta la validación de `TicketClose.post`.

**Impacto**:
- Reportes de tiempo por ticket/cliente/recurso quedan incompletos (subestiman el trabajo real).
- Facturación por horas pierde exactitud.
- El cronómetro es una feature "opcional voluntariamente ignorable" — muy fácil de omitir sin consecuencia.
- Los tests de spec 012 pasan porque el requisito nunca se agregó al quickstart de cierre.

**Fix propuesto** (a decidir con producto):
- **Opción A — validación fuerte**: en `TicketClose.post`, después de validar `close_eligible`, consultar `WorkSessionRepository.sum_minutes(ticket_id)`. Si es `0` y el `resolution_type` no está marcado como `allow_zero_time` (nuevo campo del catálogo), devolver `409 no_time_registered` con `"El ticket debe tener al menos N minutos registrados para cerrarlo"`.
- **Opción B — validación blanda con confirmación**: permitir cerrar con 0 tiempo pero el frontend muestra un `ConfirmationModal` explícito ("Este ticket se cerrará sin tiempo registrado. ¿Estás seguro?") y guarda un flag `closed_without_time` en el ticket para reportar.
- **Opción C — configurable por proyecto**: campo `require_time_on_close: bool` en Proyectos (útil para clientes con SLA de horas).

Recomendación técnica: **A + C** — la validación fuerte por defecto y un flag por proyecto para eximir proyectos donde no aplica.

**Discusión adicional**: revisar si el mismo problema aplica al cierre de **Tareas** (spec 009 ciclo unificado — `PATCH /status` libre). Si una Tarea también puede pasar a "Cerrado" sin tiempo, cubre el mismo hueco.

**Referencia**: [tickets.py:1006-1066](backend/api/routes/tickets.py), [ticket_timer_service.py](backend/domain/services/ticket_timer_service.py), spec 012 (Cronómetro), spec 009 (ciclo unificado).
**Estado**: Abierto (requiere decisión de producto)

---

### H-016 — Múltiples usuarios simultáneos en el mismo navegador (posible según postura de seguridad)
- **Severidad**: Medio (postura), Alto si el objetivo es enforcement estricto de sesión única
- **Módulo**: Autenticación · Frontend authStore
- **Rol usado**: cualquiera
- **Fecha**: 2026-07-12

**Pasos**
1. Iniciar sesión como `admin` en la pestaña A.
2. En la pestaña B (misma ventana, mismo perfil de Chrome), navegar a `/login` y entrar como `resolutor`.
3. Volver a la pestaña A → seguir operando como `admin` sin problema.
4. Recargar la pestaña A → ahora carga como `resolutor` (el último que quedó en `localStorage`).

**Esperado** (a elegir por producto/seguridad — hay tres posturas válidas):
- **Postura permisiva (web estándar)**: aceptar múltiples sesiones — para forzar aislamiento el usuario debe abrir ventana de incógnito u otro perfil de Chrome.
- **Postura enterprise "una sesión por navegador"**: al detectar login nuevo, forzar logout en las demás pestañas del mismo navegador.
- **Postura enterprise "una sesión por usuario"** (más estricta): al emitir un JWT nuevo, invalidar todos los anteriores del mismo usuario a nivel servidor.

**Observado**: el estado de auth está en Zustand con `persist` en **`localStorage`** ([authStore.ts:27-49](frontend/src/store/authStore.ts), `name: 'sywork-auth'`).

Consecuencias del diseño actual:
- `localStorage` es **compartido entre pestañas del mismo origen**, así que un login en una pestaña sobrescribe el token guardado por la anterior.
- Pero Zustand mantiene el estado en memoria por pestaña — no re-hidrata al detectar el cambio.
- Resultado: cada pestaña sigue funcionando con su token en memoria (envía Bearer diferente al backend en cada request), **hasta que una recarga la snap-ee al token que quedó último en `localStorage`**.
- El backend acepta los dos tokens porque son JWT válidos, sin registro de "sesión activa por usuario".

**Riesgos**:
1. **Estación compartida**: si un compañero deja abierta una sesión de admin y otro se loguea como QM en otra pestaña, ambos siguen "activos" — auditoría confusa.
2. **Data corruption por confusión**: si el usuario recarga la pestaña A esperando seguir como admin y termina como resolutor, puede tomar acciones "a nombre del rol equivocado" pensando que sigue en el rol original.
3. **Trazabilidad**: cada request usa el token que la pestaña tiene en memoria, pero el usuario visible en la UI puede diferir del que ejecutó la acción tras una recarga inconsistente.
4. **JWT sin lista de revocación**: `Flask-JWT-Extended` está configurado sin blocklist ([app.py:20](backend/app.py)), así que un token robado sigue vivo hasta que expire (8h — `JWT_ACCESS_TOKEN_EXPIRES = 3600 * 8`).

**Fix propuesto** (según la postura que elija producto):

| Postura | Cambios necesarios |
|---------|--------------------|
| **Permisiva** (aceptar como está) | Solo documentar en manual: "para operar con varios roles a la vez, usa ventanas incógnito o perfiles distintos de Chrome". Cerrar hallazgo. |
| **Una sesión por navegador** | (a) Cambiar `localStorage` → `sessionStorage` en `persist({ storage })`, (b) Emitir un `BroadcastChannel('sywork-auth')` en el login que dispare `logout()` en las demás pestañas, (c) Sincronizar cambios de rol/token entre pestañas del mismo login legítimo. |
| **Una sesión por usuario** (más estricta) | (a) Backend guarda `current_jti` por `user_id` al emitir cada token, (b) Middleware JWT verifica `jti == user.current_jti`, si no → 401. (c) Al login nuevo, el token anterior queda invalidado inmediatamente. Combinar con la anterior para pulir UX. |

**Recomendación técnica**: la **postura "una sesión por usuario"** es la más segura y la que suele exigir compliance interno de consultoría (SOC2, ISO 27001). El costo es medio: agregar columna `current_jti` a `users` y un check en el middleware.

**Test rápido para verificar cuando se decida**:
1. Login admin en pestaña A → capturar JWT.
2. Login admin en pestaña B (mismo usuario) → capturar JWT nuevo.
3. Usar el JWT de A vía `curl` → esperado 401 en postura estricta, 200 en postura permisiva.

**Referencia**: [authStore.ts:27-49](frontend/src/store/authStore.ts), [app.py:16-20](backend/app.py).
**Estado**: Abierto (requiere decisión de producto/seguridad)

---

### H-017 — Listados de tickets sin ordenamiento útil para el Resolutor (colores sin acompañamiento)
- **Severidad**: Medio
- **Módulo**: Tickets · Listados (TicketsPage / MyTasksPage / Kanban) · UX y consulta backend
- **Rol usado**: Resolutor
- **Fecha**: 2026-07-12

**Observación del usuario**: entrando como Resolutor, los tickets aparecen ordenados alfabéticamente y los colores de los tags de prioridad/severidad quedan "sin sentido" — no ayudan a decidir qué atender primero porque un `crítica` puede estar debajo de un `baja`.

**Confirmación técnica**: en [ticket_repo.py:11-16](backend/infra/repositories/ticket_repo.py) el diccionario de sorts es:
```python
_SORTS = {
    "created_at": TicketModel.created_at.asc(),
    "-created_at": TicketModel.created_at.desc(),
    "priority": TicketModel.priority.asc(),   # ← sort alfabético sobre texto
    "status": TicketModel.status.asc(),        # ← idem
}
```

Consecuencias:
- `ORDER BY priority ASC` devuelve `alta, baja, critica, media` — no `critica > alta > media > baja` (urgencia real).
- `ORDER BY status ASC` mezcla estados sin agrupar por columna del Kanban.
- El default de la vista más común para el Resolutor probablemente es por `created_at` (más antiguos primero o más nuevos primero), que ignora prioridad y severidad.

**Esperado** (recomendación de orden):
1. **Orden por defecto sugerido para Resolutor** (Mis Tareas + Tickets):
   ```
   ORDER BY
     CASE priority   WHEN 'critica' THEN 1 WHEN 'alta' THEN 2 WHEN 'media' THEN 3 WHEN 'baja' THEN 4 ELSE 5 END,
     CASE severity   WHEN 'critica' THEN 1 WHEN 'alta' THEN 2 WHEN 'media' THEN 3 WHEN 'baja' THEN 4 ELSE 5 END,
     created_at ASC
   ```
2. **Kanban**: dentro de cada columna, mismo orden por prioridad/severidad.
3. **Coordinador/QM**: ofrecer un toggle o `default_sort` distinto (por `created_at DESC` para triage cronológico de lo nuevo).

**Fix propuesto** (dos opciones):
- **A) Query con `CASE` (rápido, sin migración)**: agregar los sorts `"priority_desc_urgency"` y `"severity_desc_urgency"` al diccionario `_SORTS` usando `sa.case(...)`. Cero cambio de schema.
- **B) Columna numérica `priority_rank` (más robusto)**: agregar `priority_rank SMALLINT` a `tickets`, poblado por trigger o al asignar `priority`. Permite índices eficientes y sort natural. Requiere migración Alembic.

Recomendación técnica: **A** para desbloquear ya, y considerar **B** cuando la tabla crezca (más de 10k tickets).

**Fix UI complementario**:
- Mostrar el ordenamiento activo en la cabecera de la tabla (columna sorter con la flechita clara).
- En Kanban, poner un chip pequeño arriba: "Ordenado por: Prioridad ↓".
- Consistencia de color: si `critica` es rojo, que también sea el primero en la lista — así el orden refuerza el semáforo.

**Referencia**:
- [ticket_repo.py:11-63](backend/infra/repositories/ticket_repo.py) — diccionario `_SORTS` y query paginada.
- [MyTasksPage.tsx](frontend/src/pages/MyTasksPage.tsx), [TicketsPage.tsx](frontend/src/pages/TicketsPage.tsx), [KanbanPage.tsx](frontend/src/pages/KanbanPage.tsx) — vistas afectadas.

**Estado**: Abierto (recomendación — requiere decisión de producto sobre el orden por defecto por rol)

---

## 7. Bitácora de ejecución

| Fecha | Build | Ronda | Cobertura | Resultado | Notas |
|-------|-------|-------|-----------|-----------|-------|
| _(pendiente)_ | | | | | |
