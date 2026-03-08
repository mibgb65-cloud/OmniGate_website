from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.modules.base_task import BaseTask
from src.modules.chatgpt.tasks.batch_register_chatgpt_accounts import BatchRegisterChatGptAccountsTask
from src.modules.github.tasks.generate_github_token_by_account_id import GenerateGithubTokenByAccountIdTask
from src.modules.github.tasks.star_github_repo_by_account_id import StarGithubRepoByAccountIdTask
from src.modules.google.tasks.get_google_account_feature_by_account_id import (
    GetGoogleAccountFeatureByAccountIdTask,
)
from src.modules.google.tasks.get_google_account_student_eligibility_by_account_id import (
    GetGoogleAccountStudentEligibilityByAccountIdTask,
)
from src.modules.google.tasks.invite_google_family_member_by_account_id import (
    InviteGoogleFamilyMemberByAccountIdTask,
)
from src.modules.google.tasks.search_keyword import SearchKeywordTask
from src.utils.task_logger import LogSink

if TYPE_CHECKING:
    import asyncpg


@dataclass(frozen=True, slots=True)
class TaskRoute:
    module: str
    action: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TaskRoute":
        module = str(payload.get("module", "")).strip().lower()
        action = str(payload.get("action", "")).strip().lower()
        return cls(module=module, action=action)


_TASK_REGISTRY: dict[TaskRoute, type[BaseTask]] = {
    TaskRoute(
        module="chatgpt",
        action="batch_register_chatgpt_accounts",
    ): BatchRegisterChatGptAccountsTask,
    TaskRoute(module="google", action="search_keyword"): SearchKeywordTask,
    TaskRoute(
        module="google",
        action="get_google_account_feature_by_account_id",
    ): GetGoogleAccountFeatureByAccountIdTask,
    TaskRoute(
        module="google",
        action="get_google_account_student_eligibility_by_account_id",
    ): GetGoogleAccountStudentEligibilityByAccountIdTask,
    TaskRoute(
        module="google",
        action="invite_google_family_member_by_account_id",
    ): InviteGoogleFamilyMemberByAccountIdTask,
    TaskRoute(
        module="github",
        action="generate_github_token_by_account_id",
    ): GenerateGithubTokenByAccountIdTask,
    TaskRoute(
        module="github",
        action="star_github_repo_by_account_id",
    ): StarGithubRepoByAccountIdTask,
}


def create_task(
    *,
    task_payload: dict[str, Any],
    task_id: str,
    worker_instance_id: str,
    attempt_no: int | None,
    log_sink: LogSink,
    db_pool: "asyncpg.Pool | None" = None,
) -> BaseTask:
    route = TaskRoute.from_payload(task_payload)
    task_cls = _TASK_REGISTRY.get(route)
    if task_cls is None:
        raise ValueError(f"Unsupported task route: {route.module}.{route.action}")
    return task_cls(
        task_id=task_id,
        worker_instance_id=worker_instance_id,
        attempt_no=attempt_no,
        log_sink=log_sink,
        db_pool=db_pool,
    )
