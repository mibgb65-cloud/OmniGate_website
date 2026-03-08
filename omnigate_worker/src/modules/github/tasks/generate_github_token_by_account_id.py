from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import ValidationError

from src.modules.base_task import BaseTask
from src.modules.github.models.github_service_params import GenerateGithubTokenByAccountIdParams
from src.modules.github.services.generate_github_token_by_account_id import (
    GenerateGithubTokenByAccountIdService,
)
from src.utils.task_log_bridge import TaskLogBridge


class GenerateGithubTokenByAccountIdTask(BaseTask):
    module_name = "github"
    action_name = "generate_github_token_by_account_id"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self.task_id
        started_at = time.monotonic()
        step_total = 3
        await self.log_info(
            "已接收 GitHub Token 生成任务",
            step=1,
            step_total=step_total,
            context={"payload": payload, "action": self.action_name, "trace_id": trace_id},
        )

        try:
            params = GenerateGithubTokenByAccountIdParams.model_validate(
                {
                    "github_account_id": payload.get("github_account_id")
                    or payload.get("githubAccountId")
                    or payload.get("account_id")
                    or payload.get("accountId"),
                }
            )
        except ValidationError as exc:
            await self.log_error(
                "GitHub Token 生成任务参数校验失败",
                step=2,
                step_total=step_total,
                error_code="VALIDATION_ERROR",
                context={"detail": str(exc)},
            )
            return {
                "status": "failed",
                "error_code": "VALIDATION_ERROR",
                "error_message": str(exc),
            }

        elapsed = round(time.monotonic() - started_at, 2)
        await self.log_info(
            "开始执行 GitHub Token 生成服务",
            step=2,
            step_total=step_total,
            context={
                "github_account_id": params.github_account_id,
                "action": self.action_name,
                "trace_id": trace_id,
                "elapsed_seconds": elapsed,
            },
        )

        service = GenerateGithubTokenByAccountIdService(db_pool=self.db_pool)
        try:
            async with TaskLogBridge(
                sink=self._forward_bridge_log,
                logger_prefixes=("src.modules.github",),
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
                "GitHub Token 生成任务执行完成",
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
                "GitHub Token 生成任务执行失败 | task_id=%s | github_account_id=%s",
                self.task_id,
                params.github_account_id,
            )
            elapsed = round(time.monotonic() - started_at, 2)
            await self.log_error(
                "GitHub Token 生成服务执行失败",
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
        if copied.get("access_token"):
            copied["access_token"] = "<redacted>"
        login_result = copied.get("login_result")
        if isinstance(login_result, dict) and "page" in login_result:
            login_result = dict(login_result)
            login_result["page"] = "<page_object>"
            copied["login_result"] = login_result
        token_result = copied.get("token_result")
        if isinstance(token_result, dict) and token_result.get("token"):
            token_result = dict(token_result)
            token_result["token"] = "<redacted>"
            copied["token_result"] = token_result
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
