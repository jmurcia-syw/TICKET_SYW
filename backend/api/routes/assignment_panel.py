from flask import request
from flask_restx import Namespace, Resource

from backend.api.middleware.rbac import require_permission
from backend.api.routes._shared import error_model, server_error
from backend.domain.entities.ticket import STATUSES, FINAL_STATUSES, STATUS_LABELS, format_ticket_number
from backend.infra.database import get_db
from backend.infra.repositories.client_repo import ClientRepository
from backend.infra.repositories.resource_repo import ResourceRepository
from backend.infra.repositories.ticket_repo import TicketRepository

ns = Namespace("assignment_panel", description="Panel de Asignación (Triage Dashboard)",
               path="/api/assignment-panel")

_error = error_model(ns, "PanelError")

NON_FINAL = [s for s in STATUSES if s not in FINAL_STATUSES]


@ns.route("")
class AssignmentPanel(Resource):
    @ns.doc("get_assignment_panel", params={
        "statuses": {"description": "Filtro de estados (repetible)", "type": "string"},
    })
    @require_permission("assignment_panel", "view")
    def get(self):
        """Matriz resolutor × estado + tickets NUEVOS pendientes de triage (FR-025)"""
        statuses = request.args.getlist("statuses") or None
        if statuses:
            invalid = [s for s in statuses if s not in NON_FINAL]
            if invalid:
                return {"error": "validation_error",
                        "message": f"Estados inválidos: {', '.join(invalid)}"}, 400
        try:
            db = get_db()
            ticket_repo = TicketRepository(db)
            resource_repo = ResourceRepository(db)
            client_repo = ClientRepository(db)

            rows = ticket_repo.panel_matrix(statuses=statuses)
            by_resource: dict = {}
            for row in rows:
                by_resource.setdefault(row["assignee_id"], {})[row["status"]] = row["count"]

            matrix = []
            for assignee_id, counts in by_resource.items():
                resource = resource_repo.get_by_id(assignee_id)
                if not resource:
                    continue
                matrix.append({
                    "resource": {"id": str(resource.id), "full_name": resource.full_name},
                    "counts": counts,
                    "total": sum(counts.values()),
                })
            matrix.sort(key=lambda r: (-r["total"], r["resource"]["full_name"]))

            new_tickets, _ = ticket_repo.list_paginated(
                page=1, page_size=100, statuses=["nuevo"], sort="created_at")
            unassigned = []
            for t in new_tickets:
                client = client_repo.get_by_id(t.client_id)
                unassigned.append({
                    "id": str(t.id),
                    "ticket_number": format_ticket_number(t.ticket_number),
                    "title": t.title, "priority": t.priority, "severity": t.severity,
                    "client": {"id": str(client.id), "name": client.name} if client else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                })

            return {"matrix": matrix, "unassigned_new": unassigned,
                    "statuses": statuses or NON_FINAL,
                    "status_labels": {s: STATUS_LABELS[s] for s in NON_FINAL}}, 200
        except Exception:
            return server_error()
