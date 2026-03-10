from __future__ import annotations

import unittest
from typing import Any

from src.modules.chatgpt.actions.chatgpt_signin_action import ChatGPTLoginAction


class _FakePage:
    def __init__(
        self,
        *,
        has_prompt: bool = False,
        has_login_button: bool = False,
        has_email_input: bool = False,
        has_password_input: bool = False,
        current_url: str = "https://chatgpt.com/",
    ) -> None:
        self.has_prompt = has_prompt
        self.has_login_button = has_login_button
        self.has_email_input = has_email_input
        self.has_password_input = has_password_input
        self.current_url = current_url
        self.opened_urls: list[str] = []

    async def get(self, url: str) -> "_FakePage":
        self.opened_urls.append(url)
        self.current_url = url
        return self

    async def find(self, text: str, timeout: float = 1) -> Any | None:  # noqa: ARG002
        if self.has_login_button and text in {"Log in", "登录"}:
            return "login-button"
        return None

    async def select(self, selector: str, timeout: float = 1) -> Any | None:  # noqa: ARG002
        if "prompt-textarea" in selector and self.has_prompt:
            return "prompt-textarea"
        if 'input[name="username"]' in selector and self.has_email_input:
            return "email-input"
        if 'input[type="password"]' in selector and self.has_password_input:
            return "password-input"
        if 'data-testid="login-button"' in selector and self.has_login_button:
            return "login-button"
        return None

    async def evaluate(self, script: str) -> str:
        if script == "window.location.href":
            return self.current_url
        return ""


class TestChatGptSigninAction(unittest.IsolatedAsyncioTestCase):
    async def test_should_prefer_login_button_over_home_prompt(self) -> None:
        action = ChatGPTLoginAction()
        page = _FakePage(has_prompt=True, has_login_button=True)

        state = await action._wait_for_home_ready(page)

        self.assertEqual("login", state["state"])

    async def test_should_recognize_logged_in_prompt_without_login_indicators(self) -> None:
        action = ChatGPTLoginAction()
        page = _FakePage(has_prompt=True, current_url="https://chatgpt.com/")

        prompt = await action._query_logged_in_prompt(page)

        self.assertEqual("prompt-textarea", prompt)

    async def test_should_reject_prompt_on_auth_page(self) -> None:
        action = ChatGPTLoginAction()
        page = _FakePage(has_prompt=True, current_url="https://auth.openai.com/u/login")

        prompt = await action._query_logged_in_prompt(page)

        self.assertIsNone(prompt)

    async def test_should_detect_workspace_as_post_auth_state(self) -> None:
        action = ChatGPTLoginAction()
        page = _FakePage(current_url="https://auth.openai.com/workspace")

        state = await action._wait_for_post_mfa_state(page, timeout_seconds=0.1)

        self.assertEqual("workspace", state["state"])
