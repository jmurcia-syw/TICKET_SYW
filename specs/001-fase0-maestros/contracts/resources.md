# API Contract: Resources & Skills

Nota: `Resource` no tiene campo `role` propio. El rol de acceso (permisos) vive unicamente en el
`User` vinculado via `user_id` (relacion opcional 0..1) — ver Clarifications en spec.md.

---

## Resources — Base path: `/api/resources`

**Auth**: JWT Bearer requerido
**Roles (FR-009, FR-013, permisos sembrados en `009_roles_permissions_login.py`)**:
- Admin, Coordinador, QM: `resources` view/create/edit/deactivate — CRUD completo
- Resolutor: `resources: view` únicamente, y ademas restringido a su propio recurso
  (verificado por `user_id` en JWT, independiente del catalogo de permisos)

---

### GET /api/resources

**Query params**: `page`, `page_size`, `search` (nombre), `skill_code` (filtrar por skill), `active`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "full_name": "Carlos Rodriguez",
      "email": "carlos.rodriguez@sywork.net",
      "active": true,
      "skills": [
        { "id": "uuid", "code": "JDE_GL", "label": "JDE General Ledger" },
        { "id": "uuid", "code": "API_REST", "label": "API REST Integration" }
      ],
      "created_at": "2026-06-29T00:00:00Z"
    }
  ],
  "total": 8,
  "page": 1,
  "page_size": 20
}
```

---

### GET /api/resources/{id}

**Response 200**: objeto recurso completo con skills.
**Errors**: 401, 403 (Resolutor intentando ver otro recurso), 404

---

### POST /api/resources

Solo Admin.

**Body**:
```json
{
  "full_name": "Carlos Rodriguez",
  "email": "carlos.rodriguez@sywork.net",
  "user_id": "uuid",
  "skill_ids": ["uuid-jde-gl", "uuid-api-rest"],
  "notes": "Senior JDE consultant"
}
```

**Response 201**: objeto recurso creado.

**Errors**:
- 400 `{ "error": "email_duplicate", "message": "Ya existe un recurso con ese email" }`
- 400 `{ "error": "invalid_email_domain", "message": "El email debe ser @sywork.net" }`
- 401, 403

---

### PATCH /api/resources/{id}

Admin: cualquier campo. Resolutor: solo `notes` de su propio recurso.

**Response 200**: objeto recurso actualizado.
**Errors**: 400, 401, 403, 404

---

### PATCH /api/resources/{id}/skills

Reemplaza lista completa de skills del recurso. Solo Admin.

**Body**: `{ "skill_ids": ["uuid1", "uuid2"] }`

**Response 200**: objeto recurso con skills actualizados.
**Errors**: 400, 401, 403, 404

---

### PATCH /api/resources/{id}/deactivate

Solo Admin.
**Response 200**: `{ "id": "uuid", "active": false }`
**Errors**: 401, 403, 404

---

### PATCH /api/resources/{id}/activate

Reactivar un recurso previamente desactivado. Solo Admin.
**Response 200**: `{ "id": "uuid", "active": true }`
**Errors**: 409 `{ "error": "already_active" }`, 401, 403, 404

---

## Skills — Base path: `/api/skills`

**Auth**: JWT Bearer requerido
**Roles**: Admin (CRUD) — todos los roles (GET lista)

---

### GET /api/skills

**Query params**: `active` (bool, default true)

**Response 200**:
```json
{
  "items": [
    { "id": "uuid", "code": "JDE_GL", "label": "JDE General Ledger", "active": true },
    { "id": "uuid", "code": "API_REST", "label": "API REST Integration", "active": true }
  ],
  "total": 12
}
```

---

### POST /api/skills

Solo Admin.

**Body**: `{ "code": "ORACLE_FUSION", "label": "Oracle Fusion" }`

**Response 201**: skill creado.
**Errors**: 400 `{ "error": "code_duplicate" }`, 401, 403

---

### DELETE /api/skills/{id}

Solo Admin. Falla si el skill esta asignado a recursos activos.

**Response 204**: eliminado.

**Errors**:
- 409 `{ "error": "skill_in_use", "message": "El skill esta asignado a 3 recursos activos", "resource_count": 3 }`
- 401, 403, 404

---

## Ampliación SDD V3 (2026-07-02, FR-031/FR-032/FR-033)

### Perfil extendido (FR-031)

Los payloads de recurso (list, detail, create, update) incluyen ahora (todos opcionales):
`identification`, `nationality`, `birth_date` (YYYY-MM-DD), `marital_status`,
`contract_type`, `calendar_country`, `education_level`, `specialty`, `seniority`,
`certifications`, `team`, `manager_id` (UUID de otro recurso).

Reglas de `manager_id`: debe existir, estar activo y ser distinto del propio recurso
(400/404 segun el caso). `null` lo elimina.

### GET /api/resources/{id}/compensation  🔒

Area protegida (FR-032/FR-033). **Requiere JWT + permiso `compensation: view`**
(a diferencia del resto de maestros, esta ruta SI aplica enforcement en backend por
tratarse de dato sensible, mismo criterio que los campos VPN).

**Response 200**:
```json
{ "resource_id": "uuid", "base_salary": 4000.0, "total_salary": 6000.0,
  "overhead": 1200.0, "hourly_cost": 30.0, "currency": "USD", "updated_at": "iso-8601" }
```
Errores: 401 sin JWT, 403 sin permiso (payload sin detalle del recurso solicitado, FR-023),
404 recurso o compensacion inexistente.

### PUT /api/resources/{id}/compensation  🔒

**Requiere JWT + permiso `compensation: edit`.** Upsert completo.
Body: `{ "base_salary": 4000, "total_salary": 6000, "overhead": 1200, "currency": "USD" }`.
`hourly_cost` NO se acepta en el body: lo calcula el backend como
`(total_salary + overhead) / 240` (horas mes) — FR-032.
Validaciones: montos >= 0; `total_salary >= base_salary`. **Response 200** con el registro
guardado (incluye `hourly_cost` calculado).
