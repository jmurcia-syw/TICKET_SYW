# Data Model: Fase 1 — Tickets

**Date**: 2026-07-02 | **Feature**: specs/002-fase1-tickets

Extiende el MER de Fase 0 (`docs/MER.md`). Migraciones: `011_create_tickets.py`,
`012_tickets_rls.py`, `013_dynamic_record_type.py` (catálogo dinámico de tipo de registro,
amendment 2026-07-06).

## Entidades

### tickets

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK, gen_random_uuid() | Identificador |
| ticket_number | BIGINT | NOT NULL, UNIQUE, secuencia `ticket_number_seq` | Consecutivo global; se muestra `TK-000123` |
| record_type_id | UUID | NOT NULL, FK catalog_record_types(id) | Tipo de registro (Ticket/Tarea); dominio bloquea crear con "Tarea" (reservado Fase 3, FR-030) |
| ticket_type | TEXT | NOT NULL, CHECK IN ('incident','evolutive','preventive') | Tipo |
| title | TEXT | NOT NULL | Título |
| description | TEXT | NOT NULL | Descripción |
| status | TEXT | NOT NULL, CHECK IN (10 estados), default 'nuevo' | Estado FSM |
| priority | TEXT | NOT NULL, CHECK IN ('critical','high','medium','low') | Prioridad |
| severity | TEXT | NOT NULL, CHECK IN ('s1','s2','s3','s4') | Severidad |
| escalation_level | TEXT | NOT NULL, CHECK IN ('n1','n2','n3','n4'), default 'n2' | Nivel de escalamiento |
| client_id | UUID | NOT NULL, FK clients(id) | Cliente (obligatorio) |
| project_id | UUID | NULLABLE, FK projects(id) | Proyecto (opcional — soporte general) |
| tool_id | UUID | NULLABLE, FK catalog_tools(id) | Herramienta (JDE, Fusion…) |
| process_id | UUID | NULLABLE, FK catalog_processes(id) | Proceso |
| assignee_id | UUID | NULLABLE, FK resources(id) | Resolutor asignado actual |
| estimated_resolution_minutes | INTEGER | NULLABLE, CHECK >= 0 | Tiempo estimado de resolución (informativo en Fase 1) |
| resolution_type_id | UUID | NULLABLE, FK catalog_resolution_types(id) | Obligatorio solo al CERRAR (validación en dominio) |
| related_ticket_id | UUID | NULLABLE, FK tickets(id), CHECK <> id | Registro relacionado |
| created_by | UUID | NOT NULL, FK users(id) | Autor |
| resolved_at | TIMESTAMPTZ | NULLABLE | Fecha en que pasó a RESUELTO (base del cierre a 3 días) |
| closed_at | TIMESTAMPTZ | NULLABLE | Fecha de cierre |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL, now() | Auditoría mínima |

**Estados** (`status`): `nuevo`, `pre_analisis`, `contacto`, `en_analisis`, `en_ejecucion`,
`en_pruebas`, `pendiente_usuario`, `resuelto`, `cerrado`, `cancelado`.

**Índices**: `(status)`, `(client_id)`, `(assignee_id)`, `(assignee_id, status)` para el
Panel de Asignación, `(ticket_number)` UNIQUE.

**Reglas de negocio**:
- Nace siempre en `nuevo` (FR-002); el estado SOLO cambia vía FSM (nunca PATCH directo)
- `record_type_id` referencia `catalog_record_types`, administrable como los demás catálogos
  (FR-029); el dominio valida en creación que resuelva al valor "Ticket" — cualquier otro
  valor activo del catálogo (incluida "Tarea") se rechaza en esta fase (FR-030)
- `resolution_type_id` + comentario "Descripción solución" obligatorios para cerrar (FR-012)
- Bloqueos de campos por estado (FR-010) — mapa `FIELD_LOCKS` en dominio, expuesto como
  `locked_fields` en el detalle
- Solo clientes activos y proyectos activos del cliente en creación (FR-001); las
  referencias sobreviven desactivaciones posteriores
- RLS: lectura para todo usuario autenticado con permiso `tickets:view`; transiciones solo
  del asignado o Coordinador/QM/Admin (validación en servicio, FR-028)

### ticket_comments

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK | |
| ticket_id | UUID | NOT NULL, FK tickets(id) | |
| comment_type | TEXT | NOT NULL, CHECK IN (catálogo FR-013) | Tipo estructurado |
| visibility | TEXT | NOT NULL, CHECK IN ('internal','external') | FR-016 (externo = visible al cliente en Fase 8) |
| body | TEXT | NOT NULL | Contenido |
| author_id | UUID | NOT NULL, FK users(id) | Autor |
| is_automatic | BOOLEAN | NOT NULL, default false | true para Asignado/Pre-Análisis generados por asignación |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Tipos** (`comment_type`): `asignado`, `pre_analisis`, `confirmacion_atencion`,
`solicitud_informacion`, `termina_analisis`, `solicitud_cierre`, `respuesta_usuario`,
`descripcion_solucion`, `comentario_interno`, `cancelacion`.

**Reglas**: cada tipo solo es válido en los estados que la matriz permite (FR-014); los que
disparan transición se ejecutan atómicamente con ella (Decisión 2 de research.md).

### comment_attachments

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK | |
| comment_id | UUID | NOT NULL, FK ticket_comments(id) | |
| filename | TEXT | NOT NULL | Nombre original |
| content_type | TEXT | NOT NULL | MIME |
| size_bytes | BIGINT | NOT NULL, CHECK <= límite configurado | default máx 10 MB |
| storage_path | TEXT | NOT NULL | Ruta relativa bajo /repo/uploads |
| created_at | TIMESTAMPTZ | NOT NULL | |

### ticket_status_transitions (append-only)

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK | |
| ticket_id | UUID | NOT NULL, FK tickets(id) | |
| from_status / to_status | TEXT | NOT NULL | Estados origen/destino |
| actor_id | UUID | NOT NULL, FK users(id) | Quién ejecutó la acción |
| comment_id | UUID | NULLABLE, FK ticket_comments(id) | Comentario que disparó (si aplica) |
| created_at | TIMESTAMPTZ | NOT NULL | |

### ticket_assignments (append-only — Gold Standard Dataset, FR-019)

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK | |
| ticket_id | UUID | NOT NULL, FK tickets(id) | |
| assigner_id | UUID | NOT NULL, FK users(id) | Quién asignó (humano hoy, IA mañana) |
| assignee_id | UUID | NOT NULL, FK resources(id) | A quién |
| resulting_status | TEXT | NOT NULL | contacto o pre_analisis |
| context | JSONB | NOT NULL | Snapshot: `{assignee_skills: [...], assignee_open_tickets: n, ticket_priority, ticket_severity}` |
| created_at | TIMESTAMPTZ | NOT NULL | |

### notifications

| Columna | Tipo | Constraints | Descripcion |
|---------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | NOT NULL, FK users(id) | Destinatario |
| event_type | TEXT | NOT NULL | assigned, user_replied, resolution_rejected, closed, close_eligible |
| ticket_id | UUID | NOT NULL, FK tickets(id) | |
| message | TEXT | NOT NULL | Texto en español |
| read | BOOLEAN | NOT NULL, default false | |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Índice**: `(user_id, read)`.

### catalog_tools / catalog_processes / catalog_resolution_types / catalog_record_types

Estructura común (4 tablas):

| Columna | Tipo | Constraints |
|---------|------|-------------|
| id | UUID | PK |
| name | TEXT | NOT NULL, UNIQUE |
| active | BOOLEAN | NOT NULL, default true |
| created_at | TIMESTAMPTZ | NOT NULL |

**Seed inicial**: tools = JDE, Oracle Fusion, OTM, Otro; processes = Finanzas, Logística,
Manufactura, Integraciones, Otro; resolution_types = Solución definitiva, Workaround,
Configuración, Datos, No es incidente, Sin respuesta de usuario; record_types = Ticket,
Tarea (ambos activos y administrables desde el CRUD genérico de catálogos, pero el dominio
de creación de tickets en esta fase solo acepta el valor "Ticket" — FR-030).

## Permisos nuevos (seed en migración 011)

| Módulo | Acciones | Admin | Coordinador | QM | Resolutor |
|--------|----------|-------|-------------|-----|-----------|
| tickets | view, create, edit, assign, transition, cancel | todas | todas | todas menos cancel | view, create, transition (solo asignados — regla en dominio) |
| assignment_panel | view | ✓ | ✓ | ✓ | — |
| catalogs | view, create, deactivate | ✓ | ✓ | view | view |

`catalogs` aplica a los 4 catálogos por igual (`tools`, `processes`, `resolution-types`,
`record-types`) — mismo permiso, sin distinción por tipo de catálogo.

## Diagrama de relaciones (delta sobre docs/MER.md)

```
clients (1) ──── (N) tickets (N) ──── (0..1) projects
                     │ │ │ │
                     │ │ │ └── related_ticket_id ↺ (autorreferencial)
                     │ │ └── (0..1) resources [assignee]
                     │ └── (N) ticket_comments ──── (N) comment_attachments
                     ├── (N) ticket_status_transitions [append-only]
                     ├── (N) ticket_assignments [append-only, JSONB context]
                     └── (N) notifications ──── (1) users [destinatario]
tickets (N) ──── (0..1) catalog_tools / catalog_processes / catalog_resolution_types
tickets (N) ──── (1) catalog_record_types [record_type_id]
```

## FSM — transiciones codificadas (fuente: Excel + clarificaciones)

| # | From | To | Trigger |
|---|------|----|---------|
| 1 | nuevo | contacto | asignar resolutor |
| 2 | nuevo | pre_analisis | asignar QM ("Pre-Análisis") |
| 3 | pre_analisis | contacto | QM reasigna a resolutor |
| 4 | pre_analisis | pendiente_usuario | comentario solicitud_informacion |
| 5 | contacto | en_analisis | comentario confirmacion_atencion |
| 6 | en_analisis | en_ejecucion | comentario termina_analisis |
| 7 | en_analisis | pendiente_usuario | comentario solicitud_informacion |
| 8 | en_ejecucion | pendiente_usuario | comentario solicitud_informacion |
| 9 | en_ejecucion | resuelto | comentario solicitud_cierre |
| 10 | en_ejecucion | en_pruebas | acción manual del resolutor (Q1 clarificada) |
| 11 | en_pruebas | en_ejecucion | acción manual del resolutor |
| 12 | en_pruebas | resuelto | comentario solicitud_cierre |
| 13 | pendiente_usuario | en_ejecucion | comentario respuesta_usuario |
| 14 | resuelto | en_ejecucion | rechazo de resolución (registrado por el equipo, Q2) |
| 15 | resuelto | cerrado | aceptación o elegibilidad 3 días + tipo resolución + descripcion_solucion |
| 16 | cualquiera no final | cancelado | Coordinador/Admin con comentario cancelacion |

Estados finales: `cerrado`, `cancelado`.
