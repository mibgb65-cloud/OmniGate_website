from __future__ import annotations

import asyncio
import unittest

from src.browser.browser_actions import BrowserActions, PageOpenTimeoutError


class _FakeBrowser:
    def __init__(self, *, delay_seconds: float = 0.0, page: object | None = None) -> None:
        self.delay_seconds = delay_seconds
        self.page = page if page is not None else object()
        self.urls: list[str] = []

    async def get(self, url: str) -> object:
        self.urls.append(url)
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        return self.page


class TestBrowserActions(unittest.IsolatedAsyncioTestCase):
    async def test_should_raise_timeout_error_when_navigation_exceeds_timeout(self) -> None:
        actions = BrowserActions()
        browser = _FakeBrowser(delay_seconds=0.05)

        with self.assertRaises(PageOpenTimeoutError) as ctx:
            await actions.open_page(
                browser,
                "https://chatgpt.com",
                focus=False,
                timeout_seconds=0.01,
            )

        self.assertEqual("https://chatgpt.com", ctx.exception.url)
        self.assertAlmostEqual(0.01, ctx.exception.timeout_seconds, places=2)

    async def test_should_return_page_when_navigation_finishes_before_timeout(self) -> None:
        actions = BrowserActions()
        page = object()
        browser = _FakeBrowser(delay_seconds=0.01, page=page)

        result = await actions.open_page(
            browser,
            "https://chatgpt.com",
            focus=False,
            timeout_seconds=0.1,
        )

        self.assertIs(page, result)
        self.assertEqual(["https://chatgpt.com"], browser.urls)
