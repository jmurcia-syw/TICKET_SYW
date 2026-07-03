from flask import g, request
from flask_restx import Namespace, Resource, fields

from backend.api.middleware.rbac import require_permission
from backend.api.routes._shared import parse_uuid, error_model, server_error
from backend.infra.database import get_db
from backend.infra.repositories.notification_repo import NotificationRepository
from backend.infra.repositories.ticket_repo import TicketRepository

ns = Namespace("notifications", description="Notificaciones internas del usuario",
               path="/api/notifications")

_error = error_model(ns, "NotificationError")

_read_input = ns.model("NotificationsReadInput", {
    "ids": fields.List(fields.String, description="IDs a marcar como leídas"),
    "all": fields.Boolean(description="true para marcar todas"),
})


@ns.route("")
class NotificationList(Resource):
    @ns.doc("list_notifications", params={
        "unread": {"description": "true = solo no leídas", "type": "boolean"},
        "page": {"type": "integer", "default": 1},
        "page_size": {"type": "integer", "default": 20},
    })
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    # Toda cuenta autenticada ve SUS notificaciones; tickets:view lo tienen los 4 roles seed
    @require_permission("tickets", "view")
    def get(self):
        """Notificaciones del usuario autenticado (propias, nunca de otros)"""
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        unread_only = (request.args.get("unread", "false").lower() == "true")
        try:
            db = get_db()
            items, total, unread_count = NotificationRepository(db).list_for_user(
                g.current_user.id, unread_only=unread_only, page=page, page_size=page_size)
            ticket_repo = TicketRepository(db)
            result = []
            for n in items:
                ticket = ticket_repo.get_by_id(n.ticket_id)
                result.append({
                    "id": str(n.id), "event_type": n.event_type, "message": n.message,
                    "ticket": {"id": str(ticket.id), "ticket_number": ticket.number_display,
                               "title": ticket.title} if ticket else None,
                    "read": n.read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                })
            return {"items": result, "total": total, "unread_count": unread_count}, 200
        except Exception:
            return server_error()


@ns.route("/read")
class NotificationsRead(Resource):
    @ns.doc("mark_notifications_read")
    @ns.response(401, "No autenticado (token ausente o invalido)", _error)
    @ns.response(403, "Sin el permiso requerido", _error)
    @ns.expect(_read_input, validate=False)
    @require_permission("tickets", "view")
    def patch(self):
        """Marcar notificaciones propias como leídas ({ids: [...]} o {all: true})"""
        data = request.get_json(silent=True) or {}
        mark_all = bool(data.get("all"))
        ids = [parse_uuid(str(i)) for i in data.get("ids", [])]
        ids = [i for i in ids if i]
        if not mark_all and not ids:
            return {"error": "validation_error", "message": "Indica 'ids' o 'all': true"}, 400
        try:
            updated = NotificationRepository(get_db()).mark_read(
                g.current_user.id, ids=ids, mark_all=mark_all)
            return {"updated": updated}, 200
        except Exception:
            return server_error()
