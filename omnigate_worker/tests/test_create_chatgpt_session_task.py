from __future__ import annotations

import unittest
from unittest.mock import patch

from src.modules.chatgpt.tasks.create_session import CreateChatGptSessionTask


class _SuccessService:
    def __init__(self, *_args, **_kwargs) -> None:
        self.closed = False

    async def execute(self, _params, **_kwargs):
        return {
            "account_id": 12,
            "email": "demo@example.com",
            "trace_id": "trace-1",
            "login_result": {"ok": True},
            "session_result": {"ok": True, "data": {"accessToken": "sess_123"}},
            "session_token": "sess_123",
            "persisted_to_db": True,
            "browser_kept_open": False,
        }

    async def close(self) -> None:
        self.closed = True


class TestCreateChatGptSessionTask(unittest.IsolatedAsyncioTestCase):
    async def test_should_return_success_and_redact_session_token(self) -> None:
        task = CreateChatGptSessionTask(task_id="task-1")

        with patch(
            "src.modules.chatgpt.tasks.create_session.UpdateChatGptSessionByAccountIdService",
            _SuccessService,
        ):
            result = await task.run({"account_id": 12})

        self.assertEqual("success", result["status"])
        self.assertEqual(12, result["data"]["account_id"])
        self.assertEqual("<redacted>", result["data"]["session_token"])
        self.assertEqual(
            "<redacted>",
            result["data"]["session_result"]["data"]["accessToken"],
        )

    async def test_should_return_failed_status_for_validation_error(self) -> None:
        task = CreateChatGptSessionTask(task_id="task-2")

        result = await task.run({})

        self.assertEqual("failed", result["status"])
        self.assertEqual("VALIDATION_ERROR", result["error_code"])
