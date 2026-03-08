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

from src.browser.browser_actions import BrowserActions
from src.browser.browser_manager import BrowserManager
from src.config import settings
from src.config import get_settings
from src.db import Database
from src.modules.chatgpt.models import BatchRegisterChatGptAccountsParams
from src.modules.chatgpt.services import BatchRegisterChatGptAccountsService
from src.utils.logging_setup import configure_colored_logging


DEFAULT_SIGNUP_COUNT = 1


class ManualVisibleBrowserManager(BrowserManager):
    """手动测试专用浏览器管理器：强制显示窗口，并可选择是否自动关闭。"""

    def __init__(self, *, auto_close_browser: bool) -> None:
        super().__init__()
        self._auto_close_browser = auto_close_browser

    async def start(self) -> Any:
        browser_settings = get_settings()
        browser_settings.BROWSER_HEADLESS = False
        return await super().start()

    async def close(self) -> None:
        if self._auto_close_browser:
            await super().close()
            return

        logging.getLogger(__name__).info("手动测试模式：保留浏览器窗口，不自动关闭。")


class ManualVisibleBrowserActions(BrowserActions):
    """手动测试专用浏览器动作：使用可见浏览器窗口。"""

    def __init__(self, *, auto_close_browser: bool) -> None:
        super().__init__(manager=ManualVisibleBrowserManager(auto_close_browser=auto_close_browser))


class ManualTestBatchRegisterChatGptAccounts:
    """手动测试：串行批量注册 ChatGPT 账号。"""

    def __init__(self, *, signup_count: int, auto_close_browser: bool) -> None:
        self.signup_count = signup_count
        self.auto_close_browser = auto_close_browser

    async def run(self) -> dict:
        database = Database(settings.resolved_postgres_dsn)
        await database.connect()
        try:
            service = BatchRegisterChatGptAccountsService(
                db_pool=database.pool,
                browser_actions=ManualVisibleBrowserActions(
                    auto_close_browser=self.auto_close_browser,
                ),
            )
            result = await service.execute(
                BatchRegisterChatGptAccountsParams(signup_count=self.signup_count)
            )
            return result.model_dump()
        finally:
            await database.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="手动测试：串行批量注册 ChatGPT 账号")
    parser.add_argument(
        "--signup-count",
        type=int,
        default=DEFAULT_SIGNUP_COUNT,
        help=f"本次连续注册账号数量（默认: {DEFAULT_SIGNUP_COUNT}）",
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
    runner = ManualTestBatchRegisterChatGptAccounts(
        signup_count=args.signup_count,
        auto_close_browser=args.auto_close_browser,
    )
    result = await runner.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.auto_close_browser:
        logging.getLogger(__name__).info(
            "批量注册执行结束，浏览器窗口已保持打开。按 Ctrl+C 结束脚本。"
        )
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
