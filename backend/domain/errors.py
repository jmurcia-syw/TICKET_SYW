"""Shared exception hierarchy for domain/business-rule violations.

Each subclass represents a distinct family of business errors (client rules,
project rules, etc.) but shares one constructor so the HTTP layer can map any
of them to a response without re-deriving semantics per module.
"""


class DomainError(Exception):
    """Base class for business-rule violations raised by domain services.

    Carries the HTTP status_code the violation should map to, since a single
    error family (e.g. ProjectBusinessError) can represent both a 404
    ("client not found") and a 400 ("invalid dates") depending on the rule
    that failed - collapsing everything to one status per except-clause loses
    that distinction.
    """

    default_status_code = 409

    def __init__(self, code: str, message: str, status_code: int | None = None, **extra) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code or self.default_status_code
        self.extra = extra
