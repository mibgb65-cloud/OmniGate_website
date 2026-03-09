import asyncio
import logging
import random
import pyotp
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ChatGPTLoginAction:
    """ChatGPT 账号自动登录动作 (支持 2FA 双重验证)"""

    async def login(self, page: Any, email: str, password: str, totp_secret: str = None) -> Dict[str, Any]:
        """
        执行 ChatGPT 登录流程
        :param page: nodriver 的 page 对象
        :param email: 账号邮箱
        :param password: 密码
        :param totp_secret: 2FA 秘钥 (可选)
        """
        logger.info(f"[*] 开始执行 ChatGPT 登录流程 | 账号: {self._mask_email(email)}")

        try:
            # ==========================================
            # 1. 访问首页并点击登录
            # ==========================================
            logger.info("[1] 打开 ChatGPT 首页...")
            await page.get("https://chatgpt.com")
            await asyncio.sleep(random.uniform(3.0, 5.0))

            logger.info("[2] 定位并点击 Log in 按钮...")
            login_btn = await page.find("Log in", timeout=5) or await page.find("登录", timeout=5)
            if not login_btn:
                login_btn = await page.select('[data-testid="login-button"]', timeout=5)

            if login_btn:
                await login_btn.click()
            else:
                logger.warning("未找到首页 Log in 按钮，可能已处于登录态或直接被重定向，尝试继续检测...")

            await asyncio.sleep(random.uniform(2.0, 4.0))

            # ==========================================
            # 2. 输入邮箱
            # ==========================================
            logger.info("[3] 定位并输入邮箱...")
            email_input = await page.select('input[name="username"], input[name="email"], input[type="email"]',
                                            timeout=10)
            if not email_input:
                return {"ok": False, "step": "input_email", "reason": "未找到邮箱输入框 (可能被 Cloudflare 盾拦截)"}

            await email_input.click()
            await asyncio.sleep(random.uniform(0.1, 0.3))

            for char in email:
                await email_input.send_keys(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            await asyncio.sleep(0.5)
            continue_btn = await page.select('button[type="submit"], button[name="action"]', timeout=5)
            if continue_btn:
                await continue_btn.click()
            else:
                await email_input.send_keys('\n')

            # ==========================================
            # 3. 输入密码
            # ==========================================
            logger.info("[4] 等待并输入密码...")
            password_input = await page.select('input[type="password"], input[name="password"]', timeout=15)
            if not password_input:
                return {"ok": False, "step": "input_password", "reason": "未找到密码输入框"}

            await password_input.click()
            await asyncio.sleep(random.uniform(0.1, 0.3))

            for char in password:
                await password_input.send_keys(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            await asyncio.sleep(0.5)
            pwd_continue_btn = await page.select('button[type="submit"], button[name="action"]', timeout=5)
            if pwd_continue_btn:
                await pwd_continue_btn.click()
            else:
                await password_input.send_keys('\n')

            logger.info("[5] 提交密码，等待 Auth0 校验跳转...")
            await asyncio.sleep(4.0)

            # ==========================================
            # 4. 检查并处理 2FA (MFA)
            # ==========================================
            current_url = await page.evaluate("window.location.href")
            mfa_input = await page.select('input[inputmode="numeric"], input[name="code"], input[id="mfa-code"]',
                                          timeout=5)

            if mfa_input or "mfa" in current_url.lower() or "two-factor" in current_url.lower():
                logger.info("[6] 检测到 2FA (MFA) 拦截，准备输入动态码...")

                if not totp_secret:
                    return {"ok": False, "step": "2fa_required", "reason": "账号已开启 2FA，但未传入 totp_secret 秘钥"}

                if not mfa_input:
                    # 再次尝试精准定位
                    mfa_input = await page.select('input[inputmode="numeric"]', timeout=5)

                if mfa_input:
                    try:
                        totp = pyotp.TOTP(totp_secret.replace(" ", ""))
                        current_code = totp.now()
                        logger.info(f"[*] 计算得出 2FA 验证码: {current_code}")
                    except Exception as e:
                        return {"ok": False, "step": "generate_totp", "reason": f"验证码生成失败: {e}"}

                    await mfa_input.click()
                    await asyncio.sleep(0.2)

                    for digit in current_code:
                        await mfa_input.send_keys(digit)
                        await asyncio.sleep(random.uniform(0.05, 0.15))

                    await asyncio.sleep(0.5)
                    mfa_submit = await page.select('button[type="submit"]', timeout=3)
                    if mfa_submit:
                        await mfa_submit.click()
                    else:
                        await mfa_input.send_keys('\n')

                    logger.info("[7] 2FA 已提交，等待最终跳转...")
                    await asyncio.sleep(5.0)
                else:
                    return {"ok": False, "step": "input_2fa", "reason": "处于 2FA 页面但未找到输入框"}

            # ==========================================
            # 5. 验证是否成功登录
            # ==========================================
            await asyncio.sleep(3.0)
            final_url = await page.evaluate("window.location.href")

            # 判断标准：成功进入主界面（检查 prompt 聊天输入框是否存在）
            prompt_textarea = await page.select('textarea#prompt-textarea, [id="prompt-textarea"]', timeout=5)

            if "chatgpt.com" in final_url and prompt_textarea:
                logger.info("🎉 ChatGPT 登录操作成功，已到达聊天界面！")
                return {
                    "ok": True,
                    "step": "done",
                    "message": "登录成功",
                    "final_url": final_url
                }
            else:
                logger.warning(f"[!] 登录状态存疑，当前 URL: {final_url}")
                # 尝试抓取页面上的报错文本（比如密码错误、被封号等提示）
                error_msg = await page.evaluate("""
                    (() => {
                        const err = document.querySelector('[data-error], .error-message, .alert-error, form span, .cf-error-details');
                        return err ? err.innerText.trim() : '未检测到明显错误提示';
                    })();
                """)
                return {
                    "ok": False,
                    "step": "verify_login",
                    "reason": f"未能成功到达聊天界面。提示: {error_msg}"
                }

        except Exception as e:
            logger.error(f"❌ 登录流程发生异常: {e}")
            return {
                "ok": False,
                "step": "exception",
                "reason": str(e)
            }

    @staticmethod
    def _mask_email(email: str) -> str:
        """邮箱脱敏展示"""
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