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

from src.modules.google.models.google_service_params import (
    GetGoogleAccountStudentEligibilityByAccountIdParams,
)
from src.modules.google.services.get_google_account_student_eligibility_by_account_id import (
    GetGoogleAccountStudentEligibilityByAccountIdService,
)
from src.utils.logging_setup import configure_colored_logging


DEFAULT_ACCOUNT_ID = 2


class ManualTestGetGoogleAccountStudentEligibilityByAccountId:
    """Manual test: login by account id, then fetch student eligibility."""

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
        service = GetGoogleAccountStudentEligibilityByAccountIdService()
        try:
            result = await service.execute(
                GetGoogleAccountStudentEligibilityByAccountIdParams(
                    google_account_id=self.account_id,
                ),
                keep_page_open=self.keep_page_open,
                max_wait_seconds=self.max_wait_seconds,
            )
            return self._sanitize_result(result)
        finally:
            if self.auto_close_browser:
                await service.close()
            else:
                logging.getLogger(__name__).info("Manual mode: keep browser session alive.")

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
    parser = argparse.ArgumentParser(description="Manual test: student eligibility by account id")
    parser.add_argument(
        "--account-id",
        type=int,
        default=DEFAULT_ACCOUNT_ID,
        help=f"acc_google_base.id (default: {DEFAULT_ACCOUNT_ID})",
    )
    parser.add_argument(
        "--keep-page-open",
        action="store_true",
        default=True,
        help="Keep browser page open after flow (default: true)",
    )
    parser.add_argument(
        "--no-keep-page-open",
        action="store_false",
        dest="keep_page_open",
        help="Do not keep browser page open after flow",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=None,
        help="Max wait seconds in keep mode; omit to wait forever",
    )
    parser.add_argument(
        "--auto-close-browser",
        action="store_true",
        default=False,
        help="Auto close browser at end (default: false)",
    )
    return parser


async def _main_async() -> None:
    args = _build_parser().parse_args()
    runner = ManualTestGetGoogleAccountStudentEligibilityByAccountId(
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
        print("Interrupted by user.")


if __name__ == "__main__":
    main()
