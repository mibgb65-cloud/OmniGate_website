from __future__ import annotations

from dataclasses import dataclass

import asyncpg


@dataclass(slots=True)
class GoogleAccountCredentialRecord:
    """从 `acc_google_base` 读出的最小登录凭据集合。"""

    account_id: int
    email: str
    encrypted_password: str
    encrypted_totp_secret: str


class GoogleAccountRepository:
    """负责读取 Google 账号基础信息，不处理解密和业务判断。"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_active_account_credential(self, account_id: int) -> GoogleAccountCredentialRecord | None:
        """
        读取一个未删除的 Google 账号登录凭据。

        返回值是一个 dataclass，调用方后续再决定是否解密密码和 TOTP。
        """

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

        # 这里统一做基础归一化，避免上层每次都处理空字符串和类型转换。
        return GoogleAccountCredentialRecord(
            account_id=int(row["id"]),
            email=str(row["email"] or "").strip(),
            encrypted_password=str(row["password"] or ""),
            encrypted_totp_secret=str(row["totp_secret"] or ""),
        )
