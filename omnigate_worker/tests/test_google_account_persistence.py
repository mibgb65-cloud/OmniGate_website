from __future__ import annotations

import unittest
from typing import Any

from src.db.google_account_persistence import GoogleAccountPersistence


class _FakeTransaction:
    async def __aenter__(self) -> "_FakeTransaction":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeConnection:
    def __init__(self) -> None:
        self.execute_calls: list[tuple[str, tuple[Any, ...]]] = []
        self.executemany_calls: list[tuple[str, list[tuple[Any, ...]]]] = []

    async def execute(self, query: str, *args: Any) -> str:
        self.execute_calls.append((query, args))
        return "OK"

    async def executemany(self, query: str, args: list[tuple[Any, ...]]) -> str:
        self.executemany_calls.append((query, list(args)))
        return "OK"

    def transaction(self) -> _FakeTransaction:
        return _FakeTransaction()


class _FakeAcquire:
    def __init__(self, conn: _FakeConnection) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeConnection:
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakePool:
    def __init__(self, conn: _FakeConnection) -> None:
        self._conn = conn

    def acquire(self) -> _FakeAcquire:
        return _FakeAcquire(self._conn)


class TestGoogleAccountPersistence(unittest.IsolatedAsyncioTestCase):
    async def test_should_dedupe_family_members_by_email_before_insert(self) -> None:
        conn = _FakeConnection()
        persistence = GoogleAccountPersistence(_FakePool(conn))

        await persistence.persist_feature_snapshot(
            account_id=11,
            subscription_and_invite=None,
            family_status={
                "family_group_opened": True,
                "member_count": 2,
                "members": [
                    {
                        "member_name": "Pang Yiyun",
                        "member_email": "pangyiyun08@gmail.com",
                        "invite_date": "2026-03-01",
                        "member_role": "member",
                    },
                    {
                        "member_name": "Pang Yiyun Duplicate",
                        "member_email": "PANGYIYUN08@gmail.com",
                        "invite_date": "2026-03-02",
                        "member_role": "manager",
                    },
                ],
            },
        )

        self.assertEqual(1, len(conn.executemany_calls))
        inserted_rows = conn.executemany_calls[0][1]
        self.assertEqual(1, len(inserted_rows))
        self.assertEqual(11, inserted_rows[0][0])
        self.assertEqual("pangyiyun08@gmail.com", inserted_rows[0][2])
