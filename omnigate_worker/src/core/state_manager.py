from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.db import SystemSettingsRepository, TaskRunRecord, TaskRunRepository


@dataclass(slots=True)
class WorkerRuntimeSettings:
    max_concurrency: int
    max_concurrency_limit: int
    retry_max_attempts: int
    retry_delay_seconds: int


class TaskStateManager:
    def __init__(
        self,
        *,
        task_repo: TaskRunRepository,
        system_settings_repo: SystemSettingsRepository,
        default_concurrency: int,
        default_concurrency_limit: int,
        default_retry_max_attempts: int,
        default_retry_delay_seconds: int,
    ) -> None:
        self._task_repo = task_repo
        self._system_settings_repo = system_settings_repo
        self._default_concurrency = default_concurrency
        self._default_concurrency_limit = default_concurrency_limit
        self._default_retry_max_attempts = default_retry_max_attempts
        self._default_retry_delay_seconds = default_retry_delay_seconds

    async def get_runtime_settings(self) -> WorkerRuntimeSettings:
        raw = await self._system_settings_repo.get_many(
            [
                "worker.max_concurrency",
                "worker.max_concurrency_limit",
                "task.retry_max_attempts",
                "task.retry_delay_seconds",
            ]
        )

        limit = self._safe_int(
            raw.get("worker.max_concurrency_limit"),
            self._default_concurrency_limit,
        )
        limit = max(1, limit)

        concurrency = self._safe_int(raw.get("worker.max_concurrency"), self._default_concurrency)
        concurrency = max(1, min(concurrency, limit))

        retry_max_attempts = self._safe_int(raw.get("task.retry_max_attempts"), self._default_retry_max_attempts)
        retry_max_attempts = max(1, retry_max_attempts)

        retry_delay_seconds = self._safe_int(raw.get("task.retry_delay_seconds"), self._default_retry_delay_seconds)
        retry_delay_seconds = max(0, retry_delay_seconds)

        return WorkerRuntimeSettings(
            max_concurrency=concurrency,
            max_concurrency_limit=limit,
            retry_max_attempts=retry_max_attempts,
            retry_delay_seconds=retry_delay_seconds,
        )

    async def get_task_run(self, task_run_id: UUID) -> TaskRunRecord | None:
        return await self._task_repo.get_task_run(task_run_id)

    async def create_task_run(
        self,
        *,
        task_run_id: UUID,
        root_run_id: UUID,
        triggered_by: str,
        input_payload: dict,
        max_attempts: int,
    ) -> None:
        await self._task_repo.create_task_run(
            task_run_id=task_run_id,
            root_run_id=root_run_id,
            triggered_by=triggered_by,
            input_payload=input_payload,
            max_attempts=max_attempts,
        )

    async def delete_task_run(self, task_run_id: UUID) -> None:
        await self._task_repo.delete_task_run(task_run_id)

    async def mark_running(self, task_run_id: UUID, worker_instance_id: str) -> bool:
        return await self._task_repo.mark_running(task_run_id, worker_instance_id)

    async def mark_success(self, task_run_id: UUID, last_checkpoint: str | None = None) -> None:
        await self._task_repo.mark_success(task_run_id, last_checkpoint=last_checkpoint)

    async def mark_cancelled(self, task_run_id: UUID, reason: str | None = None) -> None:
        await self._task_repo.mark_cancelled(task_run_id, reason=reason)

    async def mark_timeout(self, task_run_id: UUID, reason: str | None = None) -> None:
        await self._task_repo.mark_timeout(task_run_id, reason=reason)

    async def mark_failed_and_schedule_retry(
        self,
        *,
        task_run_id: UUID,
        error_code: str | None,
        error_message: str | None,
        last_checkpoint: str | None,
        retry_delay_seconds: int,
        retry_max_attempts: int,
    ) -> UUID | None:
        return await self._task_repo.mark_failed_and_schedule_retry(
            task_run_id=task_run_id,
            error_code=error_code,
            error_message=error_message,
            last_checkpoint=last_checkpoint,
            retry_delay_seconds=retry_delay_seconds,
            retry_max_attempts=retry_max_attempts,
        )

    async def update_heartbeat(self, task_run_id: UUID) -> None:
        await self._task_repo.update_heartbeat(task_run_id)

    async def is_cancel_requested(self, task_run_id: UUID) -> bool:
        return await self._task_repo.is_cancel_requested(task_run_id)

    async def set_google_account_sync_status(self, account_id: int, sync_status: int) -> None:
        await self._task_repo.set_google_account_sync_status(account_id, sync_status)

    @staticmethod
    def _safe_int(raw: str | None, fallback: int) -> int:
        if raw is None:
            return fallback
        try:
            return int(raw)
        except (TypeError, ValueError):
            return fallback
