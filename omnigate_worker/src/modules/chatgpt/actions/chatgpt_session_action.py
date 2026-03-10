import asyncio
import json
import logging
from typing import Any, Dict, Mapping

logger = logging.getLogger(__name__)


def extract_session_storage_content(session_result: Mapping[str, Any] | None) -> str | None:
    """从 session 抓取结果中提取适合落库的完整页面内容。"""

    if not isinstance(session_result, Mapping):
        return None

    session_data = session_result.get("data")
    if not isinstance(session_data, Mapping):
        return None

    access_token = str(session_data.get("accessToken") or "").strip()
    if not access_token:
        return None

    raw_text = str(session_result.get("raw_text") or "").strip()
    if raw_text:
        return raw_text

    try:
        return json.dumps(session_data, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        return None


class ChatGPTGetSessionAction:
    """获取 ChatGPT 当前会话 Session JSON 的动作"""

    _LOG_PREFIX = "[ChatGPT获取Session]"
    _SESSION_URL = "https://chatgpt.com/api/auth/session"
    _TOTAL_STEPS = 2

    async def get_session(self, page: Any) -> Dict[str, Any]:
        """
        访问 auth/session 接口并提取 JSON 数据
        :param page: 已经登录了 ChatGPT 的 nodriver page 对象
        """
        self._log_flow(logging.INFO, "开始获取 Session JSON 数据")

        try:
            self._log_flow(
                logging.INFO,
                "请求 Session API",
                step_no=1,
                total_steps=self._TOTAL_STEPS,
                extra={"url": self._SESSION_URL},
            )
            await page.get(self._SESSION_URL)

            await asyncio.sleep(2.0)

            self._log_flow(logging.INFO, "提取并解析页面 JSON 数据", step_no=2, total_steps=self._TOTAL_STEPS)
            js_extract = """
            (() => {
                // 直接获取 body 的纯文本，这能完美规避浏览器自带的 JSON Viewer 格式化标签
                return document.body.innerText || document.documentElement.innerText;
            })();
            """
            raw_text = str(await page.evaluate(js_extract) or "").strip()

            if not raw_text:
                return {"ok": False, "step": "extract_text", "reason": "页面内容为空，未能抓取到任何文本"}

            # ==========================================
            # 3. 解析 JSON 数据
            # ==========================================
            try:
                session_data = json.loads(raw_text)
            except json.JSONDecodeError as e:
                self._log_flow(
                    logging.ERROR,
                    "JSON 解析失败",
                    step_no=2,
                    total_steps=self._TOTAL_STEPS,
                    extra={"raw_text_preview": raw_text[:100], "reason": e},
                )
                return {"ok": False, "step": "parse_json", "reason": f"提取的内容不是合法的 JSON: {e}"}

            if not session_data or "accessToken" not in session_data:
                self._log_flow(
                    logging.WARNING,
                    "成功获取 JSON，但缺少 accessToken",
                    step_no=self._TOTAL_STEPS,
                    total_steps=self._TOTAL_STEPS,
                )
                return {
                    "ok": True,
                    "step": "done",
                    "message": "获取成功，但无有效登录信息",
                    "data": session_data,
                    "raw_text": raw_text,
                }

            self._log_flow(logging.INFO, "Session 数据提取成功", step_no=self._TOTAL_STEPS, total_steps=self._TOTAL_STEPS)
            return {
                "ok": True,
                "step": "done",
                "message": "获取 JSON 成功",
                "data": session_data,
                "raw_text": raw_text,
            }

        except Exception as e:
            self._log_flow(logging.ERROR, "获取 Session 过程中发生未捕获异常", extra={"reason": e})
            return {
                "ok": False,
                "step": "exception",
                "reason": str(e)
            }

    @classmethod
    def _log_flow(
        cls,
        level: int,
        message: str,
        *,
        step_no: int | None = None,
        total_steps: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        context_parts: list[str] = []
        if step_no is not None and total_steps is not None:
            context_parts.append(f"步骤={step_no}/{total_steps}")
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
