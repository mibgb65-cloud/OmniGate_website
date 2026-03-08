"""OpenAI 注册与登录处理动作。"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
import logging
import random
from typing import Any

import asyncpg

from src.browser.browser_actions import BrowserActions
from src.modules.chatgpt.actions.chatgpt_2fa_action import ChatGPT2FAAction
from src.modules.chatgpt.utils.account_generator import (
    generate_random_email,
    generate_random_name,
    generate_random_password,
)
from src.modules.cloudmail.models.cloudmail_service_params import GetChatGptVerificationCodeParams
from src.modules.cloudmail.services import (
    CloudMailVerificationPendingError,
    GetChatGptVerificationCodeService,
)


logger = logging.getLogger(__name__)


class OpenAISignupService:
    """处理 ChatGPT 账号登录/注册，并在注册时自动从 CloudMail 拉取验证码。"""

    _LOG_PREFIX = "[ChatGPT注册]"

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        actions: BrowserActions | None = None,
        verification_code_service: GetChatGptVerificationCodeService | None = None,
        two_factor_action: ChatGPT2FAAction | None = None,
    ) -> None:
        self.actions = actions or BrowserActions()
        self._db_pool = db_pool
        self._verification_code_service = verification_code_service or (
            GetChatGptVerificationCodeService(db_pool=db_pool) if db_pool is not None else None
        )
        self._two_factor_action = two_factor_action or ChatGPT2FAAction()

    async def process_account(
        self,
    ) -> dict[str, Any]:
        """
        处理账号流程。

        账号、密码、姓名全部在内部自动生成，不接受外部传入。
        浏览器在流程结束后自动关闭。
        """

        async with self.actions.browser_lifespan() as browser:
            return await self.process_account_with_browser(browser)

    async def process_account_with_browser(
        self,
        browser: Any,
    ) -> dict[str, Any]:
        """在外部已启动的浏览器实例上执行一轮注册/登录流程。"""

        resolved_email, resolved_password, resolved_name = await self._resolve_account_inputs()
        self._log_flow(
            logging.INFO,
            "开始处理账号",
            stage="账号准备",
            email=resolved_email,
        )
        return await self._process_account_flow(
            browser=browser,
            email=resolved_email,
            password=resolved_password,
            name=resolved_name,
        )

    async def _process_account_flow(
        self,
        *,
        browser: Any,
        email: str,
        password: str,
        name: str,
    ) -> dict[str, Any]:
        try:
            await self._reset_browser_state(browser)

            self._log_flow(logging.INFO, "打开 ChatGPT 首页", stage="页面打开", email=email)
            page = await self.actions.open_page(browser, "https://chatgpt.com")
            await asyncio.sleep(4)

            self._log_flow(logging.INFO, "定位登录入口", stage="入口定位", email=email)
            login_btn = await page.find("Log in", timeout=5) or await page.find("登录", timeout=5)
            if not login_btn:
                login_btn = await page.select('[data-testid="login-button"]', timeout=5)
            if login_btn:
                await login_btn.click()
            await asyncio.sleep(2)

            self._log_flow(logging.INFO, "定位邮箱输入框", stage="邮箱输入", email=email)
            email_input = await page.select(
                'input[name="username"], input[name="email"], input[type="email"]',
                timeout=10,
            )
            if not email_input:
                raise TimeoutError("Email input field not found")

            self._log_flow(logging.INFO, "输入注册邮箱", stage="邮箱输入", email=email)
            for char in email:
                await email_input.send_keys(char)
                await asyncio.sleep(random.uniform(0.05, 0.2))
            await asyncio.sleep(0.5)

            self._log_flow(logging.INFO, "提交邮箱", stage="邮箱提交", email=email)
            continue_btn = await page.select('button[type="submit"], button[name="action"]', timeout=5)
            if continue_btn:
                await continue_btn.click()

            self._log_flow(logging.INFO, "等待密码输入页", stage="分支识别", email=email)
            try:
                password_element = await page.select(
                    'input[type="password"], input[name="password"]',
                    timeout=20,
                )
                if not password_element:
                    raise TimeoutError("Password element not found")

                current_url = await page.evaluate("window.location.href")
                page_text = (await page.get_content()).lower()

                if (
                    "welcome back" in page_text
                    or "enter your password" in page_text
                    or "login/password" in current_url
                ):
                    self._log_flow(logging.INFO, "检测到已注册账号，进入登录分支", stage="登录分支", email=email)
                    await self._type_password(page, password_element, password)
                    return {
                        "status": "REGISTERED_LOGIN_ATTEMPTED",
                        "email": email,
                        "password": password,
                        "name": name,
                        "msg": "账号已存在，已输入密码",
                    }

                if (
                    "create your account" in page_text
                    or "create a password" in page_text
                    or "create-account/password" in current_url
                ):
                    self._log_flow(logging.INFO, "检测到未注册账号，进入注册分支", stage="注册分支", email=email)
                    await self._type_password(page, password_element, password)
                    return await self._handle_full_registration_flow(
                        page,
                        email,
                        password,
                        name,
                    )

                self._log_flow(
                    logging.WARNING,
                    "已找到密码框，但页面状态未识别",
                    stage="分支识别",
                    email=email,
                )
                await page.save_screenshot("debug_unknown_state.png")
                return {
                    "status": "UNKNOWN",
                    "email": email,
                    "password": password,
                    "name": name,
                    "msg": "未知状态，可能被风控或页面改版",
                }

            except Exception as exc:  # noqa: BLE001
                current_url = await page.evaluate("window.location.href")
                self._log_flow(
                    logging.WARNING,
                    "等待密码输入页超时",
                    stage="分支识别",
                    email=email,
                    extra={"当前URL": current_url},
                )
                self._log_flow(
                    logging.ERROR,
                    "密码输入页处理失败",
                    stage="分支识别",
                    email=email,
                    extra={"原因": exc},
                )
                await page.save_screenshot("debug_timeout_no_password_box.png")
                return {
                    "status": "TIMEOUT_OR_BLOCKED",
                    "email": email,
                    "password": password,
                    "name": name,
                    "msg": f"发生错误或被拦截: {exc}",
                }

        except Exception as exc:  # noqa: BLE001
            logger.exception("%s 注册流程发生未处理异常 | 阶段=流程异常 | 邮箱=%s", self._LOG_PREFIX, self._mask_email(email))
            return {
                "status": "ERROR",
                "email": email,
                "password": password,
                "name": name,
                "msg": str(exc),
            }

    async def _handle_full_registration_flow(
        self,
        page: Any,
        email: str,
        password: str,
        name: str,
    ) -> dict[str, Any]:
        """处理设置密码之后的注册流水线：接码 -> 填姓名生日 -> 清理引导弹窗 -> 配置 2FA。"""

        self._log_flow(logging.INFO, "开始从 CloudMail 轮询验证码", stage="验证码轮询", email=email)
        try:
            otp_code = await self._wait_for_verification_code(email, timeout_seconds=90, poll_interval_seconds=5.0)
            self._log_flow(logging.INFO, "验证码已获取", stage="验证码轮询", email=email)
        except Exception as exc:  # noqa: BLE001
            self._log_flow(
                logging.ERROR,
                "验证码获取失败",
                stage="验证码轮询",
                email=email,
                extra={"原因": exc},
            )
            await page.save_screenshot("debug_otp_failed.png")
            return {
                "status": "OTP_FAILED",
                "email": email,
                "password": password,
                "name": name,
                "msg": f"邮箱接码失败: {exc}",
            }

        self._log_flow(logging.INFO, "等待验证码输入框", stage="验证码填写", email=email)
        try:
            otp_input = await page.select('input[inputmode="numeric"], input[name="code"], .code-input', timeout=20)
            if not otp_input:
                raise TimeoutError("OTP input field not found")

            for char in otp_code:
                await otp_input.send_keys(char)
                await asyncio.sleep(random.uniform(0.05, 0.2))

            await asyncio.sleep(1.5)
            try:
                otp_continue_btn = await page.select('button[type="submit"]', timeout=5)
                if otp_continue_btn:
                    await otp_continue_btn.click()
                else:
                    await otp_input.send_keys("\n")
            except Exception as exc:  # noqa: BLE001
                self._log_flow(
                    logging.ERROR,
                    "提交验证码时点击继续按钮失败，回退为回车提交",
                    stage="验证码填写",
                    email=email,
                    extra={"原因": exc},
                )
                await otp_input.send_keys("\n")

        except Exception as exc:  # noqa: BLE001
            self._log_flow(
                logging.WARNING,
                "验证码填写阶段失败",
                stage="验证码填写",
                email=email,
                extra={"原因": exc},
            )
            await page.save_screenshot("debug_otp_input_failed.png")
            return {
                "status": "OTP_INPUT_FAILED",
                "email": email,
                "password": password,
                "name": name,
                "msg": "找不到验证码输入框",
            }

        self._log_flow(logging.INFO, "验证码已提交，等待资料页加载", stage="资料填写", email=email)
        try:
            name_input = await page.select(
                'input[name="fullname"], input[name="name"], input[name="first-name"]',
                timeout=20,
            )
            if not name_input:
                raise TimeoutError("Name input field not found")

            for char in name:
                await name_input.send_keys(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            birthday = self._generate_random_adult_birthday(min_age=20, max_age=40)
            month_text = birthday.strftime("%m")
            day_text = birthday.strftime("%d")
            year_text = birthday.strftime("%Y")
            self._log_flow(
                logging.INFO,
                "开始填写生日信息",
                stage="资料填写",
                email=email,
                extra={"生日": f"{month_text}/{day_text}/{year_text}"},
            )

            month_input = await page.select('div[data-type="month"]', timeout=5)
            if month_input:
                await month_input.click()
                await asyncio.sleep(0.5)
                for _ in range(3):
                    await month_input.send_keys("\b")
                for char in month_text:
                    await month_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))

            day_input = await page.select('div[data-type="day"]', timeout=5)
            if day_input:
                await day_input.click()
                await asyncio.sleep(0.5)
                for _ in range(3):
                    await day_input.send_keys("\b")
                for char in day_text:
                    await day_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))

            year_input = await page.select('div[data-type="year"]', timeout=5)
            if year_input:
                await year_input.click()
                await asyncio.sleep(0.5)
                for _ in range(5):
                    await year_input.send_keys("\b")
                for char in year_text:
                    await year_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))

            await asyncio.sleep(1.5)
            agree_btn = await page.select('button[type="submit"]', timeout=5)
            if agree_btn:
                await agree_btn.click()

            self._log_flow(logging.INFO, "等待并清理新手引导", stage="引导清理", email=email)
            await asyncio.sleep(4)
            js_hunter = r"""
            (() => {
                const targetTexts = ["skip", "skip tour", "continue", "next", "okay, let's go", "okay, let’s go", "done", "got it"];
                const elements = document.querySelectorAll('button, a, [role="button"], div, span');

                for (const el of elements) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;

                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                    if (el.tagName !== 'BUTTON' && el.tagName !== 'A' && el.children.length > 0) continue;

                    const text = (el.innerText || el.textContent || "").replace(/\s+/g, ' ').trim().toLowerCase();
                    if (targetTexts.includes(text)) {
                        el.click();
                        el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
                        el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
                        return text;
                    }
                }
                return null;
            })();
            """

            for _ in range(20):
                try:
                    clicked_text = await page.evaluate(js_hunter)
                    if clicked_text:
                        self._log_flow(
                            logging.INFO,
                            "已点击引导弹窗按钮",
                            stage="引导清理",
                            email=email,
                            extra={"按钮": clicked_text},
                        )
                        await asyncio.sleep(1.5)
                    else:
                        await asyncio.sleep(1)
                except Exception:  # noqa: BLE001
                    await asyncio.sleep(1)

        except Exception as exc:  # noqa: BLE001
            self._log_flow(
                logging.WARNING,
                "资料填写或引导清理阶段异常",
                stage="资料填写",
                email=email,
                extra={"原因": exc},
            )
            await page.save_screenshot("debug_profile_or_onboarding_failed.png")
            return {
                "status": "PROFILE_FAILED",
                "email": email,
                "password": password,
                "name": name,
                "msg": "账号已创建，但后续资料填写或引导清理异常",
            }

        self._log_flow(logging.INFO, "开始配置账号 2FA", stage="2FA配置", email=email)
        try:
            totp_secret = await self._setup_two_factor(page, email)
        except Exception as exc:  # noqa: BLE001
            self._log_flow(
                logging.ERROR,
                "2FA 配置失败",
                stage="2FA配置",
                email=email,
                extra={"原因": exc},
            )
            await page.save_screenshot("debug_2fa_failed.png")
            return {
                "status": "TWO_FACTOR_FAILED",
                "email": email,
                "password": password,
                "name": name,
                "msg": f"账号已创建，但 2FA 配置失败: {exc}",
            }

        self._log_flow(logging.INFO, "注册与 2FA 配置完成", stage="流程完成", email=email)
        return {
            "status": "REGISTERED_SUCCESS",
            "email": email,
            "password": password,
            "name": name,
            "totp_secret": totp_secret,
            "msg": "注册成功，已完成资料填写、引导清理和 2FA 绑定",
        }

    async def _type_password(self, page: Any, password_element: Any, password: str) -> None:
        """仿生输入密码并点击继续按钮。"""

        for char in password:
            await password_element.send_keys(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

        await asyncio.sleep(1.5)
        try:
            continue_btn = await page.select('button[type="submit"]', timeout=5)
            if continue_btn:
                await continue_btn.click()
            else:
                await password_element.send_keys("\n")
        except Exception as exc:  # noqa: BLE001
            self._log_flow(
                logging.ERROR,
                "提交密码时点击继续按钮失败，回退为回车提交",
                stage="密码提交",
                extra={"原因": exc},
            )
            await password_element.send_keys("\n")
        await asyncio.sleep(2)

    async def _resolve_account_inputs(
        self,
    ) -> tuple[str, str, str]:
        """内部自动生成邮箱、密码和姓名。"""

        if self._db_pool is None:
            raise ValueError("缺少 db_pool，无法生成随机注册邮箱")

        resolved_email = await generate_random_email(db_pool=self._db_pool)
        resolved_password = generate_random_password()
        resolved_name = generate_random_name()
        return resolved_email, resolved_password, resolved_name

    async def _wait_for_verification_code(
        self,
        email: str,
        *,
        timeout_seconds: float,
        poll_interval_seconds: float,
    ) -> str:
        """轮询 CloudMail，直到拿到验证码或超时。"""

        deadline = asyncio.get_running_loop().time() + timeout_seconds

        while True:
            try:
                return await self._fetch_verification_code(email)
            except CloudMailVerificationPendingError as exc:
                now = asyncio.get_running_loop().time()
                if now >= deadline:
                    raise RuntimeError(f"等待验证码超时: {exc}") from exc

                self._log_flow(
                    logging.INFO,
                    "验证码暂未就绪，等待后重试",
                    stage="验证码轮询",
                    email=email,
                    extra={
                        "重试间隔秒": f"{poll_interval_seconds:.0f}",
                        "原因": exc,
                    },
                )
                await asyncio.sleep(poll_interval_seconds)
            except Exception:
                raise

    async def _fetch_verification_code(self, email: str) -> str:
        """调用 CloudMail service 拉取指定邮箱的最新验证码。"""

        service = self._verification_code_service
        if service is None:
            if self._db_pool is None:
                raise RuntimeError("缺少 db_pool 或 verification_code_service，无法拉取验证码")
            service = GetChatGptVerificationCodeService(db_pool=self._db_pool)
            self._verification_code_service = service

        return await service.execute(
            GetChatGptVerificationCodeParams(
                cloudmail_toEmail=email,
                cloudmail_type=0,
            )
        )

    async def _setup_two_factor(self, page: Any, email: str) -> str:
        """为新注册账号开启 2FA，并返回生成的 TOTP 密钥。"""

        result = await self._two_factor_action.setup_2fa(page)
        if not result.get("ok"):
            step = str(result.get("step") or "unknown")
            reason = str(result.get("reason") or "未知错误")
            raise RuntimeError(f"{step}: {reason}")

        totp_secret = str(result.get("secret_key") or "").strip()
        if not totp_secret:
            raise RuntimeError("2FA 返回的 secret_key 为空")

        self._log_flow(
            logging.INFO,
            "2FA 配置成功",
            stage="2FA配置",
            email=email,
        )
        return totp_secret

    async def _reset_browser_state(self, browser: Any) -> None:
        """在同一个浏览器实例里清理 cookie 和站点存储，避免上一轮登录态干扰下一轮。"""

        try:
            import nodriver.cdp.network as cdp_network
            import nodriver.cdp.storage as cdp_storage
        except Exception as exc:  # noqa: BLE001
            self._log_flow(
                logging.WARNING,
                "无法加载 nodriver CDP 清理能力，跳过浏览器状态重置",
                stage="浏览器清理",
                extra={"原因": exc},
            )
            return

        tab = getattr(browser, "main_tab", None)
        send = getattr(tab, "send", None)
        if not callable(send):
            return

        try:
            await tab.send(cdp_network.clear_browser_cookies())
        except Exception as exc:  # noqa: BLE001
            logger.debug("清理浏览器 cookies 失败: %s", exc)

        try:
            await tab.send(cdp_network.clear_browser_cache())
        except Exception as exc:  # noqa: BLE001
            logger.debug("清理浏览器缓存失败: %s", exc)

        for origin in (
            "https://chatgpt.com",
            "https://chat.openai.com",
            "https://openai.com",
            "https://auth.openai.com",
            "https://auth0.openai.com",
        ):
            try:
                await tab.send(cdp_storage.clear_data_for_origin(origin, "all"))
            except Exception as exc:  # noqa: BLE001
                logger.debug("清理站点存储失败 origin=%s err=%s", origin, exc)

    @classmethod
    def _log_flow(
        cls,
        level: int,
        message: str,
        *,
        stage: str,
        email: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        context_parts = [f"阶段={stage}"]
        if email:
            context_parts.append(f"邮箱={cls._mask_email(email)}")
        for key, value in (extra or {}).items():
            if value is None:
                continue
            text = str(value).strip()
            if text:
                context_parts.append(f"{key}={text}")

        context = " | ".join(context_parts)
        logger.log(level, "%s %s | %s", cls._LOG_PREFIX, message, context)

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

    def _generate_random_adult_birthday(self, min_age: int = 20, max_age: int = 40) -> date:
        """生成一个随机成年生日，保证年龄严格大于 19 岁。"""

        if min_age <= 19:
            raise ValueError("min_age 必须大于 19。")
        if min_age > max_age:
            raise ValueError("min_age 不能大于 max_age。")

        today = date.today()
        latest_birthdate = self._subtract_years(today, min_age)
        earliest_birthdate = self._subtract_years(today, max_age)
        day_span = (latest_birthdate - earliest_birthdate).days
        return earliest_birthdate + timedelta(days=random.randint(0, day_span))

    @staticmethod
    def _subtract_years(target_date: date, years: int) -> date:
        """安全减年，兼容闰年 2 月 29 日。"""

        try:
            return target_date.replace(year=target_date.year - years)
        except ValueError:
            return target_date.replace(year=target_date.year - years, month=2, day=28)
