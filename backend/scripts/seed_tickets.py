"""Seed de tickets de prueba para validar SC-005 (panel < 2 s) y SC-008 (listado < 1 s).

Uso: docker exec sywork_backend python -m backend.scripts.seed_tickets [cantidad]
Crea (si no existen) un cliente y 3 recursos de carga, y N tickets repartidos
entre estados no finales via la API de dominio (respetando la FSM).
"""
import random
import sys
import uuid

from backend.infra.database import get_db, close_db
# imports necesarios para que SQLAlchemy resuelva las FKs de tickets en metadata
import backend.infra.models.catalog_model  # noqa: F401
import backend.infra.models.comment_model  # noqa: F401
import backend.infra.models.user_model  # noqa: F401
from backend.domain.entities.ticket import Ticket
from backend.domain.entities.client import Client
from backend.domain.entities.resource import Resource
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.repositories.resource_repo import ResourceRepository
from backend.infra.repositories.ticket_repo import TicketRepository
from backend.infra.repositories.user_repo import UserRepository

SEED_CLIENT = "Cliente Seed Performance"
PRIORITIES = ("critical", "high", "medium", "low")
SEVERITIES = ("s1", "s2", "s3", "s4")
TYPES = ("incident", "evolutive", "preventive")
# estados alcanzables directamente para el seed (se insertan con transición registrada)
STATUSES = ("nuevo", "contacto", "en_analisis", "en_ejecucion", "pendiente_usuario", "resuelto")


def main(count: int = 500) -> None:
    db = get_db()
    clients = ClientRepository(db)
    resources = ResourceRepository(db)
    tickets = TicketRepository(db)
    admin = UserRepository(db).get_by_email("admin@sywork.net")
    assert admin, "Usuario admin semilla requerido"

    client = clients.get_by_name(SEED_CLIENT) or clients.create(Client.create(name=SEED_CLIENT))

    seed_resources = []
    for i in range(3):
        email = f"seed.resolutor{i}@sywork.net"
        resource = resources.get_by_email(email) or resources.create(
            Resource.create(full_name=f"Seed Resolutor {i}", email=email))
        seed_resources.append(resource)

    for n in range(count):
        status = random.choice(STATUSES)
        ticket = Ticket(
            id=uuid.uuid4(), ticket_number=0,
            title=f"Seed ticket {n:04d} - {random.choice(('GL', 'AP', 'AR', 'OTM', 'WMS'))}",
            description="Ticket de carga para pruebas de performance",
            ticket_type=random.choice(TYPES), priority=random.choice(PRIORITIES),
            severity=random.choice(SEVERITIES), client_id=client.id,
            created_by=admin.id,
        )
        created = tickets.create(ticket)
        if status != "nuevo":
            assignee = random.choice(seed_resources)
            tickets.update_fields(created.id, status=status, assignee_id=assignee.id)
            tickets.add_transition(created.id, "nuevo", status, admin.id, commit=True)
        if (n + 1) % 100 == 0:
            print(f"  {n + 1}/{count} tickets")

    close_db()
    print(f"Seed completo: {count} tickets para '{SEED_CLIENT}'")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 500)
