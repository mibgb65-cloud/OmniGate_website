from __future__ import annotations

import asyncio
import base64
import binascii
import re
import time
from typing import TYPE_CHECKING, Any

from src.browser.browser_actions import BrowserActions
from src.db import ChatGptAccountPersistence, ChatGptAccountRepository
from src.modules.chatgpt.models import ChatGptAccountCredential
from src.utils import AesTypeHandlerCompat

if TYPE_CHECKING:
    import asyncpg


class ChatGptServiceBase:
    """ChatGPT 账号服务的公共依赖与辅助能力。"""

    def __init__(
        self,
        *,
        db_pool: "asyncpg.Pool | None" = None,
        account_repository: ChatGptAccountRepository | None = None,
        persistence: ChatGptAccountPersistence | None = None,
        browser_actions: BrowserActions | None = None,
    ) -> None:
        if account_repository is None:
            if db_pool is None:
                raise ValueError("db_pool or account_repository is required")
            account_repository = ChatGptAccountRepository(db_pool)
        if persistence is None:
            if db_pool is None:
                raise ValueError("db_pool or persistence is required")
            persistence = ChatGptAccountPersistence(db_pool)

        self._account_repository = account_repository
        self._persistence = persistence
        self.browser_actions = browser_actions or BrowserActions()
        self._last_browser: Any | None = None
        self._decryptor = AesTypeHandlerCompat()

    async def close_browser(self) -> None:
        if self._last_browser is not None:
            await self.browser_actions.close_browser()
            self._last_browser = None

    async def close(self) -> None:
        await self.close_browser()

    async def _start_browser_and_page(self) -> tuple[Any, Any]:
        browser = await self.browser_actions.start_browser()
        self._last_browser = browser
        page = await browser.get("data:,")
        return browser, page

    async def _load_credential(self, account_id: int) -> ChatGptAccountCredential:
        record = await self._account_repository.get_active_account_credential(account_id)
        if record is None:
            raise ValueError(f"ChatGPT 账号不存在或已删除: account_id={account_id}")

        encrypted_password = record.encrypted_password
        encrypted_totp = record.encrypted_totp_secret
        if not self._decryptor.is_backend_available():
            if self._looks_like_cipher_text(encrypted_password) or self._looks_like_cipher_text(encrypted_totp):
                raise RuntimeError(
                    "检测到数据库可能为 AES 密文，但当前环境缺少 pycryptodome，无法解密。"
                    "请先执行: pip install pycryptodome"
                )

        email = record.email
        password = str(self._decryptor.decrypt_safely(encrypted_password) or "")
        if not email:
            raise ValueError(f"ChatGPT 账号邮箱为空: account_id={account_id}")
        if not password:
            raise ValueError(f"ChatGPT 账号密码为空: account_id={account_id}")

        return ChatGptAccountCredential(
            account_id=record.account_id,
            email=email,
            password=password,
            totp_secret=str(self._decryptor.decrypt_safely(encrypted_totp) or "").strip(),
        )

    async def _wait_for_manual_operation(self, *, max_wait_seconds: int | None) -> None:
        start = time.monotonic()
        while True:
            if max_wait_seconds is not None and max_wait_seconds >= 0:
                elapsed = time.monotonic() - start
                if elapsed >= max_wait_seconds:
                    return
            await asyncio.sleep(0.5)

    @staticmethod
    def _looks_like_cipher_text(value: str) -> bool:
        raw = (value or "").strip()
        if len(raw) < 24 or len(raw) % 4 != 0:
            return False
        if not re.fullmatch(r"[A-Za-z0-9+/=]+", raw):
            return False
        if not any(ch in raw for ch in "+/=") and not any(ch.islower() for ch in raw):
            return False
        try:
            decoded = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError):
            return False
        if not decoded or len(decoded) % 16 != 0:
            return False
        return True

    @staticmethod
    def _mask_email(email: str) -> str:
        normalized = email.strip()
        if "@" not in normalized:
            return normalized

        local_part, domain = normalized.split("@", 1)
        if len(local_part) <= 4:
            masked_local = f"{local_part[:1]}***"
        else:
            masked_local = f"{local_part[:2]}***{local_part[-2:]}"
        return f"{masked_local}@{domain}"
