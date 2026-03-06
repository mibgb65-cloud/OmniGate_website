from __future__ import annotations

import unittest
from typing import Any

from src.modules.google.models.google_service_params import GetGoogleAccountFeatureByAccountIdParams
from src.modules.google.services.get_google_account_feature_by_account_id import (
    GetGoogleAccountFeatureByAccountIdService,
)
from src.utils import AesTypeHandlerCompat


class _FakePool:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row
        self.last_account_id: int | None = None

    async def fetchrow(self, _query: str, account_id: int) -> dict[str, Any] | None:
        self.last_account_id = account_id
        if self.row is None:
            return None
        if int(self.row["id"]) != int(account_id):
            return None
        return self.row


class _FakeBrowserActions:
    def __init__(self) -> None:
        self.start_calls = 0
        self.close_calls = 0
        self.browser_obj = object()

    async def start_browser(self) -> Any:
        self.start_calls += 1
        return self.browser_obj

    async def close_browser(self) -> None:
        self.close_calls += 1


class _FakeAuthActions:
    def __init__(self) -> None:
        self.calls = 0
        self.last_browser: Any | None = None
        self.last_params: Any | None = None

    async def login_google(self, browser: Any, params: Any) -> dict[str, Any]:
        self.calls += 1
        self.last_browser = browser
        self.last_params = params
        return {"ok": True, "step": "done", "page": object()}


class TestGetGoogleAccountFeatureByAccountIdService(unittest.IsolatedAsyncioTestCase):
    async def test_should_load_account_and_call_google_auth(self) -> None:
        decryptor = AesTypeHandlerCompat()
        if decryptor.is_backend_available():
            stored_password = decryptor.encrypt_base64("pwd-123")
            stored_totp = decryptor.encrypt_base64("JBSWY3DPEHPK3PXP")
        else:
            stored_password = "pwd-123"
            stored_totp = "JBSWY3DPEHPK3PXP"

        fake_pool = _FakePool(
            row={
                "id": 101,
                "email": "demo@gmail.com",
                "password": stored_password,
                "totp_secret": stored_totp,
            }
        )
        fake_browser = _FakeBrowserActions()
        fake_auth = _FakeAuthActions()
        service = GetGoogleAccountFeatureByAccountIdService(
            db_pool=fake_pool,
            browser_actions=fake_browser,
            auth_actions=fake_auth,
        )

        result = await service.execute(
            GetGoogleAccountFeatureByAccountIdParams(google_account_id=101),
            keep_page_open=True,
            max_wait_seconds=0,
            collect_features=False,
        )

        self.assertEqual(fake_pool.last_account_id, 101)
        self.assertEqual(fake_browser.start_calls, 1)
        self.assertEqual(fake_browser.close_calls, 0)
        self.assertEqual(fake_auth.calls, 1)
        self.assertEqual(getattr(fake_auth.last_params, "google_account"), "demo@gmail.com")
        self.assertEqual(getattr(fake_auth.last_params, "password"), "pwd-123")
        self.assertEqual(getattr(fake_auth.last_params, "twofa"), "JBSWY3DPEHPK3PXP")
        self.assertEqual(result["account_id"], 101)
        self.assertTrue(result["browser_kept_open"])
        self.assertTrue(result["login_result"]["ok"])

        await service.close_browser()
        self.assertEqual(fake_browser.close_calls, 1)

    async def test_should_raise_when_account_not_found(self) -> None:
        service = GetGoogleAccountFeatureByAccountIdService(
            db_pool=_FakePool(row=None),
            browser_actions=_FakeBrowserActions(),
            auth_actions=_FakeAuthActions(),
        )

        with self.assertRaisesRegex(ValueError, "账号不存在|已删除"):
            await service.execute(999, keep_page_open=False, collect_features=False)
