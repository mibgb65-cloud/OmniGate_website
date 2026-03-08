"""封装 ChatGPT 账号 2FA 配置流程，供 action / service 复用。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Any

import pyotp


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChatGptTwoFactorSetupResult:
    """描述一次 ChatGPT 2FA 配置的执行结果。"""

    ok: bool
    step: str
    message: str | None = None
    reason: str | None = None
    secret_key: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """转成 action 层更容易返回的 dict 结构。"""

        payload: dict[str, Any] = {
            "ok": self.ok,
            "step": self.step,
        }
        if self.message:
            payload["message"] = self.message
        if self.reason:
            payload["reason"] = self.reason
        if self.secret_key:
            payload["secret_key"] = self.secret_key
        return payload


class ChatGptTwoFactorTool:
    """执行 ChatGPT Authenticator App 绑定，并生成一次性验证码完成校验。"""

    _LOG_PREFIX = "[ChatGPT 2FA]"
    _SECURITY_URL = "https://chatgpt.com/#settings/Security"

    async def setup_authenticator(self, page: Any) -> ChatGptTwoFactorSetupResult:
        """在已登录的 ChatGPT 页面上完成 2FA 绑定，成功时返回 TOTP 密钥。"""

        logger.info("%s 打开安全设置页", self._LOG_PREFIX)
        await page.get(self._SECURITY_URL)
        await asyncio.sleep(3.0)

        toggle_result = await self._toggle_authenticator_app(page)
        if toggle_result == "not_found":
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="toggle",
                reason="未找到 Authenticator app 开关，可能页面结构变动或未登录",
            )
        if toggle_result == "already_on":
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="toggle",
                reason="2FA 已经处于开启状态，当前流程无法重新提取密钥",
            )

        await asyncio.sleep(2.0)

        if not await self._open_trouble_scanning(page):
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="trouble_scanning",
                reason="未找到 Trouble scanning 按钮",
            )

        await asyncio.sleep(1.0)

        secret_key = await self._extract_secret_key(page)
        if not secret_key:
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="get_secret",
                reason="未能提取到 2FA 密钥文本",
            )
        logger.info(
            "%s 已提取 2FA 密钥 | 密钥=%s",
            self._LOG_PREFIX,
            self._mask_secret(secret_key),
        )

        try:
            current_code = self.generate_current_code(secret_key)
        except Exception as exc:  # noqa: BLE001
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="generate_totp",
                reason=f"验证码生成失败: {exc}",
            )

        input_el = await page.select("input#totp_otp", timeout=5)
        if not input_el:
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="input_code",
                reason="未找到 id 为 totp_otp 的输入框",
            )

        await input_el.click()
        await asyncio.sleep(0.2)
        for digit in current_code:
            await input_el.send_keys(digit)
            await asyncio.sleep(0.1)

        await asyncio.sleep(0.5)
        if not await self._click_verify(page):
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="verify",
                reason="未找到 Verify 按钮或按钮被禁用",
            )

        await asyncio.sleep(3.0)
        logger.info("%s 2FA 绑定完成", self._LOG_PREFIX)
        return ChatGptTwoFactorSetupResult(
            ok=True,
            step="done",
            message="2FA 绑定成功",
            secret_key=secret_key,
        )

    @staticmethod
    def generate_current_code(secret_key: str) -> str:
        """根据 TOTP 密钥计算当前 6 位验证码。"""

        normalized_secret = str(secret_key).replace(" ", "").strip()
        if not normalized_secret:
            raise ValueError("secret_key 不能为空")
        return pyotp.TOTP(normalized_secret).now()

    async def _toggle_authenticator_app(self, page: Any) -> str:
        """打开 Authenticator app 开关，返回 clicked / already_on / not_found。"""

        logger.info("%s 尝试开启 Authenticator app", self._LOG_PREFIX)
        return await page.evaluate(
            """
            (() => {
                const divs = Array.from(document.querySelectorAll('div'));
                const authSection = divs.find(d =>
                    d.textContent.includes('Authenticator app') &&
                    d.textContent.includes('Use one-time codes')
                );

                if (!authSection) {
                    return 'not_found';
                }

                const toggleBtn = authSection.querySelector('button[role="switch"]');
                if (!toggleBtn) {
                    return 'not_found';
                }

                if (toggleBtn.getAttribute('aria-checked') === 'true') {
                    return 'already_on';
                }

                toggleBtn.click();
                return 'clicked';
            })();
            """
        )

    async def _open_trouble_scanning(self, page: Any) -> bool:
        """切换到明文密钥展示区域。"""

        logger.info("%s 打开密钥文本视图", self._LOG_PREFIX)
        return bool(
            await page.evaluate(
                """
                (() => {
                    const els = Array.from(document.querySelectorAll('button, a, div'));
                    const target = els.find(e => (e.innerText || '').includes('Trouble scanning?'));
                    if (!target) {
                        return false;
                    }
                    target.click();
                    return true;
                })();
                """
            )
        )

    async def _extract_secret_key(self, page: Any) -> str | None:
        """从设置弹窗里提取 TOTP 密钥。"""

        logger.info("%s 提取 2FA 密钥", self._LOG_PREFIX)
        secret_key_raw = await page.evaluate(
            """
            (() => {
                const codeDiv = document.querySelector('div[aria-label="Copy code"]');
                if (codeDiv) {
                    return codeDiv.innerText.trim();
                }
                return null;
            })();
            """
        )
        if secret_key_raw is None:
            return None
        normalized_secret = str(secret_key_raw).replace(" ", "").strip()
        return normalized_secret or None

    async def _click_verify(self, page: Any) -> bool:
        """提交 2FA 验证码。"""

        logger.info("%s 提交 2FA 验证码", self._LOG_PREFIX)
        return bool(
            await page.evaluate(
                """
                (() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const verifyBtn = btns.find(b => (b.innerText || '').trim() === 'Verify');
                    if (verifyBtn && !verifyBtn.disabled) {
                        verifyBtn.click();
                        return true;
                    }
                    return false;
                })();
                """
            )
        )

    @staticmethod
    def _mask_secret(secret_key: str) -> str:
        """对日志里的 TOTP 密钥做脱敏，避免完整泄露。"""

        normalized = str(secret_key).strip()
        if len(normalized) <= 8:
            return "***"
        return f"{normalized[:4]}***{normalized[-4:]}"
