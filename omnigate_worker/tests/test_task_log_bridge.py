from __future__ import annotations

import logging
import unittest

from src.utils.task_log_bridge import TaskLogBridge


class TestTaskLogBridge(unittest.IsolatedAsyncioTestCase):
    async def test_should_forward_target_logger_records(self) -> None:
        forwarded: list[tuple[int, str, int | None, int | None, str]] = []

        async def sink(
            levelno: int,
            message: str,
            step: int | None,
            step_total: int | None,
            logger_name: str,
        ) -> None:
            forwarded.append((levelno, message, step, step_total, logger_name))

        target_logger = logging.getLogger("src.modules.google.services.demo")
        other_logger = logging.getLogger("src.modules.github.services.demo")
        target_prev_level = target_logger.level
        other_prev_level = other_logger.level

        target_logger.setLevel(logging.INFO)
        other_logger.setLevel(logging.INFO)
        try:
            async with TaskLogBridge(sink=sink, logger_prefixes=("src.modules.google",), min_level=logging.INFO):
                target_logger.info("服务流程[2/7] 开始执行")
                target_logger.warning("执行过程告警")
                other_logger.info("should be ignored")
        finally:
            target_logger.setLevel(target_prev_level)
            other_logger.setLevel(other_prev_level)

        self.assertEqual(2, len(forwarded))
        self.assertEqual("src.modules.google.services.demo", forwarded[0][4])
        self.assertEqual(2, forwarded[0][2])
        self.assertEqual(7, forwarded[0][3])
