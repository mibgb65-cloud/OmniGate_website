"""Google 登录相关动作。"""

from __future__ import annotations

import asyncio
import logging
import time
import random
from typing import Any

from src.browser.browser_actions import BrowserActions
from src.modules.google.models.google_action_params import GoogleAuthParams
from src.modules.google.utils.twofa_provider import TwoFAProvider

try:
    import nodriver.cdp.input_ as cdp_input
except Exception:  # noqa: BLE001
    cdp_input = None


logger = logging.getLogger(__name__)


class GoogleAuthActions:
    """Google 鉴权动作集合 (基于 nodriver 动态轮询 + 真实物理模拟)。"""

    def __init__(
            self,
            browser_actions: BrowserActions | None = None,
            twofa_provider: TwoFAProvider | None = None,
    ) -> None:
        self.browser_actions = browser_actions or BrowserActions()
        self.twofa_provider = twofa_provider or TwoFAProvider()

    async def login_google(self, browser: Any, params: GoogleAuthParams) -> dict[str, Any]:
        normalized = self._normalize_auth_params(params)
        total_steps = 6
        flow_started_at = time.monotonic()

        def elapsed_seconds() -> float:
            return round(time.monotonic() - flow_started_at, 2)

        def log_step(step_no: int, title: str) -> None:
            logger.info("登录流程[%s/%s] %s", step_no, total_steps, title)

        def build_failed_result(step_no: int, step_name: str, reason: str) -> dict[str, Any]:
            logger.warning(
                "登录流程失败[%s/%s] step=%s reason=%s elapsed=%.2fs",
                step_no,
                total_steps,
                step_name,
                reason,
                elapsed_seconds(),
            )
            return {
                "ok": False,
                "step": step_name,
                "step_index": step_no,
                "total_steps": total_steps,
                "reason": reason,
                "elapsed_seconds": elapsed_seconds(),
            }

        # 1. 访问直达登录地址
        log_step(1, "打开 Google 登录页")
        service_login_url = (
            "https://accounts.google.com/ServiceLogin"
            "?hl=en&continue=https%3A%2F%2Fwww.google.com%2F"
        )
        try:
            page = await self.browser_actions.open_page(browser=browser, url=service_login_url)
        except Exception as exc:  # noqa: BLE001
            return build_failed_result(1, "open_login_page", f"打开登录页失败: {exc}")

        # 2. 输入账号
        log_step(2, "输入账号并点击下一步")
        if not await self._safe_type(page, "#identifierId", normalized.google_account):
            return build_failed_result(2, "input_account", "未找到可交互的账号输入框")

        if not await self._safe_click(page, "#identifierNext"):
            return build_failed_result(2, "click_account_next", "未找到账号下一步按钮")

        # 3. 输入密码
        log_step(3, "输入密码并点击下一步")
        if not await self._safe_type(page, "input[name='Passwd']", normalized.password):
            return build_failed_result(3, "input_password", "未找到可交互的密码输入框")

        if not await self._safe_click(page, "#passwordNext"):
            return build_failed_result(3, "click_password_next", "未找到密码下一步按钮")

        # 4. 2FA 验证
        log_step(4, "处理 2FA 验证")
        twofa_code = ""
        if normalized.twofa:
            try:
                twofa_code = self.twofa_provider.generate_code(normalized.twofa)
            except Exception as exc:  # noqa: BLE001
                logger.warning("2FA 生成失败，跳过 2FA 输入: %s", exc)

        if twofa_code:
            totp_selector = "input[type='tel'], input#totpPin, input[name='totpPin']"

            logger.info("检查是否需要选择 2FA 验证方式...")
            for attempt in range(4):
                try:
                    el = await page.select(totp_selector, timeout=0.5)
                    if el and await el.apply("e => e.offsetWidth > 0 && e.offsetHeight > 0"):
                        logger.info("已处于验证码输入界面。")
                        break
                except Exception:
                    pass

                clicked_auth = await self._safe_click_by_text(
                    page,
                    ["Authenticator", "Get a verification code", "身份验证器", "获取验证码"],
                    timeout=2,
                    delay_range=(0.3, 1.0)
                )
                if clicked_auth:
                    logger.info("已点击 Authenticator 选项，等待输入框加载...")
                    await asyncio.sleep(1.5)
                    break

                clicked_other = await self._safe_click_by_text(
                    page,
                    ["Try another way", "尝试其他登录方式", "其他方式"],
                    timeout=2,
                    delay_range=(0.3, 1.0)
                )
                if clicked_other:
                    logger.info("已点击 Try another way，等待选项展开...")
                    await asyncio.sleep(1.0)

            if await self._safe_type(page, totp_selector, twofa_code, timeout=10):
                logger.info("成功输入 2FA，正在尝试点击下一步...")

                clicked = await self._safe_click(page, "#totpNext > div > button", timeout=2)
                if not clicked:
                    clicked = await self._safe_click_by_text(page, ["Next", "下一步"], timeout=2)

                if not clicked:
                    logger.info("未找到 Next 按钮，尝试回车提交...")
                    el = await page.select(totp_selector)
                    await el.send_keys("\n")
            else:
                logger.info("未检测到 2FA 输入框，可能无需验证或遇到未知的风控界面。")
        else:
            logger.info("账号无有效 2FA 密钥，跳过输入。")

        # 5. 尝试跳过拦截/推广弹窗
        log_step(5, "处理拦截或推广弹窗")
        skip_keywords = [
            "Not now", "暂不", "以后再说",
            "Cancel", "取消",
            "Skip", "跳过",
            "No thanks", "不，谢谢"
        ]

        for attempt in range(3):
            clicked = await self._safe_click_by_text(page, skip_keywords, timeout=3, delay_range=(0.5, 1.0))
            if not clicked:
                break

            logger.info(f"成功点击跳过/取消按钮 (第 {attempt + 1} 个弹窗)，等待页面跳转...")
            await asyncio.sleep(2.0)

        # 6. 成功判定：等待 URL 发生实质性变化
        log_step(6, "确认登录结果")
        login_ok = await self._wait_for_login_success(page, timeout=10)
        current_url = getattr(page, 'url', '')

        if login_ok:
            logger.info(
                "登录流程完成[%s/%s] 成功 current_url=%s elapsed=%.2fs",
                total_steps,
                total_steps,
                str(current_url)[:80],
                elapsed_seconds(),
            )
        else:
            logger.warning(
                "登录流程完成[%s/%s] 未确认成功 current_url=%s elapsed=%.2fs",
                total_steps,
                total_steps,
                str(current_url)[:80],
                elapsed_seconds(),
            )

        return {
            "ok": login_ok,
            "step": "done",
            "step_index": total_steps,
            "total_steps": total_steps,
            "current_url": current_url,
            "page": page,
            "elapsed_seconds": elapsed_seconds(),
        }

    def _normalize_auth_params(self, params: GoogleAuthParams) -> GoogleAuthParams:
        google_account = params.google_account.strip().lower()
        password = params.password.strip()
        twofa = (params.twofa or "").strip()
        if not google_account or not password:
            raise ValueError("google_account/password 不能为空")
        return GoogleAuthParams(google_account=google_account, password=password, twofa=twofa)

    async def _safe_type(self, page: Any, selector: str, text: str, timeout: int = 15) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                el = await page.select(selector, timeout=0.5)
                if el:
                    is_visible = await el.apply("e => e.offsetWidth > 0 && e.offsetHeight > 0")
                    if is_visible:
                        await self._simulate_physical_click(page, el)
                        await asyncio.sleep(random.uniform(0.2, 0.5))

                        for char in text:
                            await el.send_keys(char)
                            delay = random.uniform(0.05, 0.20)
                            if random.random() < 0.10:
                                delay += random.uniform(0.2, 0.5)
                            await asyncio.sleep(delay)

                        return True
            except Exception:
                pass
            await asyncio.sleep(0.2)
        return False

    async def _safe_click(self, page: Any, selector: str, timeout: int = 15,
                          delay_range: tuple[float, float] = (1.0, 3.0)) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                el = await page.select(selector, timeout=0.5)
                if el:
                    is_visible = await el.apply("e => e.offsetWidth > 0 && e.offsetHeight > 0")
                    if is_visible:
                        if delay_range:
                            delay = random.uniform(delay_range[0], delay_range[1])
                            logger.debug(f"准备点击 {selector}，拟人化等待 {delay:.2f} 秒...")
                            await asyncio.sleep(delay)

                        await self._simulate_physical_click(page, el)
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.2)
        return False

    async def _safe_click_by_text(self, page: Any, texts: list[str], timeout: int = 5,
                                  delay_range: tuple[float, float] = (1.0, 3.0)) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            for text in texts:
                try:
                    el = await page.find(text, timeout=0.5)
                    if el:
                        is_visible = await el.apply("e => e.offsetWidth > 0 && e.offsetHeight > 0")
                        if is_visible:
                            if delay_range:
                                delay = random.uniform(delay_range[0], delay_range[1])
                                logger.debug(f"准备点击文本按钮 '{text}'，拟人化等待 {delay:.2f} 秒...")
                                await asyncio.sleep(delay)

                            await self._simulate_physical_click(page, el)
                            return True
                except Exception:
                    continue
            await asyncio.sleep(0.2)
        return False

    async def _simulate_physical_click(self, page: Any, el: Any) -> None:
        try:
            if cdp_input is None:
                await el.click()
                return

            js_code = """
            e => {
                const rect = e.getBoundingClientRect();
                return {x: rect.x, y: rect.y, w: rect.width, h: rect.height};
            }
            """
            rect = await el.apply(js_code)

            target_x = rect['x'] + rect['w'] * random.uniform(0.2, 0.8)
            target_y = rect['y'] + rect['h'] * random.uniform(0.2, 0.8)

            await page.send(cdp_input.dispatch_mouse_event(
                "mouseMoved",
                x=target_x,
                y=target_y
            ))
            await asyncio.sleep(random.uniform(0.05, 0.15))

            await page.send(cdp_input.dispatch_mouse_event(
                "mousePressed",
                x=target_x,
                y=target_y,
                button=cdp_input.MouseButton("left"),
                click_count=1
            ))

            await asyncio.sleep(random.uniform(0.05, 0.15))

            await page.send(cdp_input.dispatch_mouse_event(
                "mouseReleased",
                x=target_x,
                y=target_y,
                button=cdp_input.MouseButton("left"),
                click_count=1
            ))

            logger.debug(f"执行了物理点击，坐标: ({target_x:.2f}, {target_y:.2f})")

        except Exception as e:
            logger.warning(f"物理点击模拟失败，回退到默认 click: {e}")
            await el.click()

    async def _wait_for_login_success(self, page: Any, timeout: int = 15) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_url = await self._get_current_url(page)
            state = await self._read_page_login_state(page)

            if state.get("has_account_entry"):
                return True

            if current_url:
                lowered = current_url.lower()
                in_accounts = "accounts.google.com" in lowered
                signin_like = any(k in lowered for k in ("servicelogin", "/signin", "/challenge"))
                in_myaccount = "myaccount.google.com" in lowered
                in_google_home = "google.com" in lowered and not in_accounts
                has_signin_button = bool(state.get("has_signin_button"))

                if in_myaccount and not signin_like:
                    return True
                if in_google_home and not has_signin_button and not signin_like:
                    return True

            await asyncio.sleep(0.5)
        return False

    async def _get_current_url(self, page: Any) -> str:
        current_url = getattr(page, "url", "")
        if current_url:
            return str(current_url)
        try:
            result = await page.evaluate("window.location.href")
            return str(result or "")
        except Exception:
            return ""

    async def _read_page_login_state(self, page: Any) -> dict[str, Any]:
        script = """
        () => {
          const txt = (document.body && document.body.innerText) ? document.body.innerText : '';
          const hasSignInButton = Boolean(document.querySelector('a[aria-label*="Sign in"], a[href*="ServiceLogin"]'));
          const hasAccountEntry = Boolean(
            document.querySelector('a[aria-label*="Google Account"], a[href*="SignOutOptions"], img[alt*="Google Account"]')
          );
          return {
            has_signin_button: hasSignInButton || /\\bSign in\\b/i.test(txt),
            has_account_entry: hasAccountEntry,
          };
        }
        """
        try:
            result = await page.evaluate(script)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}
