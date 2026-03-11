import asyncio
import logging
import random
from typing import Any

import pyotp

from src.config.config import get_settings


logger = logging.getLogger(__name__)


class ChatGPTLoginAction:
    """ChatGPT 账号自动登录动作 (支持 2FA 双重验证)。"""

    _LOG_PREFIX = "[ChatGPT登录]"
    _TOTAL_STEPS = 7
    _HOME_URL = "https://chatgpt.com"
    _EMAIL_SELECTOR = 'input[name="username"], input[name="email"], input[type="email"]'
    _PASSWORD_SELECTOR = 'input[type="password"], input[name="password"]'
    _MFA_SELECTOR = 'input[inputmode="numeric"], input[name="code"], input[id="mfa-code"]'
    _PROMPT_SELECTOR = 'textarea#prompt-textarea, [id="prompt-textarea"]'
    _SUBMIT_SELECTOR = 'button[type="submit"], button[name="action"]'
    _SELECT_QUERY_TIMEOUT_SECONDS = 2.0
    _FINAL_SELECTOR_TIMEOUT_SECONDS = 5.0
    _POLL_INTERVAL_SECONDS = 0.5

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
        self._log_flow(
            logging.INFO,
            "开始执行登录流程",
            email=email,
            extra={
                "element_timeout_seconds": f"{self._element_timeout_seconds:.0f}",
                "transition_timeout_seconds": f"{self._transition_timeout_seconds:.0f}",
            },
        )

        try:
            self._log_flow(logging.INFO, "打开 ChatGPT 首页", step_no=1, total_steps=self._TOTAL_STEPS, email=email)
            await page.get(self._HOME_URL)

            home_state = await self._wait_for_home_ready(page)
            if home_state["state"] == "prompt":
                return await self._build_success_result(page, "已存在可用登录态")

            self._log_flow(logging.INFO, "定位并点击 Log in 按钮", step_no=2, total_steps=self._TOTAL_STEPS, email=email)
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
                    self._log_flow(
                        logging.WARNING,
                        "未找到首页 Log in 按钮，尝试继续检测认证页元素",
                        step_no=2,
                        total_steps=self._TOTAL_STEPS,
                        email=email,
                    )
                auth_step = await self._wait_for_auth_step(page, timeout_seconds=self._transition_timeout_seconds)

            if auth_step is None:
                return {"ok": False, "step": "input_email", "reason": "未找到邮箱或密码输入框 (可能被 Cloudflare 盾拦截)"}

            password_input = None
            if auth_step["state"] == "email":
                self._log_flow(logging.INFO, "定位并输入邮箱", step_no=3, total_steps=self._TOTAL_STEPS, email=email)
                email_input = auth_step["element"]
                await self._type_text(email_input, email)
                await self._submit_form(primary_input=email_input, page=page)

                self._log_flow(logging.INFO, "等待并输入密码", step_no=4, total_steps=self._TOTAL_STEPS, email=email)
                password_input = await self._wait_for_password_input(page, timeout_seconds=self._transition_timeout_seconds)
                if not password_input:
                    return {"ok": False, "step": "input_password", "reason": "未找到密码输入框"}
            else:
                self._log_flow(
                    logging.INFO,
                    "检测到已进入密码页，跳过邮箱输入",
                    step_no=3,
                    total_steps=self._TOTAL_STEPS,
                    email=email,
                )
                self._log_flow(logging.INFO, "等待并输入密码", step_no=4, total_steps=self._TOTAL_STEPS, email=email)
                password_input = auth_step["element"]

            await self._type_text(password_input, password)
            await self._submit_form(primary_input=password_input, page=page)

            self._log_flow(logging.INFO, "提交密码，等待 Auth0 校验跳转", step_no=5, total_steps=self._TOTAL_STEPS, email=email)
            post_password_state = await self._wait_for_post_password_state(
                page,
                timeout_seconds=self._transition_timeout_seconds,
            )

            if post_password_state["state"] == "mfa":
                self._log_flow(
                    logging.INFO,
                    "检测到 2FA(MFA) 拦截，准备输入动态码",
                    step_no=6,
                    total_steps=self._TOTAL_STEPS,
                    email=email,
                )
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
                    self._log_flow(
                        logging.INFO,
                        "已生成 2FA 验证码",
                        step_no=6,
                        total_steps=self._TOTAL_STEPS,
                        email=email,
                        extra={"code": self._mask_code(current_code)},
                    )
                except Exception as exc:  # noqa: BLE001
                    return {"ok": False, "step": "generate_totp", "reason": f"验证码生成失败: {exc}"}

                await self._type_text(mfa_input, current_code)
                await self._submit_form(primary_input=mfa_input, page=page)

                self._log_flow(
                    logging.INFO,
                    "2FA 已提交，等待最终跳转",
                    step_no=7,
                    total_steps=self._TOTAL_STEPS,
                    email=email,
                )
                post_mfa_state = await self._wait_for_post_mfa_state(
                    page,
                    timeout_seconds=self._transition_timeout_seconds,
                )
                if post_mfa_state["state"] == "prompt":
                    return await self._build_success_result(page, "登录成功")
                if post_mfa_state["state"] == "workspace":
                    return await self._finalize_workspace_state(page)
                if post_mfa_state["state"] == "error":
                    return {"ok": False, "step": "verify_login", "reason": post_mfa_state["reason"]}
            elif post_password_state["state"] == "prompt":
                return await self._build_success_result(page, "登录成功")
            elif post_password_state["state"] == "workspace":
                return await self._finalize_workspace_state(page)
            elif post_password_state["state"] == "error":
                return {"ok": False, "step": "verify_login", "reason": post_password_state["reason"]}

            prompt_textarea = await self._wait_for_prompt_textarea(
                page,
                timeout_seconds=self._transition_timeout_seconds,
            )
            if prompt_textarea:
                return await self._build_success_result(page, "登录成功")

            final_url = await self._get_current_url(page)
            if self._is_workspace_url(final_url):
                return await self._finalize_workspace_state(page)
            self._log_flow(
                logging.WARNING,
                "登录状态存疑",
                step_no=self._TOTAL_STEPS,
                total_steps=self._TOTAL_STEPS,
                email=email,
                extra={"current_url": final_url},
            )
            error_msg = await self._extract_login_error(page)
            return {
                "ok": False,
                "step": "verify_login",
                "reason": f"未能成功到达聊天界面。提示: {error_msg}",
            }
        except Exception as exc:  # noqa: BLE001
            self._log_flow(logging.ERROR, "登录流程发生异常", email=email, extra={"reason": exc})
            return {"ok": False, "step": "exception", "reason": str(exc)}

    async def _wait_for_home_ready(self, page: Any) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + self._element_timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            auth_step = await self._query_auth_step(page)
            if auth_step is not None:
                return auth_step

            login_button = await self._query_login_button(page)
            if login_button:
                return {"state": "login", "login_button": login_button}

            prompt = await self._query_logged_in_prompt(page)
            if prompt:
                return {"state": "prompt", "element": prompt}

            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)
        return {"state": "unknown"}

    async def _wait_for_auth_step(self, page: Any, *, timeout_seconds: float) -> dict[str, Any] | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            auth_step = await self._query_auth_step(page)
            if auth_step is not None:
                return auth_step
            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)

        email_input = await self._try_select(
            page,
            self._EMAIL_SELECTOR,
            timeout_seconds=min(self._FINAL_SELECTOR_TIMEOUT_SECONDS, timeout_seconds),
        )
        if email_input:
            return {"state": "email", "element": email_input}

        password_input = await self._try_select(
            page,
            self._PASSWORD_SELECTOR,
            timeout_seconds=min(self._FINAL_SELECTOR_TIMEOUT_SECONDS, timeout_seconds),
        )
        if password_input:
            return {"state": "password", "element": password_input}
        return None

    async def _wait_for_login_button(self, page: Any, *, timeout_seconds: float) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            login_button = await self._query_login_button(page)
            if login_button:
                return login_button
            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)
        return await self._try_select(
            page,
            '[data-testid="login-button"]',
            timeout_seconds=min(self._FINAL_SELECTOR_TIMEOUT_SECONDS, timeout_seconds),
        )

    async def _wait_for_password_input(self, page: Any, *, timeout_seconds: float) -> Any | None:
        return await self._wait_for_selector(page, self._PASSWORD_SELECTOR, timeout_seconds=timeout_seconds)

    async def _wait_for_mfa_input(self, page: Any, *, timeout_seconds: float) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            mfa_input = await self._query_mfa_input(page)
            if mfa_input:
                return mfa_input
            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)
        return await self._try_select(
            page,
            self._MFA_SELECTOR,
            timeout_seconds=min(self._FINAL_SELECTOR_TIMEOUT_SECONDS, timeout_seconds),
        )

    async def _wait_for_prompt_textarea(self, page: Any, *, timeout_seconds: float) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            prompt = await self._query_logged_in_prompt(page)
            if prompt:
                return prompt
            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)
        return None

    async def _wait_for_post_password_state(self, page: Any, *, timeout_seconds: float) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            prompt = await self._query_logged_in_prompt(page)
            if prompt:
                return {"state": "prompt", "element": prompt}

            current_url = (await self._get_current_url(page)).lower()
            if self._is_workspace_url(current_url):
                return {"state": "workspace"}

            mfa_input = await self._query_mfa_input(page)
            if mfa_input or "mfa" in current_url or "two-factor" in current_url:
                return {"state": "mfa", "element": mfa_input}

            error_msg = await self._extract_login_error(page)
            if error_msg != "未检测到明显错误提示":
                return {"state": "error", "reason": error_msg}

            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)
        return {"state": "timeout"}

    async def _wait_for_post_mfa_state(self, page: Any, *, timeout_seconds: float) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            prompt = await self._query_logged_in_prompt(page)
            if prompt:
                return {"state": "prompt", "element": prompt}

            current_url = (await self._get_current_url(page)).lower()
            if self._is_workspace_url(current_url):
                return {"state": "workspace"}

            error_msg = await self._extract_login_error(page)
            if error_msg != "未检测到明显错误提示":
                return {"state": "error", "reason": error_msg}

            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)
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

    async def _wait_for_selector(self, page: Any, selector: str, *, timeout_seconds: float) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            element = await self._try_select(page, selector)
            if element:
                return element
            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)
        return await self._try_select(
            page,
            selector,
            timeout_seconds=min(self._FINAL_SELECTOR_TIMEOUT_SECONDS, timeout_seconds),
        )

    async def _query_logged_in_prompt(self, page: Any) -> Any | None:
        prompt = await self._query_prompt_textarea(page)
        if not prompt:
            return None

        auth_step = await self._query_auth_step(page)
        if auth_step is not None:
            return None

        login_button = await self._query_login_button(page)
        if login_button:
            return None

        current_url = (await self._get_current_url(page)).lower()
        if any(token in current_url for token in ("/auth/", "/login", "/signup", "auth.openai.com", "auth0")):
            return None

        return prompt

    async def _finalize_workspace_state(self, page: Any) -> dict[str, Any]:
        workspace_url = await self._get_current_url(page)
        self._log_flow(
            logging.INFO,
            "检测到 Workspace 中间页，尝试返回 ChatGPT 首页完成收口",
            step_no=self._TOTAL_STEPS,
            total_steps=self._TOTAL_STEPS,
            extra={"workspace_url": workspace_url},
        )

        try:
            await page.get(self._HOME_URL)
            prompt = await self._wait_for_prompt_textarea(
                page,
                timeout_seconds=min(self._element_timeout_seconds, 15.0),
            )
            if prompt:
                return await self._build_success_result(page, "登录成功（已通过 Workspace 中间页）")
        except Exception as exc:  # noqa: BLE001
            self._log_flow(logging.WARNING, "Workspace 收口跳转异常", extra={"reason": exc})

        final_url = await self._get_current_url(page)
        if self._is_workspace_url(final_url):
            self._log_flow(
                logging.INFO,
                "仍停留在 Workspace 中间页，按已认证状态继续后续 Session 抓取",
                step_no=self._TOTAL_STEPS,
                total_steps=self._TOTAL_STEPS,
                extra={"workspace_url": final_url},
            )
            return await self._build_success_result(page, "登录成功（停留在 Workspace 中间页）")

        error_msg = await self._extract_login_error(page)
        return {
            "ok": False,
            "step": "verify_login",
            "reason": f"Workspace 跳转未完成。提示: {error_msg}",
        }

    @staticmethod
    def _is_workspace_url(url: str) -> bool:
        normalized = str(url or "").strip().lower()
        return "auth.openai.com/workspace" in normalized or normalized.endswith("/workspace")

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
        self._log_flow(
            logging.INFO,
            "登录流程完成",
            step_no=self._TOTAL_STEPS,
            total_steps=self._TOTAL_STEPS,
            extra={"message": message, "final_url": final_url},
        )
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

    async def _try_select(self, page: Any, selector: str, *, timeout_seconds: float | None = None) -> Any | None:
        try:
            return await page.select(selector, timeout=timeout_seconds or self._SELECT_QUERY_TIMEOUT_SECONDS)
        except Exception:  # noqa: BLE001
            return None

    @classmethod
    def _log_flow(
        cls,
        level: int,
        message: str,
        *,
        step_no: int | None = None,
        total_steps: int | None = None,
        email: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        context_parts: list[str] = []
        if step_no is not None and total_steps is not None:
            context_parts.append(f"步骤={step_no}/{total_steps}")
        if email:
            context_parts.append(f"邮箱={cls._mask_email(email)}")
        for key, value in (extra or {}).items():
            if value is None:
                continue
            text = str(value).strip()
            if text:
                context_parts.append(f"{key}={text}")

        if context_parts:
            logger.log(level, "%s %s | %s", cls._LOG_PREFIX, message, " | ".join(context_parts))
            return
        logger.log(level, "%s %s", cls._LOG_PREFIX, message)

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

    @staticmethod
    def _mask_code(code: str) -> str:
        normalized = str(code).strip()
        if len(normalized) <= 2:
            return "***"
        return f"{normalized[:2]}***"


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
