from dataclasses import dataclass
from typing import Protocol

from smartdesk.domain.support_models import Ticket


@dataclass(frozen=True)
class AttemptStatus:
    reconcile: bool
    ticket: Ticket | None = None


class TicketAttemptStore(Protocol):
    def reserve(
        self, attempt_id: str, conversation: str, owner: str, version: int, fingerprint: str
    ) -> AttemptStatus: ...
    def reject(self, attempt_id: str) -> None: ...
    def complete(self, attempt_id: str, ticket: Ticket) -> None: ...
