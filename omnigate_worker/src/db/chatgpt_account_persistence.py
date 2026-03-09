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

    async def email_exists(self, email: str) -> bool:
        """检查邮箱是否已经存在于 ChatGPT 账号表中。"""

        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValueError("email 不能为空")

        exists = await self._pool.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM acc_chatgpt_base
                WHERE email = $1
            )
            """,
            normalized_email,
        )
        return bool(exists)

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
        if await self.email_exists(normalized_email):
            raise ValueError(f"ChatGPT 账号邮箱已存在: {normalized_email}")

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

        try:
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
        except asyncpg.UniqueViolationError as exc:
            raise ValueError(f"ChatGPT 账号邮箱已存在: {normalized_email}") from exc
        except asyncpg.exceptions.StringDataRightTruncationError as exc:
            self._raise_session_token_too_long_error(exc)
        if inserted_id is None:
            raise RuntimeError(f"插入 ChatGPT 账号失败: email={normalized_email}")
        return int(inserted_id)

    async def update_session_token(
        self,
        *,
        account_id: int,
        session_token: str,
        updated_by: int | None = None,
    ) -> None:
        """更新指定 ChatGPT 账号的 session_token。"""

        normalized_session_token = (session_token or "").strip()
        if int(account_id) <= 0:
            raise ValueError("account_id 必须大于 0")
        if not normalized_session_token:
            raise ValueError("session_token 不能为空")

        encrypted_session_token = self._encryptor.encrypt_base64(normalized_session_token)
        try:
            command_tag = await self._pool.execute(
                """
                UPDATE acc_chatgpt_base
                SET session_token = $2,
                    updated_by = COALESCE($3, updated_by),
                    updated_at = now()
                WHERE id = $1
                  AND deleted = 0
                """,
                int(account_id),
                encrypted_session_token,
                updated_by,
            )
        except asyncpg.exceptions.StringDataRightTruncationError as exc:
            self._raise_session_token_too_long_error(exc)
        if command_tag == "UPDATE 0":
            raise ValueError(f"ChatGPT 账号不存在或已删除: account_id={account_id}")

    @staticmethod
    def _raise_session_token_too_long_error(exc: Exception) -> None:
        raise RuntimeError(
            "ChatGPT session_token 超出数据库字段长度。"
            "请先执行后端迁移 `V1.0.11__alter_chatgpt_session_token_to_text.sql`，"
            "将 `acc_chatgpt_base.session_token` 扩容为 TEXT。"
        ) from exc
