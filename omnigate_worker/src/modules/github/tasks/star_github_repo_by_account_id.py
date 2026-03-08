from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import ValidationError

from src.modules.base_task import BaseTask
from src.modules.github.models.github_service_params import StarGithubRepoByAccountIdParams
from src.modules.github.services.star_github_repo_by_account_id import StarGithubRepoByAccountIdService
from src.utils.task_log_bridge import TaskLogBridge


class StarGithubRepoByAccountIdTask(BaseTask):
    module_name = "github"
    action_name = "star_github_repo_by_account_id"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self.task_id
        started_at = time.monotonic()
        step_total = 3
        await self.log_info(
            "已接收 GitHub 仓库 Star 任务",
            step=1,
            step_total=step_total,
            context={"payload": payload, "action": self.action_name, "trace_id": trace_id},
        )

        try:
            params = StarGithubRepoByAccountIdParams.model_validate(
                {
                    "github_account_id": payload.get("github_account_id")
                    or payload.get("githubAccountId")
                    or payload.get("account_id")
                    or payload.get("accountId"),
                    "repo_url": payload.get("repo_url")
                    or payload.get("repoUrl"),
                }
            )
        except ValidationError as exc:
            await self.log_error(
                "GitHub 仓库 Star 任务参数校验失败",
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
            "开始执行 GitHub 仓库 Star 服务",
            step=2,
            step_total=step_total,
            context={
                "github_account_id": params.github_account_id,
                "repo_url": params.repo_url,
                "action": self.action_name,
                "trace_id": trace_id,
                "elapsed_seconds": elapsed,
            },
        )

        service = StarGithubRepoByAccountIdService(db_pool=self.db_pool)
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
                "GitHub 仓库 Star 任务执行完成",
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
                "GitHub 仓库 Star 任务执行失败 | task_id=%s | github_account_id=%s | repo_url=%s",
                self.task_id,
                params.github_account_id,
                params.repo_url,
            )
            elapsed = round(time.monotonic() - started_at, 2)
            await self.log_error(
                "GitHub 仓库 Star 服务执行失败",
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
        login_result = copied.get("login_result")
        if isinstance(login_result, dict) and "page" in login_result:
            login_result = dict(login_result)
            login_result["page"] = "<page_object>"
            copied["login_result"] = login_result
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
