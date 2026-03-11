from __future__ import annotations

import unittest
from unittest.mock import patch

from src.modules.chatgpt.actions.chatgpt_signup_action import OpenAISignupService


async def _noop_sleep(_: float) -> None:
    return None


class _FakePage:
    def __init__(self, *, select_after: dict[str, int] | None = None, find_after: dict[str, int] | None = None) -> None:
        self._select_after = dict(select_after or {})
        self._find_after = dict(find_after or {})
        self._select_calls: dict[str, int] = {}
        self._find_calls: dict[str, int] = {}

    async def select(self, selector: str, timeout: float = 1) -> object | None:  # noqa: ARG002
        self._select_calls[selector] = self._select_calls.get(selector, 0) + 1
        ready_after = self._select_after.get(selector)
        if ready_after is None:
            return None
        if self._select_calls[selector] >= ready_after:
            return {"selector": selector}
        return None

    async def find(self, text: str, timeout: float = 1) -> object | None:  # noqa: ARG002
        self._find_calls[text] = self._find_calls.get(text, 0) + 1
        ready_after = self._find_after.get(text, 1_000_000)
        if self._find_calls[text] >= ready_after:
            return {"text": text}
        return None


class TestChatGptSignupAction(unittest.IsolatedAsyncioTestCase):
    async def test_wait_for_select_should_retry_until_element_appears(self) -> None:
        service = OpenAISignupService()
        selector = 'input[name="username"], input[name="email"], input[type="email"]'
        page = _FakePage(select_after={selector: 3})

        with patch("src.modules.chatgpt.actions.chatgpt_signup_action.asyncio.sleep", new=_noop_sleep):
            element = await service._wait_for_select(
                page,
                selector,
                timeout_seconds=1.0,
                stage="邮箱输入",
                description="邮箱输入框",
            )

        self.assertIsNotNone(element)
        self.assertEqual(3, page._select_calls[selector])

    async def test_wait_for_login_button_should_retry_until_it_appears(self) -> None:
        service = OpenAISignupService()
        page = _FakePage(find_after={"Log in": 3})

        with patch("src.modules.chatgpt.actions.chatgpt_signup_action.asyncio.sleep", new=_noop_sleep):
            button = await service._wait_for_login_button(page, timeout_seconds=1.0)

        self.assertEqual({"text": "Log in"}, button)
