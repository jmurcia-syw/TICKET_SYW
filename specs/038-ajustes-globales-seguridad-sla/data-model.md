# Data Model: Ajustes Globales — Seguridad/Permisos, Notificaciones, Motor de SLA, Bugs de UI y Rendimiento

Sin tablas nuevas. Cambios sobre entidades/tablas ya existentes, resumidos por user story.

## US1 — Permisos y vistas por rol

### Permiso RBAC nuevo

| Tabla | Cambio |
|-------|--------|
| `permissions` | Nueva fila `(module='tickets', action='view_assigned')` |
| `role_permissions` | Nueva fila vinculando el rol `Resolutor` al permiso `tickets:view_assigned`; se elimina (si existía) el vínculo `Resolutor` → `tickets:view` |

Semántica: un actor con `tickets:view_assigned` (y sin `tickets:view`) solo puede listar/ver
tickets donde `assignee_id` corresponde a su propio `resource_id`. No reemplaza ni modifica
`tickets:view_own` (Usuario/cliente, scoping por `client_contact_id`, migración `021`), que
permanece sin cambios.

### Preferencia de menú colapsado

No es una entidad persistida en base de datos — es estado de UI (`collapsed: boolean`) que vive en
el store de sesión del frontend (Zustand, mismo store de layout/tema ya existente o uno nuevo
acotado a esta preferencia), sin sincronizarse entre dispositivos ni persistirse en el backend.

## US2 — Motor de SLA y auditoría inicial

### `ticket_status_transitions` (existente, sin migración de esquema)

| Columna | Cambio |
|---------|--------|
| `from_status` (`Text NOT NULL`) | Nuevo valor sentinel permitido: `"creado"` — representa la entrada de auditoría inicial generada en el momento de creación del Ticket/Tarea, no una transición real del FSM |
| `to_status` | Sin cambio — para la entrada inicial, contiene el estado inicial real (`"nuevo"` u otro que aplique según el flujo de creación) |
| `comment_id` (ya `nullable`) | `NULL` para la entrada de auditoría inicial (no hay comentario tipificado asociado) |
| `actor_id` | El usuario que creó el Ticket/Tarea |

Consumo: `_transitions_with_sla()` (`backend/api/routes/tickets.py`) y el componente de Historial
de Estados en frontend distinguen `from_status === "creado"` para renderizar "Ticket creado en
estado {to_status}" en vez del formato "cambio de estado" habitual.

### `tickets` — sin columna nueva

El cómputo de fase/congelamiento de SLA se deriva en tiempo real (spec `014`) a partir de
`sla_contact_result`/`sla_execution_result` (ya existentes) y de los diccionarios de dominio
`SLA_PHASE_FOR_STATE`/`STATE_COUNTS_FOR_SLA` (`backend/domain/fsm/ticket_fsm.py`), que cambian de
valor (ver research.md Decisiones 3-4) pero no de forma/esquema.

## US4 — Formularios y validaciones

### `work_sessions.note`

Columna ya existente (`Optional[str]`) — pasa a exigirse no vacía en
`WorkSessionService.create()`/`update()` (Capa 1, validación de dominio) antes de persistir; sin
cambio de tipo de columna (sigue siendo `nullable=True` a nivel de esquema por compatibilidad con
registros históricos ya creados sin nota, pero el flujo de creación/edición nuevo la exige).

### `tickets.client_contact_id`

Sin cambio de esquema — ya es `nullable` a nivel de base de datos (una Tarea puede no tener
solicitante). El endurecimiento a "obligatorio para Ticket, opcional para Tarea" es una regla de
validación en el servicio de creación (`ticket_service.py`)/formulario, no un cambio de columna.

## US5 — Correo de bienvenida

No introduce una tabla nueva. Reutiliza el mecanismo de token de un solo uso ya existente para el
reseteo de contraseña (spec `003` — tabla/columna de token con expiración ya implementada ahí);
"Notificar al Usuario" simplemente dispara la generación de ese mismo tipo de token en el momento
de creación del usuario, en vez de esperar a que el usuario lo solicite desde "¿Olvidaste tu
contraseña?".

| Concepto (no persistido como entidad propia) | Campos |
|---|---|
| Correo de bienvenida | destinatario (email del usuario nuevo), nombre, URL de login, contraseña temporal (la ya generada hoy al crear el usuario), enlace de cambio (token existente + expiración de 30 min ya implementada) |

### `POST /api/users` (payload)

| Campo | Cambio |
|-------|--------|
| `notify` | Nuevo, `boolean`, opcional, default `false` — si es `true`, dispara el envío del correo de bienvenida tras crear el usuario exitosamente |

## US3 / US6 — Bugs de UI y rendimiento

Sin cambios de modelo de datos — son correcciones de estado de componente (frontend) y de patrón
de carga de datos (frontend + posible ajuste de consultas en `ClientRepository`, sin nueva forma de
dato expuesta al cliente).
