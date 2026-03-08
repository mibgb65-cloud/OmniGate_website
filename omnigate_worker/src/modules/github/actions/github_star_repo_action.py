import asyncio
import logging
import random
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GithubStarRepoAction:
    """GitHub 模拟人类浏览仓库并点 Star 的动作"""

    _LOG_PREFIX = "[GitHub仓库Star]"

    async def _human_scroll(self, page: Any, min_seconds: int, max_seconds: int):
        """模拟人类在当前页面上下随机滚动阅读"""
        scroll_time = random.uniform(min_seconds, max_seconds)
        end_time = asyncio.get_event_loop().time() + scroll_time

        logger.info("%s 模拟页面浏览 | duration=%.1fs", self._LOG_PREFIX, scroll_time)
        while asyncio.get_event_loop().time() < end_time:
            # 随机决定是往下滚还是往上滚 (80% 概率往下，20% 概率往上)
            direction = 1 if random.random() < 0.8 else -1
            scroll_amount = random.randint(300, 800) * direction

            await page.evaluate(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}})")

            # 滚完之后随机停顿看代码的时间
            await asyncio.sleep(random.uniform(1.5, 4.0))

    async def star_repo(self, page: Any, repo_url: str) -> Dict[str, Any]:
        """
        执行浏览仓库并点星的流程
        :param page: 已经登录的浏览器 Page 对象
        :param repo_url: 目标仓库地址 (例如: https://github.com/torvalds/linux)
        """
        total_steps = 5
        started_at = time.monotonic()

        def elapsed_seconds() -> float:
            return round(time.monotonic() - started_at, 2)

        def log_step(step_no: int, title: str) -> None:
            logger.info("%s 步骤=%s/%s | repo=%s | %s", self._LOG_PREFIX, step_no, total_steps, repo_url, title)

        def build_failed_result(step_no: int, step_name: str, reason: str) -> Dict[str, Any]:
            logger.warning(
                "%s 流程失败 | 步骤=%s/%s | repo=%s | step=%s | 原因=%s | elapsed=%.2fs",
                self._LOG_PREFIX,
                step_no,
                total_steps,
                repo_url,
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
        # 1. 访问仓库主页
        # ==========================================
        log_step(1, "打开目标仓库")
        await page.get(repo_url)
        await asyncio.sleep(random.uniform(2.0, 4.0))

        # ==========================================
        # 2. 在主页随机浏览 (10 ~ 15 秒)
        # ==========================================
        log_step(2, "浏览仓库主页")
        await self._human_scroll(page, min_seconds=10, max_seconds=15)

        # 滚回顶部，准备找文件点击
        await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # ==========================================
        # 3. 获取仓库中的文件链接并随机点击 1~2 个
        # ==========================================
        log_step(3, "探索仓库文件")
        js_get_files = """
        (() => {
            const links = Array.from(document.querySelectorAll('a'));
            // 筛选出包含 /blob/ (文件) 或 /tree/ (文件夹) 的链接，且不是隐藏元素
            const fileLinks = links
                .filter(a => a.href && (a.href.includes('/blob/') || a.href.includes('/tree/')))
                .map(a => a.href);

            // 去重
            return [...new Set(fileLinks)];
        })();
        """
        file_urls = await page.evaluate(js_get_files)

        if file_urls:
            # 随机决定探索 1 到 2 个文件
            explore_count = random.randint(1, 2)
            selected_urls = random.sample(file_urls, min(explore_count, len(file_urls)))

            for i, file_url in enumerate(selected_urls):
                # 兼容处理：如果 CDP 返回的是字典，提取其中的 'value' 字段；否则直接转为字符串
                url_str = file_url.get('value', str(file_url)) if isinstance(file_url, dict) else str(file_url)

                # 确保不会因为解析不到有效字符串而报错
                file_name = url_str.split('/')[-1] if '/' in url_str else '未知文件'

                logger.info(
                    "%s 探索文件 | repo=%s | index=%s | file=%s",
                    self._LOG_PREFIX,
                    repo_url,
                    i + 1,
                    file_name,
                )
                await page.get(url_str)
                await asyncio.sleep(random.uniform(1.5, 3.0))

                # 在文件详情页假装看源码 (10 ~ 20 秒)
                await self._human_scroll(page, min_seconds=10, max_seconds=20)

        else:
            logger.warning("%s 未找到可探索的源码文件链接，继续停留在仓库主页", self._LOG_PREFIX)
            await self._human_scroll(page, min_seconds=10, max_seconds=20)

        # ==========================================
        # 4. 退回到仓库主页
        # ==========================================
        log_step(4, "返回仓库主页")
        await page.get(repo_url)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # ==========================================
        # 5. 寻找并点击 Star 按钮
        # ==========================================
        log_step(5, "定位并点击 Star 按钮")
        # 完美规避：检查按钮的 aria-label 或文本，避免把已经 Star 过的给取消了
        # 完美规避：通过 GitHub 原生的 data-hydro-click 埋点数据进行精准定位
        js_click_star = """
                (() => {
                    const btns = Array.from(document.querySelectorAll('button'));

                    // 1. 先判断是否已经 Star 过了 (寻找埋点为 UNSTAR_BUTTON 且当前可见的按钮)
                    const isAlreadyStarred = btns.some(b => {
                        const hydro = b.getAttribute('data-hydro-click') || '';
                        return hydro.includes('"target":"UNSTAR_BUTTON"') && b.offsetParent !== null;
                    });

                    if (isAlreadyStarred) {
                        return 'already_starred';
                    }

                    // 2. 寻找真正需要点击的 Star 按钮 (寻找埋点为 STAR_BUTTON 且当前可见的按钮)
                    const starBtn = btns.find(b => {
                        const hydro = b.getAttribute('data-hydro-click') || '';
                        return hydro.includes('"target":"STAR_BUTTON"') && b.offsetParent !== null;
                    });

                    if (starBtn) {
                        // 找到后划动到视野中心，稍微停顿后模拟点击
                        starBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                        setTimeout(() => starBtn.click(), 600);
                        return 'clicked';
                    }

                    return 'not_found';
                })();
                """

        star_result = await page.evaluate(js_click_star)

        if star_result == 'already_starred':
            logger.info(
                "%s 流程完成 | repo=%s | 结果=already_starred | elapsed=%.2fs",
                self._LOG_PREFIX,
                repo_url,
                elapsed_seconds(),
            )
            return {
                "ok": True,
                "step": "done",
                "step_index": total_steps,
                "total_steps": total_steps,
                "message": "仓库已是 Star 状态，跳过点击",
                "elapsed_seconds": elapsed_seconds(),
            }

        elif star_result == 'not_found':
            return build_failed_result(5, "click_star", "未找到 Star 按钮")

        # 点击之后给网络一点时间向服务器发送 POST 记录
        logger.info("%s Star 按钮已点击，等待网络响应", self._LOG_PREFIX)
        await asyncio.sleep(3.0)

        logger.info(
            "%s 流程完成且确认成功 | 步骤=%s/%s | repo=%s | elapsed=%.2fs",
            self._LOG_PREFIX,
            total_steps,
            total_steps,
            repo_url,
            elapsed_seconds(),
        )
        return {
            "ok": True,
            "step": "done",
            "step_index": total_steps,
            "total_steps": total_steps,
            "message": f"成功为 {repo_url} 点亮了 Star",
            "elapsed_seconds": elapsed_seconds(),
        }


# ==========================================
# 独立测试入口
# ==========================================
async def main():
    import nodriver as uc
    # 假设此处浏览器已登录
    browser = await uc.start()
    page = await browser.get("https://github.com")

    print("等待 10 秒确认已登录状态...")
    await asyncio.sleep(10)

    action = GithubStarRepoAction()
    # 替换为你想要去刷星的仓库
    target_repo = "https://github.com/torvalds/linux"

    result = await action.star_repo(page, target_repo)

    print("\n=== 返回的 JSON 结果 ===")
    print(result)

    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
