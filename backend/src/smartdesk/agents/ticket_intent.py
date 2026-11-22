"""Conservative English-language gate for entering ticket preparation."""

import re

from smartdesk.rag.query_pipeline import ESCALATE

_TICKET = r"(?:ticket|support request|support case|incident)"
_ACTION = r"(?:create|open|raise|file|submit|prepare|log)"

# Recognise an offer already persisted before the employee-facing wording changed.
# This text is never used to produce a new response.
_PREVIOUS_ESCALATION_TEXT = "I don't have enough information in the knowledge base to answer that reliably. Would you like me to prepare a support ticket?"


def ticket_preparation_requested(message: str, previous_response: dict | None) -> bool:
    text = " ".join(message.lower().replace(",", "").split()).strip(" .!?,")
    # A yes to a clarification is not acceptance of a ticket offer.
    if previous_response and previous_response.get("text") in {ESCALATE, _PREVIOUS_ESCALATION_TEXT}:
        # Ignore an optional contact address only for this consent check. Ticket ownership
        # always comes from the authenticated identity.
        consent = re.sub(
            r"\s+(?:(?:my )?email(?: address)? is\s+)?[^\s@]+@[^\s@]+\.[^\s@]+$", "", text
        )
        if re.fullmatch(
            r"(?:(?:yes|yeah|yep|sure|ok(?:ay)?|absolutely)(?: please)?"
            r"(?: (?:please )?(?:do(?: (?:it|that|so))?|go ahead))?|"
            r"(?:please )?(?:go ahead|do (?:it|that|so))|please do)",
            consent,
        ):
            return True
    if re.search(rf"\b(?:do not|don't|dont|never)\s+(?:\w+\s+){{0,2}}{_ACTION}\b", text):
        return False
    if re.search(
        rf"\b(?:no|not asking for|do not want|don\x27t want)\s+(?:a\s+)?{_TICKET}\b", text
    ):
        return False
    if re.match(r"^(?:how|when|why|where|should i|do i need|what)\b", text):
        return False
    return bool(
        re.search(rf"\b{_ACTION}\s+(?:\w+\s+){{0,4}}{_TICKET}\b", text)
        or re.search(rf"\bi\s+(?:want|need|would like)\s+(?:a\s+)?{_TICKET}\b", text)
    )
