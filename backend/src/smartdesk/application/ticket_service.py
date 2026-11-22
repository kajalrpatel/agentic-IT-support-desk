import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from smartdesk.application.conversation_models import Draft
from smartdesk.application.ticket_attempt_store import TicketAttemptStore
from smartdesk.application.ticket_provider import TicketProvider
from smartdesk.domain.support_models import Identity, ServiceError, Ticket, TicketWriteRejected


def employee_label(email: str) -> str:
    return "sd-employee-" + hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]


class TicketService:
    def __init__(self, attempts: TicketAttemptStore, provider: TicketProvider):
        self.attempts = attempts
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
        attempt = self.attempts.reserve(
            attempt_id, conversation, identity.user_id, version, fingerprint
        )
        if attempt.ticket:
            return attempt.ticket
        if attempt.reconcile:
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
                self.attempts.reject(attempt_id)
                raise
        self.attempts.complete(attempt_id, ticket)
        return ticket

    def list(self, identity: Identity) -> list[Ticket]:
        return self.provider.find_owned(identity.email, employee_label(identity.email))

    def detail(self, identity: Identity, ticket_id: str) -> Ticket:
        matches = self.list(identity)
        if not any(t.id == ticket_id for t in matches):
            raise ServiceError("Ticket not found for your account.", 404)
        return self.provider.get(ticket_id)
