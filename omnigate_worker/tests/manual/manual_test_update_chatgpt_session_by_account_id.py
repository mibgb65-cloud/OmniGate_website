from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.db import Database
from src.modules.chatgpt.models import UpdateChatGptSessionByAccountIdParams
from src.modules.chatgpt.services.update_chatgpt_session_by_account_id import (
    UpdateChatGptSessionByAccountIdService,
)
from src.utils.logging_setup import configure_colored_logging
from tests.manual.github_manual_test_support import ManualVisibleBrowserActions


DEFAULT_ACCOUNT_ID = 5


class ManualTestUpdateChatGptSessionByAccountId:
    """手动测试：按账号 ID 登录 ChatGPT 并刷新 session_token。"""

    def __init__(
        self,
        *,
        account_id: int,
        keep_page_open: bool,
        max_wait_seconds: int | None,
        auto_close_browser: bool,
    ) -> None:
        self.account_id = account_id
        self.keep_page_open = keep_page_open
        self.max_wait_seconds = max_wait_seconds
        self.auto_close_browser = auto_close_browser

    async def run(self) -> dict[str, Any]:
        database = Database(settings.resolved_postgres_dsn)
        await database.connect()
        service = UpdateChatGptSessionByAccountIdService(
            db_pool=database.pool,
            browser_actions=ManualVisibleBrowserActions(auto_close_browser=self.auto_close_browser),
        )
        try:
            result = await service.execute(
                UpdateChatGptSessionByAccountIdParams(chatgpt_account_id=self.account_id),
                keep_page_open=self.keep_page_open,
                max_wait_seconds=self.max_wait_seconds,
                persist_to_db=True,
            )
            return self._sanitize_result(result)
        finally:
            await service.close()
            await database.close()

    @staticmethod
    def _sanitize_result(result: dict[str, Any]) -> dict[str, Any]:
        copied = dict(result)
        if copied.get("session_token"):
            copied["session_token"] = "<redacted>"

        login_result = copied.get("login_result")
        if isinstance(login_result, dict) and "page" in login_result:
            login_result = dict(login_result)
            login_result["page"] = "<page_object>"
            copied["login_result"] = login_result

        session_result = copied.get("session_result")
        if isinstance(session_result, dict):
            session_result = dict(session_result)
            session_data = session_result.get("data")
            if isinstance(session_data, dict) and session_data.get("accessToken"):
                session_data = dict(session_data)
                session_data["accessToken"] = "<redacted>"
                session_result["data"] = session_data
            copied["session_result"] = session_result

        return copied


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="手动测试：按账号ID刷新 ChatGPT session_token")
    parser.add_argument(
        "--account-id",
        type=int,
        default=DEFAULT_ACCOUNT_ID,
        help=f"acc_chatgpt_base.id（默认: {DEFAULT_ACCOUNT_ID}）",
    )
    parser.add_argument(
        "--keep-page-open",
        action="store_true",
        default=True,
        help="流程结束后保持页面打开（默认开启）",
    )
    parser.add_argument(
        "--no-keep-page-open",
        action="store_false",
        dest="keep_page_open",
        help="流程结束后不保持页面打开",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=None,
        help="最长等待秒数；不传则一直等待，直到 Ctrl+C",
    )
    parser.add_argument(
        "--auto-close-browser",
        action="store_true",
        default=False,
        help="流程结束时自动关闭浏览器（默认不关闭，便于手动测试）",
    )
    return parser


async def _main_async() -> None:
    args = _build_parser().parse_args()
    runner = ManualTestUpdateChatGptSessionByAccountId(
        account_id=args.account_id,
        keep_page_open=args.keep_page_open,
        max_wait_seconds=args.max_wait_seconds,
        auto_close_browser=args.auto_close_browser,
    )
    result = await runner.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.auto_close_browser and not args.keep_page_open:
        logging.getLogger(__name__).info("流程已结束，浏览器窗口保持打开。按 Ctrl+C 结束脚本。")
        await asyncio.Event().wait()


def main() -> None:
    configure_colored_logging(
        level=logging.INFO,
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        print("手动中断，测试结束。")


if __name__ == "__main__":
    main()
