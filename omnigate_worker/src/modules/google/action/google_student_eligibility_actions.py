"""Google 学生资格动作：检测状态并提取学生资格链接。"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from src.browser.browser_actions import BrowserActions
from src.modules.google.models.google_action_results import GoogleStudentEligibilityResult

logger = logging.getLogger(__name__)


class GoogleStudentEligibilityActions:
    """自动化检测 Google 学生资格状态与验证链接。"""

    STUDENT_ENTRY_URL = "https://one.google.com/ai-student"

    def __init__(self, browser_actions: BrowserActions | None = None) -> None:
        self.browser_actions = browser_actions or BrowserActions()

    async def get_student_eligibility(self, browser: Any, max_retries: int = 3) -> GoogleStudentEligibilityResult:
        """
        打开学生资格页并检测状态。
        优先返回可用验证链接；当提取到 SheerID 空 verificationId 时自动重试。
        """
        total_steps = 4
        flow_started_at = time.monotonic()

        def elapsed_seconds() -> float:
            return round(time.monotonic() - flow_started_at, 2)

        def log_step(step_no: int, title: str) -> None:
            logger.info("学生资格流程[%s/%s] %s", step_no, total_steps, title)

        retries = max(int(max_retries), 0)
        for attempt in range(retries + 1):
            round_text = f"第{attempt + 1}/{retries + 1}轮"
            log_step(1, f"{round_text} 打开学生资格页面")

            # 拟人化抖动
            if attempt > 0:
                await asyncio.sleep(random.uniform(0.5, 1.5))

            page = await self.browser_actions.open_page(browser=browser, url=self.STUDENT_ENTRY_URL)

            # 等待核心内容渲染完毕
            log_step(2, f"{round_text} 等待页面关键元素渲染")
            is_ready = await self._wait_for_page_ready(page)
            if not is_ready:
                logger.warning("页面在预期时间内未能呈现出完整的学生优惠特征，将尝试强行提取...")

            log_step(3, f"{round_text} 提取学生资格状态与链接")
            result = await self._extract_student_eligibility_result(
                page=page,
                fallback_url=self.STUDENT_ENTRY_URL,
                retries=attempt,
            )

            log_step(4, f"{round_text} 校验提取结果")
            if (
                    result.status == "未订阅 (需验证)"
                    and result.eligibility_link
                    and self._is_invalid_sheerid_link(result.eligibility_link)
                    and attempt < retries
            ):
                logger.warning("提取到无效 SheerID 链接（verificationId 为空），准备重新加载页面重试...")
                continue

            logger.info(
                "学生资格流程完成[%s/%s] status=%s link=%s retries=%s elapsed=%.2fs",
                total_steps,
                total_steps,
                result.status,
                bool(result.eligibility_link),
                result.retries,
                elapsed_seconds(),
            )
            return result

        result = GoogleStudentEligibilityResult(
            status="未知状态",
            eligibility_link=None,
            source_url=self.STUDENT_ENTRY_URL,
            current_url=None,
            retries=retries,
        )
        logger.warning(
            "学生资格流程完成[%s/%s] status=%s retries=%s elapsed=%.2fs",
            total_steps,
            total_steps,
            result.status,
            result.retries,
            elapsed_seconds(),
        )
        return result

    async def get_student_eligibility_link(self, browser: Any) -> str:
        """
        兼容旧接口：仅返回链接。
        """
        result = await self.get_student_eligibility(browser=browser)
        return result.eligibility_link or result.current_url or self.STUDENT_ENTRY_URL

    async def _wait_for_page_ready(self, page: Any, timeout: float = 15.0) -> bool:
        """
        高频轮询：严格等待具体特征文案或链接出现。
        返回 True 表示成功就绪，False 表示超时。
        """
        script = """
        (() => {
            const txt = (document.body && document.body.innerText) ? document.body.innerText.toLowerCase() : '';
            const readyKeywords = [
                "you're already subscribed",
                "you’re already subscribed",
                "manage plan",
                "get student offer",
                "verify",
                "sheerid",
                "验证",
                "管理方案",
                "已订阅"
            ];
            const hasText = readyKeywords.some(k => txt.includes(k));

            const hasLink = Array.from(document.querySelectorAll('a')).some(a => {
                const href = (a.href || '').toLowerCase();
                return href.includes('sheerid') || href.includes('verify');
            });

            const spinners = document.querySelectorAll('[role="progressbar"]');
            let isSpinning = false;
            for (let s of spinners) {
                if (s.offsetParent !== null && window.getComputedStyle(s).display !== 'none') {
                    isSpinning = true;
                    break;
                }
            }

            return (hasText || hasLink) && !isSpinning;
        })();
        """
        loop_count = max(int(timeout / 0.4), 1)
        for _ in range(loop_count):
            try:
                if await page.evaluate(script):
                    # 发现元素后给一点点时间让 DOM 稳定
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.4)

        return False

    async def _extract_student_eligibility_result(
            self,
            page: Any,
            fallback_url: str,
            retries: int,
    ) -> GoogleStudentEligibilityResult:
        """
        使用 JS 原生逻辑提取学生资格信息。
        """
        script = """
        (() => {
            try {
                function getByXpath(xpath) {
                    const result = [];
                    try {
                        const nodesSnapshot = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                        for (let i = 0; i < nodesSnapshot.snapshotLength; i++) {
                            result.push(nodesSnapshot.snapshotItem(i));
                        }
                    } catch(e) {}
                    return result;
                }

                const currentUrl = window.location.href || '';
                const txt = document.body ? document.body.innerText.toLowerCase() : '';

                const xpathSub = '//*[contains(text(), "You\\'re already subscribed") or contains(text(), "已订阅")] | //a[@aria-label="Manage plan" or contains(@aria-label, "管理")]';
                const isSubscribed = getByXpath(xpathSub).length > 0 || txt.includes("you're already subscribed") || txt.includes("you’re already subscribed") || txt.includes("manage plan");

                const xpathCertified = '//*[contains(text(), "Get student offer") or contains(text(), "获取学生")]';
                const isCertified = getByXpath(xpathCertified).length > 0 || txt.includes("get student offer");

                const xpathVerify = '//a[contains(@href, "sheerid")] | //a[contains(@aria-label, "Verify")] | //a[contains(@aria-label, "验证")] | //*[contains(text(), "Verify") or contains(text(), "验证")]';
                const verifyNodes = getByXpath(xpathVerify);

                let candidateLink = null;
                for (const node of verifyNodes) {
                    let href = node.getAttribute('href');
                    if (href && href.includes('http')) {
                        candidateLink = href;
                        break;
                    }
                    const closestA = node.closest('a');
                    if (closestA) {
                        href = closestA.getAttribute('href');
                        if (href && href.includes('http')) {
                            candidateLink = href;
                            break;
                        }
                    }
                }

                if (!candidateLink) {
                    const allLinks = Array.from(document.querySelectorAll('a'));
                    const sheeridLink = allLinks.find(a => a.href && a.href.includes('sheerid'));
                    if (sheeridLink) {
                        candidateLink = sheeridLink.href;
                    }
                }

                return JSON.stringify({
                    current_url: currentUrl,
                    has_subscribed: isSubscribed,
                    has_student_offer: isCertified,
                    candidate_link: candidateLink
                });
            } catch (e) {
                return JSON.stringify({ error: e.toString() });
            }
        })();
        """
        try:
            payload_raw = await page.evaluate(script)
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            if payload.get("error"):
                logger.error(f"JS 执行错误: {payload['error']}")
        except Exception as exc:
            logger.warning("提取学生资格状态失败，返回未知状态: %s", exc)
            return GoogleStudentEligibilityResult(
                status="未知状态",
                eligibility_link=fallback_url,
                source_url=fallback_url,
                current_url=None,
                retries=retries,
            )

        current_url = ""
        candidate_link = ""
        has_subscribed = False
        has_student_offer = False

        if isinstance(payload, dict):
            current_url = str(payload.get("current_url") or "").strip()
            candidate_link = str(payload.get("candidate_link") or "").strip()
            has_subscribed = bool(payload.get("has_subscribed"))
            has_student_offer = bool(payload.get("has_student_offer"))

        resolved_candidate = urljoin(current_url or fallback_url, candidate_link) if candidate_link else None

        if has_subscribed:
            logger.info("解析状态: 已订阅")
            return GoogleStudentEligibilityResult(
                status="已订阅",
                eligibility_link=None,
                source_url=fallback_url,
                current_url=current_url or fallback_url,
                retries=retries,
            )
        if has_student_offer:
            logger.info("解析状态: 已认证/未订阅")
            return GoogleStudentEligibilityResult(
                status="已认证/未订阅",
                eligibility_link=None,
                source_url=fallback_url,
                current_url=current_url or fallback_url,
                retries=retries,
            )
        if resolved_candidate:
            logger.info(f"解析状态: 未订阅 (需验证) - 抓取到链接: {resolved_candidate}")
            return GoogleStudentEligibilityResult(
                status="未订阅 (需验证)",
                eligibility_link=resolved_candidate,
                source_url=fallback_url,
                current_url=current_url or fallback_url,
                retries=retries,
            )

        logger.warning("解析状态: 未知状态 (页面中没有识别到任何特征)")
        return GoogleStudentEligibilityResult(
            status="未知状态",
            eligibility_link=current_url or fallback_url,
            source_url=fallback_url,
            current_url=current_url or fallback_url,
            retries=retries,
        )

    def _is_invalid_sheerid_link(self, link: str) -> bool:
        """
        仅判定旧脚本定义的无效场景：
        - 链接属于 services.sheerid.com/verify
        - 带 verificationId 参数但值为空
        """
        try:
            parsed = urlparse(link)
            if "services.sheerid.com" not in (parsed.netloc or "").lower():
                return False
            if "/verify" not in (parsed.path or "").lower():
                return False

            query = parse_qs(parsed.query, keep_blank_values=True)
            if "verificationId" not in query:
                return False
            values = query.get("verificationId") or []
            if not values:
                return True
            return all(not str(v).strip() for v in values)
        except Exception:
            return False
