# Implementation Plan: Accesos y conexiones múltiples del Cliente

**Branch**: `018-cliente-accesos-conexiones` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/018-cliente-accesos-conexiones/spec.md`

## Summary

Reemplazar los campos simples `vpn_ips`/`vpn_credentials` del Cliente por una entidad hija
`ClientAccess` (accesos y conexiones), 1-a-muchos con Cliente, con tipo/ambiente/usuario/
contraseña/host/notas y adjuntos de archivo a nivel de cliente. Se sigue el mismo patrón ya
usado por `ClientSystem` (portafolio de software): repositorio con métodos
list/add/delete independientes del guardado principal del cliente, expuestos en endpoints REST
propios y renderizados en una pestaña separada (Ant Design `Tabs`) dentro del modal de
Detalle/Edición, con tabla ancha horizontal. Contraseña enmascarada por defecto, gobernada por
el mismo permiso `include_sensitive` que ya existe. Migración de datos automática y sin pérdida
desde `vpn_ips`/`vpn_credentials` hacia un registro `ClientAccess` inicial tipo VPN.

## Technical Context

**Language/Version**: Python 3.12 (Flask, backend) · TypeScript 5.6 strict + React 19 (frontend)

**Primary Dependencies**: Flask-RESTX (contrato Swagger/OpenAPI), SQLAlchemy + Alembic, Ant Design 5 (`Table`, `Tabs`, `Modal`, `Input.Password`) — todas ya aprobadas en la Constitución, sin altas nuevas. Reutiliza y generaliza `backend/infra/storage/attachments.py` (hoy acoplado a `ticket_id`) para adjuntos de clientes.

**Storage**: PostgreSQL 16 — dos tablas nuevas: `client_access` (FK `client_id`) y `client_access_attachments` (FK `client_id`), ambas con Row Level Security habilitado (mismo patrón app-level que `020_client_contacts_rls.py`).

**Testing**: pytest en backend, ultra-limitado por Principio VII (≤10 registros por test, solo el módulo tocado). No hay framework de tests de frontend configurado en este repo (verificación manual en navegador vía Docker, igual que specs previas).

**Target Platform**: Web app en Docker Compose on-premise — sin cambios de infraestructura.

**Project Type**: Web application (monorepo `backend/` + `frontend/`, Option 2).

**Performance Goals**: N/A — uso interno de bajo volumen (decenas de clientes, pocos accesos por cliente); sin metas de throughput específicas.

**Constraints**: La migración de datos existentes (`vpn_ips`/`vpn_credentials` → `client_access`) DEBE ejecutarse dentro de la misma migración Alembic que crea la tabla, DEBE ser reversible (`downgrade` reconstruye los campos originales) y no debe perder información. RLS obligatorio en ambas tablas nuevas por contener credenciales (Principio IV).

**Scale/Scope**: Acotado a Maestros > Clientes (creación, edición, detalle). No toca Proyectos, Tickets ni otros módulos.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Estado |
|---|---|---|
| I. API-First y Dominio Primero | Nuevos endpoints (`GET/POST/PATCH/DELETE /api/clients/{id}/access`, `POST/GET/DELETE /api/clients/{id}/access-attachments`) se documentan en Swagger (Flask-RESTX `@ns.expect`/`@ns.response`) antes de implementar el handler, igual que el resto de `clients.py`. Lógica de migración/validación vive en `backend/domain/`, no en la ruta. | PASS |
| II. Clean Architecture (3 capas) | `ClientAccess` como entidad en `backend/domain/entities/client.py` (junto a `ClientSystem`); `ClientAccessModel`/`ClientAccessAttachmentModel` en `backend/infra/models/`; `ClientRepository` gana métodos `list_access/add_access/update_access/delete_access` — mismo patrón que `list_systems/add_system/delete_system`, sin lógica de negocio en la ruta Flask. | PASS |
| III. Tipado estricto | Tipos TS nuevos (`ClientAccess`, `ClientAccessFormData`) en `frontend/src/types/client.ts`; sin `any`. Type hints en entidades/servicios Python. | PASS |
| IV. Seguridad en profundidad | RLS habilitado en `client_access` y `client_access_attachments` (mismo patrón que `client_contacts`). Contraseña cifrada en reposo igual que `vpn_credentials` hoy. Enmascarado en UI gobernado por el permiso `include_sensitive` ya existente — no se crea un permiso nuevo. | PASS |
| V. Gobernanza de librerías | Sin dependencias nuevas: Ant Design (`Tabs`, `Input.Password`) y SQLAlchemy/Alembic ya están aprobados y en uso. | PASS |
| VI. AI-Native | No aplica — no es un flujo de asignación/triage ni genera Gold Standard Dataset. Sin impacto. | N/A |
| VII. Alcance de sesión / testing ultra-limitado | Implementación acotada a Maestros > Clientes. Tests backend nuevos ≤10 registros de prueba, solo sobre el modelo/repositorio/ruta tocados. | PASS |

**Resultado**: Sin violaciones. No se requiere `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/018-cliente-accesos-conexiones/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/            # Fase 1
└── tasks.md              # Fase 2 (/speckit-tasks, no generado por /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── domain/
│   └── entities/
│       └── client.py                  # + dataclass ClientAccess, ClientAccessAttachment
├── infra/
│   ├── models/
│   │   └── client_model.py            # + ClientAccessModel, ClientAccessAttachmentModel
│   ├── repositories/
│   │   └── client_repo.py             # + list_access/add_access/update_access/delete_access
│   ├── storage/
│   │   └── attachments.py             # generalizar save()/open_path() para aceptar entity_type
│   └── migrations/versions/
│       ├── 030_client_access.py       # crea tablas + migra vpn_ips/vpn_credentials existentes
│       └── 031_client_access_rls.py   # RLS en ambas tablas nuevas
└── api/
    └── routes/
        └── clients.py                 # + endpoints CRUD de access y access-attachments

frontend/
├── src/
│   ├── types/
│   │   └── client.ts                  # + ClientAccess, ClientAccessFormData
│   ├── services/
│   │   └── clientService.ts           # + listAccess/addAccess/updateAccess/deleteAccess/uploadAccessAttachment
│   └── pages/
│       └── ClientsPage.tsx            # Modal de Detalle → Tabs ("Datos generales" / "Accesos y conexiones")
```

**Structure Decision**: Se mantiene el layout de repo existente (Clean Architecture 3 capas en
`backend/`, `pages/services/types` en `frontend/`). No se crean paquetes ni directorios nuevos de
alto nivel — todo el trabajo extiende archivos ya existentes de Clientes, siguiendo el patrón
`ClientSystem` ya validado en producción.

## Complexity Tracking

*No aplica — Constitution Check sin violaciones.*
