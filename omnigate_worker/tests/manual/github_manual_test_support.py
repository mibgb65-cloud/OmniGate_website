from __future__ import annotations

import logging
from typing import Any

from src.browser.browser_actions import BrowserActions
from src.browser.browser_manager import BrowserManager
from src.config import get_settings


class ManualVisibleBrowserManager(BrowserManager):
    """手动测试专用浏览器管理器：强制显示窗口，可选择是否自动关闭。"""

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
    """手动测试专用浏览器动作。"""

    def __init__(self, *, auto_close_browser: bool) -> None:
        super().__init__(manager=ManualVisibleBrowserManager(auto_close_browser=auto_close_browser))
