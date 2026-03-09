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

from src.db.chatgpt_account_repository import ChatGptAccountRepository


class _FakePool:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row
        self.fetchrow_calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        self.fetchrow_calls.append((query, args))
        return self.row


class TestChatGptAccountRepository(unittest.IsolatedAsyncioTestCase):
    async def test_should_return_active_account_credential_record(self) -> None:
        pool = _FakePool(
            {
                "id": 88,
                "email": "Demo@Example.com ",
                "password": "enc:pwd",
                "totp_secret": "enc:totp",
            }
        )
        repository = ChatGptAccountRepository(pool)

        result = await repository.get_active_account_credential(88)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(88, result.account_id)
        self.assertEqual("demo@example.com", result.email)
        self.assertEqual("enc:pwd", result.encrypted_password)
        self.assertEqual("enc:totp", result.encrypted_totp_secret)
        self.assertIn("FROM acc_chatgpt_base", pool.fetchrow_calls[0][0])
        self.assertEqual((88,), pool.fetchrow_calls[0][1])

    async def test_should_return_none_when_account_not_found(self) -> None:
        repository = ChatGptAccountRepository(_FakePool(None))

        result = await repository.get_active_account_credential(999)

        self.assertIsNone(result)
