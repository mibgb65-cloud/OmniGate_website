from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from uuid import UUID

from src.core.worker_node import WorkerNode


class _FakeStateManager:
    def __init__(self) -> None:
        self.created_runs: list[dict] = []
        self.deleted_run_ids: list[str] = []

    async def create_task_run(
        self,
        *,
        task_run_id,
        root_run_id,
        triggered_by,
        input_payload,
        max_attempts,
    ) -> None:
        self.created_runs.append(
            {
                "task_run_id": str(task_run_id),
                "root_run_id": str(root_run_id),
                "triggered_by": triggered_by,
                "input_payload": input_payload,
                "max_attempts": max_attempts,
            }
        )

    async def delete_task_run(self, task_run_id) -> None:
        self.deleted_run_ids.append(str(task_run_id))


class _FakeStreamClient:
    def __init__(self) -> None:
        self.added_messages: list[dict[str, str]] = []

    async def add_task_message(self, *, stream: str, fields: dict[str, str]) -> str:
        self.added_messages.append({"stream": stream, **fields})
        return "1-0"


class TestWorkerChatGptBatchSerialQueue(unittest.IsolatedAsyncioTestCase):
    def _build_node(self) -> tuple[WorkerNode, _FakeStateManager, _FakeStreamClient]:
        state_manager = _FakeStateManager()
        stream_client = _FakeStreamClient()
        settings = SimpleNamespace(
            task_stream="task_stream",
            task_stream_group="worker_group",
            task_stream_consumer="worker-local-1",
            worker_instance_id="worker-local-1",
        )
        node = WorkerNode(
            settings=settings,  # type: ignore[arg-type]
            db_pool=SimpleNamespace(),  # type: ignore[arg-type]
            state_manager=state_manager,  # type: ignore[arg-type]
            stream_client=stream_client,  # type: ignore[arg-type]
            heartbeat_service=SimpleNamespace(),  # type: ignore[arg-type]
        )
        return node, state_manager, stream_client

    async def test_should_enqueue_next_child_task_for_chatgpt_batch(self) -> None:
        node, state_manager, stream_client = self._build_node()
        task_record = SimpleNamespace(
            root_run_id=UUID("00000000-0000-0000-0000-000000000010"),
            triggered_by="tester",
            max_attempts=3,
        )
        task_payload = {
            "module": "chatgpt",
            "action": "batch_register_chatgpt_accounts",
            "payload": {
                "signup_count": 1,
                "requested_count": 5,
                "current_index": 1,
            },
        }

        await node._enqueue_next_chatgpt_batch_task_if_needed(
            task_record=task_record,
            task_payload=task_payload,
        )

        self.assertEqual(1, len(state_manager.created_runs))
        created = state_manager.created_runs[0]
        self.assertEqual("tester", created["triggered_by"])
        self.assertEqual(3, created["max_attempts"])
        self.assertEqual(2, created["input_payload"]["payload"]["current_index"])
        self.assertEqual(1, created["input_payload"]["payload"]["signup_count"])

        self.assertEqual(1, len(stream_client.added_messages))
        message = stream_client.added_messages[0]
        self.assertEqual("task_stream", message["stream"])
        decoded_payload = json.loads(message["payload"])
        self.assertEqual(2, decoded_payload["payload"]["current_index"])
        self.assertEqual("00000000-0000-0000-0000-000000000010", message["root_run_id"])

    async def test_should_not_enqueue_when_current_child_is_last_one(self) -> None:
        node, state_manager, stream_client = self._build_node()
        task_record = SimpleNamespace(
            root_run_id=UUID("00000000-0000-0000-0000-000000000011"),
            triggered_by="tester",
            max_attempts=3,
        )
        task_payload = {
            "module": "chatgpt",
            "action": "batch_register_chatgpt_accounts",
            "payload": {
                "signup_count": 1,
                "requested_count": 2,
                "current_index": 2,
            },
        }

        await node._enqueue_next_chatgpt_batch_task_if_needed(
            task_record=task_record,
            task_payload=task_payload,
        )

        self.assertEqual([], state_manager.created_runs)
        self.assertEqual([], stream_client.added_messages)
