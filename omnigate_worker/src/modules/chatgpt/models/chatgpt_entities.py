from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ChatGptAccountCredential:
    """ChatGPT 登录所需的已解密账号实体。"""

    account_id: int
    email: str
    password: str
    totp_secret: str
