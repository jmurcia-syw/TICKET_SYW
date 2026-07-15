---
id: ITER-003
fecha: 2026-07-14
version_probada: "Múltiples builds durante la sesión: `ae4f590` (línea base, merge Fase 3 Tareas) hasta `866b223` (post spec 012, smoke test); ver Build/commit específico de cada hallazgo cuando difiere"
entorno: Docker Compose (sywork_db:5432, sywork_backend:5000, sywork_frontend:5173)
responsable_sesion: Emilio Vargas
alcance: "QA técnico exhaustivo: smoke test, quickstart spec 009 (Listas/Subtareas/ciclo unificado), regresión specs 002–008, exploración de bordes (permisos, FSM, jerarquía de 5 niveles, registro de tiempo, concurrencia, adjuntos, autenticación)"
estado_iteracion: Cerrada
---

# ITER-003 — Iteración de pruebas

## Objetivo de la iteración

Incorporación al framework UAT de la documentación técnica de QA recopilada por Emilio Vargas en `docs/HALLAZGOS.md` y `docs/PLAN_PRUEBAS.md` (17 hallazgos, H-001–H-017), producto de una sesión de pruebas más profunda que las anteriores: incluye smoke test, validación dirigida de la spec 009, regresión de specs 002–008 y exploración de bordes (permisos por rol, FSM de Ticket vs. transición libre de Tarea, jerarquía de 5 niveles, registro de tiempo, concurrencia, adjuntos, autenticación). A diferencia de ITER-001/ITER-002, cada hallazgo incluye causa raíz con referencia a archivo/línea de código y fix propuesto — se preserva ese detalle dentro de "Descripción" y "Resultado actual / Propuesta de mejora" de cada observación porque es información directamente accionable para el desarrollador.

**Nota de deduplicación**: H-005 ("Teléfono sin longitud máxima") describe el mismo síntoma que `OBS-0007` (ITER-002, "Validación insuficiente en el campo Teléfono", reportado por Arely Pazmiño — acepta letras y no valida longitud mínima). Por convención (no duplicar IDs para el mismo síntoma), **no se crea un OBS nuevo para H-005**: queda registrado como reafirmación de `OBS-0007`, ya abierta en el backlog. El resto de hallazgos de Emilio Vargas (H-001 a H-004, H-006 a H-017) sí son síntomas nuevos y se registran como `OBS-0013` a `OBS-0028`.

## Resumen de observaciones

| ID | Módulo/Pantalla | Tipo | Estado | Reportado por |
|---|---|---|---|---|
| OBS-0013 | Auth · Maestros | Defecto | Abierta | Emilio Vargas |
| OBS-0014 | Maestros > Clientes | Defecto | Abierta | Emilio Vargas |
| OBS-0015 | Maestros > Clientes | Mejora | Abierta | Emilio Vargas |
| OBS-0016 | Maestros > Clientes (UX) | Mejora | Abierta | Emilio Vargas |
| OBS-0017 | Maestros > Clientes (seguridad) | Defecto | Abierta | Emilio Vargas |
| OBS-0018 | Global (formularios) | Mejora | Abierta | Emilio Vargas |
| OBS-0019 | Maestros > Proyectos | Defecto | Abierta | Emilio Vargas |
| OBS-0020 | Equipo > Perfil extendido (SDD V3) | Defecto | Abierta | Emilio Vargas |
| OBS-0021 | Equipo > Perfil extendido (SDD V3) | Mejora | Abierta | Emilio Vargas |
| OBS-0022 | Equipo > Perfil extendido (SDD V3) | Defecto | Abierta | Emilio Vargas |
| OBS-0023 | Equipo > Perfil extendido (SDD V3) | Mejora | Abierta | Emilio Vargas |
| OBS-0024 | Equipo > Perfil extendido (SDD V3) | Mejora | Abierta | Emilio Vargas |
| OBS-0025 | Roles y Permisos | Defecto | Abierta | Emilio Vargas |
| OBS-0026 | Tickets > Cierre · Cronómetro | Defecto | Abierta | Emilio Vargas |
| OBS-0027 | Autenticación > Frontend authStore | Mejora | Abierta | Emilio Vargas |
| OBS-0028 | Tickets > Listados | Mejora | Abierta | Emilio Vargas |

## Detalle de observaciones

### OBS-0013 — JWT inválido o usuario inexistente devuelve 500 en vez de 401 en todos los maestros

- **Módulo/Pantalla:** Auth · Maestros (Clientes, Proyectos, Recursos, Usuarios, Roles, Permisos)
- **Tipo:** Defecto
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
Al ingresar con un JWT correspondiente a un usuario inexistente o desactivado (ej. tras `docker compose down -v` con BD nueva, conservando el JWT del entorno anterior), el sistema responde 500 opaco en vez de 401. Ocurre en `GET/POST /api/clients` y `GET /api/projects`, y previsiblemente en cualquier endpoint protegido por el mismo middleware.

Causa raíz: `jwt_required_active` en `backend/api/middleware/auth.py:43` retorna `jsonify({...}), 401` — `jsonify()` devuelve un objeto `Response`. `enforce_module` en `backend/api/middleware/rbac.py:97-101` recibe ese `Response` como `denied` y lo re-retorna a Flask-RESTX, que intenta serializarlo como JSON y lanza `TypeError: Object of type Response is not JSON serializable` → 500.

**Pasos para reproducir**
1. `docker compose down -v` (entorno limpio, BD nueva).
2. `docker compose up -d` + `alembic upgrade head`.
3. Con el navegador conservando el JWT del entorno anterior, entrar a Clientes y pulsar "Nuevo cliente" → Guardar.

**Resultado esperado / Situación actual**
Esperado: 401 limpio y el frontend redirige a login (o muestra mensaje claro de sesión expirada).
Actual: 500 opaco; en UI el botón "Guardar" no reacciona visiblemente; el log del backend muestra el `TypeError` descrito arriba.

**Resultado actual / Propuesta de mejora**
En `auth.py:43`, reemplazar `return jsonify({...}), 401` por `return {"error": "unauthorized", "message": "Acceso denegado"}, 401` (dict + tuple, no `Response`), consistente con lo que Flask-RESTX espera poder serializar.

**Criterios de aceptación**
- [ ] Un JWT de usuario inexistente o desactivado devuelve 401 (no 500) en todos los endpoints de maestros.
- [ ] El frontend detecta el 401 y redirige a login o muestra mensaje de sesión expirada.
- [ ] El log del backend ya no registra el `TypeError` de serialización de `Response`.

**Evidencia**
_Sin evidencia gráfica adjunta — ver log de error citado en la descripción y referencias de código (`auth.py:43`, `rbac.py:97-101`)._

---

### OBS-0014 — Campo "Nombre" del cliente sin validación de caracteres

- **Módulo/Pantalla:** Maestros > Clientes
- **Tipo:** Defecto
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El campo "Nombre" en el formulario de creación/edición de cliente acepta cualquier cadena, incluidos solo símbolos o solo emojis, sin exigir carácter alfanumérico ni limitar longitud.

**Pasos para reproducir**
1. Menú Clientes → Nuevo cliente.
2. En "Nombre" escribir una cadena sin letras/números (ej. `!@#$%^&*` o `😀😀`) → Guardar.

**Resultado esperado / Situación actual**
Esperado: rechazar cadenas que no contengan ninguna letra/número (un nombre de empresa debería exigir al menos un carácter alfanumérico) y limitar la longitud a un máximo razonable (≤ 120).
Actual: se acepta cualquier cadena, incluso solo símbolos o emojis.

**Resultado actual / Propuesta de mejora**
Agregar regla de validación en el formulario (y replicarla en backend) que exija al menos un carácter alfanumérico y una longitud máxima de 120 caracteres.

**Criterios de aceptación**
- [ ] El campo "Nombre" rechaza cadenas compuestas solo por símbolos o emojis (sin ningún alfanumérico).
- [ ] El campo "Nombre" tiene una longitud máxima validada (120 caracteres).
- [ ] La validación se aplica tanto en frontend como en backend.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/ClientsPage.tsx:165` (regla actual solo `required`)._

---

### OBS-0015 — Email de contacto solo valida formato, no existencia real

- **Módulo/Pantalla:** Maestros > Clientes
- **Tipo:** Mejora
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El campo de email de contacto en Clientes acepta cualquier cadena con formato `a@b.c` como válida, sin verificar que el dominio o la dirección existan realmente.

**Pasos para reproducir** (no aplica — Mejora)

**Resultado esperado / Situación actual**
Situación actual: cualquier cadena con formato de email es aceptada; no hay verificación de existencia real ni aviso al usuario de que no se verifica.

**Resultado actual / Propuesta de mejora**
Opción A: validar dominio contra registro MX al menos best-effort en backend. Opción B: enviar email de verificación al contacto. Como mínimo, documentar en el placeholder del campo que "el email no se verifica". **Nota**: es un compromiso de negocio, no un bug puro — discutir con producto antes de definir el alcance del fix.

**Criterios de aceptación**
- [ ] Producto decide el alcance (validación MX, verificación por correo, o solo aclaración en UI).
- [ ] Se implementa la opción decidida y se documenta el comportamiento esperado del campo.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/ClientsPage.tsx:169` (regla actual solo `{ type: 'email' }`)._

---

### OBS-0016 — Teléfono sin selector de código de país

- **Módulo/Pantalla:** Maestros > Clientes (UX)
- **Tipo:** Mejora
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El campo Teléfono en el formulario de cliente es un input de texto libre, sin un componente que permita elegir código de país ni indique el formato esperado. Relacionado con `OBS-0007` (mismo campo, síntoma de validación de contenido/longitud).

**Pasos para reproducir** (no aplica — Mejora)

**Resultado esperado / Situación actual**
Situación actual: input de texto libre; el usuario puede escribir cualquier cosa sin formato ni indicación de país.

**Resultado actual / Propuesta de mejora**
Incorporar un componente con dropdown de código de país (bandera + `+57`, `+1`, etc.) y campo separado para el número local, siguiendo el estándar E.164 (ej. librerías `react-phone-number-input` o `antd-country-phone-input`). Guardar en formato E.164 (`+573001234567`).

**Criterios de aceptación**
- [ ] El campo Teléfono cuenta con selector de código de país.
- [ ] El valor se guarda en formato E.164.
- [ ] Se coordina con la resolución de `OBS-0007` para no duplicar el trabajo de validación del mismo campo.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/ClientsPage.tsx:170`._

---

### OBS-0017 — Campos VPN (IPs y Credenciales) visibles en texto plano al crear/editar

- **Módulo/Pantalla:** Maestros > Clientes (seguridad)
- **Tipo:** Defecto
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
En el formulario de creación/edición de cliente, los campos "IPs VPN" y "Credenciales VPN" se renderizan como `Input.TextArea` en texto plano — cualquiera que mire por encima del hombro los ve. Esto es inconsistente con el modal de Detalle, que sí enmascara esos mismos campos con `••••••••` y un botón "ojito" (`EyeOutlined`) para revelarlos bajo demanda.

**Nota de relación**: los campos VPN ya tienen dos observaciones previas abiertas — `OBS-0001` (ITER-001, ampliar a múltiples accesos) y `OBS-0008` (ITER-002, datos cruzados entre clientes). Al rediseñar esta sección (por `OBS-0001`), conviene resolver las tres en conjunto para no reintroducir ninguno de los tres defectos.

**Pasos para reproducir**
1. Menú Clientes → Nuevo cliente.
2. Escribir contenido en "IPs VPN" y "Credenciales VPN".
3. Observar que el contenido queda visible en texto plano mientras se escribe y tras guardar, al reabrir el formulario de edición.

**Resultado esperado / Situación actual**
Esperado: los campos sensibles deberían renderizarse como `Input.Password` (o un textarea custom con toggle "ojito"), igual que en el modal de Detalle.
Actual: ambos campos son `Input.TextArea` plano en el formulario de creación/edición.

**Resultado actual / Propuesta de mejora**
Reemplazar `Input.TextArea` por `Input.Password` (o textarea custom con toggle) en las líneas correspondientes del formulario. Mantener el parámetro `include_sensitive` ya existente en la API.

**Criterios de aceptación**
- [ ] Los campos "IPs VPN" y "Credenciales VPN" se muestran enmascarados por defecto en el formulario de creación/edición.
- [ ] Existe un control ("ojito") para revelar el contenido bajo demanda.
- [ ] El comportamiento es consistente con el modal de Detalle.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/ClientsPage.tsx:174-175` (formulario), contraste con líneas 187-198 (modal de detalle, que sí enmascara)._

---

### OBS-0018 — Falta feedback claro cuando la validación falla (transversal)

- **Módulo/Pantalla:** Global (Clientes, Proyectos, Recursos, Usuarios, Roles, Tickets, Tareas — todo formulario)
- **Tipo:** Mejora
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El backend devuelve mensajes de error tipados y específicos (ej. `ClientBusinessError("name_duplicate", "Ya existe un cliente con ese nombre")`), pero el frontend solo los muestra como un toast fugaz de Ant Design (`message.error(msg)`) en la esquina superior, sin marcar el campo problemático ni impedir que el modal se cierre. Cuando ocurre un 500 (ver `OBS-0013`), el mensaje se pierde y solo aparece "Error al guardar" genérico o nada. Esto hace que, en muchos casos, parezca que "el botón no hace nada".

**Pasos para reproducir** (no aplica — Mejora)

**Resultado esperado / Situación actual**
Situación actual: toast fugaz sin distinguir el tipo de error (duplicado 409, validación 400, sin permisos 403, sesión expirada 401, error de servidor 500) ni marcar el campo en el formulario.

**Resultado actual / Propuesta de mejora**
Dos capas: (1) introducir un helper `mapApiErrorToFormFields(err, form)` que traduzca `err.response.data.error` a `form.setFields([{ name, errors: [msg] }])` para pintar el error inline junto al campo; (2) mantener el toast solo como respaldo para errores no asociados a un campo (500, 403, red caída). Verificar si el commit `523f91c` (spec 013, normalizador global de errores) ya resolvió parte de esto tras el rebuild.

**Criterios de aceptación**
- [ ] Errores de validación de campo (400) se muestran inline junto al campo, no solo en toast.
- [ ] Errores de duplicado (409) identifican el campo en conflicto.
- [ ] El modal permanece abierto cuando hay un error de validación de campo.
- [ ] Errores sin campo asociado (403, 500, red) siguen mostrándose por toast.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/ClientsPage.tsx:87-102` (patrón repetido en `ProjectsPage.tsx`, `TeamPage.tsx`, etc.), `backend/domain/services/client_service.py:16`._

---

### OBS-0019 — Editar Proyecto permite cambiar el Cliente pero el backend lo ignora silenciosamente

- **Módulo/Pantalla:** Maestros > Proyectos
- **Tipo:** Defecto
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
Al editar un proyecto existente y cambiar su Cliente en el combo, el sistema muestra un toast de éxito ("Proyecto actualizado"), pero el cliente asociado no cambia realmente — el cambio se pierde en silencio, lo cual es peor que un rechazo porque el usuario cree que se aplicó.

Causa raíz: en frontend, `ProjectsPage.tsx:160-162` muestra el Select de Cliente también en modo edición y envía `client_id` en el payload. En backend, el schema `_project_update` (`backend/api/routes/projects.py:54-64`) no incluye `client_id`, y el handler PATCH (`projects.py:264-268`) solo aplica los campos `("name", "description", "overview", "components_sold")` — ignora `client_id` sin devolver error.

**Pasos para reproducir**
1. Menú Proyectos → editar un proyecto existente.
2. Cambiar el Cliente a otro cliente activo del combo → Guardar.
3. Observar el toast "Proyecto actualizado".
4. Revisar la fila en el listado o reabrir el proyecto: el cliente sigue siendo el original.

**Resultado esperado / Situación actual**
Esperado: el proyecto queda asociado al nuevo cliente, o el frontend debería deshabilitar el campo Cliente en modo edición si el diseño no permite mover proyectos entre clientes.
Actual: la UI reporta éxito, pero el cliente no cambia; el dato se pierde sin aviso.

**Resultado actual / Propuesta de mejora**
Requiere decisión de producto entre dos opciones: (A) permitir reasignar Cliente — backend acepta `client_id` en el PATCH, validando que el cliente destino exista y esté activo, y evaluando impacto en tickets/tareas/tiempos existentes; (B) prohibir la reasignación — frontend deshabilita el Select de Cliente en modo edición y explica que para mover un proyecto se debe cancelar y crear uno nuevo. Combina mal con `OBS-0018`: no hay feedback de "campo no editable".

**Criterios de aceptación**
- [ ] Producto decide entre permitir o prohibir la reasignación de Cliente en edición.
- [ ] Si se permite: el backend persiste el `client_id` nuevo y valida que el cliente destino esté activo.
- [ ] Si se prohíbe: el campo Cliente queda deshabilitado en modo edición, con explicación visible al usuario.
- [ ] En ningún caso el sistema reporta éxito sobre un cambio que no se aplicó.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/ProjectsPage.tsx:66-70, 160-162`, `backend/api/routes/projects.py:246-274`._

---

### OBS-0020 — Identificación acepta cualquier carácter y longitud

- **Módulo/Pantalla:** Equipo > Perfil extendido (SDD V3)
- **Tipo:** Defecto
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El campo "Identificación" del perfil extendido de un integrante de Equipo acepta cualquier combinación de símbolos, letras y números, sin restricción de longitud.

**Pasos para reproducir**
1. Menú Equipo → Nuevo integrante → expandir "Perfil extendido (SDD V3)".
2. En "Identificación" escribir símbolos, letras y números mezclados (ej. `AB#12!@$99...`) → Guardar.

**Resultado esperado / Situación actual**
Esperado: solo dígitos, con longitud acotada según país (Colombia CC 6-10, cédula de extranjería 6-7, pasaporte alfanumérico 6-12); como mínimo, un patrón `/^[0-9]{6,15}$/` y `maxLength`.
Actual: input libre, acepta cualquier símbolo y cualquier longitud.

**Resultado actual / Propuesta de mejora**
Si se va a soportar pasaporte alfanumérico, agregar un Select "Tipo de documento" (CC / CE / Pasaporte / NIT) y validar el patrón según el tipo elegido.

**Criterios de aceptación**
- [ ] El campo Identificación valida un patrón acorde al tipo de documento.
- [ ] Se define y aplica una longitud máxima razonable.
- [ ] (Opcional, recomendado) Existe un selector de "Tipo de documento" que ajusta la validación.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/TeamPage.tsx:348`._

---

### OBS-0021 — Nacionalidad es input libre en vez de lista de países

- **Módulo/Pantalla:** Equipo > Perfil extendido (SDD V3)
- **Tipo:** Mejora
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El campo "Nacionalidad" del perfil extendido es un `Input` de texto libre; acepta cualquier cadena, lo que rompe reportes agregados y filtros. Inconsistente con el campo adyacente "País calendario", que sí es un `Select`.

**Pasos para reproducir** (no aplica — Mejora)

**Resultado esperado / Situación actual**
Situación actual: `Input` de texto libre; cualquier cadena se acepta como "nacionalidad".

**Resultado actual / Propuesta de mejora**
Reemplazar por un `Select` con lista ISO 3166-1 de países (con búsqueda por nombre), guardando el código ISO alpha-2 (`CO`, `AR`, `EC`, ...) en base de datos, igual criterio que ya se aplica a "País calendario".

**Criterios de aceptación**
- [ ] El campo Nacionalidad es un `Select` con lista de países ISO 3166-1 y búsqueda por nombre.
- [ ] Se guarda el código ISO alpha-2, no texto libre.
- [ ] Consistente con el patrón ya usado en "País calendario".

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/TeamPage.tsx:349` (contraste con líneas 356-358)._

---

### OBS-0022 — Fecha de nacimiento sin validación de edad mínima

- **Módulo/Pantalla:** Equipo > Perfil extendido (SDD V3)
- **Tipo:** Defecto
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El campo "Fecha de nacimiento" del perfil extendido acepta cualquier fecha reciente, incluso futura, sin validar una edad mínima (mayoría de edad).

**Pasos para reproducir**
1. Menú Equipo → Nuevo integrante → Perfil extendido → "Fecha de nacimiento" → ingresar `2020-01-01` (un niño) → Guardar.

**Resultado esperado / Situación actual**
Esperado: `max` del input de fecha = hoy - 18 años; `min` razonable (ej. hoy - 100 años); validación replicada en backend.
Actual: acepta cualquier fecha reciente, incluso futura.

**Resultado actual / Propuesta de mejora**
Calcular `max = format(subYears(new Date(), 18), 'yyyy-MM-dd')` y pasarlo al input, más una regla de formulario que compare y rechace fechas fuera de rango. Replicar la validación en backend.

**Criterios de aceptación**
- [ ] El input de Fecha de nacimiento rechaza fechas que impliquen menos de 18 años de edad.
- [ ] El input rechaza fechas futuras.
- [ ] La validación existe también en backend (no solo en frontend).

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/TeamPage.tsx:350`._

---

### OBS-0023 — Nivel de estudios es input libre en vez de catálogo

- **Módulo/Pantalla:** Equipo > Perfil extendido (SDD V3)
- **Tipo:** Mejora
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El campo "Nivel de estudios" es un `Input` de texto libre; cada usuario escribe variantes distintas ("Universitario", "Ingeniero", "profesional"), lo que rompe agrupaciones en reportes. Inconsistente con "Especialidad" y "Seniority" adyacentes, que ya son `Select`.

**Pasos para reproducir** (no aplica — Mejora)

**Resultado esperado / Situación actual**
Situación actual: `Input` de texto libre sin estandarización.

**Resultado actual / Propuesta de mejora**
Reemplazar por un `Select` con niveles estándar: Bachiller, Técnico, Tecnólogo, Pregrado, Especialización, Maestría, Doctorado, Otro.

**Criterios de aceptación**
- [ ] El campo Nivel de estudios es un `Select` con las opciones estándar definidas.
- [ ] Incluye una opción "Otro" para casos no cubiertos.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/TeamPage.tsx:360` (contraste con líneas 361-366)._

---

### OBS-0024 — Equipo es input libre en vez de catálogo administrable

- **Módulo/Pantalla:** Equipo > Perfil extendido (SDD V3)
- **Tipo:** Mejora
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El campo "Equipo" (equipo de trabajo interno al que pertenece el integrante) es un `Input` de texto libre, con riesgo de que cada administrador cree una variante distinta del mismo equipo real.

**Pasos para reproducir** (no aplica — Mejora)

**Resultado esperado / Situación actual**
Situación actual: `Input` de texto libre.

**Resultado actual / Propuesta de mejora**
Reemplazar por un `Select` administrable desde Catálogos (Oracle EBS, Oracle Fusion, Data & Analytics, Infraestructura, etc.), con opción "Otro" para casos no cubiertos, alineado con la nomenclatura oficial del equipo SyWork.

**Criterios de aceptación**
- [ ] El campo Equipo es un `Select` alimentado por un catálogo administrable.
- [ ] Incluye una opción "Otro".
- [ ] Las opciones del catálogo son administrables desde el módulo de Catálogos.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/pages/TeamPage.tsx:368`._

---

### OBS-0025 — Matriz de permisos en Roles muestra celdas vacías y omite 9 permisos reales

- **Módulo/Pantalla:** Roles y Permisos
- **Tipo:** Defecto
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
La matriz "módulo × acción" en la pantalla de Roles presenta dos problemas: (a) siempre renderiza 4 columnas fijas (`view`, `create`, `edit`, `deactivate`); para módulos donde no existen esas acciones, las celdas quedan en blanco sin explicación ("cosas para chulear que no existen"); (b) 9 permisos que sí existen en base de datos nunca se muestran en la UI, por lo que no se pueden asignar desde la pantalla de Roles: `client_contacts.manage`; `tickets.assign`, `tickets.cancel`, `tickets.transition`, `tickets.view_own`; `work_sessions.manage`, `work_sessions.manage_all`, `work_sessions.view_all`, `work_sessions.view_own`.

Los roles semilla (Admin, Coordinador, QM, Resolutor) tienen algunos de estos permisos porque las migraciones los sembraron por SQL directo, pero un admin que crea un rol nuevo desde la UI **no puede** darle permiso de transicionar tickets, asignar, cancelar, ni gestionar sesiones de trabajo.

Causa raíz: en `frontend/src/components/roles/PermissionMatrix.tsx:6`, `const ACTIONS = ['view', 'create', 'edit', 'deactivate'] as const` — las columnas están hardcodeadas y no reflejan el catálogo dinámico de permisos.

**Pasos para reproducir**
1. Menú Roles → Nuevo rol "TestQA" → Guardar.
2. Editar "TestQA" → observar la matriz módulo × acción.
3. Comparar contra `SELECT module, action FROM permissions`.

**Resultado esperado / Situación actual**
Esperado: la matriz muestra todas las combinaciones (módulo, acción) que existen en base de datos, y solo esas; las celdas donde no existe la combinación deben distinguirse visualmente (ej. "—" o gris deshabilitado) de las que sí existen pero no están marcadas.
Actual: columnas fijas que no reflejan el catálogo real, y 9 permisos reales inasignables desde la UI.

**Resultado actual / Propuesta de mejora**
(1) Calcular las columnas dinámicamente: `const ACTIONS = Array.from(new Set(allPermissions.map(p => p.action))).sort()`. (2) Para módulos donde `byAction[action]` es `undefined`, renderizar un guión gris ("—") en vez de celda vacía. (3) Agregar `ACTION_LABELS` para las acciones nuevas (`assign`, `cancel`, `transition`, `manage`, `manage_all`, `view_all`, `view_own`), más un fallback genérico.

**Criterios de aceptación**
- [ ] La matriz de permisos refleja dinámicamente todas las combinaciones (módulo, acción) existentes en base de datos.
- [ ] Las celdas "no existe la combinación" se distinguen visualmente de "existe pero no está marcada".
- [ ] Un rol creado desde la UI puede recibir los 9 permisos actualmente ocultos.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/components/roles/PermissionMatrix.tsx:6-58`; verificado contra `SELECT module, action FROM permissions`._

---

### OBS-0026 — Un ticket se puede cerrar sin tiempo registrado (cronómetro sin efecto sobre el cierre)

- **Módulo/Pantalla:** Tickets > Cierre · Cronómetro (spec 012)
- **Tipo:** Defecto
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
Un ticket puede transitar hasta "Cerrado" con 0 minutos registrados en `work_sessions`, sin correr el cronómetro. El endpoint de cierre no consulta `work_sessions` ni el timer en ningún momento, por lo que el cronómetro entregado en spec 012 termina siendo decorativo — no afecta el cierre ni queda como requisito.

Causa raíz: el flujo de cierre nunca se actualizó cuando se mergeó spec 012 (Cronómetro). El servicio `ticket_timer_service.py` existe y el endpoint `timer.py` está registrado, pero ninguna de sus salidas alimenta la validación de `TicketClose.post` (`backend/api/routes/tickets.py:1006-1066`).

**Pasos para reproducir**
1. Crear un ticket nuevo → asignarlo a un usuario (Resolutor).
2. Transicionarlo hasta "Resuelto" sin correr el cronómetro ni registrar ninguna sesión de trabajo.
3. Confirmar el cierre (aceptación del usuario o esperar 3+ días).
4. `POST /api/tickets/{id}/close` con `resolution_type_id` y `body` → devuelve 200 y el ticket queda cerrado.
5. Verificar `SELECT SUM(duration_minutes) FROM work_sessions WHERE ticket_id = ...` → `0` o `NULL`.

**Resultado esperado / Situación actual**
Esperado: el cierre debería validar que el ticket tiene al menos algún tiempo registrado (vía `work_sessions` o cronómetro cerrado), excepto para tipos de resolución que semánticamente no requieren trabajo (Duplicado, No aplica, Reasignado a otro sistema, etc.).
Actual: el endpoint no valida tiempo registrado en ningún caso.

**Resultado actual / Propuesta de mejora**
Requiere decisión de producto entre: (A) validación fuerte — en `TicketClose.post`, tras validar `close_eligible`, consultar `WorkSessionRepository.sum_minutes(ticket_id)`; si es 0 y el tipo de resolución no está marcado `allow_zero_time` (nuevo campo de catálogo), devolver `409 no_time_registered`; (B) validación blanda — permitir cerrar con 0 tiempo pero mostrar un modal de confirmación explícito y guardar un flag `closed_without_time`; (C) configurable por proyecto — campo `require_time_on_close: bool`. Recomendación técnica: **A + C**. Revisar además si el mismo hueco aplica al cierre de Tareas (spec 009, `PATCH /status` libre).

**Criterios de aceptación**
- [ ] Producto decide la postura (A, B, C o combinación).
- [ ] El cierre de tickets valida tiempo registrado según la postura elegida, salvo excepciones explícitas por tipo de resolución.
- [ ] Se revisa si el mismo hueco aplica al cierre de Tareas y se decide si se corrige en el mismo esfuerzo.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `backend/api/routes/tickets.py:1006-1066`, `backend/domain/services/ticket_timer_service.py`; spec 012 (Cronómetro), spec 009 (ciclo unificado)._

---

### OBS-0027 — Múltiples usuarios simultáneos en el mismo navegador (postura de seguridad a definir)

- **Módulo/Pantalla:** Autenticación > Frontend authStore
- **Tipo:** Mejora
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
El estado de autenticación vive en Zustand con `persist` en `localStorage` (`sywork-auth`), que es compartido entre pestañas del mismo origen. Un login en una pestaña sobrescribe el token guardado por otra, pero Zustand mantiene el estado en memoria por pestaña — no re-hidrata al detectar el cambio. Resultado: cada pestaña sigue operando con su propio token en memoria hasta que se recarga, momento en el que toma el último token que quedó en `localStorage`. El backend acepta ambos tokens porque son JWT válidos, sin registro de "sesión activa por usuario", y `Flask-JWT-Extended` está configurado sin blocklist (token robado sigue vivo hasta expirar, 8h).

**Pasos para reproducir**
1. Iniciar sesión como `admin` en la pestaña A.
2. En la pestaña B (mismo navegador/perfil), navegar a `/login` y entrar como `resolutor`.
3. Volver a la pestaña A → sigue operando como `admin` sin problema.
4. Recargar la pestaña A → ahora carga como `resolutor` (el último que quedó en `localStorage`).

**Resultado esperado / Situación actual**
Hay tres posturas válidas a elegir por producto/seguridad: (1) permisiva — aceptar múltiples sesiones, documentar que para aislar hay que usar incógnito/otro perfil; (2) una sesión por navegador — forzar logout en las demás pestañas al detectar login nuevo; (3) una sesión por usuario (más estricta) — invalidar a nivel servidor todos los JWT anteriores del mismo usuario al emitir uno nuevo. Riesgos del estado actual: estación compartida con sesiones cruzadas confusas para auditoría; posible confusión de rol tras una recarga inconsistente; sin lista de revocación de JWT.

**Resultado actual / Propuesta de mejora**
Según la postura elegida: permisiva (solo documentar), "una sesión por navegador" (cambiar `localStorage`→`sessionStorage`, `BroadcastChannel` para forzar logout cruzado), o "una sesión por usuario" (columna `current_jti` en `users`, middleware que valida `jti == user.current_jti`, invalidando el token anterior en cada login nuevo). Recomendación técnica: la postura "una sesión por usuario" es la más segura y la que suele exigir compliance interno (SOC2, ISO 27001); costo medio.

**Criterios de aceptación**
- [ ] Producto/seguridad define la postura a adoptar (permisiva, una sesión por navegador, o una sesión por usuario).
- [ ] Se implementan los cambios correspondientes a la postura elegida.
- [ ] Test de verificación: login del mismo usuario en dos pestañas — el JWT de la primera responde según la postura elegida (401 en posturas estrictas, 200 en permisiva).

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `frontend/src/store/authStore.ts:27-49`, `backend/app.py:16-20`._

---

### OBS-0028 — Listados de tickets sin ordenamiento útil para el Resolutor

- **Módulo/Pantalla:** Tickets > Listados (TicketsPage / MyTasksPage / Kanban)
- **Tipo:** Mejora
- **Estado:** Abierta
- **Reportado por:** Emilio Vargas
- **Iteración de origen:** ITER-003
- **Iteración de cierre:** —

**Descripción**
Entrando como Resolutor, los tickets aparecen ordenados alfabéticamente y los colores de los tags de prioridad/severidad quedan sin acompañamiento — no ayudan a decidir qué atender primero porque un ticket `crítica` puede aparecer debajo de uno `baja`. Confirmado en código: `backend/infra/repositories/ticket_repo.py:11-16` ordena `priority` y `status` con `ASC` alfabético sobre texto (`alta, baja, critica, media` en vez de urgencia real `critica > alta > media > baja`), y no agrupa por columna del Kanban.

**Pasos para reproducir** (no aplica — Mejora, hallazgo de UX/consulta)

**Resultado esperado / Situación actual**
Esperado (orden por defecto sugerido para Resolutor, Mis Tareas + Tickets): ordenar por urgencia real de prioridad, luego severidad, luego fecha de creación — no alfabéticamente. Mismo criterio en cada columna del Kanban. Coordinador/QM podrían tener un `default_sort` distinto (por `created_at DESC` para triage cronológico).
Actual: orden alfabético sobre texto en `priority` y `status`.

**Resultado actual / Propuesta de mejora**
Opción A (rápida, sin migración): agregar sorts `priority_desc_urgency` / `severity_desc_urgency` al diccionario `_SORTS` usando `CASE` de SQLAlchemy. Opción B (más robusta, requiere migración): columna numérica `priority_rank` poblada por trigger o al asignar prioridad, para sort e índices eficientes — considerar cuando la tabla supere ~10k tickets. Recomendación técnica: A ahora, evaluar B más adelante. Complementar con UI: mostrar el ordenamiento activo en la cabecera/columna sorter, y en Kanban un chip "Ordenado por: Prioridad ↓".

**Criterios de aceptación**
- [ ] El orden por defecto para Resolutor prioriza urgencia real (crítica > alta > media > baja), no orden alfabético.
- [ ] El mismo criterio de orden aplica dentro de cada columna del Kanban.
- [ ] Se decide con producto si Coordinador/QM requieren un `default_sort` distinto.
- [ ] La UI indica visualmente el criterio de ordenamiento activo.

**Evidencia**
_Sin evidencia gráfica adjunta — referencia de código: `backend/infra/repositories/ticket_repo.py:11-63`; vistas afectadas: `MyTasksPage.tsx`, `TicketsPage.tsx`, `KanbanPage.tsx`._
