from __future__ import annotations

import asyncio
import logging

from src.config import settings
from src.core.heartbeat import HeartbeatService
from src.core.state_manager import TaskStateManager
from src.core.worker_node import WorkerNode
from src.db import Database, SystemSettingsRepository, TaskRunRepository
from src.redis_io import RedisStreamClient
from src.utils.logging_setup import configure_colored_logging


def configure_logging() -> None:
    configure_colored_logging(
        level=logging.INFO,
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )


async def run_worker() -> None:
    database = Database(settings.postgres_dsn)
    await database.connect()
    try:
        task_repo = TaskRunRepository(database.pool)
        system_settings_repo = SystemSettingsRepository(database.pool)
        state_manager = TaskStateManager(
            task_repo=task_repo,
            system_settings_repo=system_settings_repo,
            default_concurrency=settings.worker_concurrency,
            default_concurrency_limit=settings.worker_max_concurrency_limit,
            default_retry_max_attempts=settings.retry_max_attempts,
            default_retry_delay_seconds=settings.retry_delay_seconds,
        )
        stream_client = RedisStreamClient(settings.redis_url)
        heartbeat = HeartbeatService(
            interval_seconds=settings.heartbeat_interval_seconds,
            writer=state_manager.update_heartbeat,
        )
        worker = WorkerNode(
            settings=settings,
            state_manager=state_manager,
            stream_client=stream_client,
            heartbeat_service=heartbeat,
        )
        await worker.start()
    finally:
        await database.close()


def main() -> None:
    configure_logging()
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Worker interrupted by user.")


if __name__ == "__main__":
    main()
