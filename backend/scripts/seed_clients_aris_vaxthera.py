"""Seed de datos base para los clientes reales Aris y Vaxthera (spec 026).

Uso: docker exec sywork_backend python -m backend.scripts.seed_clients_aris_vaxthera

Crea los clientes Aris (Colombia) y Vaxthera (Ecuador), sus proyectos, los usuarios
"Usuario/cliente" (Encargados de sus proyectos — se sembraron también como
`client_contacts`, no solo como `project_members`, para que aparezcan en Maestros >
Usuarios/clientes igual que cualquier Encargado dado de alta por la UI), la matriz de
SLA de 4 niveles del proyecto Soporte de Aris y las Listas de Tareas de cada proyecto
Soporte.

Re-ejecutable: los valores de este seed son fijos y autoritativos, así que si alguno de
estos registros ya existe con un valor distinto (p. ej. el país/zona horaria de un
cliente, o el rol de uno de estos 3 emails), el script lo actualiza para que converja
con el valor sembrado — nunca se deja "a medias" ni se aborta por un conflicto. Esto no
toca ningún otro cliente, proyecto o usuario del sistema fuera de los aquí listados.
"""
import secrets
import sys
import uuid
from datetime import date

from werkzeug.security import generate_password_hash

from backend.infra.database import get_db, close_db
from backend.domain.entities.client import Client
from backend.domain.entities.project import Project
from backend.domain.entities.user import User, USUARIO_CLIENTE_ROLE_NAME
from backend.domain.entities.client_contact import ClientContact
from backend.domain.entities.project_member import ProjectMember
from backend.domain.entities.sla_rule import SlaRule
from backend.domain.entities.task_list import TaskList
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.repositories.project_repo import ProjectRepository
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.repositories.client_contact_repo import ClientContactRepository
from backend.infra.repositories.project_member_repo import ProjectMemberRepository
from backend.infra.repositories.sla_rule_repo import SlaRuleRepository
from backend.infra.repositories.task_list_repo import TaskListRepository

# ── datos de origen (Aris/Vaxthera, ver specs/026-seed-clientes-proyectos/data-model.md) ──

CLIENTS = [
    {"name": "Aris", "country": "Colombia", "timezone": "America/Bogota"},
    {"name": "Vaxthera", "country": "Ecuador", "timezone": "America/Guayaquil"},
]

PROJECTS = [
    {"client": "Aris", "name": "Evolutivo"},
    {"client": "Aris", "name": "Preventa"},
    {"client": "Aris", "name": "Soporte"},
    {"client": "Vaxthera", "name": "Soporte"},
]

# Encargados (rol "Usuario/cliente") de los proyectos indicados — NO son recursos/equipo.
USERS = [
    {"email": "Eliseon@aris.ming.com", "client": "Aris", "projects": ["Evolutivo", "Preventa", "Soporte"]},
    {"email": "paulaBlanco@aris.ming.com", "client": "Aris", "projects": ["Evolutivo", "Preventa", "Soporte"]},
    {"email": "pablo@vaxthera.com", "client": "Vaxthera", "projects": ["Soporte"]},
]

# (priority, contact_minutes, execution_minutes) — solo Aris/Soporte tiene SLA
SLA_ARIS_SOPORTE = [
    ("critical", 120, 240),
    ("high", 240, 480),
    ("medium", 480, 1440),
    ("low", 1440, 2880),
]

TASK_LISTS = {
    ("Aris", "Soporte"): [
        "Servicios Correctivos", "Servicios Adaptativos", "Servicios Evolutivos",
        "Servicios Administrativos", "Seguimiento", "Coordinación",
        "Servicios preventivos IT", "Redwood",
    ],
    ("Vaxthera", "Soporte"): [
        "Servicios Evolutivos", "Servicios Administrativos", "Servicios Correctivos",
        "Servicios Adaptativos", "Seguimiento (Completadas)",
    ],
}


def main() -> None:
    db = get_db()
    clients = ClientRepository(db)
    projects = ProjectRepository(db)
    users = UserRepository(db)
    roles = RoleRepository(db)
    contacts = ClientContactRepository(db)
    members = ProjectMemberRepository(db)
    sla_rules = SlaRuleRepository(db)
    task_lists = TaskListRepository(db)

    resumen = {"creados": [], "actualizados": [], "omitidos": []}

    # ── precondición bloqueante — el rol "Usuario/cliente" ya debe existir ──
    usuario_cliente_role = roles.get_by_name(USUARIO_CLIENTE_ROLE_NAME)
    assert usuario_cliente_role, (
        f'Rol "{USUARIO_CLIENTE_ROLE_NAME}" no encontrado — requerido para sembrar usuarios de Aris/Vaxthera'
    )

    # ── clientes (converge country/timezone al valor sembrado si difieren) ─────
    client_by_name = {}
    for c in CLIENTS:
        existing = clients.get_by_name(c["name"])
        if existing:
            if existing.country != c["country"] or existing.timezone != c["timezone"]:
                existing.country = c["country"]
                existing.timezone = c["timezone"]
                existing = clients.update(existing)
                resumen["actualizados"].append(
                    f'cliente {c["name"]} (country/timezone -> {c["country"]}/{c["timezone"]})')
            else:
                resumen["omitidos"].append(f'cliente {c["name"]}')
            client_by_name[c["name"]] = existing
        else:
            created = clients.create(Client.create(name=c["name"], country=c["country"], timezone=c["timezone"]))
            client_by_name[c["name"]] = created
            resumen["creados"].append(f'cliente {c["name"]}')

    # ── proyectos ─────────────────────────────────────────────────────────────
    project_by_key = {}
    for p in PROJECTS:
        client = client_by_name[p["client"]]
        existing = projects.get_by_client_and_name(client.id, p["name"])
        if existing:
            project_by_key[(p["client"], p["name"])] = existing
            resumen["omitidos"].append(f'proyecto {p["client"]}/{p["name"]}')
        else:
            created = projects.create(Project.create(client_id=client.id, name=p["name"], start_date=date.today()))
            project_by_key[(p["client"], p["name"])] = created
            resumen["creados"].append(f'proyecto {p["client"]}/{p["name"]}')

    # ── usuarios "Usuario/cliente" == Encargados de sus proyectos ─────────────
    # (nunca recursos/equipo: además de la membresía de proyecto se siembra su
    # client_contacts, que es lo que los hace aparecer como Encargado en la UI)
    passwords_generadas = {}
    for u in USERS:
        existing = users.get_by_email(u["email"])
        if existing:
            if existing.role.name != USUARIO_CLIENTE_ROLE_NAME:
                users.update_role(existing.id, usuario_cliente_role.id)
                resumen["actualizados"].append(
                    f'usuario {u["email"]} (rol {existing.role.name} -> {USUARIO_CLIENTE_ROLE_NAME})')
            else:
                resumen["omitidos"].append(f'usuario {u["email"]}')
            user = existing
        else:
            password = secrets.token_urlsafe(12)
            passwords_generadas[u["email"]] = password
            username = u["email"].split("@", 1)[0]
            user = users.create(User(
                id=uuid.uuid4(), email=u["email"], username=username, role=usuario_cliente_role,
                password_hash=generate_password_hash(password),
            ))
            resumen["creados"].append(f'usuario {u["email"]}')

        client = client_by_name[u["client"]]
        if contacts.get_by_user_id(user.id):
            resumen["omitidos"].append(f'client_contact {u["email"]}')
        else:
            contacts.create(ClientContact(id=uuid.uuid4(), user_id=user.id, client_id=client.id))
            resumen["creados"].append(f'client_contact {u["email"]} (Encargado de {u["client"]})')

        for project_name in u["projects"]:
            project = project_by_key[(u["client"], project_name)]
            if members.is_member(project.id, user.id):
                resumen["omitidos"].append(f'membresía {u["email"]} -> {u["client"]}/{project_name}')
            else:
                members.create(ProjectMember.create(project_id=project.id, user_id=user.id))
                resumen["creados"].append(f'membresía {u["email"]} -> {u["client"]}/{project_name}')

    # ── matriz de SLA — solo Aris/Soporte (Evolutivo, Preventa y Vaxthera/Soporte quedan sin SLA) ──
    aris_soporte = project_by_key[("Aris", "Soporte")]
    for priority, contact_minutes, execution_minutes in SLA_ARIS_SOPORTE:
        existing = sla_rules.find_by_project_priority(aris_soporte.id, priority)
        if existing:
            if existing.contact_minutes != contact_minutes or existing.execution_minutes != execution_minutes:
                existing.contact_minutes = contact_minutes
                existing.execution_minutes = execution_minutes
                sla_rules.update(existing)
                resumen["actualizados"].append(
                    f'SLA Aris/Soporte/{priority} ({contact_minutes}/{execution_minutes} min)')
            else:
                resumen["omitidos"].append(f'SLA Aris/Soporte/{priority}')
        else:
            sla_rules.create(SlaRule.create(
                project_id=aris_soporte.id, priority=priority,
                contact_minutes=contact_minutes, execution_minutes=execution_minutes,
            ))
            resumen["creados"].append(f'SLA Aris/Soporte/{priority}')

    # ── listas de tareas ──────────────────────────────────────────────────────
    for (client_name, project_name), names in TASK_LISTS.items():
        project = project_by_key[(client_name, project_name)]
        for name in names:
            if task_lists.get_by_project_and_name(project.id, name):
                resumen["omitidos"].append(f'lista {client_name}/{project_name}/{name}')
            else:
                position = task_lists.next_position(project.id)
                task_lists.create(TaskList(id=uuid.uuid4(), project_id=project.id, name=name, position=position))
                resumen["creados"].append(f'lista {client_name}/{project_name}/{name}')

    close_db()

    print(f'Seed completo: {len(resumen["creados"])} creados, {len(resumen["actualizados"])} '
          f'actualizados para converger con el seed, {len(resumen["omitidos"])} sin cambios.')
    for label, items in (("Creados", resumen["creados"]), ("Actualizados", resumen["actualizados"])):
        if items:
            print(f'{label}:')
            for item in items:
                print(f'  - {item}')
    if passwords_generadas:
        print("Contraseñas iniciales (solo se muestran una vez, entregar de forma segura):")
        for email, password in passwords_generadas.items():
            print(f'  - {email}: {password}')


if __name__ == "__main__":
    sys.exit(main())
