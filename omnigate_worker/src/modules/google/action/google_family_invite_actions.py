"""Google 家庭组动作：邀请/拉取新成员。"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

from src.browser.browser_actions import BrowserActions
from src.modules.google.models.google_action_params import GoogleFamilyInviteParams
from src.modules.google.models.google_action_results import GoogleFamilyInviteResult

logger = logging.getLogger(__name__)


class GoogleFamilyInviteActions:
    """自动化邀请邮箱加入 Google 家庭组的动作。"""

    def __init__(self, browser_actions: BrowserActions | None = None) -> None:
        self.browser_actions = browser_actions or BrowserActions()

    async def invite_family_member(
            self,
            browser: Any,
            params: GoogleFamilyInviteParams,
    ) -> GoogleFamilyInviteResult:
        """
        邀请目标邮箱加入家庭组。
        """
        total_steps = 6
        flow_started_at = time.monotonic()

        def elapsed_seconds() -> float:
            return round(time.monotonic() - flow_started_at, 2)

        def log_step(step_no: int, title: str) -> None:
            logger.info("家庭邀请流程[%s/%s] %s", step_no, total_steps, title)

        def log_failed(step_no: int, reason: str) -> None:
            logger.warning(
                "家庭邀请流程失败[%s/%s] %s elapsed=%.2fs",
                step_no,
                total_steps,
                reason,
                elapsed_seconds(),
            )

        source_url = "https://myaccount.google.com/family/invitemembers?hl=en"
        target_email = params.target_email
        log_step(1, f"打开家庭组邀请页面: {source_url}")
        page = await self.browser_actions.open_page(browser=browser, url=source_url)

        # 2. 动态等待页面渲染与拦截/重定向检测
        log_step(2, "等待页面渲染并检测拦截/重定向状态")
        page_status = await self._wait_for_page_ready(page)

        if page_status == "auth":
            current_url = await page.evaluate("() => window.location.href")
            logger.error(f"抓取被拦截！需要二次验证。当前所处 URL: {current_url}")
            log_failed(2, "auth_required")
            return GoogleFamilyInviteResult(
                success=False,
                message="auth_required",
                details=str(current_url) if current_url else "",
            )

        if page_status == "full":
            logger.warning("页面被重定向到了 people-and-sharing，判定为家庭组已满或无权限。")
            log_failed(2, "family_group_full_or_no_permission")
            return GoogleFamilyInviteResult(
                success=False,
                message="该账号家庭组已满，请更换。"
            )

        if page_status != "ready":
            logger.warning("邀请页面未能在预期时间内就绪（可能是网络卡顿或页面元素未匹配）。")
            log_failed(2, "page_not_ready_or_spinning")
            return GoogleFamilyInviteResult(success=False, message="page_not_ready_or_spinning")

        # 拟人化延迟，代替原先死板的 3.0 秒强制等待
        await asyncio.sleep(random.uniform(1.2, 2.0))

        # 3. 输入目标邮箱并选择下拉项
        log_step(3, f"输入目标邮箱并确认下拉项: {target_email}")
        inject_success = False

        input_selector = 'input[role="combobox"][placeholder*="name or email"]'

        for attempt in range(3):
            try:
                # 动态查找输入框
                input_el = None
                for _ in range(5):
                    input_el = await page.select(input_selector, timeout=0.5)
                    if input_el:
                        break
                    input_el = await page.select('input[type="text"][role="combobox"]', timeout=0.5)
                    if input_el:
                        input_selector = 'input[type="text"][role="combobox"]'
                        break
                    await asyncio.sleep(0.3)

                if not input_el:
                    logger.warning(f"第 {attempt + 1} 次尝试：未找到输入框。")
                    continue

                logger.info(f"第 {attempt + 1} 次尝试：正在激活输入框并粘贴邮箱...")
                # 优化：通过 JS 发送更完整的事件序列来模拟真实输入
                paste_script = f"""
                (() => {{
                    const input = document.querySelector('{input_selector}');
                    if (input) {{
                        input.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        input.focus();
                        input.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                        input.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true }}));
                        input.click();

                        input.value = ''; 

                        document.execCommand('insertText', false, '{target_email}');

                        // 触发 React/Angular 绑定的多种输入事件
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, key: 'Enter', code: 'Enter' }}));
                    }}
                }})();
                """
                await page.evaluate(paste_script)

                logger.info("文本粘贴完成，正在高频轮询下拉联想选项...")
                dropdown_script = f"""
                (() => {{
                    const options = Array.from(document.querySelectorAll('[role="option"], li, [data-value]'));
                    const targetOption = options.find(opt => {{
                        if (opt.tagName.toLowerCase() === 'input') return false;
                        const text = (opt.innerText || opt.textContent || '').toLowerCase();
                        return text.includes('{target_email.lower()}');
                    }});

                    if (targetOption) {{
                        targetOption.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        targetOption.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                        targetOption.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true }}));
                        targetOption.click();
                        return true;
                    }}
                    return false;
                }})();
                """

                # 高频轮询下拉框
                clicked_dropdown = False
                for _ in range(12):  # 缩短单次间隔，增加总次数，更敏捷
                    if await page.evaluate(dropdown_script):
                        clicked_dropdown = True
                        break
                    await asyncio.sleep(0.2)

                if clicked_dropdown:
                    logger.info("成功点中下拉框选项，邮箱已转化为发送标签。")
                else:
                    logger.warning("未检测到下拉选项，触发物理回车键兜底...")
                    await input_el.send_keys('\n')

                # 短暂等待确认状态更新
                await asyncio.sleep(random.uniform(0.6, 1.0))

                log_step(4, "校验 Send 按钮是否可点击")
                if await self._is_send_button_enabled(page):
                    inject_success = True
                    break
                else:
                    logger.warning(f"第 {attempt + 1} 次输入后 Send 按钮未被激活，准备清空重试...")
                    clear_script = f"document.querySelector('{input_selector}').value = '';"
                    await page.evaluate(clear_script)
                    await asyncio.sleep(random.uniform(0.8, 1.5))

            except Exception as e:
                logger.error(f"第 {attempt + 1} 次尝试交互时发生底层异常: {e}")
                await asyncio.sleep(1.0)

        if not inject_success:
            logger.error("多次尝试均未能成功激活发送按钮，输入流程失败。")
            log_failed(4, "input_failed_to_activate_send")
            return GoogleFamilyInviteResult(success=False, message="input_failed_to_activate_send")

        # 5. 点击发送按钮
        log_step(5, "点击 Send 发送邀请")
        send_clicked = await self._click_send_button(page)
        if not send_clicked:
            log_failed(5, "failed_to_click_send")
            return GoogleFamilyInviteResult(success=False, message="failed_to_click_send")

        # 6. 验证成功页面 (Invitation sent)
        log_step(6, "确认 Invitation sent 成功标志")
        is_success = await self._wait_for_success_message(page)

        if is_success:
            logger.info(
                "家庭邀请流程完成[%s/%s] success=true target_email=%s elapsed=%.2fs",
                total_steps,
                total_steps,
                target_email,
                elapsed_seconds(),
            )
            return GoogleFamilyInviteResult(success=True, message="invitation_sent")
        else:
            logger.warning("未检测到成功标志，可能邀请被风控拦截或目标邮箱存在异常。")
            log_failed(6, "success_timeout")
            return GoogleFamilyInviteResult(success=False, message="success_timeout")

    async def _wait_for_page_ready(self, page: Any) -> str:
        script = """
        (() => {
            const url = window.location.href.toLowerCase();
            if (url.includes('signin') || url.includes('challenge')) return 'auth';
            if (url.includes('people-and-sharing')) return 'full';

            const input = document.querySelector('input[placeholder*="name or email"]') || document.querySelector('input[role="combobox"]');

            const spinners = document.querySelectorAll('[role="progressbar"]');
            let isSpinning = false;
            for (let s of spinners) {
                if (s.offsetParent !== null && window.getComputedStyle(s).display !== 'none') {
                    isSpinning = true;
                    break;
                }
            }

            if (input && !isSpinning) return 'ready';
            return 'waiting';
        })();
        """
        for _ in range(50):
            try:
                status = await page.evaluate(script)
                if status in ['auth', 'full', 'ready']:
                    return status
            except Exception:
                pass
            await asyncio.sleep(0.3)
        return "timeout"

    async def _is_send_button_enabled(self, page: Any) -> bool:
        script = """
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const sendBtn = btns.find(b => {
                const text = (b.innerText || '').toLowerCase().trim();
                return (text === 'send' || text === '发送');
            });
            return sendBtn ? !sendBtn.disabled : false;
        })();
        """
        try:
            return bool(await page.evaluate(script))
        except Exception:
            return False

    async def _click_send_button(self, page: Any) -> bool:
        script = """
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const sendBtn = btns.find(b => {
                const text = (b.innerText || '').toLowerCase().trim();
                return (text === 'send' || text === '发送') && !b.disabled;
            });

            if (sendBtn) {
                sendBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                sendBtn.click();
                return true;
            }
            return false;
        })();
        """
        try:
            return bool(await page.evaluate(script))
        except Exception:
            return False

    async def _wait_for_success_message(self, page: Any) -> bool:
        script = """
        (() => {
            const headers = Array.from(document.querySelectorAll('h2, div[role="alert"]'));
            const matchH2 = headers.some(h => {
                const text = (h.innerText || '').toLowerCase();
                return text.includes('invitation sent') || text.includes('已发送邀请') || text.includes('invitations sent');
            });
            if (matchH2) return true;

            const bodyText = document.body ? document.body.innerText.toLowerCase() : '';
            // 排除按钮文本造成的误判，主要关注成功提示文案
            const isSuccess = /invitation(?:s)? sent\\b|已发送邀请/.test(bodyText);
            return isSuccess;
        })();
        """
        for _ in range(40):
            try:
                if await page.evaluate(script):
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.2)  # 缩短轮询间隔，提高响应速度
        return False
