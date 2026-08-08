from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.connection_manager import manager
from app.redis_bus import bus
from app import models, schemas

router = APIRouter(tags=["chat"])


@router.websocket("/ws/{room}")
async def chat_socket(websocket: WebSocket, room: str, sender: str = Query("anonymous")):
    await manager.connect(room, websocket)
    try:
        while True:
            raw = await websocket.receive_json()
            content = raw.get("content", "").strip()
            if not content:
                continue

            # Persist first so history survives restarts / new joiners.
            db: Session = next(get_db())
            try:
                message = models.Message(room=room, sender=sender, content=content)
                db.add(message)
                db.commit()
                db.refresh(message)
                payload = {
                    "id": message.id,
                    "room": room,
                    "sender": sender,
                    "content": content,
                    "created_at": message.created_at.isoformat(),
                    "handled_by": settings.instance_id,
                }
            finally:
                db.close()

            # Fan out to every replica (including this one) via Redis.
            await bus.publish(f"{settings.broadcast_channel_prefix}{room}", payload)

    except WebSocketDisconnect:
        manager.disconnect(room, websocket)


@router.get("/api/rooms/{room}/history", response_model=list[schemas.MessageOut])
def room_history(room: str, limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(models.Message)
        .filter(models.Message.room == room)
        .order_by(models.Message.created_at.desc())
        .limit(limit)
        .all()[::-1]
    )
