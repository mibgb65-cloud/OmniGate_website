from __future__ import annotations

import unittest
from typing import Any

from src.modules.chatgpt.models import BatchRegisterChatGptAccountsParams
from src.modules.chatgpt.services.batch_register_chatgpt_accounts import (
    BatchRegisterChatGptAccountsService,
    RetryableChatGptSignupError,
)


class _FakeBrowserActions:
    def __init__(self) -> None:
        self.start_calls = 0
        self.close_calls = 0
        self.browsers: list[dict[str, int]] = []

    async def start_browser(self) -> dict[str, int]:
        self.start_calls += 1
        browser = {"id": self.start_calls}
        self.browsers.append(browser)
        return browser

    async def close_browser(self) -> None:
        self.close_calls += 1


class _RetryThenSuccessSignupAction:
    def __init__(self) -> None:
        self.calls = 0
        self.browser_ids: list[int] = []

    async def process_account_with_browser(self, browser: dict[str, int]) -> dict[str, Any]:
        self.calls += 1
        self.browser_ids.append(browser["id"])
        if self.calls == 1:
            return {
                "status": "OPEN_PAGE_TIMEOUT",
                "email": "retry@example.com",
                "password": "pwd-1",
                "name": "Retry",
                "msg": "打开页面超时 | url=https://chatgpt.com | timeout_seconds=45.0",
            }

        return {
            "status": "REGISTERED_SUCCESS",
            "email": "success@example.com",
            "password": "pwd-2",
            "name": "Success",
            "totp_secret": "totp-secret",
            "msg": "ok",
        }


class _AlwaysTimeoutSignupAction:
    async def process_account_with_browser(self, _browser: dict[str, int]) -> dict[str, Any]:
        return {
            "status": "OPEN_PAGE_TIMEOUT",
            "email": "timeout@example.com",
            "password": "pwd-3",
            "name": "Timeout",
            "msg": "打开页面超时 | url=https://chatgpt.com | timeout_seconds=45.0",
        }


class _FakePersistence:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    async def create_account(self, email: str, password: str, totp_secret: str | None) -> int:
        self.calls.append((email, password, totp_secret))
        return 101


class TestBatchRegisterChatGptAccountsService(unittest.IsolatedAsyncioTestCase):
    async def test_should_restart_browser_and_retry_same_index_when_home_open_times_out(self) -> None:
        browser_actions = _FakeBrowserActions()
        signup_action = _RetryThenSuccessSignupAction()
        persistence = _FakePersistence()
        service = BatchRegisterChatGptAccountsService(
            browser_actions=browser_actions,
            signup_action=signup_action,
            account_persistence=persistence,
            chatgpt_home_open_max_retries=1,
        )

        result = await service.execute(BatchRegisterChatGptAccountsParams(signup_count=1))

        self.assertEqual(2, browser_actions.start_calls)
        self.assertEqual(2, browser_actions.close_calls)
        self.assertEqual([1, 2], signup_action.browser_ids)
        self.assertEqual(1, result.success_count)
        self.assertEqual(0, result.failed_count)
        self.assertEqual(
            [("success@example.com", "pwd-2", "totp-secret")],
            persistence.calls,
        )

    async def test_should_raise_retryable_error_when_first_account_keeps_timing_out(self) -> None:
        browser_actions = _FakeBrowserActions()
        service = BatchRegisterChatGptAccountsService(
            browser_actions=browser_actions,
            signup_action=_AlwaysTimeoutSignupAction(),
            account_persistence=_FakePersistence(),
            chatgpt_home_open_max_retries=1,
        )

        with self.assertRaises(RetryableChatGptSignupError):
            await service.execute(BatchRegisterChatGptAccountsParams(signup_count=1))

        self.assertEqual(2, browser_actions.start_calls)
        self.assertEqual(2, browser_actions.close_calls)
