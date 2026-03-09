import asyncio
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ChatGPTGetSessionAction:
    """获取 ChatGPT 当前会话 Session JSON 的动作"""

    async def get_session(self, page: Any) -> Dict[str, Any]:
        """
        访问 auth/session 接口并提取 JSON 数据
        :param page: 已经登录了 ChatGPT 的 nodriver page 对象
        """
        logger.info("[*] 准备获取 ChatGPT Session JSON 数据...")

        try:
            # ==========================================
            # 1. 访问 session API 接口页面
            # ==========================================
            logger.info("[1] 正在请求 https://chatgpt.com/api/auth/session ...")
            await page.get("https://chatgpt.com/api/auth/session")

            # API 接口纯文本渲染很快，通常 1.5 到 2 秒足够了
            await asyncio.sleep(2.0)

            # ==========================================
            # 2. 提取页面纯文本内容
            # ==========================================
            logger.info("[2] 正在提取并解析页面 JSON 数据...")
            js_extract = """
            (() => {
                // 直接获取 body 的纯文本，这能完美规避浏览器自带的 JSON Viewer 格式化标签
                return document.body.innerText || document.documentElement.innerText;
            })();
            """
            raw_text = await page.evaluate(js_extract)

            if not raw_text or not raw_text.strip():
                return {"ok": False, "step": "extract_text", "reason": "页面内容为空，未能抓取到任何文本"}

            # ==========================================
            # 3. 解析 JSON 数据
            # ==========================================
            try:
                session_data = json.loads(raw_text.strip())
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 解析失败，抓取到的原始文本前 100 字符: {raw_text[:100]}")
                return {"ok": False, "step": "parse_json", "reason": f"提取的内容不是合法的 JSON: {e}"}

            # ==========================================
            # 4. 数据有效性校验
            # ==========================================
            # 如果未登录，接口通常会返回 {}
            if not session_data or "accessToken" not in session_data:
                logger.warning("[!] 成功获取 JSON，但里面没有 accessToken。账号可能处于未登录状态或 Token 已失效。")
                return {
                    "ok": True,
                    "step": "done",
                    "message": "获取成功，但无有效登录信息",
                    "data": session_data
                }

            logger.info("🎉 成功提取 Session 数据！已获取到 accessToken。")
            return {
                "ok": True,
                "step": "done",
                "message": "获取 JSON 成功",
                "data": session_data
            }

        except Exception as e:
            logger.error(f"❌ 获取 Session 过程中发生未捕获异常: {e}")
            return {
                "ok": False,
                "step": "exception",
                "reason": str(e)
            }


# ==========================================
# 独立测试入口
# ==========================================
async def main():
    import nodriver as uc

    # 启动浏览器。如果你有已经登录过 ChatGPT 的 user_data_dir，可以在这里传入复用
    # browser = await uc.start(user_data_dir="./gpt_profile")
    browser = await uc.start()
    page = await browser.get("data:,")

    # 注意：独立测试时，如果你启动的是一个全新且没有登录过的浏览器实例，
    # 抓取到的 JSON 将会是空的 {}，这是正常现象。

    action = ChatGPTGetSessionAction()
    result = await action.get_session(page)

    print("\n=== 提取到的 Session 结果 ===")
    print(json.dumps(result, indent=4, ensure_ascii=False))

    print("\n🛑 测试结束，浏览器保留 10 秒后关闭...")
    await asyncio.sleep(10)
    browser.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main())