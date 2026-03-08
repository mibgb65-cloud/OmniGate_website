"""根据账号 ID 登录 GitHub 并为仓库点 Star。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

import asyncpg

from src.browser.browser_actions import BrowserActions
from src.db import GithubAccountPersistence, GithubAccountRepository
from src.modules.github.actions.github_login_action import GithubLoginAction
from src.modules.github.actions.github_star_repo_action import GithubStarRepoAction
from src.modules.github.models.github_entities import GithubRepoIdentity
from src.modules.github.models.github_service_params import StarGithubRepoByAccountIdParams
from src.modules.github.models.github_service_results import StarGithubRepoByAccountIdResult
from src.modules.github.services._base import GithubServiceBase


logger = logging.getLogger(__name__)


class StarGithubRepoByAccountIdService(GithubServiceBase):
    """服务流程：读取账号 -> 登录 GitHub -> Star 仓库 -> 记录交互表。"""

    _LOG_PREFIX = "[GitHub仓库Star]"

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        account_repository: GithubAccountRepository | None = None,
        persistence: GithubAccountPersistence | None = None,
        browser_actions: BrowserActions | None = None,
        login_action: GithubLoginAction | None = None,
        star_repo_action: GithubStarRepoAction | None = None,
    ) -> None:
        super().__init__(
            db_pool=db_pool,
            account_repository=account_repository,
            persistence=persistence,
            browser_actions=browser_actions,
        )
        self.login_action = login_action or GithubLoginAction()
        self.star_repo_action = star_repo_action or GithubStarRepoAction()

    async def execute(
        self,
        params: StarGithubRepoByAccountIdParams | dict[str, Any],
        *,
        keep_page_open: bool = True,
        max_wait_seconds: int | None = None,
        persist_to_db: bool = True,
    ) -> dict[str, Any]:
        action = "star_github_repo_by_account_id"
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
        repo = GithubRepoIdentity.from_url(req.repo_url)

        log_step(1, f"读取账号凭据 account_id={req.github_account_id} repo={repo.repo_full_name}")
        credential = await self._load_credential(req.github_account_id)
        logger.info(
            "%s 账号凭据读取完成 | trace_id=%s | username=%s | email=%s | repo=%s",
            self._LOG_PREFIX,
            trace_id,
            credential.username or "-",
            self._mask_email(credential.email),
            repo.repo_full_name,
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

        star_result: dict[str, Any] | None = None
        persisted_to_db = False
        if login_result.get("ok"):
            log_step(4, "执行 GitHub Star 动作")
            try:
                star_result = await self.star_repo_action.star_repo(page, repo.repo_url)
            except Exception as exc:  # noqa: BLE001
                logger.exception("%s GitHub Star 动作异常 | trace_id=%s", self._LOG_PREFIX, trace_id)
                star_result = {"ok": False, "step": "star_repo_exception", "reason": str(exc)}

            if persist_to_db and star_result and star_result.get("ok"):
                log_step(5, "写入仓库交互记录表")
                await self._persistence.upsert_repo_interaction(
                    account_id=credential.account_id,
                    repo_owner=repo.repo_owner,
                    repo_name=repo.repo_name,
                    repo_url=repo.repo_url,
                    starred=True,
                )
                persisted_to_db = True
        else:
            logger.warning("%s 登录未成功，跳过 Star 动作 | trace_id=%s", self._LOG_PREFIX, trace_id)

        result = StarGithubRepoByAccountIdResult(
            account_id=credential.account_id,
            username=credential.username or None,
            email=credential.email,
            trace_id=trace_id,
            repo_url=repo.repo_url,
            repo_owner=repo.repo_owner,
            repo_name=repo.repo_name,
            repo_full_name=repo.repo_full_name,
            login_result=login_result,
            star_result=star_result,
            persisted_to_db=persisted_to_db,
            browser_kept_open=keep_page_open,
        ).model_dump()

        if keep_page_open:
            log_step(6, "等待手动操作")
            await self._wait_for_manual_operation(max_wait_seconds=max_wait_seconds)
        else:
            log_step(6, "跳过手动等待（keep_page_open=false）")

        logger.info(
            "%s 服务流程完成 | 步骤=%s/%s | action=%s | trace_id=%s | account_id=%s | repo=%s | elapsed=%.2fs",
            self._LOG_PREFIX,
            total_steps,
            total_steps,
            action,
            trace_id,
            credential.account_id,
            repo.repo_full_name,
            elapsed_seconds(),
        )
        return result

    @staticmethod
    def _normalize_params(
        params: StarGithubRepoByAccountIdParams | dict[str, Any],
    ) -> StarGithubRepoByAccountIdParams:
        if isinstance(params, StarGithubRepoByAccountIdParams):
            return params
        if isinstance(params, dict):
            return StarGithubRepoByAccountIdParams.model_validate(params)
        raise TypeError("params must be StarGithubRepoByAccountIdParams or dict")
