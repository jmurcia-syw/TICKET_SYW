"""spec 010, US4 — estructura de Skill (tipo obligatorio, herramienta/proceso opcionales)
y semillas de la migración 025."""
import uuid


def _skills_by_code(client):
    resp = client.get("/api/skills?active=all")
    assert resp.status_code == 200
    return {s["code"]: s for s in resp.get_json()["items"]}


# ── Semillas (FR-015/FR-016/FR-017, migración 025) ───────────────────────────

def test_seed_skills_have_tool_process_and_type(client):
    skills = _skills_by_code(client)
    jde_gl = skills["JDE_GL"]
    assert jde_gl["skill_type"] == "funcional"
    assert jde_gl["tool_name"] == "JDE"
    assert jde_gl["process_name"] == "Finanzas"

    oic = skills["OIC"]
    assert oic["skill_type"] == "tecnico"
    assert oic["tool_name"] == "Oracle Fusion"
    assert oic["process_name"] == "Integraciones"

    dba = skills["DBA"]
    assert dba["skill_type"] == "tecnico"
    assert dba["tool_name"] is None
    assert dba["process_name"] is None

    for code in ("JDE_AP", "JDE_MTC", "BSFN", "SQL_JDE", "APEX", "BI", "JAVA_PYTHON_REACT"):
        assert code in skills, f"semilla {code} ausente"


def test_seed_upsert_did_not_duplicate_existing_codes(client):
    resp = client.get("/api/skills?active=all")
    codes = [s["code"] for s in resp.get_json()["items"]]
    assert codes.count("JDE_GL") == 1
    assert codes.count("JDE_AP") == 1


def test_preexisting_skills_got_type_backfilled(client):
    skills = _skills_by_code(client)
    assert skills["JDE_AR"]["skill_type"] == "funcional"
    assert skills["API_REST"]["skill_type"] == "tecnico"


def test_seed_processes_compras_mantenimiento_exist(client):
    resp = client.get("/api/catalogs/processes?active=all")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.get_json()["items"]}
    assert {"Compras", "Mantenimiento"} <= names


# ── POST /api/skills (FR-013/FR-014) ─────────────────────────────────────────

def test_create_skill_without_type_returns_400(client, unique_name):
    resp = client.post("/api/skills", json={
        "code": f"NOTYPE_{unique_name}", "label": "Sin tipo",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_skill_with_invalid_type_returns_400(client, unique_name):
    resp = client.post("/api/skills", json={
        "code": f"BADTYPE_{unique_name}", "label": "Tipo inválido", "skill_type": "gerencial",
    })
    assert resp.status_code == 400


def test_create_skill_with_type_and_no_catalogs_succeeds(client, unique_name):
    resp = client.post("/api/skills", json={
        "code": f"OK_{unique_name}", "label": "Solo tipo", "skill_type": "funcional",
    })
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["skill_type"] == "funcional"
    assert body["tool_id"] is None
    assert body["process_id"] is None


def test_create_skill_with_unknown_tool_returns_404(client, unique_name):
    resp = client.post("/api/skills", json={
        "code": f"GHOST_{unique_name}", "label": "Tool fantasma", "skill_type": "tecnico",
        "tool_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 404


# ── PATCH /api/skills/{id} (FR-018) ──────────────────────────────────────────

def test_patch_skill_changes_type_and_tool(client, unique_name):
    created = client.post("/api/skills", json={
        "code": f"PATCH_{unique_name}", "label": "Para editar", "skill_type": "tecnico",
    }).get_json()
    tools = client.get("/api/catalogs/tools?active=all").get_json()["items"]
    jde = next(t for t in tools if t["name"] == "JDE")

    resp = client.patch(f"/api/skills/{created['id']}", json={
        "skill_type": "funcional", "tool_id": jde["id"], "label": "Editado",
    })
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["skill_type"] == "funcional"
    assert body["tool_name"] == "JDE"
    assert body["label"] == "Editado"


def test_patch_skill_invalid_type_returns_400(client, unique_name):
    created = client.post("/api/skills", json={
        "code": f"PATCHBAD_{unique_name}", "label": "Para fallar", "skill_type": "tecnico",
    }).get_json()
    resp = client.patch(f"/api/skills/{created['id']}", json={"skill_type": "otro"})
    assert resp.status_code == 400


def test_patch_unknown_skill_returns_404(client):
    resp = client.patch(f"/api/skills/{uuid.uuid4()}", json={"label": "Nada"})
    assert resp.status_code == 404
