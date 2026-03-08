from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import ValidationError

from src.modules.base_task import BaseTask
from src.modules.chatgpt.models import BatchRegisterChatGptAccountsParams
from src.modules.chatgpt.services import BatchRegisterChatGptAccountsService


class BatchRegisterChatGptAccountsTask(BaseTask):
    module_name = "chatgpt"
    action_name = "batch_register_chatgpt_accounts"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self.task_id
        started_at = time.monotonic()
        step_total = 3

        await self.log_info(
            "已接收 ChatGPT 批量注册任务",
            step=1,
            step_total=step_total,
            context={"payload": payload, "action": self.action_name, "trace_id": trace_id},
        )

        try:
            params = BatchRegisterChatGptAccountsParams.model_validate(
                {
                    "signup_count": payload.get("signup_count")
                    or payload.get("signupCount")
                    or payload.get("count"),
                }
            )
        except ValidationError as exc:
            await self.log_error(
                "ChatGPT 批量注册任务参数校验失败",
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
            "开始执行 ChatGPT 批量注册服务",
            step=2,
            step_total=step_total,
            context={
                "signup_count": params.signup_count,
                "action": self.action_name,
                "trace_id": trace_id,
                "elapsed_seconds": elapsed,
            },
        )

        service = BatchRegisterChatGptAccountsService(db_pool=self.db_pool)
        try:
            result = await service.execute(params)
            elapsed = round(time.monotonic() - started_at, 2)
            await self.log_info(
                "ChatGPT 批量注册任务执行完成",
                step=3,
                step_total=step_total,
                context={
                    "action": self.action_name,
                    "trace_id": trace_id,
                    "elapsed_seconds": elapsed,
                    "requested_count": result.requested_count,
                    "success_count": result.success_count,
                    "failed_count": result.failed_count,
                },
            )
            return {
                "status": "success",
                "trace_id": trace_id,
                "data": result.model_dump(),
            }
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).exception(
                "ChatGPT 批量注册任务执行失败 | task_id=%s | signup_count=%s",
                self.task_id,
                params.signup_count,
            )
            elapsed = round(time.monotonic() - started_at, 2)
            await self.log_error(
                "ChatGPT 批量注册服务执行失败",
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
