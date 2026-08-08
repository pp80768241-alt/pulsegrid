import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App configuration. Every backend replica reads the same env values,
    which is what lets them coordinate through Redis/Postgres instead of
    sharing in-process memory."""

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://pulse_user:pulse_pass@localhost:5432/pulsegrid",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    instance_id: str = os.getenv("HOSTNAME", "local-instance")
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    notification_queue_key: str = "pulsegrid:notifications:queue"
    broadcast_channel_prefix: str = "pulsegrid:room:"

    class Config:
        env_file = ".env"


settings = Settings()
