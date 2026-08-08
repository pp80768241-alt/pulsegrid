from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    room: str
    sender: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    recipient: str
    title: str
    body: str


class NotificationOut(BaseModel):
    id: int
    recipient: str
    title: str
    body: str
    delivered: bool
    created_at: datetime
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True


class HealthOut(BaseModel):
    status: str
    instance_id: str
    active_connections: int
