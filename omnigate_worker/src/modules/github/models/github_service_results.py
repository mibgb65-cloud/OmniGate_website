"""GitHub 相关 Service 出参模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateGithubTokenByAccountIdResult(BaseModel):
    account_id: int
    username: str | None = None
    email: str
    trace_id: str
    login_result: dict[str, Any]
    token_result: dict[str, Any] | None = None
    access_token: str | None = None
    access_token_note: str | None = None
    persisted_to_db: bool = False
    browser_kept_open: bool = True


class StarGithubRepoByAccountIdResult(BaseModel):
    account_id: int
    username: str | None = None
    email: str
    trace_id: str
    repo_url: str
    repo_owner: str
    repo_name: str
    repo_full_name: str
    login_result: dict[str, Any]
    star_result: dict[str, Any] | None = None
    persisted_to_db: bool = False
    browser_kept_open: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)
