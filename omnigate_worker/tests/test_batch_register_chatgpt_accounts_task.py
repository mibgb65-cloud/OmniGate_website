from __future__ import annotations

import unittest
from unittest.mock import patch

from src.modules.chatgpt.tasks.batch_register_chatgpt_accounts import BatchRegisterChatGptAccountsTask
from src.modules.chatgpt.services import RetryableChatGptSignupError


class _RetryableFailureService:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def execute(self, _params) -> None:
        raise RetryableChatGptSignupError("打开 ChatGPT 首页连续超时")


class TestBatchRegisterChatGptAccountsTask(unittest.IsolatedAsyncioTestCase):
    async def test_should_return_failed_status_for_retryable_home_open_timeout(self) -> None:
        task = BatchRegisterChatGptAccountsTask(task_id="task-1")

        with patch(
            "src.modules.chatgpt.tasks.batch_register_chatgpt_accounts.BatchRegisterChatGptAccountsService",
            _RetryableFailureService,
        ):
            result = await task.run({"signup_count": 1})

        self.assertEqual("failed", result["status"])
        self.assertEqual("RETRYABLE_OPEN_PAGE_TIMEOUT", result["error_code"])
        self.assertIn("连续超时", result["error_message"])
