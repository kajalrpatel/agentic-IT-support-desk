import hashlib
import threading
from contextlib import contextmanager
from uuid import uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from smartdesk.domain.support_models import ServiceError
from smartdesk.infrastructure.postgres.database_models import Conversation, Message


class Repository:
    def __init__(self, url: str):
        self.engine = create_engine(url, pool_pre_ping=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

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
