"""把 ChatGPT 注册结果写入 `acc_chatgpt_base`。"""

from __future__ import annotations

from datetime import date

import asyncpg

from src.utils import AesTypeHandlerCompat


class ChatGptAccountPersistence:
    """负责把 worker 生成的 ChatGPT 账号落到业务表。"""

    DEFAULT_SUB_TIER = "free"
    DEFAULT_ACCOUNT_STATUS = "active"

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        encryptor: AesTypeHandlerCompat | None = None,
    ) -> None:
        self._pool = pool
        self._encryptor = encryptor or AesTypeHandlerCompat()

    async def create_account(
        self,
        *,
        email: str,
        password: str,
        session_token: str | None = None,
        totp_secret: str | None = None,
        sub_tier: str = DEFAULT_SUB_TIER,
        account_status: str = DEFAULT_ACCOUNT_STATUS,
        expire_date: date | None = None,
        created_by: int | None = None,
        updated_by: int | None = None,
    ) -> int:
        """
        插入一条 ChatGPT 账号记录。

        密码、session_token 和 totp_secret 按后端约定做 AES 加密后再写库。
        """

        normalized_email = email.strip().lower()
        normalized_password = password
        normalized_session_token = (session_token or "").strip() or None
        normalized_totp_secret = (totp_secret or "").strip() or None

        if not normalized_email:
            raise ValueError("email 不能为空")
        if not normalized_password:
            raise ValueError("password 不能为空")

        encrypted_password = self._encryptor.encrypt_base64(normalized_password)
        encrypted_session_token = (
            self._encryptor.encrypt_base64(normalized_session_token)
            if normalized_session_token is not None
            else None
        )
        encrypted_totp_secret = (
            self._encryptor.encrypt_base64(normalized_totp_secret)
            if normalized_totp_secret is not None
            else None
        )

        inserted_id = await self._pool.fetchval(
            """
            INSERT INTO acc_chatgpt_base (
                email,
                password,
                session_token,
                totp_secret,
                sub_tier,
                account_status,
                expire_date,
                created_by,
                updated_by,
                deleted,
                created_at,
                updated_at
            )
            VALUES (
                $1,
                $2,
                $3,
                $4,
                $5,
                $6,
                $7,
                $8,
                $9,
                0,
                now(),
                now()
            )
            RETURNING id
            """,
            normalized_email,
            encrypted_password,
            encrypted_session_token,
            encrypted_totp_secret,
            (sub_tier or self.DEFAULT_SUB_TIER).strip() or self.DEFAULT_SUB_TIER,
            (account_status or self.DEFAULT_ACCOUNT_STATUS).strip() or self.DEFAULT_ACCOUNT_STATUS,
            expire_date,
            created_by,
            updated_by,
        )
        if inserted_id is None:
            raise RuntimeError(f"插入 ChatGPT 账号失败: email={normalized_email}")
        return int(inserted_id)
