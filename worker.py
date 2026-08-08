"""
Standalone worker process — run as its own container, separate from the
API replicas.

This is the classic producer/consumer split: `POST /api/notifications`
enqueues a job in Redis and returns instantly. This worker (you can run
N copies of it) pulls jobs off that queue with a blocking pop, "delivers"
them (stubbed here — swap in email/SMS/push provider calls), and marks
them delivered in Postgres.

Run it with:  python -m app.worker
"""

import asyncio
import logging
from datetime import datetime

from app.config import settings
from app.database import SessionLocal
from app.redis_bus import bus
from app import models

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(message)s")
log = logging.getLogger(__name__)


async def deliver(notification_id: int):
    """Stand-in for a real delivery integration (SES, Twilio, FCM, etc).
    Swap this out; everything else in the pipeline stays the same."""
    await asyncio.sleep(0.2)  # simulate network latency to a provider
    return True


async def process_one(job: dict):
    notification_id = job["id"]
    db = SessionLocal()
    try:
        notification = db.query(models.Notification).get(notification_id)
        if not notification:
            log.warning("Notification %s not found, skipping", notification_id)
            return

        success = await deliver(notification_id)
        if success:
            notification.delivered = True
            notification.delivered_at = datetime.utcnow()
            db.commit()
            log.info("Delivered notification %s to %s", notification_id, notification.recipient)
        else:
            log.error("Delivery failed for notification %s", notification_id)
    finally:
        db.close()


async def run_worker():
    await bus.connect()
    log.info("Worker started, polling queue '%s'", settings.notification_queue_key)
    while True:
        job = await bus.pop_queue(settings.notification_queue_key, timeout=5)
        if job is None:
            continue  # timed out waiting, loop again (keeps the container responsive to shutdown)
        try:
            await process_one(job)
        except Exception:
            log.exception("Failed processing job %s", job)


if __name__ == "__main__":
    asyncio.run(run_worker())
