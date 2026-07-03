# MER — Modelo Entidad-Relación (Fase 0 Maestros + Ampliación SDD V3)

**Generado**: 2026-07-02, extraído del esquema real de PostgreSQL (`information_schema`).
**Migración vigente**: `010_extend_masters_sdd_v3.py` (head).

```mermaid
erDiagram
    clients ||--o{ projects : "tiene"
    clients ||--o{ client_systems : "posee software"
    users }o--|| roles : "tiene rol"
    roles ||--o{ role_permissions : ""
    permissions ||--o{ role_permissions : ""
    users |o--o| resources : "cuenta de acceso"
    resources ||--o| resource_compensation : "compensacion 1:1"
    resources ||--o{ resource_skills : ""
    skills ||--o{ resource_skills : ""
    resources |o--o{ resources : "jefe (manager_id)"

    clients {
        uuid id PK
        text name UK
        text slug UK
        boolean active
        text contact_name
        text contact_email
        text contact_phone
        bytea vpn_ips "cifrado pgcrypto"
        bytea vpn_credentials "cifrado pgcrypto"
        numeric annual_billing_usd "SDD V3"
        text notes
        timestamptz created_at
        timestamptz updated_at
    }

    client_systems {
        uuid id PK
        uuid client_id FK
        text system_type "ERP/WMS/CRM/OTM/otro"
        text brand
        text version
        text notes
        timestamptz created_at
    }

    projects {
        uuid id PK
        uuid client_id FK
        text name "UQ por cliente"
        text description
        text overview "SDD V3"
        numeric sale_services_usd "SDD V3"
        numeric sale_licenses_usd "SDD V3"
        numeric sale_subscriptions_usd "SDD V3"
        text components_sold "SDD V3"
        boolean active
        date start_date
        date end_date_estimated "CHECK >= start_date"
        timestamptz created_at
        timestamptz updated_at
    }

    users {
        uuid id PK
        text email UK "CHECK @sywork.net"
        text username UK
        uuid role_id FK
        text password_hash "login provisional"
        text google_sub UK "Google OAuth2"
        boolean active
        timestamptz last_login_at
        timestamptz created_at
    }

    roles {
        uuid id PK
        text name UK "seed: Admin, Coordinador, QM, Resolutor"
        text description
        boolean active
        timestamptz created_at
    }

    permissions {
        uuid id PK
        text module "clients..roles + compensation"
        text action "view/create/edit/deactivate"
        text description
    }

    role_permissions {
        uuid role_id PK,FK
        uuid permission_id PK,FK
    }

    resources {
        uuid id PK
        uuid user_id FK "UQ, 0..1 con users"
        uuid manager_id FK "autorref, CHECK <> id"
        text full_name
        text email UK
        boolean active
        text identification "SDD V3"
        text nationality "SDD V3"
        date birth_date "SDD V3"
        text marital_status "SDD V3"
        text contract_type "SDD V3"
        text calendar_country "SDD V3"
        text education_level "SDD V3"
        text specialty "SDD V3"
        text seniority "SDD V3"
        text certifications "SDD V3"
        text team "SDD V3"
        text notes
        timestamptz created_at
        timestamptz updated_at
    }

    resource_compensation {
        uuid resource_id PK,FK "1:1 con resources"
        bytea base_salary "cifrado pgcrypto"
        bytea total_salary "cifrado pgcrypto"
        bytea overhead "cifrado pgcrypto"
        bytea hourly_cost "cifrado, calculado por backend"
        text currency
        timestamptz updated_at
    }

    resource_skills {
        uuid resource_id PK,FK
        uuid skill_id PK,FK
        timestamptz assigned_at
    }

    skills {
        uuid id PK
        text code UK "UPPER_SNAKE, ej JDE_GL"
        text label
        boolean active
        timestamptz created_at
    }
```

## Reglas de negocio ancladas al modelo

- `clients` es el **RLS root**: las políticas de Row Level Security parten de aquí (extensible
  a tickets en Fase 1).
- `projects.name` es único **por cliente**, no globalmente (`UNIQUE (client_id, name)`).
- `users.role_id` es NOT NULL: exactamente un rol por usuario; regla del "último Admin"
  aplicada en dominio.
- `resources.manager_id` tiene `CHECK (manager_id IS NULL OR manager_id <> id)`; el dominio
  exige además que el jefe sea un recurso activo.
- `resource_compensation` es accesible solo con permiso `compensation:view/edit`
  (sembrado únicamente para Admin); el endpoint es la única ruta de maestros con
  enforcement JWT en esta fase (FR-033). `hourly_cost` lo calcula el backend:
  `(total_salary + overhead) / 240 h/mes`.
- Campos `bytea` = cifrados en reposo (pgcrypto; implementación dev es placeholder,
  reemplazar por `pgp_sym_encrypt` en producción).
- Un `skill` no puede eliminarse si está asignado a algún recurso; un `permission` no puede
  eliminarse si está asignado a algún rol.

---

# Ampliación Fase 1 — Tickets (2026-07-02, migraciones 011-012)

```mermaid
erDiagram
    clients ||--o{ tickets : ""
    projects |o--o{ tickets : "opcional"
    resources |o--o{ tickets : "assignee"
    users ||--o{ tickets : "created_by"
    tickets |o--o{ tickets : "related_ticket_id"
    tickets ||--o{ ticket_comments : ""
    ticket_comments ||--o{ comment_attachments : ""
    tickets ||--o{ ticket_status_transitions : "append-only"
    tickets ||--o{ ticket_assignments : "append-only (Gold Standard)"
    tickets ||--o{ notifications : ""
    users ||--o{ notifications : "destinatario"
    catalog_tools |o--o{ tickets : ""
    catalog_processes |o--o{ tickets : ""
    catalog_resolution_types |o--o{ tickets : "al cerrar"

    tickets {
        uuid id PK
        bigint ticket_number UK "secuencia, TK-nnnnnn"
        text record_type "ticket|task (task=Fase 3)"
        text ticket_type "incident|evolutive|preventive"
        text status "10 estados FSM"
        text priority "critical..low"
        text severity "s1..s4"
        text escalation_level "n1..n4"
        uuid client_id FK
        uuid project_id FK "nullable"
        uuid tool_id FK "nullable"
        uuid process_id FK "nullable"
        uuid assignee_id FK "nullable"
        int estimated_resolution_minutes
        uuid resolution_type_id FK "obligatorio al cerrar"
        uuid related_ticket_id FK "autorref"
        uuid created_by FK
        timestamptz resolved_at
        timestamptz resolution_accepted_at
        timestamptz closed_at
    }

    ticket_comments {
        uuid id PK
        uuid ticket_id FK
        text comment_type "10 tipos estructurados"
        text visibility "internal|external"
        text body
        uuid author_id FK
        boolean is_automatic
    }

    comment_attachments {
        uuid id PK
        uuid comment_id FK
        text filename
        text content_type
        bigint size_bytes "max 10MB"
        text storage_path "uploads/tickets/id/"
    }

    ticket_status_transitions {
        uuid id PK
        uuid ticket_id FK
        text from_status
        text to_status
        uuid actor_id FK
        uuid comment_id FK "nullable"
    }

    ticket_assignments {
        uuid id PK
        uuid ticket_id FK
        uuid assigner_id FK
        uuid assignee_id FK
        text resulting_status
        jsonb context "skills, carga, prioridad, severidad"
    }

    notifications {
        uuid id PK
        uuid user_id FK
        text event_type "5 eventos"
        uuid ticket_id FK
        text message
        boolean read
    }
```

**Reglas Fase 1**: estado solo cambia vía FSM (`domain/fsm/ticket_fsm.py`, python-transitions,
16 transiciones); `ticket_status_transitions` y `ticket_assignments` son append-only;
RLS habilitado en todas las tablas de tickets (migración 012); permisos: módulos `tickets`
(6 acciones), `assignment_panel`, `catalogs`; enforcement JWT+permiso activo en TODA la API.
