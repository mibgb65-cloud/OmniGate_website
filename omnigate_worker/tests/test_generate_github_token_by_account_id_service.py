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

from src.db.github_account_repository import GithubAccountCredentialRecord
from src.modules.github.models.github_service_params import GenerateGithubTokenByAccountIdParams
from src.modules.github.services.generate_github_token_by_account_id import (
    GenerateGithubTokenByAccountIdService,
)
from src.utils import AesTypeHandlerCompat


class _FakeAccountRepository:
    def __init__(self, record: GithubAccountCredentialRecord | None) -> None:
        self.record = record
        self.last_account_id: int | None = None

    async def get_active_account_credential(self, account_id: int) -> GithubAccountCredentialRecord | None:
        self.last_account_id = account_id
        if self.record is None:
            return None
        if int(self.record.account_id) != int(account_id):
            return None
        return self.record


class _FakePersistence:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def update_access_token(self, *, account_id: int, access_token: str, token_note: str | None = None) -> None:
        self.calls.append(
            {
                "account_id": account_id,
                "access_token": access_token,
                "token_note": token_note,
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

    async def login_github(self, page: Any, email: str, password: str, totp_secret: str | None = None) -> dict[str, Any]:
        self.calls.append(
            {
                "page": page,
                "email": email,
                "password": password,
                "totp_secret": totp_secret,
            }
        )
        return dict(self.result)


class _FakeGenerateTokenAction:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def generate_token(self, page: Any, totp_secret: str) -> dict[str, Any]:
        self.calls.append({"page": page, "totp_secret": totp_secret})
        return dict(self.result)


class TestGenerateGithubTokenByAccountIdService(unittest.IsolatedAsyncioTestCase):
    async def test_should_load_account_login_and_persist_token(self) -> None:
        decryptor = AesTypeHandlerCompat()
        if decryptor.is_backend_available():
            stored_password = decryptor.encrypt_base64("pwd-123")
            stored_totp = decryptor.encrypt_base64("JBSWY3DPEHPK3PXP")
        else:
            stored_password = "pwd-123"
            stored_totp = "JBSWY3DPEHPK3PXP"

        repository = _FakeAccountRepository(
            GithubAccountCredentialRecord(
                account_id=101,
                username="octocat",
                email="demo@example.com",
                encrypted_password=stored_password,
                encrypted_totp_secret=stored_totp,
            )
        )
        persistence = _FakePersistence()
        browser_actions = _FakeBrowserActions()
        login_action = _FakeLoginAction({"ok": True, "step": "done"})
        token_action = _FakeGenerateTokenAction(
            {"ok": True, "step": "done", "token": "ghp_token_123", "note": "AutoToken_abcd"}
        )
        service = GenerateGithubTokenByAccountIdService(
            account_repository=repository,
            persistence=persistence,
            browser_actions=browser_actions,
            login_action=login_action,
            generate_token_action=token_action,
        )

        result = await service.execute(
            GenerateGithubTokenByAccountIdParams(github_account_id=101),
            keep_page_open=False,
        )

        self.assertEqual(repository.last_account_id, 101)
        self.assertEqual(browser_actions.start_calls, 1)
        self.assertEqual(browser_actions.browser.opened_urls, ["data:,"])
        self.assertEqual(login_action.calls[0]["email"], "demo@example.com")
        self.assertEqual(login_action.calls[0]["password"], "pwd-123")
        self.assertEqual(login_action.calls[0]["totp_secret"], "JBSWY3DPEHPK3PXP")
        self.assertEqual(token_action.calls[0]["totp_secret"], "JBSWY3DPEHPK3PXP")
        self.assertEqual(len(persistence.calls), 1)
        self.assertEqual(persistence.calls[0]["account_id"], 101)
        self.assertEqual(persistence.calls[0]["access_token"], "ghp_token_123")
        self.assertEqual(persistence.calls[0]["token_note"], "AutoToken_abcd")
        self.assertEqual(result["account_id"], 101)
        self.assertEqual(result["username"], "octocat")
        self.assertEqual(result["access_token"], "ghp_token_123")
        self.assertTrue(result["persisted_to_db"])

        await service.close()
        self.assertEqual(browser_actions.close_calls, 1)

    async def test_should_raise_when_account_not_found(self) -> None:
        service = GenerateGithubTokenByAccountIdService(
            account_repository=_FakeAccountRepository(record=None),
            persistence=_FakePersistence(),
            browser_actions=_FakeBrowserActions(),
            login_action=_FakeLoginAction({"ok": True, "step": "done"}),
            generate_token_action=_FakeGenerateTokenAction({"ok": True, "token": "ghp_x"}),
        )

        with self.assertRaisesRegex(ValueError, "账号不存在|已删除"):
            await service.execute(999, keep_page_open=False)
