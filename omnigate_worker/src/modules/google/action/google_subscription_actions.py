"""Google 订阅信息动作：读取 One Pro 状态与到期时间。"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from typing import Any

from src.browser.browser_actions import BrowserActions
from src.modules.google.models.google_action_results import (
    GoogleInviteResult,
    GoogleSubscriptionAndInviteResult,
    GoogleSubscriptionResult,
)

logger = logging.getLogger(__name__)


class GoogleSubscriptionActions:
    """Google One 订阅信息提取动作。"""

    _LOG_PREFIX = "[Google订阅动作]"

    def __init__(self, browser_actions: BrowserActions | None = None) -> None:
        self.browser_actions = browser_actions or BrowserActions()

    async def get_onepro_subscription_status(self, browser: Any) -> GoogleSubscriptionAndInviteResult:
        total_steps = 3
        flow_started_at = time.monotonic()

        def elapsed_seconds() -> float:
            return round(time.monotonic() - flow_started_at, 2)

        def log_step(step_no: int, title: str) -> None:
            logger.info("%s 步骤=%s/%s | %s", self._LOG_PREFIX, step_no, total_steps, title)

        log_step(1, "抓取订阅页信息")
        try:
            sub_res = await self._fetch_subscription_data(browser)
        except Exception:
            logger.exception("%s 抓取订阅页异常 | 步骤=1/%s | elapsed=%.2fs", self._LOG_PREFIX, total_steps, elapsed_seconds())
            raise

        log_step(2, "抓取邀请页信息")
        try:
            inv_res = await self._fetch_invite_data(browser)
        except Exception:
            logger.exception("%s 抓取邀请页异常 | 步骤=2/%s | elapsed=%.2fs", self._LOG_PREFIX, total_steps, elapsed_seconds())
            raise

        log_step(3, "合并结果并返回")
        result = GoogleSubscriptionAndInviteResult(
            **sub_res.model_dump(),
            **inv_res.model_dump(),
        )
        logger.info(
            "%s 流程完成 | 步骤=%s/%s | found_onepro=%s | has_referral_invite=%s | elapsed=%.2fs",
            self._LOG_PREFIX,
            total_steps,
            total_steps,
            result.found_onepro,
            result.has_referral_invite,
            elapsed_seconds(),
        )
        return result

    async def _fetch_subscription_data(self, browser: Any) -> GoogleSubscriptionResult:
        url = "https://myaccount.google.com/subscriptions?hl=en"
        logger.info("%s 打开订阅页 | url=%s", self._LOG_PREFIX, url)
        page = await self.browser_actions.open_page(browser=browser, url=url)
        logger.info("%s 订阅页打开完成 | current_url=%s", self._LOG_PREFIX, await self._get_current_url(page))
        await self._wait_for_subscription_page_ready(page)

        subscription_result = await self._extract_page_payload(page)
        subscription_result.source_url = url

        # 已移除可能导致 nodriver 底层 WebSocket 崩溃的 await page.close()

        return subscription_result

    async def _fetch_invite_data(self, browser: Any) -> GoogleInviteResult:
        invite_url = "https://one.google.com/ai/invite?g1_landing_page=0"
        logger.info("%s 打开邀请页 | url=%s", self._LOG_PREFIX, invite_url)

        # 错峰打开，模拟人类习惯
        await asyncio.sleep(random.uniform(0.2, 0.5))
        invite_page = await self.browser_actions.open_page(browser=browser, url=invite_url)
        logger.info("%s 邀请页打开完成 | current_url=%s", self._LOG_PREFIX, await self._get_current_url(invite_page))

        await self._wait_for_invite_page_ready(invite_page)

        invite_result = await self._extract_invite_payload(invite_page)
        invite_result.invite_source_url = invite_url

        # 已移除可能导致 nodriver 底层 WebSocket 崩溃的 await invite_page.close()

        return invite_result

    async def _extract_page_payload(self, page: Any) -> GoogleSubscriptionResult:
        logger.info("正在提取订阅卡片数据...")
        cards = await self._extract_subscription_cards(page)
        logger.info("共找到 %s 张订阅卡片", len(cards))

        onepro_card = self._pick_onepro_card(cards)

        if onepro_card is not None:
            logger.info("结构化解析成功：命中 One Pro / AI Pro 订阅卡片")
            found_onepro = True
            subscription_status = "ACTIVE"
            expires_at_text = self._extract_expire_from_details(onepro_card.get("details", []))
        else:
            logger.warning("未找到结构化的 AI Pro 卡片，触发全页面文本兜底解析...")
            text = await self._extract_page_text(page)
            found_onepro = self._detect_onepro(text)
            subscription_status = self._detect_subscription_status(text)
            expires_at_text = self._detect_expire_text(text)

        logger.info(
            "订阅解析结果 | 发现订阅=%s 状态=%s 到期时间=%s",
            found_onepro,
            subscription_status,
            expires_at_text,
        )

        return GoogleSubscriptionResult(
            found_onepro=found_onepro,
            subscription_status=subscription_status,
            expires_at_text=expires_at_text,
            subscription_name=onepro_card.get("title") if onepro_card else None,
            subscription_details=onepro_card.get("details") if onepro_card else None,
        )

    async def _extract_invite_payload(self, page: Any) -> GoogleInviteResult:
        logger.info("正在提取邀请页链接与额度数据...")
        # 使用 JSON.stringify 防止 CDP 传输丢字段
        script = """
        (() => {
          const titleEl = document.querySelector('h1.axZOlc');
          let linkEl = document.querySelector('span.gzdqbb');
          if (!linkEl) {
              const spans = Array.from(document.querySelectorAll('span'));
              linkEl = spans.find(el => (el.textContent || '').includes('g.co/g1referral/'));
          }
          const usageEl = document.querySelector('div.R6iuQe');
          return JSON.stringify({
            invite_title: titleEl ? (titleEl.textContent || '').trim() : null,
            referral_link: linkEl ? (linkEl.textContent || '').trim() : null,
            invitation_usage_text: usageEl ? (usageEl.textContent || '').trim() : null,
          });
        })();
        """
        invite_title: str | None = None
        referral_link: str | None = None
        usage_text: str | None = None

        # 核心优化：前置 wait_for_invite 已经过滤了无资格/空白页，这里只需少量重试 (4次) 即可快速提取，避免无意义的死等
        for _ in range(4):
            try:
                result_str = await page.evaluate(script)
                if isinstance(result_str, str):
                    result = json.loads(result_str)
                else:
                    result = result_str if isinstance(result_str, dict) else {}

                invite_title = self._norm_text(result.get("invite_title"))
                referral_link = self._norm_text(result.get("referral_link"))
                usage_text = self._norm_text(result.get("invitation_usage_text"))
                if referral_link:
                    break
            except Exception as e:
                logger.debug("邀请页 JS 提取发生异常 (可忽略): %s", e)

            await asyncio.sleep(random.uniform(0.2, 0.4))

        if not referral_link:
            logger.info("DOM 中未找到邀请链接，可能无 AI Pro 邀请资格，尝试使用正则兜底匹配源码...")
            page_text = await self._extract_page_text(page)
            m = re.search(r"((?:https?://)?g\.co/g1referral/[A-Za-z0-9_-]+)", page_text, re.IGNORECASE)
            if m:
                referral_link = m.group(1)
                logger.info("正则兜底匹配到邀请链接: %s", referral_link)
            if not usage_text:
                m_usage = re.search(r"(\d+\s+of\s+\d+\s+invitations\s+accepted)", page_text, re.IGNORECASE)
                if m_usage:
                    usage_text = m_usage.group(1)

        has_referral_invite = bool(
            referral_link or (invite_title and "give friends 4 months of google ai pro" in invite_title.lower())
        )
        used, total = self._parse_usage_count(usage_text)

        logger.info(
            "邀请解析结果 | 具备邀请资格=%s 链接=%s 使用情况=%s",
            has_referral_invite,
            referral_link,
            usage_text,
        )

        return GoogleInviteResult(
            has_referral_invite=has_referral_invite,
            invite_title=invite_title,
            referral_link=referral_link,
            invitation_usage_text=usage_text,
            invitations_used=used,
            invitations_total=total,
        )

    async def _wait_for_subscription_page_ready(self, page: Any) -> None:
        logger.info("正在动态等待订阅页渲染...")
        script = """
        (() => {
          const ready = document.readyState;
          const cards = document.querySelectorAll('a.tIl6ib').length;
          const txt = (document.body && document.body.innerText) ? document.body.innerText.toLowerCase() : '';
          const hasKeywords = ['google one', 'one pro', 'ai pro', 'subscriptions', 'renews on'].some((k) => txt.includes(k));
          return JSON.stringify({ ready, cards, hasKeywords });
        })();
        """
        for _ in range(30):
            try:
                result_str = await page.evaluate(script)
                res = json.loads(result_str) if isinstance(result_str, str) else result_str
                if isinstance(res, dict):
                    ready = str(res.get("ready", ""))
                    if ready in {"interactive", "complete"} and (res.get("cards") or res.get("hasKeywords")):
                        return
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.3, 0.6))
        logger.warning("订阅页动态等待超时，继续强行解析")

    async def _wait_for_invite_page_ready(self, page: Any) -> None:
        logger.info("正在动态等待邀请页渲染...")
        script = """
        (() => {
          const ready = document.readyState;
          const url = window.location.href.toLowerCase();
          
          // 1. 如果 URL 发生了重定向（脱离了 /ai/invite），说明根本没资格，可以直接放行
          const isRedirected = !url.includes('/ai/invite');

          // 2. 正常邀请页的特征
          const hasTitle = Boolean(document.querySelector('h1.axZOlc'));
          const hasLink = Boolean(document.querySelector('div.tBENuf span.gzdqbb') || document.querySelector('span.gzdqbb'));
          const hasUsage = Boolean(document.querySelector('div.R6iuQe'));
          
          const txt = (document.body && document.body.innerText) ? document.body.innerText.toLowerCase() : '';
          const hasKeyword = txt.includes('g.co/g1referral') || txt.includes('google ai pro');
          
          // 3. 页面如果没有邀请资格，通常会显示 Upgrade, 或者 Plans, 说明是普通页面
          const hasNonEligibleText = txt.includes('upgrade') || txt.includes('plans') || txt.includes('offers');

          return JSON.stringify({ 
              ready, 
              isRedirected, 
              hasInviteElements: hasTitle || hasLink || hasUsage || hasKeyword,
              hasNonEligibleText
          });
        })();
        """
        for i in range(25):
            try:
                result_str = await page.evaluate(script)
                res = json.loads(result_str) if isinstance(result_str, str) else result_str
                if isinstance(res, dict):
                    ready = str(res.get("ready", ""))
                    if ready in {"interactive", "complete"}:
                        # 核心优化：针对无资格账号的空白页/重定向页快速放行，最大等待 8 次（约 3 秒）后跳出
                        if (res.get("hasInviteElements") or
                            res.get("isRedirected") or
                            res.get("hasNonEligibleText") or
                            i > 8):
                            logger.info("%s 邀请页就绪检测通过 | elapsed≈%.1fs", self._LOG_PREFIX, i * 0.4)
                            return
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.3, 0.5))

        logger.warning("邀请页动态等待超时，页面可能为空白，继续强行解析...")

    def _parse_usage_count(self, usage_text: str | None) -> tuple[int | None, int | None]:
        if not usage_text: return None, None
        m = re.search(r"(\d+)\s+of\s+(\d+)", usage_text, re.IGNORECASE)
        if m: return int(m.group(1)), int(m.group(2))
        m = re.search(r"(\d+)\s*/\s*(\d+)", usage_text)
        if m: return int(m.group(1)), int(m.group(2))
        return None, None

    def _norm_text(self, value: Any) -> str | None:
        if value is None: return None
        text = str(value).strip()
        return text if text else None

    async def _extract_subscription_cards(self, page: Any) -> list[dict[str, Any]]:
        script = """
        (() => {
          const cards = [];
          const anchors = Array.from(document.querySelectorAll('a.tIl6ib'));
          for (const a of anchors) {
            const titleEl = a.querySelector('.pGTWsc');
            const detailEls = Array.from(a.querySelectorAll('.SeZS9d'));
            cards.push({
              title: titleEl ? titleEl.textContent.trim() : '',
              details: detailEls.map((el) => (el.textContent || '').trim()).filter(Boolean),
              href: a.getAttribute('href') || '',
            });
          }
          const listItems = Array.from(document.querySelectorAll('div[role="listitem"]'));
          for (const item of listItems) {
            const titleEl = item.querySelector('.pGTWsc');
            const detailEls = Array.from(item.querySelectorAll('.SeZS9d'));
            if (!titleEl && detailEls.length === 0) continue;
            const linkEl = item.querySelector('a.tIl6ib, a[href*="subscriptions"]');
            cards.push({
              title: titleEl ? (titleEl.textContent || '').trim() : '',
              details: detailEls.map((el) => (el.textContent || '').trim()).filter(Boolean),
              href: linkEl ? (linkEl.getAttribute('href') || '') : '',
            });
          }
          const seen = new Set();
          const filtered = cards.filter((c) => {
            const key = `${c.title}::${(c.details || []).join('|')}::${c.href}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          });
          return JSON.stringify(filtered);
        })();
        """
        try:
            result_str = await page.evaluate(script)
            if isinstance(result_str, str):
                return json.loads(result_str)
            if isinstance(result_str, list):
                return result_str
        except Exception as e:
            logger.error("提取订阅卡片 JS 执行异常: %s", e)
        return []

    def _pick_onepro_card(self, cards: list[dict[str, Any]]) -> dict[str, Any] | None:
        for card in cards:
            title = str(card.get("title", "")).lower()
            details = " ".join(str(x).lower() for x in card.get("details", []))
            merged = f"{title} {details}"
            # 此处已涵盖 one pro, ai pro, ai premium
            if "google one" in merged or "one pro" in merged or "ai pro" in merged or "ai premium" in merged:
                return card
        return None

    def _extract_expire_from_details(self, details: list[str]) -> str | None:
        for line in details:
            m = re.search(r"renews on\s+(.+)$", line, re.IGNORECASE)
            if m: return m.group(1).strip()
            m = re.search(r"(?:到期|续订)\s*[:：]?\s*(.+)$", line, re.IGNORECASE)
            if m: return m.group(1).strip()
        return None

    async def _extract_page_text(self, page: Any) -> str:
        script = "(() => { const title = document.title || ''; const bodyText = (document.body && document.body.innerText) ? document.body.innerText : ''; return `${title}\\n${bodyText}`; })();"
        try:
            result = await page.evaluate(script)
            return str(result or "")
        except Exception:
            return ""

    async def _get_current_url(self, page: Any) -> str:
        current_url = getattr(page, "url", "")
        if current_url:
            return str(current_url)
        try:
            result = await page.evaluate("window.location.href")
            return str(result or "")
        except Exception:
            return ""

    def _detect_onepro(self, text: str) -> bool:
        lower_text = text.lower()
        keywords = ["google one", "one pro", "onepro", "ai premium", "ai pro", "google one 高级版", "google one 会员", "google one premium"]
        return any(word in lower_text for word in keywords)

    def _detect_subscription_status(self, text: str) -> str:
        lower_text = text.lower()
        active_keywords = ["active", "renews", "next billing", "valid until", "有效", "已开通", "续订", "下次扣费"]
        inactive_keywords = ["expired", "canceled", "cancelled", "not active", "已过期", "已取消", "未开通"]
        if any(word in lower_text for word in inactive_keywords): return "INACTIVE"
        if any(word in lower_text for word in active_keywords): return "ACTIVE"
        return "UNKNOWN"

    def _detect_expire_text(self, text: str) -> str | None:
        patterns = [
            r"(?:Renews on|Next billing date|Expires on|Valid until)\s*[:：]?\s*([^\n]{1,60})",
            r"(?:到期(?:时间|日期)?|续订(?:时间|日期)?|下次扣费(?:时间|日期)?)\s*[:：]?\s*([^\n]{1,60})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match: return match.group(1).strip()
        date_patterns = [r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", r"(\d{4}年\d{1,2}月\d{1,2}日)", r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})"]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match: return match.group(1).strip()
        return None
