from typing import Optional
import uuid

from sqlalchemy.orm import Session

from backend.domain.entities.sla_rule import SlaRule
from backend.infra.models.sla_rule_model import SlaRuleModel


class SlaRuleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, rule_id: uuid.UUID) -> Optional[SlaRule]:
        model = self._db.get(SlaRuleModel, rule_id)
        return model.to_entity() if model else None

    def find_by_project_priority(self, project_id: uuid.UUID, priority: str) -> Optional[SlaRule]:
        """Búsqueda exacta, sin fallback (research.md Decisión 3, revisada 2026-07-14)."""
        model = (self._db.query(SlaRuleModel)
                 .filter(SlaRuleModel.project_id == project_id,
                         SlaRuleModel.priority == priority,
                         SlaRuleModel.active.is_(True))
                 .first())
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20,
                        project_id: uuid.UUID | None = None) -> tuple[list[SlaRule], int]:
        q = self._db.query(SlaRuleModel)
        if project_id:
            q = q.filter(SlaRuleModel.project_id == project_id)
        total = q.count()
        models = (q.order_by(SlaRuleModel.created_at)
                  .offset((page - 1) * page_size).limit(page_size).all())
        return [m.to_entity() for m in models], total

    def exists_active(self, project_id: uuid.UUID, priority: str,
                       exclude_id: uuid.UUID | None = None) -> bool:
        q = self._db.query(SlaRuleModel).filter(
            SlaRuleModel.project_id == project_id,
            SlaRuleModel.priority == priority,
            SlaRuleModel.active.is_(True),
        )
        if exclude_id:
            q = q.filter(SlaRuleModel.id != exclude_id)
        return self._db.query(q.exists()).scalar()

    def create(self, rule: SlaRule) -> SlaRule:
        model = SlaRuleModel.from_entity(rule)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update(self, rule: SlaRule) -> SlaRule:
        model = self._db.get(SlaRuleModel, rule.id)
        if not model:
            return rule
        for f in ("contact_minutes", "execution_minutes", "active"):
            setattr(model, f, getattr(rule, f))
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()
