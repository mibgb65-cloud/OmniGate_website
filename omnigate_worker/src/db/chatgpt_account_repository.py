from __future__ import annotations

from dataclasses import dataclass

import asyncpg


@dataclass(slots=True)
class ChatGptAccountCredentialRecord:
    """从 `acc_chatgpt_base` 读出的最小登录凭据集合。"""

    account_id: int
    email: str
    encrypted_password: str
    encrypted_totp_secret: str


class ChatGptAccountRepository:
    """负责读取 ChatGPT 账号基础信息，不处理解密和业务判断。"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_active_account_credential(self, account_id: int) -> ChatGptAccountCredentialRecord | None:
        """读取一个未删除的 ChatGPT 账号登录凭据。"""

        query = """
            SELECT id, email, password, COALESCE(totp_secret, '') AS totp_secret
            FROM acc_chatgpt_base
            WHERE id = $1
              AND deleted = 0
            LIMIT 1
        """
        row = await self._pool.fetchrow(query, account_id)
        if row is None:
            return None

        return ChatGptAccountCredentialRecord(
            account_id=int(row["id"]),
            email=str(row["email"] or "").strip().lower(),
            encrypted_password=str(row["password"] or ""),
            encrypted_totp_secret=str(row["totp_secret"] or ""),
        )
