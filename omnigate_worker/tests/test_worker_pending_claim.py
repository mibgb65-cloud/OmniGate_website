from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.core.worker_node import WorkerNode
from src.redis_io import TaskStreamMessage


class _FakeStreamClient:
    def __init__(self, responses: list[tuple[str, list[TaskStreamMessage]]]) -> None:
        self._responses = responses
        self.call_count = 0

    async def auto_claim(
        self,
        *,
        stream: str,
        group: str,
        consumer: str,
        min_idle_ms: int,
        start_id: str,
        count: int,
    ) -> tuple[str, list[TaskStreamMessage]]:
        self.call_count += 1
        if self._responses:
            return self._responses.pop(0)
        return "0-0", []


class TestWorkerPendingClaim(unittest.IsolatedAsyncioTestCase):
    def _build_node(self, stream_client: _FakeStreamClient) -> WorkerNode:
        settings = SimpleNamespace(
            task_stream="task_stream",
            task_stream_group="worker_group",
            task_stream_consumer="worker-local-1",
            worker_instance_id="worker-local-1",
            task_stream_claim_idle_ms=60000,
            task_stream_claim_count=10,
            task_stream_claim_interval_ms=3000,
        )
        return WorkerNode(
            settings=settings,  # type: ignore[arg-type]
            db_pool=SimpleNamespace(),  # type: ignore[arg-type]
            state_manager=SimpleNamespace(),  # type: ignore[arg-type]
            stream_client=stream_client,  # type: ignore[arg-type]
            heartbeat_service=SimpleNamespace(),  # type: ignore[arg-type]
        )

    async def test_should_return_claimed_messages(self) -> None:
        claimed = TaskStreamMessage(
            stream="task_stream",
            message_id="1-0",
            fields={"task_run_id": "00000000-0000-0000-0000-000000000001"},
        )
        stream_client = _FakeStreamClient([("9-0", [claimed])])
        node = self._build_node(stream_client)

        result = await node._read_pending_messages(available=3)

        self.assertEqual(1, stream_client.call_count)
        self.assertEqual("9-0", node._pending_claim_cursor)
        self.assertEqual(1, len(result))
        self.assertEqual("1-0", result[0].message_id)

    async def test_should_throttle_claim_when_nothing_claimed(self) -> None:
        stream_client = _FakeStreamClient([("0-0", [])])
        node = self._build_node(stream_client)

        first = await node._read_pending_messages(available=3)
        second = await node._read_pending_messages(available=3)

        self.assertEqual([], first)
        self.assertEqual([], second)
        self.assertEqual(1, stream_client.call_count)
