from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import ValidationError

from src.modules.base_task import BaseTask
from src.modules.google.models.google_service_params import InviteGoogleFamilyMemberByAccountIdParams
from src.modules.google.services.invite_google_family_member_by_account_id import (
    InviteGoogleFamilyMemberByAccountIdService,
)
from src.utils.task_log_bridge import TaskLogBridge


class InviteGoogleFamilyMemberByAccountIdTask(BaseTask):
    module_name = "google"
    action_name = "invite_google_family_member_by_account_id"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self.task_id
        started_at = time.monotonic()
        step_total = 3
        await self.log_info(
            "Task accepted",
            step=1,
            step_total=step_total,
            context={"payload": payload, "action": self.action_name, "trace_id": trace_id},
        )

        try:
            params = InviteGoogleFamilyMemberByAccountIdParams.model_validate(
                {
                    "google_account_id": payload.get("google_account_id")
                    or payload.get("googleAccountId")
                    or payload.get("account_id")
                    or payload.get("accountId"),
                    "invited_account_email": payload.get("invited_account_email")
                    or payload.get("invitedAccountEmail")
                    or payload.get("target_email")
                    or payload.get("targetEmail"),
                }
            )
        except ValidationError as exc:
            await self.log_error(
                "Invalid payload for family invite task",
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
            "Start service execution",
            step=2,
            step_total=step_total,
            context={
                "google_account_id": params.google_account_id,
                "invited_account_email": params.invited_account_email,
                "action": self.action_name,
                "trace_id": trace_id,
                "elapsed_seconds": elapsed,
            },
        )

        service = InviteGoogleFamilyMemberByAccountIdService(db_pool=self.db_pool)
        try:
            async with TaskLogBridge(
                sink=self._forward_bridge_log,
                logger_prefixes=("src.modules.google",),
                min_level=logging.INFO,
            ):
                result = await service.execute(
                    params,
                    keep_page_open=False,
                    max_wait_seconds=0,
                )
            sanitized = self._sanitize_result(result)
            elapsed = round(time.monotonic() - started_at, 2)
            await self.log_info(
                "Task finished",
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
                "Family invite task failed. task_id=%s google_account_id=%s target_email=%s",
                self.task_id,
                params.google_account_id,
                params.invited_account_email,
            )
            elapsed = round(time.monotonic() - started_at, 2)
            await self.log_error(
                "Service execution failed",
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
