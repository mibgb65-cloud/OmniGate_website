"""OpenAI 注册与登录处理动作。"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
import logging
import random
from typing import Any

import asyncpg

from src.browser.browser_actions import BrowserActions, PageOpenTimeoutError
from src.config.config import get_settings
from src.modules.chatgpt.actions.chatgpt_2fa_action import ChatGPT2FAAction
from src.modules.chatgpt.actions.chatgpt_session_action import (
    ChatGPTGetSessionAction,
    extract_session_storage_content,
)
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
    _SELECT_QUERY_TIMEOUT_SECONDS = 2.0
    _POLL_INTERVAL_SECONDS = 0.5

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        actions: BrowserActions | None = None,
        verification_code_service: GetChatGptVerificationCodeService | None = None,
        two_factor_action: ChatGPT2FAAction | None = None,
        session_action: ChatGPTGetSessionAction | None = None,
        chatgpt_home_open_timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self.actions = actions or BrowserActions()
        self._db_pool = db_pool
        self._verification_code_service = verification_code_service or (
            GetChatGptVerificationCodeService(db_pool=db_pool) if db_pool is not None else None
        )
        self._two_factor_action = two_factor_action or ChatGPT2FAAction()
        self._session_action = session_action or ChatGPTGetSessionAction()
        resolved_timeout = (
            chatgpt_home_open_timeout_seconds
            if chatgpt_home_open_timeout_seconds is not None
            else settings.CHATGPT_HOME_OPEN_TIMEOUT_SECONDS
        )
        self._chatgpt_home_open_timeout_seconds = max(1.0, float(resolved_timeout))
        self._form_element_timeout_seconds = max(20.0, float(settings.CHATGPT_LOGIN_ELEMENT_TIMEOUT_SECONDS))
        self._form_transition_timeout_seconds = max(
            self._form_element_timeout_seconds,
            float(settings.CHATGPT_LOGIN_TRANSITION_TIMEOUT_SECONDS),
        )

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
            page = await self.actions.open_page(
                browser,
                "https://chatgpt.com",
                timeout_seconds=self._chatgpt_home_open_timeout_seconds,
            )
            await asyncio.sleep(4)

            self._log_flow(logging.INFO, "定位登录入口", stage="入口定位", email=email)
            login_btn = await self._wait_for_login_button(
                page,
                timeout_seconds=min(20.0, self._form_element_timeout_seconds),
                email=email,
            )
            if login_btn:
                await login_btn.click()
            await asyncio.sleep(2)

            self._log_flow(logging.INFO, "定位邮箱输入框", stage="邮箱输入", email=email)
            email_input = await self._wait_for_select(
                page,
                'input[name="username"], input[name="email"], input[type="email"]',
                timeout_seconds=self._form_transition_timeout_seconds,
                stage="邮箱输入",
                description="邮箱输入框",
                email=email,
            )
            if not email_input:
                raise TimeoutError("Email input field not found")

            self._log_flow(logging.INFO, "输入注册邮箱", stage="邮箱输入", email=email)
            for char in email:
                await email_input.send_keys(char)
                await asyncio.sleep(random.uniform(0.05, 0.2))
            await asyncio.sleep(0.5)

            self._log_flow(logging.INFO, "提交邮箱", stage="邮箱提交", email=email)
            continue_btn = await self._wait_for_select(
                page,
                'button[type="submit"], button[name="action"]',
                timeout_seconds=10.0,
                stage="邮箱提交",
                description="继续按钮",
                email=email,
                log_on_timeout=False,
            )
            if continue_btn:
                await continue_btn.click()
            else:
                await email_input.send_keys("\n")

            self._log_flow(logging.INFO, "等待密码输入页", stage="分支识别", email=email)
            try:
                password_element = await self._wait_for_select(
                    page,
                    'input[type="password"], input[name="password"]',
                    timeout_seconds=self._form_transition_timeout_seconds,
                    stage="分支识别",
                    description="密码输入框",
                    email=email,
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

        except PageOpenTimeoutError as exc:
            self._log_flow(
                logging.ERROR,
                "打开 ChatGPT 首页超时",
                stage="页面打开",
                email=email,
                extra={
                    "超时秒数": f"{exc.timeout_seconds:.0f}",
                    "URL": exc.url,
                },
            )
            return {
                "status": "OPEN_PAGE_TIMEOUT",
                "email": email,
                "password": password,
                "name": name,
                "msg": str(exc),
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
            otp_input = await self._wait_for_select(
                page,
                'input[inputmode="numeric"], input[name="code"], .code-input',
                timeout_seconds=self._form_transition_timeout_seconds,
                stage="验证码填写",
                description="验证码输入框",
                email=email,
            )
            if not otp_input:
                raise TimeoutError("OTP input field not found")

            for char in otp_code:
                await otp_input.send_keys(char)
                await asyncio.sleep(random.uniform(0.05, 0.2))

            await asyncio.sleep(1.5)
            try:
                otp_continue_btn = await self._wait_for_select(
                    page,
                    'button[type="submit"]',
                    timeout_seconds=10.0,
                    stage="验证码填写",
                    description="验证码继续按钮",
                    email=email,
                    log_on_timeout=False,
                )
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
            name_input = await self._wait_for_select(
                page,
                'input[name="fullname"], input[name="name"], input[name="first-name"]',
                timeout_seconds=self._form_transition_timeout_seconds,
                stage="资料填写",
                description="姓名输入框",
                email=email,
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

            month_input = await self._wait_for_select(
                page,
                'div[data-type="month"]',
                timeout_seconds=10.0,
                stage="资料填写",
                description="月份输入框",
                email=email,
                log_on_timeout=False,
            )
            if month_input:
                await month_input.click()
                await asyncio.sleep(0.5)
                for _ in range(3):
                    await month_input.send_keys("\b")
                for char in month_text:
                    await month_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))

            day_input = await self._wait_for_select(
                page,
                'div[data-type="day"]',
                timeout_seconds=10.0,
                stage="资料填写",
                description="日期输入框",
                email=email,
                log_on_timeout=False,
            )
            if day_input:
                await day_input.click()
                await asyncio.sleep(0.5)
                for _ in range(3):
                    await day_input.send_keys("\b")
                for char in day_text:
                    await day_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))

            year_input = await self._wait_for_select(
                page,
                'div[data-type="year"]',
                timeout_seconds=10.0,
                stage="资料填写",
                description="年份输入框",
                email=email,
                log_on_timeout=False,
            )
            if year_input:
                await year_input.click()
                await asyncio.sleep(0.5)
                for _ in range(5):
                    await year_input.send_keys("\b")
                for char in year_text:
                    await year_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))

            await asyncio.sleep(1.5)
            agree_btn = await self._wait_for_select(
                page,
                'button[type="submit"]',
                timeout_seconds=10.0,
                stage="资料填写",
                description="资料提交按钮",
                email=email,
                log_on_timeout=False,
            )
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

        session_token = await self._try_get_session_content(page, email)

        self._log_flow(logging.INFO, "注册、2FA 与 Session 抓取完成", stage="流程完成", email=email)
        return {
            "status": "REGISTERED_SUCCESS",
            "email": email,
            "password": password,
            "name": name,
            "totp_secret": totp_secret,
            "session_token": session_token,
            "msg": "注册成功，已完成资料填写、引导清理、2FA 绑定与 Session 抓取",
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

        resolved_name = generate_random_name()
        resolved_email = await generate_random_email(
            db_pool=self._db_pool,
            preferred_name=resolved_name,
        )
        resolved_password = generate_random_password()
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
        """为新注册账号开启 2FA，并返回生成的 TOTP 密钥。增加兜底状态校验。"""

        # 1. 执行 2FA 工具类流程
        result = await self._two_factor_action.setup_2fa(page)

        # 即使流程报错，我们也要尝试提取 secret_key
        totp_secret = str(result.get("secret_key") or "").strip()

        # 2. 如果工具类报告失败，触发兜底校验逻辑
        if not result.get("ok"):
            if totp_secret:
                self._log_flow(
                    logging.INFO,
                    "2FA 流程报告失败，正在执行 DOM 兜底状态校验...",
                    stage="2FA配置",
                    email=email
                )

                # 检查页面上 Authenticator app 的开关是否处于打开状态
                is_actually_enabled = await self._verify_2fa_enabled_in_dom(page)
                if is_actually_enabled:
                    self._log_flow(
                        logging.INFO,
                        "兜底校验通过：检测到 2FA 开关已处于打开状态，强制放行",
                        stage="2FA配置",
                        email=email
                    )
                    return totp_secret

            # 如果没有 secret，或者开关确实没打开，则抛出原本的错误
            step = str(result.get("step") or "unknown")
            reason = str(result.get("reason") or "未知错误")
            raise RuntimeError(f"{step}: {reason}")

        if not totp_secret:
            raise RuntimeError("2FA 返回的 secret_key 为空")

        self._log_flow(
            logging.INFO,
            "2FA 配置正常完成",
            stage="2FA配置",
            email=email,
        )
        return totp_secret

    async def _verify_2fa_enabled_in_dom(self, page: Any) -> bool:
        """
        兜底探针：检查当前页面是否处于 Security 设置页，且 Authenticator app 开关已打开。
        """
        try:
            # 留出一点时间让页面动画或跳转完成
            await asyncio.sleep(2)

            js_check = """
            (() => {
                // 1. 确认我们在 Security 页面且包含 MFA 相关的文本
                const bodyText = document.body.innerText || "";
                if (!bodyText.includes('Authenticator app') && !bodyText.includes('Multi-factor authentication')) {
                    return false;
                }

                // 2. 寻找处于激活状态的开关。
                const activeSwitches = document.querySelectorAll('button[role="switch"][aria-checked="true"], input[type="checkbox"]:checked');
                
                // 只要页面上有激活的开关，且包含 2FA 文本，大概率就是成功了
                return activeSwitches.length > 0;
            })();
            """
            return await page.evaluate(js_check)
        except Exception as exc:
            logger.debug(f"2FA 兜底校验发生异常: {exc}")
            return False

    async def _try_get_session_content(self, page: Any, email: str) -> str | None:
        """尽量抓取当前账号的 ChatGPT 完整 session 页面内容。"""

        self._log_flow(logging.INFO, "开始抓取 Session 信息", stage="Session抓取", email=email)
        try:
            session_result = await self._session_action.get_session(page)
        except Exception as exc:  # noqa: BLE001
            self._log_flow(
                logging.WARNING,
                "Session 抓取异常，跳过保存",
                stage="Session抓取",
                email=email,
                extra={"原因": exc},
            )
            return None

        if not session_result.get("ok"):
            self._log_flow(
                logging.WARNING,
                "Session 抓取失败，跳过保存",
                stage="Session抓取",
                email=email,
                extra={"原因": session_result.get("reason") or session_result.get("message")},
            )
            return None

        session_data = session_result.get("data")
        if not isinstance(session_data, dict):
            self._log_flow(
                logging.WARNING,
                "Session 抓取结果缺少 data 字段",
                stage="Session抓取",
                email=email,
            )
            return None

        session_content = extract_session_storage_content(session_result)
        if not session_content:
            self._log_flow(
                logging.WARNING,
                "Session 抓取成功但缺少可持久化的完整内容",
                stage="Session抓取",
                email=email,
            )
            return None

        self._log_flow(logging.INFO, "Session 抓取成功", stage="Session抓取", email=email)
        return session_content

    async def _wait_for_login_button(self, page: Any, *, timeout_seconds: float, email: str | None = None) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            try:
                login_btn = await page.find("Log in", timeout=1) or await page.find("登录", timeout=1)
                if login_btn:
                    return login_btn
            except Exception:  # noqa: BLE001
                pass

            login_btn = await self._try_select(page, '[data-testid="login-button"]')
            if login_btn:
                return login_btn
            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)

        self._log_flow(
            logging.WARNING,
            "等待登录入口超时",
            stage="入口定位",
            email=email,
            extra={"超时秒数": f"{timeout_seconds:.0f}"},
        )
        return None

    async def _wait_for_select(
        self,
        page: Any,
        selector: str,
        *,
        timeout_seconds: float,
        stage: str,
        description: str,
        email: str | None = None,
        log_on_timeout: bool = True,
    ) -> Any | None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            element = await self._try_select(page, selector)
            if element:
                return element
            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)

        if log_on_timeout:
            self._log_flow(
                logging.WARNING,
                "等待页面元素超时",
                stage=stage,
                email=email,
                extra={
                    "元素": description,
                    "超时秒数": f"{timeout_seconds:.0f}",
                },
            )
        return None

    async def _try_select(self, page: Any, selector: str, *, timeout_seconds: float | None = None) -> Any | None:
        try:
            return await page.select(selector, timeout=timeout_seconds or self._SELECT_QUERY_TIMEOUT_SECONDS)
        except Exception:  # noqa: BLE001
            return None

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