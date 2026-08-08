"""
Redis pub/sub bus.

Why this exists: a WebSocket connection lives in the memory of exactly one
backend process. If we run 3 replicas behind a load balancer, a message
posted by a client connected to replica A must still reach a client
connected to replica B or C. Redis pub/sub is the coordination layer that
makes that possible — every replica subscribes to the same channels and
re-broadcasts to its own locally-connected clients.

This is the same pattern used in production chat/notification systems
(Slack, Discord-style gateways) before they graduate to Kafka for
durability + replay.
"""

import json
import asyncio
from typing import Callable, Awaitable

import redis.asyncio as aioredis

from app.config import settings


class RedisBus:
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None

    async def connect(self):
        self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()

    async def publish(self, channel: str, payload: dict):
        await self._redis.publish(channel, json.dumps(payload))

    async def subscribe_and_listen(self, channel_pattern: str, on_message: Callable[[str, dict], Awaitable[None]]):
        """Subscribe to a pattern (e.g. 'pulsegrid:room:*') and invoke on_message
        for every message published by ANY replica, including this one."""
        await self._pubsub.psubscribe(channel_pattern)

        async def _listen():
            async for message in self._pubsub.listen():
                if message["type"] != "pmessage":
                    continue
                channel = message["channel"]
                try:
                    data = json.loads(message["data"])
                except (TypeError, json.JSONDecodeError):
                    continue
                await on_message(channel, data)

        self._listener_task = asyncio.create_task(_listen())

    async def push_queue(self, key: str, payload: dict):
        await self._redis.rpush(key, json.dumps(payload))

    async def pop_queue(self, key: str, timeout: int = 5) -> dict | None:
        result = await self._redis.blpop(key, timeout=timeout)
        if not result:
            return None
        _, raw = result
        return json.loads(raw)

    async def close(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()


bus = RedisBus(settings.redis_url)
