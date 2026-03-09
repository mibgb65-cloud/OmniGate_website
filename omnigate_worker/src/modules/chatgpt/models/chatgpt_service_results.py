"""ChatGPT 相关 Service 返回结果模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatGptBatchRegisterItemResult(BaseModel):
    """单个账号注册结果。"""

    index: int
    email: str | None = None
    password: str | None = None
    name: str | None = None
    status: str
    msg: str | None = None
    persisted: bool = False
    account_id: int | None = None


class ChatGptBatchRegisterResult(BaseModel):
    """批量自动注册的汇总结果。"""

    requested_count: int
    success_count: int
    failed_count: int
    results: list[ChatGptBatchRegisterItemResult] = Field(default_factory=list)


class UpdateChatGptSessionByAccountIdResult(BaseModel):
    account_id: int
    email: str
    trace_id: str
    login_result: dict[str, Any]
    session_result: dict[str, Any] | None = None
    session_token: str | None = None
    persisted_to_db: bool = False
    browser_kept_open: bool = True
