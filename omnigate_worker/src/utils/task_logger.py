from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class TaskLogEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    level: LogLevel
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    step: int | None = Field(default=None, ge=1)
    step_total: int | None = Field(default=None, ge=1)
    module: str | None = None
    action: str | None = None
    worker_instance_id: str | None = None
    attempt_no: int | None = Field(default=None, ge=1)
    context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_steps(self) -> "TaskLogEvent":
        if self.step is None and self.step_total is not None:
            raise ValueError("step_total requires step")
        if self.step is not None and self.step_total is not None and self.step > self.step_total:
            raise ValueError("step cannot be greater than step_total")
        return self

    def to_payload(self) -> dict[str, Any]:
        payload = self.model_dump(exclude_none=True)
        payload["timestamp"] = (
            self.timestamp.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        )
        return payload

    def to_stream_fields(self) -> dict[str, str]:
        payload = self.to_payload()
        fields: dict[str, str] = {}
        for key, value in payload.items():
            if key == "context":
                fields[key] = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
            else:
                fields[key] = str(value)
        return fields


LogPayload = dict[str, Any]
LogSink = Callable[[LogPayload], None | Awaitable[None]]


def stdout_log_sink(payload: LogPayload) -> None:
    print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))


class TaskLogger:
    def __init__(
        self,
        task_id: str,
        *,
        module: str | None = None,
        action: str | None = None,
        worker_instance_id: str | None = None,
        attempt_no: int | None = None,
        sink: LogSink | None = None,
    ) -> None:
        self.task_id = task_id
        self.module = module
        self.action = action
        self.worker_instance_id = worker_instance_id
        self.attempt_no = attempt_no
        self._sink = sink or stdout_log_sink

    async def log(
        self,
        level: LogLevel,
        message: str,
        *,
        step: int | None = None,
        step_total: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> TaskLogEvent:
        event = TaskLogEvent(
            task_id=self.task_id,
            level=level,
            message=message,
            step=step,
            step_total=step_total,
            module=self.module,
            action=self.action,
            worker_instance_id=self.worker_instance_id,
            attempt_no=self.attempt_no,
            context=context,
        )
        payload = event.to_payload()
        maybe_awaitable = self._sink(payload)
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable
        return event

    async def debug(
        self,
        message: str,
        *,
        step: int | None = None,
        step_total: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> TaskLogEvent:
        return await self.log(LogLevel.DEBUG, message, step=step, step_total=step_total, context=context)

    async def info(
        self,
        message: str,
        *,
        step: int | None = None,
        step_total: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> TaskLogEvent:
        return await self.log(LogLevel.INFO, message, step=step, step_total=step_total, context=context)

    async def warning(
        self,
        message: str,
        *,
        step: int | None = None,
        step_total: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> TaskLogEvent:
        return await self.log(LogLevel.WARNING, message, step=step, step_total=step_total, context=context)

    async def error(
        self,
        message: str,
        *,
        step: int | None = None,
        step_total: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> TaskLogEvent:
        return await self.log(LogLevel.ERROR, message, step=step, step_total=step_total, context=context)
