"""
Tracks WebSocket connections held by THIS process only.

Combined with RedisBus, the full fan-out path for a chat message is:

  client -> this replica's WebSocket -> persist to Postgres
         -> publish to Redis channel "pulsegrid:room:<room>"
         -> every replica's Redis subscriber (including this one) receives it
         -> each replica pushes it out to its own locally-connected clients

This is what lets you horizontally scale the WebSocket gateway: add more
replicas behind the load balancer and every one of them stays in sync
without talking to each other directly.
"""

from collections import defaultdict
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._rooms: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, room: str, websocket: WebSocket):
        await websocket.accept()
        self._rooms[room].add(websocket)

    def disconnect(self, room: str, websocket: WebSocket):
        self._rooms[room].discard(websocket)
        if not self._rooms[room]:
            del self._rooms[room]

    async def broadcast_local(self, room: str, payload: dict):
        """Send to every client connected to THIS process for a room."""
        dead = []
        for ws in self._rooms.get(room, set()):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(room, ws)

    def total_connections(self) -> int:
        return sum(len(clients) for clients in self._rooms.values())


manager = ConnectionManager()
