"""根据账号 ID 登录 GitHub 并生成 PAT。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

import asyncpg

from src.browser.browser_actions import BrowserActions
from src.db import GithubAccountPersistence, GithubAccountRepository
from src.modules.github.actions.github_generate_token_action import GithubGenerateTokenAction
from src.modules.github.actions.github_login_action import GithubLoginAction
from src.modules.github.models.github_service_params import GenerateGithubTokenByAccountIdParams
from src.modules.github.models.github_service_results import GenerateGithubTokenByAccountIdResult
from src.modules.github.services._base import GithubServiceBase


logger = logging.getLogger(__name__)


class GenerateGithubTokenByAccountIdService(GithubServiceBase):
    """服务流程：读取账号 -> 登录 GitHub -> 生成 Token -> 写回数据库。"""

    _LOG_PREFIX = "[GitHub生成Token]"

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        account_repository: GithubAccountRepository | None = None,
        persistence: GithubAccountPersistence | None = None,
        browser_actions: BrowserActions | None = None,
        login_action: GithubLoginAction | None = None,
        generate_token_action: GithubGenerateTokenAction | None = None,
    ) -> None:
        super().__init__(
            db_pool=db_pool,
            account_repository=account_repository,
            persistence=persistence,
            browser_actions=browser_actions,
        )
        self.login_action = login_action or GithubLoginAction()
        self.generate_token_action = generate_token_action or GithubGenerateTokenAction()

    async def execute(
        self,
        params: GenerateGithubTokenByAccountIdParams | int,
        *,
        keep_page_open: bool = True,
        max_wait_seconds: int | None = None,
        persist_to_db: bool = True,
    ) -> dict[str, Any]:
        action = "generate_github_token_by_account_id"
        trace_id = uuid4().hex[:12]
        total_steps = 6
        started_at = time.monotonic()

        def elapsed_seconds() -> float:
            return round(time.monotonic() - started_at, 2)

        def log_step(step_no: int, title: str) -> None:
            logger.info(
                "%s 步骤=%s/%s | action=%s | trace_id=%s | %s",
                self._LOG_PREFIX,
                step_no,
                total_steps,
                action,
                trace_id,
                title,
            )

        req = self._normalize_params(params)
        log_step(1, f"读取账号凭据 account_id={req.github_account_id}")
        credential = await self._load_credential(req.github_account_id)
        logger.info(
            "%s 账号凭据读取完成 | trace_id=%s | username=%s | email=%s",
            self._LOG_PREFIX,
            trace_id,
            credential.username or "-",
            self._mask_email(credential.email),
        )

        log_step(2, "启动浏览器")
        _, page = await self._start_browser_and_page()

        log_step(3, "执行 GitHub 登录")
        try:
            login_result = await self.login_action.login_github(
                page,
                credential.email,
                credential.password,
                credential.totp_secret or None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s GitHub 登录动作异常 | trace_id=%s", self._LOG_PREFIX, trace_id)
            login_result = {"ok": False, "step": "login_exception", "reason": str(exc)}

        token_result: dict[str, Any] | None = None
        access_token: str | None = None
        access_token_note: str | None = None
        persisted_to_db = False

        if login_result.get("ok"):
            log_step(4, "生成 GitHub Token")
            try:
                token_result = await self.generate_token_action.generate_token(page, credential.totp_secret or "")
            except Exception as exc:  # noqa: BLE001
                logger.exception("%s GitHub Token 动作异常 | trace_id=%s", self._LOG_PREFIX, trace_id)
                token_result = {"ok": False, "step": "generate_token_exception", "reason": str(exc)}

            if isinstance(token_result, dict):
                access_token = str(token_result.get("token") or "") or None
                access_token_note = str(token_result.get("note") or "") or None

            if persist_to_db and token_result and token_result.get("ok") and access_token:
                log_step(5, "写回 GitHub Token 到数据库")
                await self._persistence.update_access_token(
                    account_id=credential.account_id,
                    access_token=access_token,
                    token_note=access_token_note,
                )
                persisted_to_db = True
        else:
            logger.warning("%s 登录未成功，跳过 Token 生成 | trace_id=%s", self._LOG_PREFIX, trace_id)

        result = GenerateGithubTokenByAccountIdResult(
            account_id=credential.account_id,
            username=credential.username or None,
            email=credential.email,
            trace_id=trace_id,
            login_result=login_result,
            token_result=token_result,
            access_token=access_token,
            access_token_note=access_token_note,
            persisted_to_db=persisted_to_db,
            browser_kept_open=keep_page_open,
        ).model_dump()

        if keep_page_open:
            log_step(6, "等待手动操作")
            await self._wait_for_manual_operation(max_wait_seconds=max_wait_seconds)
        else:
            log_step(6, "跳过手动等待（keep_page_open=false）")

        logger.info(
            "%s 服务流程完成 | 步骤=%s/%s | action=%s | trace_id=%s | account_id=%s | elapsed=%.2fs",
            self._LOG_PREFIX,
            total_steps,
            total_steps,
            action,
            trace_id,
            credential.account_id,
            elapsed_seconds(),
        )
        return result

    @staticmethod
    def _normalize_params(
        params: GenerateGithubTokenByAccountIdParams | int,
    ) -> GenerateGithubTokenByAccountIdParams:
        if isinstance(params, GenerateGithubTokenByAccountIdParams):
            return params
        return GenerateGithubTokenByAccountIdParams(github_account_id=int(params))
