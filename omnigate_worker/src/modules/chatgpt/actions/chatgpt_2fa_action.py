import asyncio
import logging
import pyotp
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ChatGPT2FAAction:
    """ChatGPT 账号 2FA 自动配置动作 (增强弹窗异步等待版)"""

    async def setup_2fa(self, page: Any) -> Dict[str, Any]:
        """
        执行 2FA 绑定流程，返回绑定结果和 Secret Key
        前提：浏览器已经登录了 ChatGPT 账号
        """
        logger.info("[1] 准备访问 Security 设置页面...")
        await page.get("https://chatgpt.com/#settings/Security")

        # 等待页面和设置弹窗初始加载
        await asyncio.sleep(3.0)

        # 2. 找到并打开 Authenticator app 开关
        logger.info("[2] 正在寻找并点击 Authenticator app 开关...")
        js_click_toggle = """
        (() => {
            const divs = Array.from(document.querySelectorAll('div'));
            const authSection = divs.find(d => 
                d.textContent.includes('Authenticator app') && 
                d.textContent.includes('Use one-time codes')
            );

            if (authSection) {
                const toggleBtn = authSection.querySelector('button[role="switch"]');
                if (toggleBtn) {
                    if (toggleBtn.getAttribute('aria-checked') !== 'true') {
                        toggleBtn.click();
                        return 'clicked';
                    }
                    return 'already_on';
                }
            }
            return 'not_found';
        })();
        """
        toggle_result = await page.evaluate(js_click_toggle)
        if toggle_result == 'not_found':
            return {"ok": False, "step": "toggle", "reason": "未找到 Authenticator app 开关"}
        elif toggle_result == 'already_on':
            logger.warning("[!] 2FA 开关已经是打开状态，可能已绑定过。")
            return {"ok": False, "step": "toggle", "reason": "2FA 已经处于开启状态"}

        # 3. 动态轮询等待弹窗和 "Trouble scanning?" 按钮加载
        logger.info("[3] 正在等待二维码弹窗加载并点击 Trouble scanning? ...")
        js_click_trouble = """
        (() => {
            // 专门查找 button 标签，精准匹配文本
            const btns = Array.from(document.querySelectorAll('button'));
            const target = btns.find(b => (b.innerText || '').trim() === 'Trouble scanning?');

            // 确保按钮存在且在屏幕上可见
            if (target && target.offsetParent !== null) {
                target.click();
                return true;
            }
            return false;
        })();
        """

        # 核心修复：最多等待 10 秒，每 1 秒探测一次，直到弹窗和按钮完全渲染
        clicked_trouble = False
        for attempt in range(10):
            if await page.evaluate(js_click_trouble):
                clicked_trouble = True
                logger.info(f"[*] 第 {attempt + 1} 次探测：成功找到并点击 Trouble scanning? 按钮！")
                break
            await asyncio.sleep(1.0)

        if not clicked_trouble:
            return {"ok": False, "step": "trouble_scanning",
                    "reason": "网络延迟或弹窗未正常加载，未能找到 Trouble scanning 按钮"}

        # 给 "Trouble scanning?" 点击后展开秘钥文本留出动画渲染时间
        await asyncio.sleep(1.5)

        # 4. 获取 2FA Secret Key
        logger.info("[4] 正在提取 2FA Secret Key...")
        js_get_secret = """
        (() => {
            const codeDiv = document.querySelector('div[aria-label="Copy code"]');
            if (codeDiv) {
                return codeDiv.innerText.trim();
            }
            return null;
        })();
        """
        secret_key_raw = await page.evaluate(js_get_secret)
        if not secret_key_raw:
            return {"ok": False, "step": "get_secret", "reason": "未能提取到 2FA 秘钥文本"}

        secret_key = secret_key_raw.replace(" ", "")
        logger.info(f"[*] 成功获取 2FA 秘钥: {secret_key}")

        # 5. 调用本地 pyotp 生成 6 位验证码
        logger.info("[5] 正在通过 pyotp 计算当前验证码...")
        try:
            totp = pyotp.TOTP(secret_key)
            current_code = totp.now()
            logger.info(f"[*] 计算得出验证码: {current_code}")
        except Exception as e:
            return {"ok": False, "step": "generate_totp", "reason": f"验证码生成失败: {e}"}

        # 6. 将验证码填入输入框
        logger.info("[6] 正在填入验证码...")
        input_el = await page.select('input#totp_otp', timeout=5)
        if not input_el:
            return {"ok": False, "step": "input_code", "reason": "未找到 id 为 totp_otp 的输入框"}

        await input_el.click()
        await asyncio.sleep(0.2)
        for digit in current_code:
            await input_el.send_keys(digit)
            await asyncio.sleep(0.1)

        await asyncio.sleep(0.5)

        # 7. 点击 Verify 按钮
        logger.info("[7] 准备点击 Verify 按钮...")
        js_click_verify = """
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
        if not await page.evaluate(js_click_verify):
            return {"ok": False, "step": "verify", "reason": "未找到 Verify 按钮或按钮被禁用"}

        # 8. 等待验证结果
        logger.info("[8] 等待 ChatGPT 后端校验...")
        await asyncio.sleep(3.0)

        logger.info("🎉 2FA 绑定流程执行完毕！")

        return {
            "ok": True,
            "step": "done",
            "message": "2FA 绑定成功",
            "secret_key": secret_key
        }