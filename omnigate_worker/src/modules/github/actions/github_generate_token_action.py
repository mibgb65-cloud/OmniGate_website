import asyncio
import logging
import random
import time
import uuid
import pyotp
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GithubGenerateTokenAction:
    """GitHub 自动生成 Personal Access Token (Classic) 动作"""

    _LOG_PREFIX = "[GitHub生成Token]"

    async def generate_token(self, page: Any, totp_secret: str) -> Dict[str, Any]:
        """
        执行生成 Token 流程
        :param page: 已经登录的浏览器 Page 对象
        :param totp_secret: 你的 2FA 秘钥 (如: MJLUSAVWFJMO2PK2)
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

        # ==========================================
        # 1. 访问新建 Token 页面
        # ==========================================
        log_step(1, "打开新建 Token 页面")
        await page.get("https://github.com/settings/tokens/new")
        await asyncio.sleep(random.uniform(2.5, 4.0))

        # ==========================================
        # 2. 处理可能出现的 Sudo 模式 (2FA 验证)
        # ==========================================
        log_step(2, "检查 Sudo 验证")
        current_url = await page.evaluate("window.location.href")

        # Sudo 模式下，页面通常会跳转到 /sudo 或者包含 app_totp 输入框
        totp_input = await page.select("input#app_totp, input[name='app_totp']", timeout=2)

        if "sudo" in current_url or totp_input:
            logger.info("%s 检测到 Sudo 验证，准备处理 2FA", self._LOG_PREFIX)
            if not totp_secret:
                return build_failed_result(2, "sudo_2fa", "需要 2FA 验证，但未提供秘钥")

            try:
                totp = pyotp.TOTP(totp_secret.replace(" ", ""))
                current_code = totp.now()
            except Exception as e:
                return build_failed_result(2, "sudo_2fa", f"验证码生成失败: {e}")

            logger.info("%s Sudo 验证码已生成，准备提交", self._LOG_PREFIX)

            if not totp_input:
                totp_input = await page.select("input#app_totp", timeout=5)
            if not totp_input:
                return build_failed_result(2, "sudo_2fa", "未找到 Sudo 2FA 输入框 (input#app_totp)")

            await totp_input.click()
            await asyncio.sleep(0.2)
            for digit in current_code:
                await totp_input.send_keys(digit)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            await asyncio.sleep(0.5)

            # 点击验证按钮
            js_verify_sudo = """
            (() => {
                const btn = document.querySelector('button[type="submit"]');
                if (btn && (btn.innerText || '').toLowerCase().includes('verify')) {
                    btn.click();
                    return true;
                }
                return false;
            })();
            """
            await page.evaluate(js_verify_sudo)
            logger.info("%s 已提交 Sudo 2FA 验证，等待返回 Token 页面", self._LOG_PREFIX)
            await asyncio.sleep(4.0)
        else:
            logger.info("%s 当前流程未触发 Sudo 验证", self._LOG_PREFIX)

        # ==========================================
        # 3. 在 note 中输入随机名字
        # ==========================================
        log_step(3, "填写 Token Note")
        note_input = await page.select("input#oauth_access_description", timeout=10)
        if not note_input:
            return build_failed_result(3, "input_note", "未找到 Note 输入框 (input#oauth_access_description)")

        random_note_name = f"AutoToken_{str(uuid.uuid4().hex)[:6]}"
        await note_input.click()
        await asyncio.sleep(0.2)

        for char in random_note_name:
            await note_input.send_keys(char)
            await asyncio.sleep(random.uniform(0.02, 0.08))

        # ==========================================
        # 4. 选择 Expiration 为 90 days
        # ==========================================
        log_step(4, "设置 Token 过期时间")
        js_select_expiration = """
        (() => {
            const selectEl = document.querySelector('select#oauth_access_expiration');
            if (selectEl) {
                // 遍历所有的 option，找到包含 90 的选项
                for (let i = 0; i < selectEl.options.length; i++) {
                    if (selectEl.options[i].text.includes('90')) {
                        selectEl.selectedIndex = i;
                        // 手动触发 change 事件让前端框架感知
                        selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
            }
            return false;
        })();
        """
        is_expiration_set = await page.evaluate(js_select_expiration)
        if not is_expiration_set:
            logger.warning("%s 未能自动选择 90 days，可能继续使用默认过期时间", self._LOG_PREFIX)

        await asyncio.sleep(0.5)

        # ==========================================
        # 5. 勾选 repo 和 user 权限
        # ==========================================
        log_step(5, "勾选 Token 权限范围")
        js_check_scopes = """
        (() => {
            // 找到 repo 的顶层多选框和 user 的顶层多选框并点击
            const repoCheck = document.querySelector('input[value="repo"]');
            const userCheck = document.querySelector('input[value="user"]');

            let checkedCount = 0;
            if (repoCheck && !repoCheck.checked) {
                repoCheck.click();
                checkedCount++;
            }
            if (userCheck && !userCheck.checked) {
                userCheck.click();
                checkedCount++;
            }
            return checkedCount;
        })();
        """
        await page.evaluate(js_check_scopes)
        await asyncio.sleep(0.5)

        # ==========================================
        # 6. 点击最下方的 Generate token 按钮
        # ==========================================
        log_step(6, "提交 Token 创建表单")
        js_submit_form = """
        (() => {
            const btns = Array.from(document.querySelectorAll('button[type="submit"]'));
            const generateBtn = btns.find(b => (b.innerText || '').toLowerCase().includes('generate token'));
            if (generateBtn) {
                generateBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                setTimeout(() => generateBtn.click(), 500);
                return true;
            }
            return false;
        })();
        """
        if not await page.evaluate(js_submit_form):
            return build_failed_result(6, "submit_token", "未找到 Generate token 按钮")

        # 等待页面提交和跳转
        log_step(7, "等待 Token 生成结果")
        await asyncio.sleep(4.0)

        # ==========================================
        # 7 & 8. 提取并打印生成的 ghp_ Token
        # ==========================================
        log_step(8, "提取生成的 Token")

        js_extract_token = """
        (() => {
            // GitHub 生成的 token 通常放在 id 为 new-oauth-token 的 code 标签里
            const tokenCode = document.querySelector('code#new-oauth-token');
            if (tokenCode) {
                return tokenCode.innerText.trim();
            }
            return null;
        })();
        """

        # 动态轮询提取（防网络稍慢）
        generated_token = None
        for _ in range(5):
            generated_token = await page.evaluate(js_extract_token)
            if generated_token and generated_token.startswith("ghp_"):
                break
            await asyncio.sleep(1.0)

        if not generated_token:
            return build_failed_result(8, "extract_token", "页面跳转成功，但未能提取到 ghp_ 开头的 Token 文本")

        logger.info(
            "%s 流程完成且确认成功 | 步骤=%s/%s | note=%s | token_length=%s | elapsed=%.2fs",
            self._LOG_PREFIX,
            total_steps,
            total_steps,
            random_note_name,
            len(generated_token),
            elapsed_seconds(),
        )

        return {
            "ok": True,
            "step": "done",
            "step_index": total_steps,
            "total_steps": total_steps,
            "message": "Token 生成并提取成功",
            "token": generated_token,
            "note": random_note_name,
            "elapsed_seconds": elapsed_seconds(),
        }


# ==========================================
# 独立测试入口
# ==========================================
async def main():
    import nodriver as uc
    # 假设此时浏览器已经处于登录状态
    browser = await uc.start()
    page = await browser.get("https://github.com")

    print("等待 10 秒确认已登录状态...")
    await asyncio.sleep(10)

    action = GithubGenerateTokenAction()
    totp_secret = "MJLUSAVWFJMO2PK2"

    result = await action.generate_token(page, totp_secret)

    print("\n=== 返回的 JSON 结果 ===")
    print(result)

    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
