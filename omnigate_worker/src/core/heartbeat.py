from __future__ import annotations

import asyncio
from typing import Awaitable, Callable
from uuid import UUID


HeartbeatWriter = Callable[[UUID], Awaitable[None]]


class HeartbeatService:
    def __init__(self, *, interval_seconds: int, writer: HeartbeatWriter) -> None:
        self._interval_seconds = max(1, interval_seconds)
        self._writer = writer
        self._workers: dict[UUID, asyncio.Task[None]] = {}

    async def start(self, task_run_id: UUID) -> None:
        await self.stop(task_run_id)
        worker = asyncio.create_task(self._run(task_run_id))
        self._workers[task_run_id] = worker

    async def stop(self, task_run_id: UUID) -> None:
        worker = self._workers.pop(task_run_id, None)
        if worker is None:
            return
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass

    async def shutdown(self) -> None:
        task_ids = list(self._workers.keys())
        for task_run_id in task_ids:
            await self.stop(task_run_id)

    async def _run(self, task_run_id: UUID) -> None:
        try:
            while True:
                await asyncio.sleep(self._interval_seconds)
                await self._writer(task_run_id)
        except asyncio.CancelledError:
            raise
