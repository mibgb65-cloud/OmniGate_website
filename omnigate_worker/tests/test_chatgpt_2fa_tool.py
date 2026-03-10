from __future__ import annotations

import unittest
from unittest.mock import patch

from src.modules.chatgpt.utils.chatgpt_2fa_tool import ChatGptTwoFactorTool


async def _noop_sleep(_: float) -> None:
    return None


class _FakeInputElement:
    def __init__(self) -> None:
        self.keys: list[str] = []
        self.clicked = False

    async def click(self) -> None:
        self.clicked = True

    async def send_keys(self, value: str) -> None:
        self.keys.append(value)


class _FakePage:
    def __init__(self, *, snapshots: list[dict[str, object]] | None = None) -> None:
        self.input_element = _FakeInputElement()
        self.current_url = "https://chatgpt.com/#settings/Security"
        self._snapshots = list(snapshots or [])
        self._last_snapshot = self._snapshots[-1] if self._snapshots else {"current_url": self.current_url}

    async def get(self, url: str) -> "_FakePage":
        self.current_url = url
        return self

    async def select(self, selector: str, timeout: float = 1) -> object | None:  # noqa: ARG002
        if selector == "input#totp_otp":
            return self.input_element
        return None

    async def evaluate(self, script: str) -> object:
        if script == "window.location.href":
            return self.current_url

        if "__OMNIGATE_2FA_POST_VERIFY_STATE__" in script:
            if self._snapshots:
                snapshot = self._snapshots.pop(0)
                self._last_snapshot = snapshot
            else:
                snapshot = self._last_snapshot
            self.current_url = str(snapshot.get("current_url") or self.current_url)
            return snapshot

        return None


class _DeterministicTwoFactorTool(ChatGptTwoFactorTool):
    def __init__(self, *, verify_state: dict[str, object]) -> None:
        super().__init__()
        self._verify_state = verify_state

    async def _toggle_authenticator_app(self, page: object) -> str:  # noqa: ARG002
        return "clicked"

    async def _open_trouble_scanning(self, page: object) -> int | None:  # noqa: ARG002
        return 1

    async def _extract_secret_key(self, page: object) -> str | None:  # noqa: ARG002
        return "JBSWY3DPEHPK3PXP"

    async def _click_verify(self, page: object) -> bool:  # noqa: ARG002
        return True

    async def _wait_for_post_verify_state(self, page: object) -> dict[str, object]:  # noqa: ARG002
        return self._verify_state


class TestChatGptTwoFactorTool(unittest.IsolatedAsyncioTestCase):
    async def test_wait_for_post_verify_state_should_detect_success(self) -> None:
        tool = ChatGptTwoFactorTool()
        page = _FakePage(
            snapshots=[
                {
                    "current_url": "https://chatgpt.com/#settings/Security",
                    "otp_input_visible": True,
                    "verify_button_visible": True,
                    "authenticator_enabled": True,
                    "has_prompt": False,
                    "has_recovery_codes": False,
                    "error_text": "",
                },
                {
                    "current_url": "https://chatgpt.com/",
                    "otp_input_visible": False,
                    "verify_button_visible": False,
                    "authenticator_enabled": True,
                    "has_prompt": True,
                    "has_recovery_codes": False,
                    "error_text": "",
                },
            ]
        )

        with patch("src.modules.chatgpt.utils.chatgpt_2fa_tool.asyncio.sleep", new=_noop_sleep):
            state = await tool._wait_for_post_verify_state(page)

        self.assertEqual("done", state["state"])
        self.assertEqual("https://chatgpt.com/", state["current_url"])

    async def test_wait_for_post_verify_state_should_surface_error(self) -> None:
        tool = ChatGptTwoFactorTool()
        page = _FakePage(
            snapshots=[
                {
                    "current_url": "https://chatgpt.com/#settings/Security",
                    "otp_input_visible": True,
                    "verify_button_visible": True,
                    "authenticator_enabled": True,
                    "has_prompt": False,
                    "has_recovery_codes": False,
                    "error_text": "invalid code",
                }
            ]
        )

        with patch("src.modules.chatgpt.utils.chatgpt_2fa_tool.asyncio.sleep", new=_noop_sleep):
            state = await tool._wait_for_post_verify_state(page)

        self.assertEqual("error", state["state"])
        self.assertEqual("invalid code", state["reason"])

    async def test_setup_authenticator_should_fail_when_verify_transition_times_out(self) -> None:
        tool = _DeterministicTwoFactorTool(
            verify_state={
                "state": "timeout",
                "current_url": "https://chatgpt.com/#settings/Security",
            }
        )
        page = _FakePage()

        with patch("src.modules.chatgpt.utils.chatgpt_2fa_tool.asyncio.sleep", new=_noop_sleep):
            result = await tool.setup_authenticator(page)

        self.assertFalse(result.ok)
        self.assertEqual("verify_transition", result.step)
        self.assertIn("当前URL=https://chatgpt.com/#settings/Security", result.reason or "")

    async def test_setup_authenticator_should_return_secret_only_after_verify_success(self) -> None:
        tool = _DeterministicTwoFactorTool(
            verify_state={
                "state": "done",
                "current_url": "https://chatgpt.com/",
            }
        )
        page = _FakePage()

        with patch("src.modules.chatgpt.utils.chatgpt_2fa_tool.asyncio.sleep", new=_noop_sleep):
            result = await tool.setup_authenticator(page)

        self.assertTrue(result.ok)
        self.assertEqual("done", result.step)
        self.assertEqual("JBSWY3DPEHPK3PXP", result.secret_key)
