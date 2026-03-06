from __future__ import annotations

import unittest

from src.modules.chatgpt.actions import create_task
from src.modules.google.tasks.get_google_account_feature_by_account_id import (
    GetGoogleAccountFeatureByAccountIdTask,
)


async def _noop_log_sink(_payload: dict) -> None:
    return None


class TestTaskRegistryGoogleFeature(unittest.TestCase):
    def test_should_create_google_feature_task(self) -> None:
        task = create_task(
            task_payload={
                "module": "google",
                "action": "get_google_account_feature_by_account_id",
            },
            task_id="task-1",
            worker_instance_id="worker-local-1",
            attempt_no=1,
            log_sink=_noop_log_sink,
        )

        self.assertIsInstance(task, GetGoogleAccountFeatureByAccountIdTask)
