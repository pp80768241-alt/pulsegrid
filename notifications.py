from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.redis_bus import bus
from app import models, schemas

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("", response_model=schemas.NotificationOut)
async def create_notification(payload: schemas.NotificationCreate, db: Session = Depends(get_db)):
    """Persist the notification as 'pending' and enqueue it for async
    delivery. The request returns immediately — a separate worker process
    (worker.py) does the actual delivery, which keeps this endpoint fast
    even under load and decouples ingestion from processing."""
    notification = models.Notification(
        recipient=payload.recipient, title=payload.title, body=payload.body
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    await bus.push_queue(settings.notification_queue_key, {"id": notification.id})

    return notification


@router.get("/{notification_id}", response_model=schemas.NotificationOut)
def get_notification(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(models.Notification).get(notification_id)
    if not notification:
        raise HTTPException(404, "Notification not found")
    return notification


@router.get("", response_model=list[schemas.NotificationOut])
def list_notifications(recipient: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Notification)
    if recipient:
        query = query.filter(models.Notification.recipient == recipient)
    return query.order_by(models.Notification.created_at.desc()).limit(100).all()
