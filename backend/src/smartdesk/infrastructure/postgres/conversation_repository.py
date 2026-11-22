import hashlib
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from smartdesk.domain.support_models import ServiceError
from smartdesk.infrastructure.postgres.database_models import Conversation, Message, Request


class Repository:
    def __init__(self, url: str):
        self.engine = create_engine(url, pool_pre_ping=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def check_readiness(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM conversations LIMIT 1"))

    def create_conversation(self, owner: str) -> Conversation:
        with self.sessions.begin() as session:
            item = Conversation(id=str(uuid4()), owner=owner)
            session.add(item)
        return item

    def owned(self, conversation_id: str, owner: str):
        with self.sessions() as session:
            item = session.get(Conversation, conversation_id)
            if item is None or item.owner != owner:
                raise ServiceError("Conversation not found.", 404)
            return item

    def conversations(self, owner: str):
        with self.sessions() as session:
            return list(
                session.scalars(
                    select(Conversation)
                    .where(Conversation.owner == owner)
                    .order_by(Conversation.created_at.desc())
                    .limit(100)
                )
            )

    def messages(self, conversation_id: str):
        with self.sessions() as session:
            return list(
                session.scalars(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.id)
                )
            )

    @contextmanager
    def lock(self, conversation_id: str):
        if self.engine.dialect.name == "postgresql":
            key = int.from_bytes(
                hashlib.sha256(conversation_id.encode()).digest()[:8], "big", signed=True
            )
            with self.engine.connect() as connection:
                acquired = connection.scalar(
                    text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
                )
                if not acquired:
                    raise ServiceError(
                        "Another message is being processed. Please try again shortly.", 409
                    )
                try:
                    yield
                finally:
                    connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
        else:
            with self._guard:
                lock = self._locks.setdefault(conversation_id, threading.Lock())
            if not lock.acquire(blocking=False):
                raise ServiceError("Another message is being processed.", 409)
            try:
                yield
            finally:
                lock.release()

    def request_replay(
        self, conversation: str, request_id: str, fingerprint: str, owner: str, rate_limit: int
    ) -> dict | None:
        with self.sessions() as session:
            previous = session.get(Request, request_id)
            if previous:
                if previous.conversation_id != conversation or previous.fingerprint != fingerprint:
                    raise ServiceError(
                        "Request ID has already been used for a different operation.", 409
                    )
                if previous.response:
                    return previous.response
                raise ServiceError(
                    "This request was interrupted or is still being reconciled. Reload the conversation before sending a new request.",
                    409,
                )
            count = session.scalar(
                select(func.count())
                .select_from(Request)
                .join(Conversation)
                .where(
                    Conversation.owner == owner,
                    Request.created_at > datetime.now(UTC) - timedelta(minutes=1),
                )
            )
            if count and count >= rate_limit:
                raise ServiceError("Too many messages. Please wait a minute.", 429)
            return None

    def start_request(
        self, conversation: str, request_id: str, fingerprint: str, text: str
    ) -> None:
        with self.sessions.begin() as session:
            session.add(
                Request(id=request_id, conversation_id=conversation, fingerprint=fingerprint)
            )
            session.add(
                Message(
                    conversation_id=conversation,
                    role="user",
                    content=text,
                    request_id=request_id,
                )
            )
            item = session.get(Conversation, conversation)
            if item and item.title == "New conversation":
                item.title = text[:80]

    def complete_request(
        self, conversation: str, request_id: str, text: str, response: dict
    ) -> None:
        with self.sessions.begin() as session:
            record = session.get(Request, request_id)
            assert record is not None
            record.status = "complete"
            record.response = response
            session.add(
                Message(
                    conversation_id=conversation,
                    role="assistant",
                    content=text,
                    request_id=request_id,
                    response=response,
                )
            )

    def history(self, conversation: str) -> list[dict[str, str]]:
        with self.sessions() as session:
            rows = session.execute(
                select(Message.role, Message.content)
                .where(Message.conversation_id == conversation)
                .order_by(Message.id)
            )
            return [{"role": role, "content": content} for role, content in rows]
