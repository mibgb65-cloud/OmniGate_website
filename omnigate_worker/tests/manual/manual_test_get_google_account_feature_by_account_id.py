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

from src.modules.google.models.google_service_params import GetGoogleAccountFeatureByAccountIdParams
from src.modules.google.services.get_google_account_feature_by_account_id import (
    GetGoogleAccountFeatureByAccountIdService,
)
from src.utils.logging_setup import configure_colored_logging


DEFAULT_ACCOUNT_ID = 9


class ManualTestGetGoogleAccountFeatureByAccountId:
    """手动测试：按账号 ID 读取凭据并执行 Google 登录。"""

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
        service = GetGoogleAccountFeatureByAccountIdService()
        try:
            result = await service.execute(
                GetGoogleAccountFeatureByAccountIdParams(google_account_id=self.account_id),
                keep_page_open=self.keep_page_open,
                max_wait_seconds=self.max_wait_seconds,
            )
            return self._sanitize_result(result)
        finally:
            if self.auto_close_browser:
                await service.close()
            else:
                logging.getLogger(__name__).info("手动测试模式：保留浏览器会话，不自动关闭。")

    @staticmethod
    def _sanitize_result(result: dict[str, Any]) -> dict[str, Any]:
        login_result = result.get("login_result")
        if isinstance(login_result, dict) and "page" in login_result:
            copied = dict(login_result)
            copied["page"] = "<page_object>"
            result = dict(result)
            result["login_result"] = copied
        return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="手动测试：按账号ID登录 Google")
    parser.add_argument(
        "--account-id",
        type=int,
        default=DEFAULT_ACCOUNT_ID,
        help=f"acc_google_base.id（默认: {DEFAULT_ACCOUNT_ID}）",
    )
    parser.add_argument(
        "--keep-page-open",
        action="store_true",
        default=True,
        help="登录后保持页面打开（默认开启）",
    )
    parser.add_argument(
        "--no-keep-page-open",
        action="store_false",
        dest="keep_page_open",
        help="关闭页面保持模式，流程结束后直接返回",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=None,
        help="最多等待秒数；不传则一直等待，直到 Ctrl+C",
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
    runner = ManualTestGetGoogleAccountFeatureByAccountId(
        account_id=args.account_id,
        keep_page_open=args.keep_page_open,
        max_wait_seconds=args.max_wait_seconds,
        auto_close_browser=args.auto_close_browser,
    )
    result = await runner.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


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
