import asyncio
import logging
import random
import time
import pyotp
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GithubLoginAction:
    """GitHub 账号自动登录动作 (支持 2FA 双重验证)"""

    _LOG_PREFIX = "[GitHub登录]"

    async def login_github(self, page: Any, email: str, password: str, totp_secret: str = None) -> Dict[str, Any]:
        """
        执行 GitHub 登录流程
        :param totp_secret: 你的 2FA 秘钥 (如: MJLUSAVWFJMO2PK2)，如果不传则跳过 2FA 逻辑
        """
        total_steps = 8
        started_at = time.monotonic()

        def elapsed_seconds() -> float:
            return round(time.monotonic() - started_at, 2)

        def log_step(step_no: int, title: str) -> None:
            logger.info("%s 步骤=%s/%s | %s", self._LOG_PREFIX, step_no, total_steps, title)

        def build_failed_result(step_no: int, step_name: str, reason: str) -> Dict[str, Any]:
            logger.warning(
                "%s 流程失败 | 步骤=%s/%s | step=%s | 原因=%s | elapsed=%.2fs",
                self._LOG_PREFIX,
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

        log_step(1, "打开 GitHub 登录页")
        await page.get("https://github.com/login")

        # 等待页面初始加载
        await asyncio.sleep(random.uniform(2.0, 3.0))

        # ==========================================
        # 1. 输入邮箱
        # ==========================================
        log_step(2, "输入登录邮箱")
        email_input = await page.select("input#login_field", timeout=10)
        if not email_input:
            return build_failed_result(2, "input_email", "未找到邮箱输入框 (input#login_field)")

        await email_input.click()
        await asyncio.sleep(random.uniform(0.1, 0.3))

        for char in email:
            await email_input.send_keys(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

        await asyncio.sleep(random.uniform(0.3, 0.7))

        # ==========================================
        # 2. 输入密码
        # ==========================================
        log_step(3, "输入登录密码")
        pwd_input = await page.select("input#password", timeout=5)
        if not pwd_input:
            return build_failed_result(3, "input_password", "未找到密码输入框 (input#password)")

        await pwd_input.click()
        await asyncio.sleep(random.uniform(0.1, 0.3))

        for char in password:
            await pwd_input.send_keys(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

        await asyncio.sleep(random.uniform(0.5, 1.2))

        # ==========================================
        # 3. 点击 Sign in 按钮
        # ==========================================
        log_step(4, "提交登录表单")
        sign_in_btn = await page.select('input[name="commit"], button[name="commit"]', timeout=5)
        if not sign_in_btn:
            return build_failed_result(4, "click_login", "未找到 Sign in 按钮")

        await sign_in_btn.click()

        # ==========================================
        # 4. 等待跳转与状态校验
        # ==========================================
        log_step(5, "等待登录结果")
        await asyncio.sleep(4.0)

        current_url = await page.evaluate("window.location.href")

        # 检查是否因为账号密码错误留在登录页
        if "github.com/login" in current_url and "sessions/two-factor" not in current_url:
            error_msg = await page.evaluate("""
                (() => {
                    const alert = document.querySelector('.js-flash-alert');
                    return alert ? alert.innerText.trim() : '未知登录拦截';
                })();
            """)
            return build_failed_result(5, "verify_result", f"登录失败: {error_msg}")

        # ==========================================
        # 5. 检查并处理 2FA 验证
        # ==========================================
        if "two-factor" in current_url:
            log_step(6, "处理 2FA 验证")
            if not totp_secret:
                return build_failed_result(6, "2fa_required", "账号已开启 2FA 验证，但未传入 totp_secret 秘钥")

            # 生成 6 位动态码
            try:
                # 清理秘钥中可能存在的空格
                totp = pyotp.TOTP(totp_secret.replace(" ", ""))
                current_code = totp.now()
            except Exception as e:
                return build_failed_result(6, "generate_totp", f"验证码生成失败: {e}")

            logger.info("%s 2FA 验证码已生成，准备提交", self._LOG_PREFIX)

            # 寻找 2FA 输入框 (GitHub 使用的是 id 为 app_totp 的输入框)
            totp_input = await page.select("input#app_totp, input[name='app_totp']", timeout=5)
            if not totp_input:
                return build_failed_result(6, "input_2fa", "未找到 2FA 验证码输入框 (input#app_totp)")

            await totp_input.click()
            await asyncio.sleep(random.uniform(0.2, 0.4))

            # 拟人化逐字输入 6 位验证码
            for digit in current_code:
                await totp_input.send_keys(digit)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            await asyncio.sleep(0.5)

            # 很多时候 GitHub 在输入满 6 位后会自动发请求校验，如果没有自动校验则手动点击 Verify 按钮
            log_step(7, "提交 2FA 验证")
            js_verify_btn = """
            (() => {
                const btn = document.querySelector('button.js-octocaptcha-form-submit, button[type="submit"]');
                if (btn && (btn.innerText || '').toLowerCase().includes('verify')) {
                    btn.click();
                    return true;
                }
                return false;
            })();
            """
            await page.evaluate(js_verify_btn)

            # 等待 2FA 提交后的页面跳转
            await asyncio.sleep(4.0)

            # 如果 URL 里还有 two-factor，说明验证码可能错了或者过期了
            current_url = await page.evaluate("window.location.href")
            if "two-factor" in current_url:
                return build_failed_result(
                    7,
                    "verify_2fa_result",
                    "2FA 验证码提交后未能成功跳转，可能是秘钥错误或时间未同步",
                )

            # ==========================================
            # 6. 处理 Passkey / Trusted Device 提示页面
            # ==========================================
            current_url = await page.evaluate("window.location.href")
            if "sessions/trusted-device" in current_url:
                log_step(8, "处理 Trusted Device 提示页")
                # 使用 JS 遍历所有按钮和链接，寻找包含 "Ask me later" 的元素
                js_click_ask_later = """
                (() => {
                    // 获取页面上所有的 a 标签和 button 标签
                    const elements = Array.from(document.querySelectorAll('a, button'));
                    // 寻找文本内容包含 "Ask me later" 的元素
                    const targetBtn = elements.find(el => {
                        const text = (el.innerText || '').trim().toLowerCase();
                        return text === 'ask me later' || text.includes('ask me later');
                    });
                    if (targetBtn) {
                        targetBtn.click();
                        return true;
                    }
                    // 备用方案：如果没找到 Ask me later，尝试找 "Don't ask again for this browser"
                    const notInterestedBtn = elements.find(el => {
                        const text = (el.innerText || '').trim().toLowerCase();
                        return text.includes("don't ask again");
                    });
                    if (notInterestedBtn) {
                        notInterestedBtn.click();
                        return true;
                    }
                    return false;
                })();
                """
                clicked = await page.evaluate(js_click_ask_later)
                if clicked:
                    logger.info("%s 已跳过 Trusted Device 提示页，等待页面跳转", self._LOG_PREFIX)
                    # 点击后稍微多等一会，让页面彻底回到 GitHub 首页
                    await asyncio.sleep(4.0)
                else:
                    logger.warning("%s 未找到 Trusted Device 跳过按钮，可能页面 UI 已更新", self._LOG_PREFIX)
                # 重新获取最终跳转后的 URL
                current_url = await page.evaluate("window.location.href")

        else:
            logger.info("%s 当前流程未触发 2FA 验证", self._LOG_PREFIX)

        final_step_index = total_steps
        logger.info(
            "%s 流程完成且确认成功 | 步骤=%s/%s | current_url=%s | elapsed=%.2fs",
            self._LOG_PREFIX,
            final_step_index,
            total_steps,
            str(current_url)[:120],
            elapsed_seconds(),
        )
        return {
            "ok": True,
            "step": "done",
            "step_index": final_step_index,
            "total_steps": total_steps,
            "message": "登录成功",
            "current_url": current_url,
            "elapsed_seconds": elapsed_seconds(),
        }


# ==========================================
# 独立测试入口
# ==========================================
async def main():
    import nodriver as uc
    browser = await uc.start()
    page = await browser.get("data:,")  # 初始空白页

    action = GithubLoginAction()

    # 【请替换】为你的真实测试邮箱和密码
    test_email = "your_email@example.com"
    test_password = "YourPassword123"

    # 传入你的 2FA 秘钥
    totp_secret = "MJLUSAVWFJMO2PK2"

    result = await action.login_github(page, test_email, test_password, totp_secret)

    print("\n=== 最终执行结果 ===")
    print(result)

    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
