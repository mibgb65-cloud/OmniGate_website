"""根据账号 ID 登录 ChatGPT 并刷新 session_token。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

import asyncpg

from src.browser.browser_actions import BrowserActions
from src.db import ChatGptAccountPersistence, ChatGptAccountRepository
from src.modules.chatgpt.actions.chatgpt_session_action import ChatGPTGetSessionAction
from src.modules.chatgpt.actions.chatgpt_signin_action import ChatGPTLoginAction
from src.modules.chatgpt.models.chatgpt_service_params import UpdateChatGptSessionByAccountIdParams
from src.modules.chatgpt.models.chatgpt_service_results import UpdateChatGptSessionByAccountIdResult
from src.modules.chatgpt.services._base import ChatGptServiceBase


logger = logging.getLogger(__name__)


class UpdateChatGptSessionByAccountIdService(ChatGptServiceBase):
    """服务流程：读取账号 -> 登录 ChatGPT -> 获取 Session -> 写回数据库。"""

    _LOG_PREFIX = "[ChatGPT更新Session]"

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        account_repository: ChatGptAccountRepository | None = None,
        persistence: ChatGptAccountPersistence | None = None,
        browser_actions: BrowserActions | None = None,
        login_action: ChatGPTLoginAction | None = None,
        session_action: ChatGPTGetSessionAction | None = None,
    ) -> None:
        super().__init__(
            db_pool=db_pool,
            account_repository=account_repository,
            persistence=persistence,
            browser_actions=browser_actions,
        )
        self.login_action = login_action or ChatGPTLoginAction()
        self.session_action = session_action or ChatGPTGetSessionAction()

    async def execute(
        self,
        params: UpdateChatGptSessionByAccountIdParams | int,
        *,
        keep_page_open: bool = True,
        max_wait_seconds: int | None = None,
        persist_to_db: bool = True,
    ) -> dict[str, Any]:
        action = "update_chatgpt_session_by_account_id"
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
        log_step(1, f"读取账号凭据 account_id={req.chatgpt_account_id}")
        credential = await self._load_credential(req.chatgpt_account_id)
        logger.info(
            "%s 账号凭据读取完成 | trace_id=%s | email=%s",
            self._LOG_PREFIX,
            trace_id,
            self._mask_email(credential.email),
        )

        log_step(2, "启动浏览器")
        _, page = await self._start_browser_and_page()

        log_step(3, "执行 ChatGPT 登录")
        try:
            login_result = await self.login_action.login(
                page,
                credential.email,
                credential.password,
                credential.totp_secret or None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s ChatGPT 登录动作异常 | trace_id=%s", self._LOG_PREFIX, trace_id)
            login_result = {"ok": False, "step": "login_exception", "reason": str(exc)}

        session_result: dict[str, Any] | None = None
        session_token: str | None = None
        persisted_to_db = False

        if login_result.get("ok"):
            log_step(4, "提取 ChatGPT Session")
            try:
                session_result = await self.session_action.get_session(page)
            except Exception as exc:  # noqa: BLE001
                logger.exception("%s ChatGPT Session 动作异常 | trace_id=%s", self._LOG_PREFIX, trace_id)
                session_result = {"ok": False, "step": "get_session_exception", "reason": str(exc)}

            if isinstance(session_result, dict):
                session_data = session_result.get("data")
                if isinstance(session_data, dict):
                    session_token = str(session_data.get("accessToken") or "").strip() or None

            if persist_to_db and session_result and session_result.get("ok") and session_token:
                log_step(5, "写回 session_token 到数据库")
                await self._persistence.update_session_token(
                    account_id=credential.account_id,
                    session_token=session_token,
                )
                persisted_to_db = True
            elif persist_to_db and session_result and session_result.get("ok"):
                logger.warning("%s Session 返回成功但缺少 accessToken，跳过数据库写回 | trace_id=%s", self._LOG_PREFIX, trace_id)
        else:
            logger.warning(
                "%s 登录未成功，跳过 Session 提取 | trace_id=%s | step=%s | reason=%s",
                self._LOG_PREFIX,
                trace_id,
                login_result.get("step"),
                login_result.get("reason"),
            )

        result = UpdateChatGptSessionByAccountIdResult(
            account_id=credential.account_id,
            email=credential.email,
            trace_id=trace_id,
            login_result=login_result,
            session_result=session_result,
            session_token=session_token,
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
        params: UpdateChatGptSessionByAccountIdParams | int,
    ) -> UpdateChatGptSessionByAccountIdParams:
        if isinstance(params, UpdateChatGptSessionByAccountIdParams):
            return params
        return UpdateChatGptSessionByAccountIdParams(chatgpt_account_id=int(params))
