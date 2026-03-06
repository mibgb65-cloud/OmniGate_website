from __future__ import annotations

from dataclasses import dataclass

import asyncpg


@dataclass(slots=True)
class GoogleAccountCredentialRecord:
    account_id: int
    email: str
    encrypted_password: str
    encrypted_totp_secret: str


class GoogleAccountRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_active_account_credential(self, account_id: int) -> GoogleAccountCredentialRecord | None:
        query = """
            SELECT id, email, password, COALESCE(totp_secret, '') AS totp_secret
            FROM acc_google_base
            WHERE id = $1
              AND deleted = 0
            LIMIT 1
        """
        row = await self._pool.fetchrow(query, account_id)
        if row is None:
            return None

        return GoogleAccountCredentialRecord(
            account_id=int(row["id"]),
            email=str(row["email"] or "").strip(),
            encrypted_password=str(row["password"] or ""),
            encrypted_totp_secret=str(row["totp_secret"] or ""),
        )
