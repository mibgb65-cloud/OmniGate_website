from __future__ import annotations

import asyncio
import logging
import re
from typing import Awaitable, Callable


BridgeSink = Callable[[int, str, int | None, int | None, str], Awaitable[None]]


class _TaskLogForwardHandler(logging.Handler):
    _STEP_PATTERN = re.compile(r"\[(\d+)\s*/\s*(\d+)\]")

    def __init__(
        self,
        *,
        sink: BridgeSink,
        logger_prefixes: tuple[str, ...],
        loop: asyncio.AbstractEventLoop,
        min_level: int,
    ) -> None:
        super().__init__(level=min_level)
        self._sink = sink
        self._logger_prefixes = logger_prefixes
        self._loop = loop
        self._pending: set[asyncio.Task[None]] = set()
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        if not self._is_target_logger(record.name):
            return
        if record.levelno < self.level:
            return

        message = self.format(record)
        step, step_total = self._extract_steps(message)

        task = self._loop.create_task(
            self._sink(
                record.levelno,
                message,
                step,
                step_total,
                record.name,
            )
        )
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def drain(self) -> None:
        if not self._pending:
            return
        await asyncio.gather(*list(self._pending), return_exceptions=True)

    def _is_target_logger(self, logger_name: str) -> bool:
        for prefix in self._logger_prefixes:
            if logger_name == prefix or logger_name.startswith(f"{prefix}."):
                return True
        return False

    @classmethod
    def _extract_steps(cls, message: str) -> tuple[int | None, int | None]:
        match = cls._STEP_PATTERN.search(message)
        if not match:
            return None, None
        try:
            step = int(match.group(1))
            step_total = int(match.group(2))
        except ValueError:
            return None, None
        if step <= 0 or step_total <= 0 or step > step_total:
            return None, None
        return step, step_total


class TaskLogBridge:
    """Forward selected Python logger records into task log sink."""

    def __init__(
        self,
        *,
        sink: BridgeSink,
        logger_prefixes: tuple[str, ...],
        min_level: int = logging.INFO,
    ) -> None:
        self._sink = sink
        self._logger_prefixes = logger_prefixes
        self._min_level = min_level
        self._handler: _TaskLogForwardHandler | None = None

    async def __aenter__(self) -> "TaskLogBridge":
        loop = asyncio.get_running_loop()
        self._handler = _TaskLogForwardHandler(
            sink=self._sink,
            logger_prefixes=self._logger_prefixes,
            loop=loop,
            min_level=self._min_level,
        )
        logging.getLogger().addHandler(self._handler)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._handler is None:
            return
        logging.getLogger().removeHandler(self._handler)
        await self._handler.drain()
        self._handler = None
