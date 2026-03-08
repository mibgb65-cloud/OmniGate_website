"""浏览器动作封装：启动/关闭浏览器，打开/关闭页面。"""

from contextlib import asynccontextmanager
from inspect import isawaitable
from typing import Any

import asyncio
import logging

from src.browser.browser_manager import BrowserManager

logger = logging.getLogger(__name__)
LOG_PREFIX = "[浏览器动作]"


class BrowserActions:
    """浏览器通用动作，供多个 service 复用。"""

    def __init__(self, manager: BrowserManager | None = None) -> None:
        self.manager = manager or BrowserManager()

    async def start_browser(self) -> Any:
        """启动浏览器并返回浏览器实例。"""
        return await self.manager.start()

    async def close_browser(self) -> None:
        """关闭浏览器实例。"""
        # 兼容旧版/异常 manager：优先 close，其次 stop，再次尝试关闭底层 _browser
        close = getattr(self.manager, "close", None)
        stop = getattr(self.manager, "stop", None)

        if callable(close):
            result = close()
            if isawaitable(result):
                await result
            await asyncio.sleep(0.1)
            return

        if callable(stop):
            result = stop()
            if isawaitable(result):
                await result
            await asyncio.sleep(0.1)
            return

        browser = getattr(self.manager, "_browser", None)
        if browser is not None:
            browser_stop = getattr(browser, "stop", None)
            browser_close = getattr(browser, "close", None)
            try:
                if callable(browser_stop):
                    result = browser_stop()
                    if isawaitable(result):
                        await result
                elif callable(browser_close):
                    result = browser_close()
                    if isawaitable(result):
                        await result
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s 关闭底层浏览器实例异常 | 原因=%s", LOG_PREFIX, exc)

        await asyncio.sleep(0.1)

    async def open_page(self, browser: Any, url: str, *, focus: bool = True) -> Any:
        """在浏览器中打开页面并返回页面对象。"""
        page = await browser.get(url)
        if focus:
            await self.focus_page(page)
        return page

    async def close_page(self, page: Any) -> None:
        """关闭页面对象（兼容不同对象能力）。"""
        if page is None:
            return

        close = getattr(page, "close", None)
        if callable(close):
            result = close()
            if hasattr(result, "__await__"):
                await result

    async def focus_page(self, page: Any) -> None:
        """尽量把页面切换到前台，便于手动观察跳转。"""
        if page is None:
            return

        activate = getattr(page, "activate", None)
        if callable(activate):
            try:
                result = activate()
                if isawaitable(result):
                    await result
                return
            except Exception as exc:  # noqa: BLE001
                logger.debug("%s page.activate() 失败 | 原因=%s", LOG_PREFIX, exc)

        bring_to_front = getattr(page, "bring_to_front", None)
        if callable(bring_to_front):
            try:
                result = bring_to_front()
                if isawaitable(result):
                    await result
                return
            except Exception as exc:  # noqa: BLE001
                logger.debug("%s page.bring_to_front() 失败 | 原因=%s", LOG_PREFIX, exc)

        try:
            import nodriver.cdp.page as cdp_page

            send = getattr(page, "send", None)
            if callable(send):
                result = send(cdp_page.bring_to_front())
                if isawaitable(result):
                    await result
        except Exception as exc:  # noqa: BLE001
            logger.debug("%s CDP bring_to_front 失败 | 原因=%s", LOG_PREFIX, exc)

    @asynccontextmanager
    async def browser_lifespan(self, *, auto_close: bool = True):
        """浏览器生命周期上下文。"""
        browser = await self.start_browser()
        try:
            yield browser
        finally:
            if auto_close:
                await self.close_browser()
