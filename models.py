from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.database import Base


class Message(Base):
    """A persisted chat message. Written once by whichever backend replica
    received it, then fanned out to every replica via Redis pub/sub so
    every connected client sees it regardless of which instance they're
    attached to."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room = Column(String, index=True, nullable=False)
    sender = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """An async notification job. Enqueued instantly via a REST call,
    then picked up by a separate worker process so the API request
    returns immediately instead of blocking on delivery."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    delivered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
