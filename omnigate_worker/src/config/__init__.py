"""统一配置导出：
1) settings/Settings: Worker 运行配置（小写字段）
2) get_settings: 浏览器模块使用的应用配置（来自 config.py，大写字段）
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.config import Settings as AppSettings
from src.config.config import get_settings


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    worker_instance_id: str = "worker-local-1"
    redis_url: str = "redis://localhost:6379/0"
    postgres_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/omnigate"

    task_stream: str = "task_stream"
    task_log_stream: str = "task_log_stream"
    task_stream_group: str = "worker_group"
    task_stream_consumer: str = ""
    task_stream_block_ms: int = 2000
    task_stream_read_count: int = 10
    task_stream_claim_idle_ms: int = 60000
    task_stream_claim_count: int = 10
    task_stream_claim_interval_ms: int = 3000
    task_log_stream_maxlen: int = 10000

    worker_concurrency: int = 3
    worker_max_concurrency_limit: int = 10
    heartbeat_interval_seconds: int = 30
    retry_max_attempts: int = 3
    retry_delay_seconds: int = 10


settings = Settings()

__all__ = [
    "AppSettings",
    "Settings",
    "get_settings",
    "settings",
]
