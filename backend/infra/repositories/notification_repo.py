import uuid

from sqlalchemy.orm import Session

from backend.domain.entities.notification import Notification
from backend.infra.models.notification_model import NotificationModel


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, notification: Notification, commit: bool = True) -> None:
        self._db.add(NotificationModel.from_entity(notification))
        if commit:
            self._db.commit()

    def list_for_user(self, user_id: uuid.UUID, unread_only: bool = False,
                      page: int = 1, page_size: int = 20) -> tuple[list[Notification], int, int]:
        q = self._db.query(NotificationModel).filter(NotificationModel.user_id == user_id)
        unread_count = q.filter(NotificationModel.read.is_(False)).count()
        if unread_only:
            q = q.filter(NotificationModel.read.is_(False))
        total = q.count()
        models = (q.order_by(NotificationModel.created_at.desc())
                  .offset((page - 1) * page_size).limit(page_size).all())
        return [m.to_entity() for m in models], total, unread_count

    def mark_read(self, user_id: uuid.UUID, ids: list[uuid.UUID] | None = None,
                  mark_all: bool = False) -> int:
        q = self._db.query(NotificationModel).filter(
            NotificationModel.user_id == user_id, NotificationModel.read.is_(False))
        if not mark_all:
            q = q.filter(NotificationModel.id.in_(ids or []))
        updated = q.update({NotificationModel.read: True}, synchronize_session=False)
        self._db.commit()
        return updated
