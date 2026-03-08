"""串行批量注册 ChatGPT 账号。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import asyncpg

from src.browser.browser_actions import BrowserActions
from src.config.config import get_settings
from src.db import ChatGptAccountPersistence
from src.modules.chatgpt.models import (
    BatchRegisterChatGptAccountsParams,
    ChatGptBatchRegisterItemResult,
    ChatGptBatchRegisterResult,
)

if TYPE_CHECKING:
    from src.modules.chatgpt.actions.chatgpt_signup_action import OpenAISignupService


logger = logging.getLogger(__name__)


class RetryableChatGptSignupError(RuntimeError):
    """适合交给 worker 进行整任务重试的可恢复异常。"""


class BatchRegisterChatGptAccountsService:
    """按顺序批量注册并持久化 ChatGPT 账号，每个账号使用独立浏览器实例。"""

    _LOG_PREFIX = "[ChatGPT批量注册]"
    _PERSISTABLE_STATUSES = {"REGISTERED_SUCCESS"}
    _RETRYABLE_STATUSES = {"OPEN_PAGE_TIMEOUT"}

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        browser_actions: BrowserActions | None = None,
        signup_action: "OpenAISignupService | None" = None,
        account_persistence: ChatGptAccountPersistence | None = None,
        chatgpt_home_open_max_retries: int | None = None,
    ) -> None:
        if db_pool is None and (signup_action is None or account_persistence is None):
            raise ValueError("db_pool or explicit dependencies are required")

        settings = get_settings()
        self._browser_actions = browser_actions or BrowserActions()
        if signup_action is None:
            from src.modules.chatgpt.actions.chatgpt_signup_action import OpenAISignupService

            signup_action = OpenAISignupService(
                db_pool=db_pool,
                actions=self._browser_actions,
            )
        self._signup_action = signup_action
        self._account_persistence = account_persistence or ChatGptAccountPersistence(db_pool)  # type: ignore[arg-type]
        resolved_max_retries = (
            chatgpt_home_open_max_retries
            if chatgpt_home_open_max_retries is not None
            else settings.CHATGPT_HOME_OPEN_MAX_RETRIES
        )
        self._chatgpt_home_open_max_retries = max(0, int(resolved_max_retries))

    async def execute(
        self,
        params: BatchRegisterChatGptAccountsParams | int,
    ) -> ChatGptBatchRegisterResult:
        """按数量顺序执行注册；前一个完成后才开始下一个。"""

        request = self._normalize_params(params)
        results: list[ChatGptBatchRegisterItemResult] = []
        success_count = 0

        logger.info("%s 批次开始 | 请求数量=%s", self._LOG_PREFIX, request.signup_count)
        for index in range(1, request.signup_count + 1):
            logger.info(
                "%s 开始处理账号 | 进度=%s/%s",
                self._LOG_PREFIX,
                index,
                request.signup_count,
            )
            signup_result: dict[str, Any] | None = None
            try:
                signup_result = await self._run_single_account(
                    index=index,
                    total=request.signup_count,
                )
                persisted = False
                account_id: int | None = None
                status = str(signup_result.get("status") or "UNKNOWN")
                if status in self._RETRYABLE_STATUSES and success_count == 0:
                    message = str(signup_result.get("msg") or "打开 ChatGPT 首页连续超时")
                    raise RetryableChatGptSignupError(message)
                if self._should_persist(status):
                    account_id = await self._account_persistence.create_account(
                        email=str(signup_result.get("email") or ""),
                        password=str(signup_result.get("password") or ""),
                        totp_secret=str(signup_result.get("totp_secret") or "") or None,
                    )
                    persisted = True
                    success_count += 1

                logger.info(
                    "%s 单个账号处理完成 | 进度=%s/%s | 状态=%s | 持久化=%s | 邮箱=%s",
                    self._LOG_PREFIX,
                    index,
                    request.signup_count,
                    status,
                    persisted,
                    self._mask_email(str(signup_result.get("email") or "")),
                )
                results.append(
                    self._build_item_result(
                        index=index,
                        signup_result=signup_result,
                        persisted=persisted,
                        account_id=account_id,
                    )
                )
            except RetryableChatGptSignupError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "%s 单个账号处理失败 | 进度=%s/%s",
                    self._LOG_PREFIX,
                    index,
                    request.signup_count,
                )
                results.append(
                    self._build_item_result(
                        index=index,
                        signup_result=signup_result,
                        persisted=False,
                        account_id=None,
                        override_status="FAILED",
                        override_msg=str(exc),
                    )
                )

        result = ChatGptBatchRegisterResult(
            requested_count=request.signup_count,
            success_count=success_count,
            failed_count=request.signup_count - success_count,
            results=results,
        )
        logger.info(
            "%s 批次完成 | 请求数量=%s | 成功=%s | 失败=%s",
            self._LOG_PREFIX,
            result.requested_count,
            result.success_count,
            result.failed_count,
        )
        return result

    async def _run_single_account(
        self,
        *,
        index: int,
        total: int,
    ) -> dict[str, Any]:
        browser = await self._browser_actions.start_browser()
        logger.info(
            "%s 当前账号浏览器已启动 | 进度=%s/%s",
            self._LOG_PREFIX,
            index,
            total,
        )
        try:
            _, signup_result = await self._process_account_with_retry(
                browser=browser,
                index=index,
                total=total,
            )
            return signup_result
        finally:
            await self._browser_actions.close_browser()
            logger.info(
                "%s 当前账号浏览器已关闭 | 进度=%s/%s",
                self._LOG_PREFIX,
                index,
                total,
            )

    async def _process_account_with_retry(
        self,
        *,
        browser: Any,
        index: int,
        total: int,
    ) -> tuple[Any, dict[str, Any]]:
        max_attempts = self._chatgpt_home_open_max_retries + 1

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                logger.info(
                    "%s 当前账号开始重试 | 进度=%s/%s | 尝试=%s/%s",
                    self._LOG_PREFIX,
                    index,
                    total,
                    attempt,
                    max_attempts,
                )

            signup_result = await self._signup_action.process_account_with_browser(browser)
            status = str(signup_result.get("status") or "UNKNOWN")
            if status not in self._RETRYABLE_STATUSES:
                return browser, signup_result

            logger.warning(
                "%s 当前账号首页打开失败 | 进度=%s/%s | 尝试=%s/%s | 状态=%s | 原因=%s",
                self._LOG_PREFIX,
                index,
                total,
                attempt,
                max_attempts,
                status,
                str(signup_result.get("msg") or "-"),
            )
            if attempt >= max_attempts:
                return browser, signup_result

            await self._browser_actions.close_browser()
            browser = await self._browser_actions.start_browser()

        raise RuntimeError("unreachable")

    @staticmethod
    def _normalize_params(
        params: BatchRegisterChatGptAccountsParams | int,
    ) -> BatchRegisterChatGptAccountsParams:
        if isinstance(params, BatchRegisterChatGptAccountsParams):
            return params
        return BatchRegisterChatGptAccountsParams(signup_count=int(params))

    @classmethod
    def _should_persist(cls, status: str) -> bool:
        return status in cls._PERSISTABLE_STATUSES

    @staticmethod
    def _mask_email(email: str) -> str:
        normalized = email.strip()
        if "@" not in normalized:
            return normalized or "-"

        local_part, domain = normalized.split("@", 1)
        if len(local_part) <= 4:
            masked_local = f"{local_part[:1]}***"
        else:
            masked_local = f"{local_part[:2]}***{local_part[-2:]}"
        return f"{masked_local}@{domain}"

    @staticmethod
    def _build_item_result(
        *,
        index: int,
        signup_result: dict[str, Any] | None,
        persisted: bool,
        account_id: int | None,
        override_status: str | None = None,
        override_msg: str | None = None,
    ) -> ChatGptBatchRegisterItemResult:
        payload = signup_result or {}
        return ChatGptBatchRegisterItemResult(
            index=index,
            email=str(payload.get("email") or "") or None,
            password=str(payload.get("password") or "") or None,
            name=str(payload.get("name") or "") or None,
            status=override_status or str(payload.get("status") or "UNKNOWN"),
            msg=override_msg or (str(payload.get("msg")) if payload.get("msg") is not None else None),
            persisted=persisted,
            account_id=account_id,
        )
