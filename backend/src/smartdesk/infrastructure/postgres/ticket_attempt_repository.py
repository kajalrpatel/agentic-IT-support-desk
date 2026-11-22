from dataclasses import asdict

from sqlalchemy.orm import sessionmaker

from smartdesk.application.ticket_attempt_store import AttemptStatus
from smartdesk.domain.support_models import ServiceError, Ticket
from smartdesk.infrastructure.postgres.database_models import TicketAttempt


class TicketAttemptRepository:
    def __init__(self, sessions: sessionmaker):
        self.sessions = sessions

    def reserve(
        self, attempt_id: str, conversation: str, owner: str, version: int, fingerprint: str
    ) -> AttemptStatus:
        with self.sessions.begin() as session:
            record = session.get(TicketAttempt, attempt_id, with_for_update=True)
            if record is None:
                session.add(
                    TicketAttempt(
                        id=attempt_id,
                        conversation_id=conversation,
                        draft_version=version,
                        owner=owner,
                        draft_hash=fingerprint,
                    )
                )
                return AttemptStatus(reconcile=False)
            if record.owner != owner or record.draft_hash != fingerprint:
                raise ServiceError("This draft has changed. Confirm the updated version.", 409)
            if record.ticket:
                return AttemptStatus(reconcile=False, ticket=Ticket(**record.ticket))
            reconcile = record.status != "rejected"
            record.status = "pending"
            return AttemptStatus(reconcile=reconcile)

    def reject(self, attempt_id: str) -> None:
        with self.sessions.begin() as session:
            record = session.get_one(TicketAttempt, attempt_id)
            record.status = "rejected"

    def complete(self, attempt_id: str, ticket: Ticket) -> None:
        with self.sessions.begin() as session:
            record = session.get_one(TicketAttempt, attempt_id)
            record.status = "created"
            record.ticket = asdict(ticket)
