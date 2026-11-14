from dataclasses import dataclass, field


@dataclass(frozen=True)
class Identity:
    user_id: str
    email: str


@dataclass(frozen=True)
class Passage:
    id: str
    title: str
    text: str
    source: str
    score: float = 0.0


@dataclass
class Ticket:
    id: str
    summary: str
    status: str
    url: str
    comments: list[str] = field(default_factory=list)


class ServiceError(Exception):
    """A safe, user-facing error; never include provider credentials or raw bodies."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


class TicketWriteRejected(ServiceError):
    """The provider definitely rejected the request before creating a ticket."""
