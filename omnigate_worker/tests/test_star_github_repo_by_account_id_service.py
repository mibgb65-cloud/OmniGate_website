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
from src.modules.github.models.github_service_params import StarGithubRepoByAccountIdParams
from src.modules.github.services.star_github_repo_by_account_id import StarGithubRepoByAccountIdService
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

    async def upsert_repo_interaction(
        self,
        *,
        account_id: int,
        repo_owner: str,
        repo_name: str,
        repo_url: str,
        starred: bool | None = None,
        forked: bool | None = None,
        watched: bool | None = None,
        followed: bool | None = None,
    ) -> None:
        self.calls.append(
            {
                "account_id": account_id,
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "repo_url": repo_url,
                "starred": starred,
                "forked": forked,
                "watched": watched,
                "followed": followed,
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


class _FakeStarRepoAction:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def star_repo(self, page: Any, repo_url: str) -> dict[str, Any]:
        self.calls.append({"page": page, "repo_url": repo_url})
        return dict(self.result)


class TestStarGithubRepoByAccountIdService(unittest.IsolatedAsyncioTestCase):
    async def test_should_login_star_repo_and_persist_interaction(self) -> None:
        decryptor = AesTypeHandlerCompat()
        if decryptor.is_backend_available():
            stored_password = decryptor.encrypt_base64("pwd-123")
            stored_totp = decryptor.encrypt_base64("JBSWY3DPEHPK3PXP")
        else:
            stored_password = "pwd-123"
            stored_totp = "JBSWY3DPEHPK3PXP"

        repository = _FakeAccountRepository(
            GithubAccountCredentialRecord(
                account_id=7,
                username="octocat",
                email="demo@example.com",
                encrypted_password=stored_password,
                encrypted_totp_secret=stored_totp,
            )
        )
        persistence = _FakePersistence()
        browser_actions = _FakeBrowserActions()
        login_action = _FakeLoginAction({"ok": True, "step": "done"})
        star_action = _FakeStarRepoAction({"ok": True, "step": "done", "message": "already starred"})
        service = StarGithubRepoByAccountIdService(
            account_repository=repository,
            persistence=persistence,
            browser_actions=browser_actions,
            login_action=login_action,
            star_repo_action=star_action,
        )

        result = await service.execute(
            StarGithubRepoByAccountIdParams(
                github_account_id=7,
                repo_url="https://github.com/openai/openai-python/tree/main?tab=readme",
            ),
            keep_page_open=False,
        )

        self.assertEqual(repository.last_account_id, 7)
        self.assertEqual(browser_actions.start_calls, 1)
        self.assertEqual(browser_actions.browser.opened_urls, ["data:,"])
        self.assertEqual(login_action.calls[0]["email"], "demo@example.com")
        self.assertEqual(login_action.calls[0]["password"], "pwd-123")
        self.assertEqual(login_action.calls[0]["totp_secret"], "JBSWY3DPEHPK3PXP")
        self.assertEqual(star_action.calls[0]["repo_url"], "https://github.com/openai/openai-python")
        self.assertEqual(len(persistence.calls), 1)
        self.assertEqual(persistence.calls[0]["account_id"], 7)
        self.assertEqual(persistence.calls[0]["repo_owner"], "openai")
        self.assertEqual(persistence.calls[0]["repo_name"], "openai-python")
        self.assertEqual(persistence.calls[0]["repo_url"], "https://github.com/openai/openai-python")
        self.assertTrue(persistence.calls[0]["starred"])
        self.assertEqual(result["repo_full_name"], "openai/openai-python")
        self.assertTrue(result["persisted_to_db"])

        await service.close()
        self.assertEqual(browser_actions.close_calls, 1)

    async def test_should_raise_for_invalid_repo_url(self) -> None:
        service = StarGithubRepoByAccountIdService(
            account_repository=_FakeAccountRepository(record=None),
            persistence=_FakePersistence(),
            browser_actions=_FakeBrowserActions(),
            login_action=_FakeLoginAction({"ok": True, "step": "done"}),
            star_repo_action=_FakeStarRepoAction({"ok": True, "step": "done"}),
        )

        with self.assertRaisesRegex(ValueError, "GitHub 仓库地址|owner/repo"):
            await service.execute(
                {"github_account_id": 1, "repo_url": "https://example.com/openai/openai-python"},
                keep_page_open=False,
            )
