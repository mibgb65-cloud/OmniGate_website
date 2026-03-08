"""ChatGPT 2FA Action，作为注册流程对 2FA 工具类的轻量包装。"""

from __future__ import annotations

from typing import Any

from src.modules.chatgpt.utils.chatgpt_2fa_tool import ChatGptTwoFactorTool


class ChatGPT2FAAction:
    """对外暴露 ChatGPT 2FA 配置能力，返回 action 层通用字典结构。"""

    def __init__(self, tool: ChatGptTwoFactorTool | None = None) -> None:
        self._tool = tool or ChatGptTwoFactorTool()

    async def setup_2fa(self, page: Any) -> dict[str, Any]:
        """在已登录页面上执行 2FA 绑定，并返回可直接给上游消费的 payload。"""

        result = await self._tool.setup_authenticator(page)
        return result.to_payload()
