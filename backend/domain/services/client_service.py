from typing import Optional
from backend.domain.entities.client import Client


class ClientBusinessError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ClientService:
    def validate_unique_name(self, name: str, existing_id=None, repo=None) -> None:
        if repo is None:
            return
        existing = repo.get_by_name(name)
        if existing and (existing_id is None or existing.id != existing_id):
            raise ClientBusinessError("name_duplicate", "Ya existe un cliente con ese nombre")

    def get_deactivation_impact(self, client_id, projects_repo=None) -> dict:
        active_projects = 0
        if projects_repo:
            _, active_projects = projects_repo.list_paginated(client_id=client_id, active=True)
        return {"active_projects_count": active_projects, "open_tickets_count": 0}
