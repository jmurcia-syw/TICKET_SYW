from typing import Optional
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.domain.entities.ticket import Ticket
from backend.infra.models.ticket_model import TicketModel, StatusTransitionModel, AssignmentModel

_SORTS = {
    "created_at": TicketModel.created_at.asc(),
    "-created_at": TicketModel.created_at.desc(),
    "priority": TicketModel.priority.asc(),
    "status": TicketModel.status.asc(),
}


class TicketRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, ticket_id: uuid.UUID) -> Optional[Ticket]:
        model = self._db.get(TicketModel, ticket_id)
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20, search: str | None = None,
                       client_id: uuid.UUID | None = None, project_id: uuid.UUID | None = None,
                       statuses: list[str] | None = None, priority: str | None = None,
                       severity: str | None = None, ticket_type: str | None = None,
                       assignee_id: uuid.UUID | None = None, escalation_level: str | None = None,
                       sort: str = "-created_at",
                       created_by: uuid.UUID | None = None) -> tuple[list[Ticket], int]:
        q = self._db.query(TicketModel)
        if created_by:
            q = q.filter(TicketModel.created_by == created_by)
        if search:
            like = f"%{search}%"
            filters = [TicketModel.title.ilike(like)]
            digits = "".join(ch for ch in search if ch.isdigit())
            if digits:
                filters.append(TicketModel.ticket_number == int(digits))
            from sqlalchemy import or_
            q = q.filter(or_(*filters))
        if client_id:
            q = q.filter(TicketModel.client_id == client_id)
        if project_id:
            q = q.filter(TicketModel.project_id == project_id)
        if statuses:
            q = q.filter(TicketModel.status.in_(statuses))
        if priority:
            q = q.filter(TicketModel.priority == priority)
        if severity:
            q = q.filter(TicketModel.severity == severity)
        if ticket_type:
            q = q.filter(TicketModel.ticket_type == ticket_type)
        if assignee_id:
            q = q.filter(TicketModel.assignee_id == assignee_id)
        if escalation_level:
            q = q.filter(TicketModel.escalation_level == escalation_level)
        total = q.count()
        order = _SORTS.get(sort, _SORTS["-created_at"])
        models = q.order_by(order).offset((page - 1) * page_size).limit(page_size).all()
        return [m.to_entity() for m in models], total

    def create(self, ticket: Ticket) -> Ticket:
        model = TicketModel(
            id=ticket.id,
            record_type_id=ticket.record_type_id,
            ticket_type=ticket.ticket_type,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            severity=ticket.severity,
            escalation_level=ticket.escalation_level,
            client_id=ticket.client_id,
            project_id=ticket.project_id,
            tool_id=ticket.tool_id,
            process_id=ticket.process_id,
            related_ticket_id=ticket.related_ticket_id,
            created_by=ticket.created_by,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update_fields(self, ticket_id: uuid.UUID, **fields) -> Optional[Ticket]:
        model = self._db.get(TicketModel, ticket_id)
        if not model:
            return None
        for k, v in fields.items():
            if hasattr(model, k):
                setattr(model, k, v)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    # ── historiales (append-only) ───────────────────────────────────────

    def add_transition(self, ticket_id: uuid.UUID, from_status: str, to_status: str,
                       actor_id: uuid.UUID, comment_id: uuid.UUID | None = None,
                       commit: bool = True) -> None:
        self._db.add(StatusTransitionModel(
            ticket_id=ticket_id, from_status=from_status, to_status=to_status,
            actor_id=actor_id, comment_id=comment_id,
        ))
        if commit:
            self._db.commit()

    def list_transitions(self, ticket_id: uuid.UUID) -> list[dict]:
        rows = (self._db.query(StatusTransitionModel)
                .filter(StatusTransitionModel.ticket_id == ticket_id)
                .order_by(StatusTransitionModel.created_at).all())
        return [{
            "id": str(r.id), "from_status": r.from_status, "to_status": r.to_status,
            "actor_id": str(r.actor_id),
            "comment_id": str(r.comment_id) if r.comment_id else None,
            "created_at": r.created_at.isoformat(),
        } for r in rows]

    def add_assignment(self, ticket_id: uuid.UUID, assigner_id: uuid.UUID,
                       assignee_id: uuid.UUID, resulting_status: str, context: dict,
                       commit: bool = True) -> uuid.UUID:
        model = AssignmentModel(
            ticket_id=ticket_id, assigner_id=assigner_id, assignee_id=assignee_id,
            resulting_status=resulting_status, context=context,
        )
        self._db.add(model)
        if commit:
            self._db.commit()
            self._db.refresh(model)
        return model.id

    def list_assignments(self, ticket_id: uuid.UUID) -> list[dict]:
        rows = (self._db.query(AssignmentModel)
                .filter(AssignmentModel.ticket_id == ticket_id)
                .order_by(AssignmentModel.created_at).all())
        return [{
            "id": str(r.id), "assigner_id": str(r.assigner_id),
            "assignee_id": str(r.assignee_id), "resulting_status": r.resulting_status,
            "context": r.context, "created_at": r.created_at.isoformat(),
        } for r in rows]

    def count_open_by_assignee(self, assignee_id: uuid.UUID) -> int:
        return (self._db.query(TicketModel)
                .filter(TicketModel.assignee_id == assignee_id,
                        TicketModel.status.notin_(("cerrado", "cancelado")))
                .count())

    def panel_matrix(self, statuses: list[str] | None = None) -> list[dict]:
        """Conteo de tickets por (assignee, status) para el Panel de Asignación."""
        q = (self._db.query(TicketModel.assignee_id, TicketModel.status,
                            func.count(TicketModel.id))
             .filter(TicketModel.assignee_id.isnot(None),
                     TicketModel.status.notin_(("cerrado", "cancelado")))
             .group_by(TicketModel.assignee_id, TicketModel.status))
        if statuses:
            q = q.filter(TicketModel.status.in_(statuses))
        return [{"assignee_id": row[0], "status": row[1], "count": row[2]} for row in q.all()]

    def count_using_catalog(self, column: str, catalog_id: uuid.UUID) -> int:
        """Tickets no finales que referencian un valor de catálogo (bloqueo por uso)."""
        return (self._db.query(TicketModel)
                .filter(getattr(TicketModel, column) == catalog_id,
                        TicketModel.status.notin_(("cerrado", "cancelado")))
                .count())
