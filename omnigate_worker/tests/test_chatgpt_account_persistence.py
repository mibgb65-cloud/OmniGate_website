from __future__ import annotations

import unittest
from typing import Any

import asyncpg

from src.db.chatgpt_account_persistence import ChatGptAccountPersistence


class _FakeEncryptor:
    def encrypt_base64(self, plain_text: str) -> str:
        return f"enc:{plain_text}"


class _FakePool:
    def __init__(
        self,
        *,
        exists_values: list[bool],
        insert_result: int | None = 1,
        fetchval_error: Exception | None = None,
        execute_error: Exception | None = None,
    ) -> None:
        self._exists_values = list(exists_values)
        self._insert_result = insert_result
        self._fetchval_error = fetchval_error
        self._execute_error = execute_error
        self.fetchval_calls: list[tuple[str, tuple[Any, ...]]] = []
        self.execute_calls: list[tuple[str, tuple[Any, ...]]] = []
        self.execute_result = "UPDATE 1"

    async def fetchval(self, query: str, *args: Any) -> Any:
        self.fetchval_calls.append((query, args))
        if "SELECT EXISTS" in query:
            if not self._exists_values:
                raise AssertionError("missing exists_values for SELECT EXISTS")
            return self._exists_values.pop(0)
        if self._fetchval_error is not None:
            raise self._fetchval_error
        return self._insert_result

    async def execute(self, query: str, *args: Any) -> str:
        self.execute_calls.append((query, args))
        if self._execute_error is not None:
            raise self._execute_error
        return self.execute_result


class TestChatGptAccountPersistence(unittest.IsolatedAsyncioTestCase):
    async def test_should_raise_when_email_already_exists_before_insert(self) -> None:
        pool = _FakePool(exists_values=[True])
        persistence = ChatGptAccountPersistence(pool, encryptor=_FakeEncryptor())

        with self.assertRaisesRegex(ValueError, "ChatGPT 账号邮箱已存在"):
            await persistence.create_account(email="Demo@Example.com", password="pwd-123456")

        self.assertEqual(1, len(pool.fetchval_calls))
        self.assertIn("SELECT EXISTS", pool.fetchval_calls[0][0])
        self.assertEqual(("demo@example.com",), pool.fetchval_calls[0][1])

    async def test_should_insert_when_email_does_not_exist(self) -> None:
        pool = _FakePool(exists_values=[False], insert_result=101)
        persistence = ChatGptAccountPersistence(pool, encryptor=_FakeEncryptor())

        inserted_id = await persistence.create_account(email="Demo@Example.com", password="pwd-123456")

        self.assertEqual(101, inserted_id)
        self.assertEqual(2, len(pool.fetchval_calls))
        self.assertIn("SELECT EXISTS", pool.fetchval_calls[0][0])
        self.assertIn("INSERT INTO acc_chatgpt_base", pool.fetchval_calls[1][0])
        self.assertEqual("demo@example.com", pool.fetchval_calls[1][1][0])

    async def test_should_update_session_token(self) -> None:
        pool = _FakePool(exists_values=[])
        persistence = ChatGptAccountPersistence(pool, encryptor=_FakeEncryptor())

        await persistence.update_session_token(account_id=5, session_token="sess_abc123")

        self.assertEqual(1, len(pool.execute_calls))
        self.assertIn("UPDATE acc_chatgpt_base", pool.execute_calls[0][0])
        self.assertEqual((5, "enc:sess_abc123", None), pool.execute_calls[0][1])

    async def test_should_raise_clear_error_when_insert_session_token_exceeds_column_length(self) -> None:
        pool = _FakePool(
            exists_values=[False],
            fetchval_error=asyncpg.exceptions.StringDataRightTruncationError("too long"),
        )
        persistence = ChatGptAccountPersistence(pool, encryptor=_FakeEncryptor())

        with self.assertRaisesRegex(RuntimeError, "session_token 超出数据库字段长度"):
            await persistence.create_account(
                email="Demo@Example.com",
                password="pwd-123456",
                session_token="x" * 2048,
            )

    async def test_should_raise_clear_error_when_update_session_token_exceeds_column_length(self) -> None:
        pool = _FakePool(
            exists_values=[],
            execute_error=asyncpg.exceptions.StringDataRightTruncationError("too long"),
        )
        persistence = ChatGptAccountPersistence(pool, encryptor=_FakeEncryptor())

        with self.assertRaisesRegex(RuntimeError, "session_token 超出数据库字段长度"):
            await persistence.update_session_token(account_id=5, session_token="x" * 2048)
