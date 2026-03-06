from __future__ import annotations

import asyncio
from typing import Any

from src.modules.base_task import BaseTask


class SearchKeywordTask(BaseTask):
    module_name = "google"
    action_name = "search_keyword"

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        keyword = str(payload.get("keyword", "")).strip()
        if not keyword:
            await self.log_error(
                "Missing required field: keyword",
                error_code="VALIDATION_ERROR",
            )
            return {
                "status": "failed",
                "error_code": "VALIDATION_ERROR",
                "error_message": "keyword is required",
            }

        step_total = 3
        await self.log_info("Task accepted", step=1, step_total=step_total, context={"keyword": keyword})
        await asyncio.sleep(0.1)

        await self.log_info("Open Google search page", step=2, step_total=step_total)
        await asyncio.sleep(0.1)

        await self.log_info("Search flow completed", step=3, step_total=step_total)
        return {
            "status": "success",
            "data": {
                "keyword": keyword,
                "results_count": 0,
            },
        }
