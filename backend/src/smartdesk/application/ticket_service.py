import hashlib
import json
from dataclasses import asdict
from uuid import NAMESPACE_URL, uuid5

from smartdesk.api.schemas import Draft
from smartdesk.application.ports import TicketProvider
from smartdesk.domain.models import Identity, ServiceError, Ticket, TicketWriteRejected
from smartdesk.infrastructure.postgres.models import TicketAttempt
from smartdesk.infrastructure.postgres.repository import Repository


def employee_label(email: str) -> str:
    return "sd-employee-" + hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]


class TicketService:
    def __init__(self, repo: Repository, provider: TicketProvider):
        self.repo = repo
        self.provider = provider

    def create(
        self,
        conversation: str,
        identity: Identity,
        draft: Draft,
        version: int,
        approved_version: int | None,
    ) -> Ticket:
        if version != approved_version:
            raise ServiceError("Please confirm the current ticket draft before submitting.", 409)
        if str(draft.email).lower() != identity.email.lower():
            raise ServiceError("The ticket email must match your signed-in identity.", 403)
        data = draft.model_dump(mode="json")
        fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        attempt_id = str(uuid5(NAMESPACE_URL, f"{conversation}:{version}"))
        correlation = "sd-request-" + attempt_id
        with self.repo.sessions.begin() as session:
            record = session.get(TicketAttempt, attempt_id)
            existing = record is not None
            if record:
                if record.owner != identity.user_id or record.draft_hash != fingerprint:
                    raise ServiceError("This draft has changed. Confirm the updated version.", 409)
                if record.ticket:
                    return Ticket(**record.ticket)
                existing = record.status != "rejected"
                record.status = "pending"
            else:
                session.add(
                    TicketAttempt(
                        id=attempt_id,
                        conversation_id=conversation,
                        draft_version=version,
                        owner=identity.user_id,
                        draft_hash=fingerprint,
                    )
                )
        if existing:
            matches = self.provider.find(correlation)
            if len(matches) != 1:
                raise ServiceError(
                    "The earlier submission's outcome is not yet confirmed. We will not create a duplicate. Retry reconciliation later or contact support.",
                    409,
                )
            ticket = matches[0]
        else:
            # Never retry an uncertain external write. A later call reconciles the label.
            try:
                ticket = self.provider.create(data, correlation, employee_label(identity.email))
            except TicketWriteRejected:
                with self.repo.sessions.begin() as session:
                    record = session.get(TicketAttempt, attempt_id)
                    assert record is not None
                    record.status = "rejected"
                raise
        with self.repo.sessions.begin() as session:
            record = session.get(TicketAttempt, attempt_id)
            assert record is not None
            record.ticket = asdict(ticket)
            record.status = "created"
        return ticket

    def list(self, identity: Identity) -> list[Ticket]:
        return self.provider.find(employee_label(identity.email))

    def detail(self, identity: Identity, ticket_id: str) -> Ticket:
        matches = self.list(identity)
        if not any(t.id == ticket_id for t in matches):
            raise ServiceError("Ticket not found for your account.", 404)
        return self.provider.get(ticket_id)
