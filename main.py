from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.config import settings
from app.redis_bus import bus
from app.connection_manager import manager
from app.routes import chat, notifications

Base.metadata.create_all(bind=engine)


async def _on_room_message(channel: str, payload: dict):
    """Called for every message published on any 'pulsegrid:room:*' channel,
    by ANY replica. Re-broadcasts to whatever clients are connected to
    THIS replica specifically."""
    room = channel.replace(settings.broadcast_channel_prefix, "", 1)
    await manager.broadcast_local(room, payload)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bus.connect()
    await bus.subscribe_and_listen(f"{settings.broadcast_channel_prefix}*", _on_room_message)
    yield
    await bus.close()


app = FastAPI(
    title="PulseGrid — Distributed Real-Time Backend",
    description="Horizontally-scalable WebSocket chat + async notification pipeline, "
    "coordinated across replicas via Redis pub/sub and a Redis-backed job queue.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(notifications.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "instance_id": settings.instance_id,
        "active_connections": manager.total_connections(),
    }
