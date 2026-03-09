from __future__ import annotations

import sys
import types
import unittest
from typing import Any

if "asyncpg" not in sys.modules:
    asyncpg_stub = types.ModuleType("asyncpg")
    asyncpg_stub.Pool = object
    asyncpg_stub.UniqueViolationError = Exception
    sys.modules["asyncpg"] = asyncpg_stub

from src.db.chatgpt_account_repository import ChatGptAccountCredentialRecord
from src.modules.chatgpt.models.chatgpt_service_params import UpdateChatGptSessionByAccountIdParams
from src.modules.chatgpt.services.update_chatgpt_session_by_account_id import (
    UpdateChatGptSessionByAccountIdService,
)
from src.utils import AesTypeHandlerCompat


class _FakeAccountRepository:
    def __init__(self, record: ChatGptAccountCredentialRecord | None) -> None:
        self.record = record
        self.last_account_id: int | None = None

    async def get_active_account_credential(self, account_id: int) -> ChatGptAccountCredentialRecord | None:
        self.last_account_id = account_id
        if self.record is None:
            return None
        if int(self.record.account_id) != int(account_id):
            return None
        return self.record


class _FakePersistence:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def update_session_token(self, *, account_id: int, session_token: str, updated_by: int | None = None) -> None:
        self.calls.append(
            {
                "account_id": account_id,
                "session_token": session_token,
                "updated_by": updated_by,
            }
        )


class _FakeBrowser:
    def __init__(self) -> None:
        self.opened_urls: list[str] = []
        self.page = object()

    async def get(self, url: str) -> Any:
        self.opened_urls.append(url)
        return self.page


class _FakeBrowserActions:
    def __init__(self) -> None:
        self.browser = _FakeBrowser()
        self.start_calls = 0
        self.close_calls = 0

    async def start_browser(self) -> _FakeBrowser:
        self.start_calls += 1
        return self.browser

    async def close_browser(self) -> None:
        self.close_calls += 1


class _FakeLoginAction:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def login(self, page: Any, email: str, password: str, totp_secret: str | None = None) -> dict[str, Any]:
        self.calls.append(
            {
                "page": page,
                "email": email,
                "password": password,
                "totp_secret": totp_secret,
            }
        )
        return dict(self.result)


class _FakeSessionAction:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def get_session(self, page: Any) -> dict[str, Any]:
        self.calls.append({"page": page})
        return dict(self.result)


class TestUpdateChatGptSessionByAccountIdService(unittest.IsolatedAsyncioTestCase):
    async def test_should_load_account_login_get_session_and_persist_token(self) -> None:
        decryptor = AesTypeHandlerCompat()
        if decryptor.is_backend_available():
            stored_password = decryptor.encrypt_base64("pwd-123")
            stored_totp = decryptor.encrypt_base64("JBSWY3DPEHPK3PXP")
        else:
            stored_password = "pwd-123"
            stored_totp = "JBSWY3DPEHPK3PXP"

        repository = _FakeAccountRepository(
            ChatGptAccountCredentialRecord(
                account_id=301,
                email="demo@example.com",
                encrypted_password=stored_password,
                encrypted_totp_secret=stored_totp,
            )
        )
        persistence = _FakePersistence()
        browser_actions = _FakeBrowserActions()
        login_action = _FakeLoginAction({"ok": True, "step": "done"})
        session_action = _FakeSessionAction(
            {
                "ok": True,
                "step": "done",
                "data": {"accessToken": "sess_123456", "user": {"email": "demo@example.com"}},
            }
        )
        service = UpdateChatGptSessionByAccountIdService(
            account_repository=repository,
            persistence=persistence,
            browser_actions=browser_actions,
            login_action=login_action,
            session_action=session_action,
        )

        result = await service.execute(
            UpdateChatGptSessionByAccountIdParams(chatgpt_account_id=301),
            keep_page_open=False,
        )

        self.assertEqual(repository.last_account_id, 301)
        self.assertEqual(browser_actions.start_calls, 1)
        self.assertEqual(browser_actions.browser.opened_urls, ["data:,"])
        self.assertEqual(login_action.calls[0]["email"], "demo@example.com")
        self.assertEqual(login_action.calls[0]["password"], "pwd-123")
        self.assertEqual(login_action.calls[0]["totp_secret"], "JBSWY3DPEHPK3PXP")
        self.assertEqual(len(session_action.calls), 1)
        self.assertEqual(len(persistence.calls), 1)
        self.assertEqual(persistence.calls[0]["account_id"], 301)
        self.assertEqual(persistence.calls[0]["session_token"], "sess_123456")
        self.assertEqual(result["account_id"], 301)
        self.assertEqual(result["session_token"], "sess_123456")
        self.assertTrue(result["persisted_to_db"])

        await service.close()
        self.assertEqual(browser_actions.close_calls, 1)

    async def test_should_raise_when_account_not_found(self) -> None:
        service = UpdateChatGptSessionByAccountIdService(
            account_repository=_FakeAccountRepository(record=None),
            persistence=_FakePersistence(),
            browser_actions=_FakeBrowserActions(),
            login_action=_FakeLoginAction({"ok": True, "step": "done"}),
            session_action=_FakeSessionAction({"ok": True, "data": {"accessToken": "sess_x"}}),
        )

        with self.assertRaisesRegex(ValueError, "账号不存在|已删除"):
            await service.execute(999, keep_page_open=False)
