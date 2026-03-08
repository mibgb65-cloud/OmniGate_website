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
    _TROUBLE_SCANNING_POLL_LIMIT = 10
    _TROUBLE_SCANNING_POLL_INTERVAL_SECONDS = 1.0

    async def setup_authenticator(self, page: Any) -> ChatGptTwoFactorSetupResult:
        """在已登录的 ChatGPT 页面上完成 2FA 绑定，成功时返回 TOTP 密钥。"""

        self._log_flow(logging.INFO, "打开安全设置页", stage="页面打开")
        await page.get(self._SECURITY_URL)
        await asyncio.sleep(3.0)

        toggle_result = await self._toggle_authenticator_app(page)
        if toggle_result == "not_found":
            self._log_flow(logging.WARNING, "未找到 Authenticator app 开关", stage="开关启用")
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="toggle",
                reason="未找到 Authenticator app 开关，可能页面结构变动或未登录",
            )
        if toggle_result == "already_on":
            self._log_flow(logging.WARNING, "Authenticator app 已经开启", stage="开关启用")
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="toggle",
                reason="2FA 已经处于开启状态，当前流程无法重新提取密钥",
            )
        self._log_flow(logging.INFO, "Authenticator app 开关已点击", stage="开关启用")

        trouble_scanning_attempt = await self._open_trouble_scanning(page)
        if trouble_scanning_attempt is None:
            self._log_flow(logging.WARNING, "未找到 Trouble scanning 按钮", stage="密钥展示")
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="trouble_scanning",
                reason="未找到 Trouble scanning 按钮",
            )

        await asyncio.sleep(1.0)

        secret_key = await self._extract_secret_key(page)
        if not secret_key:
            self._log_flow(logging.WARNING, "未提取到 2FA 密钥文本", stage="密钥提取")
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="get_secret",
                reason="未能提取到 2FA 密钥文本",
            )
        self._log_flow(
            logging.INFO,
            "已提取 2FA 密钥",
            stage="密钥提取",
            extra={
                "探测次数": trouble_scanning_attempt,
                "密钥": self._mask_secret(secret_key),
            },
        )

        try:
            current_code = self.generate_current_code(secret_key)
        except Exception as exc:  # noqa: BLE001
            self._log_flow(
                logging.ERROR,
                "生成 TOTP 验证码失败",
                stage="验证码生成",
                extra={"原因": exc},
            )
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="generate_totp",
                reason=f"验证码生成失败: {exc}",
            )
        self._log_flow(
            logging.INFO,
            "已生成 TOTP 验证码",
            stage="验证码生成",
            extra={"验证码": self._mask_code(current_code)},
        )

        input_el = await page.select("input#totp_otp", timeout=5)
        if not input_el:
            self._log_flow(logging.WARNING, "未找到 2FA 验证码输入框", stage="验证码填写")
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="input_code",
                reason="未找到 id 为 totp_otp 的输入框",
            )

        self._log_flow(logging.INFO, "开始填写 TOTP 验证码", stage="验证码填写")
        await input_el.click()
        await asyncio.sleep(0.2)
        for digit in current_code:
            await input_el.send_keys(digit)
            await asyncio.sleep(0.1)

        await asyncio.sleep(0.5)
        if not await self._click_verify(page):
            self._log_flow(logging.WARNING, "Verify 按钮不可用", stage="验证码提交")
            return ChatGptTwoFactorSetupResult(
                ok=False,
                step="verify",
                reason="未找到 Verify 按钮或按钮被禁用",
            )

        await asyncio.sleep(3.0)
        self._log_flow(logging.INFO, "2FA 绑定完成", stage="流程完成")
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

        self._log_flow(logging.INFO, "尝试开启 Authenticator app", stage="开关启用")
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

    async def _open_trouble_scanning(self, page: Any) -> int | None:
        """轮询切换到明文密钥展示区域，成功时返回点击时的探测次数。"""

        self._log_flow(
            logging.INFO,
            "等待并点击 Trouble scanning 按钮",
            stage="密钥展示",
            extra={
                "最大探测次数": self._TROUBLE_SCANNING_POLL_LIMIT,
                "探测间隔秒": f"{self._TROUBLE_SCANNING_POLL_INTERVAL_SECONDS:.0f}",
            },
        )
        for attempt in range(1, self._TROUBLE_SCANNING_POLL_LIMIT + 1):
            clicked = bool(
                await page.evaluate(
                    """
                    (() => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        const target = btns.find(
                            b => (b.innerText || '').trim() === 'Trouble scanning?'
                        );
                        if (!target || target.offsetParent === null) {
                            return false;
                        }
                        target.click();
                        return true;
                    })();
                    """
                )
            )
            if clicked:
                self._log_flow(
                    logging.INFO,
                    "已点击 Trouble scanning 按钮",
                    stage="密钥展示",
                    extra={"探测次数": attempt},
                )
                return attempt

            await asyncio.sleep(self._TROUBLE_SCANNING_POLL_INTERVAL_SECONDS)

        return None

    async def _extract_secret_key(self, page: Any) -> str | None:
        """从设置弹窗里提取 TOTP 密钥。"""

        self._log_flow(logging.INFO, "提取 2FA 密钥", stage="密钥提取")
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

        self._log_flow(logging.INFO, "提交 2FA 验证码", stage="验证码提交")
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

    @staticmethod
    def _mask_code(code: str) -> str:
        """对日志里的 2FA 验证码做脱敏。"""

        normalized = str(code).strip()
        if len(normalized) <= 2:
            return "***"
        return f"{normalized[:2]}***"

    @classmethod
    def _log_flow(
        cls,
        level: int,
        message: str,
        *,
        stage: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """统一输出 ChatGPT 2FA 日志，便于和注册主链路一起追踪。"""

        context_parts = [f"阶段={stage}"]
        for key, value in (extra or {}).items():
            if value is None:
                continue
            text = str(value).strip()
            if text:
                context_parts.append(f"{key}={text}")

        logger.log(level, "%s %s | %s", cls._LOG_PREFIX, message, " | ".join(context_parts))
