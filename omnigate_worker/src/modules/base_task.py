from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.utils.task_logger import LogSink, TaskLogger

if TYPE_CHECKING:
    import asyncpg


class BaseTask(ABC):
    module_name: str = "common"
    action_name: str = "task"

    def __init__(
        self,
        task_id: str | None = None,
        *,
        log_sink: LogSink | None = None,
        worker_instance_id: str | None = None,
        attempt_no: int | None = None,
        db_pool: "asyncpg.Pool | None" = None,
    ) -> None:
        self.task_id = task_id or str(uuid4())
        self.db_pool = db_pool
        self.logger = TaskLogger(
            task_id=self.task_id,
            module=self.module_name,
            action=self.action_name,
            worker_instance_id=worker_instance_id,
            attempt_no=attempt_no,
            sink=log_sink,
        )

    async def log_info(
        self,
        message: str,
        *,
        step: int | None = None,
        step_total: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        await self.logger.info(message, step=step, step_total=step_total, context=context)

    async def log_warning(
        self,
        message: str,
        *,
        step: int | None = None,
        step_total: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        await self.logger.warning(message, step=step, step_total=step_total, context=context)

    async def log_error(
        self,
        message: str,
        *,
        step: int | None = None,
        step_total: int | None = None,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        merged_context = dict(context or {})
        if error_code:
            merged_context["error_code"] = error_code
        await self.logger.error(message, step=step, step_total=step_total, context=merged_context or None)

    @abstractmethod
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
