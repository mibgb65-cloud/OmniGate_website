import asyncio
import logging
import random
from typing import Any

import pyotp

from src.config.config import get_settings


logger = logging.getLogger(__name__)


class ChatGPTLoginAction:
    """ChatGPT 账号自动登录动作 (支持 2FA 双重验证)。"""

    _HOME_URL = "https://chatgpt.com"
    _EMAIL_SELECTOR = 'input[name="username"], input[name="email"], input[type="email"]'
    _PASSWORD_SELECTOR = 'input[type="password"], input[name="password"]'
    _MFA_SELECTOR = 'input[inputmode="numeric"], input[name="code"], input[id="mfa-code"]'
    _PROMPT_SELECTOR = 'textarea#prompt-textarea, [id="prompt-textarea"]'
    _SUBMIT_SELECTOR = 'button[type="submit"], button[name="action"]'

    def __init__(
        self,
        *,
        element_timeout_seconds: float | None = None,
        transition_timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self._element_timeout_seconds = max(
            5.0,
            float(
                element_timeout_seconds
                if element_timeout_seconds is not None
                else settings.CHATGPT_LOGIN_ELEMENT_TIMEOUT_SECONDS
            ),
        )
        self._transition_timeout_seconds = max(
            5.0,
            float(
                transition_timeout_seconds
                if transition_timeout_seconds is not None
                else settings.CHATGPT_LOGIN_TRANSITION_TIMEOUT_SECONDS
            ),
        )

    async def login(self, page: Any, email: str, password: str, totp_secret: str | None = None) -> dict[str, Any]:
        logger.info("[*] 开始执行 ChatGPT 登录流程 | 账号: %s", self._mask_email(email))

        try:
            logger.info("[1] 打开 ChatGPT 首页...")
            await page.get(self._HOME_URL)

            home_state = await self._wait_for_home_ready(page)
            if home_state["state"] == "prompt":
                return await self._build_success_result(page, "已存在可用登录态")

            logger.info("[2] 定位并点击 Log in 按钮...")
            auth_step: dict[str, Any] | None = None
            if home_state["state"] in {"email", "password"}:
                auth_step = home_state
            else:
                login_btn = home_state.get("login_button") or await self._wait_for_login_button(
                    page,
                    timeout_seconds=self._element_timeout_seconds,
                )
                if login_btn:
                    await login_btn.click()
                else:
                    logger.warning("未找到首页 Log in 按钮，尝试继续检测认证页元素...")
                auth_step = await self._wait_for_auth_step(page, timeout_seconds=self._transition_timeout_seconds)

            if auth_step is None:
                return {"ok": False, "step": "input_email", "reason": "未找到邮箱或密码输入框 (可能被 Cloudflare 盾拦截)"}

            password_input = None
            if auth_step["state"] == "email":
                logger.info("[3] 定位并输入邮箱...")
                email_input = auth_step["element"]
                await self._type_text(email_input, email)
                await self._submit_form(primary_input=email_input, page=page)

                logger.info("[4] 等待并输入密码...")
                password_input = await self._wait_for_password_input(page, timeout_seconds=self._transition_timeout_seconds)
                if not password_input:
                    return {"ok": False, "step": "input_password", "reason": "未找到密码输入框"}
            else:
                logger.info("[3] 检测到已进入密码页，跳过邮箱输入")
                logger.info("[4] 等待并输入密码...")
                password_input = auth_step["element"]

            await self._type_text(password_input, password)
            await self._submit_form(primary_input=password_input, page=page)

            logger.info("[5] 提交密码，等待 Auth0 校验跳转...")
            post_password_state = await self._wait_for_post_password_state(
                page,
                timeout_seconds=self._transition_timeout_seconds,
            )

            if post_password_state["state"] == "mfa":
                logger.info("[6] 检测到 2FA (MFA) 拦截，准备输入动态码...")
                if not totp_secret:
                    return {"ok": False, "step": "2fa_required", "reason": "账号已开启 2FA，但未传入 totp_secret 秘钥"}

                mfa_input = post_password_state.get("element") or await self._wait_for_mfa_input(
                    page,
                    timeout_seconds=self._element_timeout_seconds,
                )
                if not mfa_input:
                    return {"ok": False, "step": "input_2fa", "reason": "处于 2FA 页面但未找到输入框"}

                try:
                    totp = pyotp.TOTP(totp_secret.replace(" ", ""))
                    current_code = totp.now()
                    logger.info("[*] 计算得出 2FA 验证码: %s", current_code)
                except Exception as exc:  # noqa: BLE001
                    return {"ok": False, "step": "generate_totp", "reason": f"验证码生成失败: {exc}"}

                await self._type_text(mfa_input, current_code)
                await self._submit_form(primary_input=mfa_input, page=page)

                logger.info("[7] 2FA 已提交，等待最终跳转...")
                prompt_textarea = await self._wait_for_prompt_textarea(
                    page,
                    timeout_seconds=self._transition_timeout_seconds,
                )
                if prompt_textarea:
                    return await self._build_success_result(page, "登录成功")
            elif post_password_state["state"] == "prompt":
                return await self._build_success_result(page, "登录成功")
            elif post_password_state["state"] == "error":
                return {"ok": False, "step": "verify_login", "reason": post_password_state["reason"]}

            prompt_textarea = await self._wait_for_prompt_textarea(
                page,
                timeout_seconds=self._transition_timeout_seconds,
            )
            if prompt_textarea:
                return await self._build_success_result(page, "登录成功")

            final_url = await self._get_current_url(page)
            logger.warning("[!] 登录状态存疑，当前 URL: %s", final_url)
            error_msg = await self._extract_login_error(page)
            return {
                "ok": False,
                "step": "verify_login",
                "reason": f"未能成功到达聊天界面。提示: {error_msg}",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ 登录流程发生异常: %s", exc)
            return {"ok": False, "step": "exception", "reason": str(exc)}

    async def _wait_for_home_ready(self, page: Any) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + self._element_timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            prompt = await self._query_prompt_textarea(page)
            if prompt:
                return {"state": "prompt", "element": prompt}

            auth_step = await self._query_auth_step(page)
            if auth_step is not None:
                return auth_step

            login_button = await self._query_login_button(page)
            if login_button:
                return {"state": "login", "login_button": login_button}

            await asyncio.sleep(0.5)
        return {"state": "unknown"}

    async def _wait_for_auth_step(self, page: Any, *, timeout_seconds: float) -> dict[str, Any] | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            auth_step = await self._query_auth_step(page)
            if auth_step is not None:
                return auth_step
            await asyncio.sleep(0.5)
        return None

    async def _wait_for_login_button(self, page: Any, *, timeout_seconds: float) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            login_button = await self._query_login_button(page)
            if login_button:
                return login_button
            await asyncio.sleep(0.5)
        return None

    async def _wait_for_password_input(self, page: Any, *, timeout_seconds: float) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            password_input = await self._try_select(page, self._PASSWORD_SELECTOR)
            if password_input:
                return password_input
            await asyncio.sleep(0.5)
        return None

    async def _wait_for_mfa_input(self, page: Any, *, timeout_seconds: float) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            mfa_input = await self._query_mfa_input(page)
            if mfa_input:
                return mfa_input
            await asyncio.sleep(0.5)
        return None

    async def _wait_for_prompt_textarea(self, page: Any, *, timeout_seconds: float) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            prompt = await self._query_prompt_textarea(page)
            if prompt:
                return prompt
            await asyncio.sleep(0.5)
        return None

    async def _wait_for_post_password_state(self, page: Any, *, timeout_seconds: float) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            prompt = await self._query_prompt_textarea(page)
            if prompt:
                return {"state": "prompt", "element": prompt}

            current_url = (await self._get_current_url(page)).lower()
            mfa_input = await self._query_mfa_input(page)
            if mfa_input or "mfa" in current_url or "two-factor" in current_url:
                return {"state": "mfa", "element": mfa_input}

            error_msg = await self._extract_login_error(page)
            if error_msg != "未检测到明显错误提示":
                return {"state": "error", "reason": error_msg}

            await asyncio.sleep(0.5)
        return {"state": "timeout"}

    async def _query_auth_step(self, page: Any) -> dict[str, Any] | None:
        email_input = await self._try_select(page, self._EMAIL_SELECTOR)
        if email_input:
            return {"state": "email", "element": email_input}

        password_input = await self._try_select(page, self._PASSWORD_SELECTOR)
        if password_input:
            return {"state": "password", "element": password_input}
        return None

    async def _query_login_button(self, page: Any) -> Any | None:
        try:
            login_btn = await page.find("Log in", timeout=1) or await page.find("登录", timeout=1)
            if login_btn:
                return login_btn
        except Exception:  # noqa: BLE001
            pass
        return await self._try_select(page, '[data-testid="login-button"]')

    async def _query_mfa_input(self, page: Any) -> Any | None:
        mfa_input = await self._try_select(page, self._MFA_SELECTOR)
        if mfa_input:
            return mfa_input
        return await self._try_select(page, 'input[inputmode="numeric"]')

    async def _query_prompt_textarea(self, page: Any) -> Any | None:
        return await self._try_select(page, self._PROMPT_SELECTOR)

    async def _submit_form(self, *, primary_input: Any, page: Any) -> None:
        await asyncio.sleep(0.5)
        submit_btn = await self._try_select(page, self._SUBMIT_SELECTOR)
        if submit_btn:
            await submit_btn.click()
            return
        await primary_input.send_keys("\n")

    async def _type_text(self, input_element: Any, text: str) -> None:
        await input_element.click()
        await asyncio.sleep(random.uniform(0.1, 0.3))
        for char in text:
            await input_element.send_keys(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def _build_success_result(self, page: Any, message: str) -> dict[str, Any]:
        final_url = await self._get_current_url(page)
        logger.info("🎉 ChatGPT 登录操作成功，已到达聊天界面！")
        return {"ok": True, "step": "done", "message": message, "final_url": final_url}

    async def _extract_login_error(self, page: Any) -> str:
        try:
            return str(
                await page.evaluate(
                    """
                    (() => {
                        const err = document.querySelector('[data-error], .error-message, .alert-error, form span, .cf-error-details');
                        return err ? err.innerText.trim() : '未检测到明显错误提示';
                    })();
                    """
                )
                or "未检测到明显错误提示"
            )
        except Exception:  # noqa: BLE001
            return "未检测到明显错误提示"

    async def _get_current_url(self, page: Any) -> str:
        try:
            return str(await page.evaluate("window.location.href") or "")
        except Exception:  # noqa: BLE001
            return ""

    async def _try_select(self, page: Any, selector: str) -> Any | None:
        try:
            return await page.select(selector, timeout=1)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _mask_email(email: str) -> str:
        normalized = email.strip()
        if "@" not in normalized:
            return normalized
        local_part, domain = normalized.split("@", 1)
        if len(local_part) <= 4:
            masked_local = f"{local_part[:1]}***"
        else:
            masked_local = f"{local_part[:2]}***{local_part[-2:]}"
        return f"{masked_local}@{domain}"


# ==========================================
# 独立测试入口
# ==========================================
async def main():
    import nodriver as uc
    browser = await uc.start()
    page = await browser.get("data:,")

    action = ChatGPTLoginAction()

    # 替换为真实的测试数据
    test_email = "x3i15ssao8pk@198994216.xyz"
    test_password = "31<ABrI|NQe#B"
    totp_secret = "DRGZ4IICMR5OQ4BKZRTG7YNBJNHSAUQ5"  # 如果没有 2FA，传 None

    result = await action.login(page, test_email, test_password, totp_secret)

    print("\n=== 执行结果 ===")
    print(result)

    print("\n🛑 测试结束，浏览器保留开启状态供调试...")
    # 故意不关闭 browser，方便你观察页面停留在哪里
    await asyncio.sleep(3600)


if __name__ == "__main__":
    # 配置基础日志输出
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main())
