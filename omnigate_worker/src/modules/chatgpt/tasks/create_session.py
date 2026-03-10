from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import ValidationError

from src.modules.base_task import BaseTask
from src.modules.chatgpt.models import UpdateChatGptSessionByAccountIdParams
from src.modules.chatgpt.services import UpdateChatGptSessionByAccountIdService
from src.utils.task_log_bridge import TaskLogBridge


class CreateChatGptSessionTask(BaseTask):
    module_name = "chatgpt"
    action_name = "create_session"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self.task_id
        started_at = time.monotonic()
        step_total = 3
        await self.log_info(
            "已接收 ChatGPT Session 更新任务",
            step=1,
            step_total=step_total,
            context={"payload": payload, "action": self.action_name, "trace_id": trace_id},
        )

        try:
            params = UpdateChatGptSessionByAccountIdParams.model_validate(
                {
                    "chatgpt_account_id": payload.get("chatgpt_account_id")
                    or payload.get("chatgptAccountId")
                    or payload.get("account_id")
                    or payload.get("accountId")
                    or payload.get("id"),
                }
            )
        except ValidationError as exc:
            await self.log_error(
                "ChatGPT Session 更新任务参数校验失败",
                step=2,
                step_total=step_total,
                error_code="VALIDATION_ERROR",
                context={"detail": str(exc)},
            )
            return {
                "status": "failed",
                "trace_id": trace_id,
                "error_code": "VALIDATION_ERROR",
                "error_message": str(exc),
            }

        elapsed = round(time.monotonic() - started_at, 2)
        await self.log_info(
            "开始执行 ChatGPT Session 更新服务",
            step=2,
            step_total=step_total,
            context={
                "chatgpt_account_id": params.chatgpt_account_id,
                "action": self.action_name,
                "trace_id": trace_id,
                "elapsed_seconds": elapsed,
            },
        )

        service = UpdateChatGptSessionByAccountIdService(db_pool=self.db_pool)
        try:
            async with TaskLogBridge(
                sink=self._forward_bridge_log,
                logger_prefixes=("src.modules.chatgpt",),
                min_level=logging.INFO,
            ):
                result = await service.execute(
                    params,
                    keep_page_open=False,
                    max_wait_seconds=0,
                    persist_to_db=True,
                )
            sanitized = self._sanitize_result(result)
            elapsed = round(time.monotonic() - started_at, 2)
            await self.log_info(
                "ChatGPT Session 更新任务执行完成",
                step=3,
                step_total=step_total,
                context={"action": self.action_name, "trace_id": trace_id, "elapsed_seconds": elapsed},
            )
            return {
                "status": "success",
                "trace_id": trace_id,
                "data": sanitized,
            }
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).exception(
                "ChatGPT Session 更新任务执行失败 | task_id=%s | chatgpt_account_id=%s",
                self.task_id,
                params.chatgpt_account_id,
            )
            elapsed = round(time.monotonic() - started_at, 2)
            await self.log_error(
                "ChatGPT Session 更新服务执行失败",
                step=3,
                step_total=step_total,
                error_code="SERVICE_ERROR",
                context={
                    "detail": str(exc),
                    "action": self.action_name,
                    "trace_id": trace_id,
                    "elapsed_seconds": elapsed,
                },
            )
            return {
                "status": "failed",
                "trace_id": trace_id,
                "error_code": "SERVICE_ERROR",
                "error_message": str(exc),
            }
        finally:
            await service.close()

    @staticmethod
    def _sanitize_result(result: dict[str, Any]) -> dict[str, Any]:
        copied = dict(result)
        if copied.get("session_token"):
            copied["session_token"] = "<redacted>"
        session_result = copied.get("session_result")
        if isinstance(session_result, dict):
            session_result = dict(session_result)
            if session_result.get("raw_text"):
                session_result["raw_text"] = "<redacted>"
            session_data = session_result.get("data")
            if isinstance(session_data, dict) and session_data.get("accessToken"):
                session_data = dict(session_data)
                session_data["accessToken"] = "<redacted>"
                session_result["data"] = session_data
            copied["session_result"] = session_result
        return copied

    async def _forward_bridge_log(
        self,
        levelno: int,
        message: str,
        step: int | None,
        step_total: int | None,
        logger_name: str,
    ) -> None:
        context = {"logger": logger_name}
        if levelno >= logging.ERROR:
            await self.log_error(message, step=step, step_total=step_total, context=context)
            return
        if levelno >= logging.WARNING:
            await self.log_warning(message, step=step, step_total=step_total, context=context)
            return
        await self.log_info(message, step=step, step_total=step_total, context=context)
