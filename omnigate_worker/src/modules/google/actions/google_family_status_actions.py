"""Google 家庭组检查动作。"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from typing import Any

from src.browser.browser_actions import BrowserActions
from src.modules.google.models.google_action_results import GoogleFamilyCheckResult, GoogleFamilyMemberInfo

logger = logging.getLogger(__name__)


class GoogleFamilyActions:
    """检查家庭组开通状态、成员邮箱、邀请剩余数量。"""

    _LOG_PREFIX = "[Google家庭状态]"

    def __init__(self, browser_actions: BrowserActions | None = None) -> None:
        self.browser_actions = browser_actions or BrowserActions()

    async def check_family_group(self, browser: Any) -> GoogleFamilyCheckResult:
        total_steps = 5
        flow_started_at = time.monotonic()

        def elapsed_seconds() -> float:
            return round(time.monotonic() - flow_started_at, 2)

        def log_step(step_no: int, title: str) -> None:
            logger.info("%s 步骤=%s/%s | %s", self._LOG_PREFIX, step_no, total_steps, title)

        source_url = "https://myaccount.google.com/family/details?hl=en"
        log_step(1, "打开家庭组详情页")
        page = await self.browser_actions.open_page(browser=browser, url=source_url)

        log_step(2, "等待页面渲染并检查拦截状态")
        await self._wait_for_family_page_ready(page)

        current_url = await self._get_current_url(page)
        current_url_str = current_url.lower()

        if "signin" in current_url_str or "challenge" in current_url_str:
            logger.error("%s 页面被拦截，需要二次验证 | current_url=%s", self._LOG_PREFIX, current_url)
            result = GoogleFamilyCheckResult(
                source_url=str(current_url),
                family_group_opened=False,
                has_get_started=False,
                can_send_invitations=False,
                invitations_left=None,
                invitations_text=None,
                member_count=0,
                members=[],
            )
            logger.warning(
                "%s 流程完成 | 步骤=%s/%s | auth_required=%s | elapsed=%.2fs",
                self._LOG_PREFIX,
                total_steps,
                total_steps,
                True,
                elapsed_seconds(),
            )
            return result

        log_step(3, "解析家庭组概要信息")
        summary = await self._extract_family_summary(page)

        if "error" in summary:
            logger.error("%s JS 执行异常 | 原因=%s", self._LOG_PREFIX, summary["error"])

        has_get_started = bool(summary.get("has_get_started"))
        member_candidates = summary.get("member_candidates", [])

        invitations_text = self._norm_text(summary.get("invitations_text"))
        invitations_left = self._parse_invitations_left(invitations_text)

        family_group_opened = not has_get_started
        members: list[GoogleFamilyMemberInfo] = []

        log_step(4, "抓取家庭成员详情")
        if family_group_opened and member_candidates:
            logger.info("%s 已提取待抓取成员，开始并发抓取详情 | count=%s", self._LOG_PREFIX, len(member_candidates))

            seen_href: set[str] = set()
            # 限制并发数为 3，防止一次性打开太多标签页被 Google 封控或浏览器卡死
            semaphore = asyncio.Semaphore(3)
            tasks = []

            for item in member_candidates:
                href = self._to_absolute_member_url(item.get("href"))
                if not href or href in seen_href:
                    continue
                seen_href.add(href)

                # 创建并发任务
                tasks.append(self._fetch_single_member_info(browser, href, item, semaphore))

            # 核心优化：并行执行所有成员的详情页抓取
            results = await asyncio.gather(*tasks)
            members = self._dedupe_members([res for res in results if res is not None])
        else:
            logger.info("当前无需抓取成员详情（家庭组未开通或无可解析成员）。")

        log_step(5, "汇总家庭组结果")
        result = GoogleFamilyCheckResult(
            source_url=source_url,
            family_group_opened=family_group_opened,
            has_get_started=has_get_started,
            can_send_invitations=invitations_left is not None and invitations_left > 0,
            invitations_left=invitations_left,
            invitations_text=invitations_text,
            member_count=len(members),
            members=members,
        )
        logger.info(
            "%s 流程完成 | 步骤=%s/%s | opened=%s | invitations_left=%s | members=%s | elapsed=%.2fs",
            self._LOG_PREFIX,
            total_steps,
            total_steps,
            result.family_group_opened,
            result.invitations_left,
            result.member_count,
            elapsed_seconds(),
        )
        return result

    async def _fetch_single_member_info(self, browser: Any, href: str, item: dict,
                                        semaphore: asyncio.Semaphore) -> GoogleFamilyMemberInfo | None:
        """并发抓取单名成员的逻辑封装"""
        async with semaphore:
            try:
                # 拟人化错峰打开
                await asyncio.sleep(random.uniform(0.1, 0.5))
                member_page = await self.browser_actions.open_page(browser=browser, url=href)
                await self._wait_for_member_page_ready(member_page)

                member_detail = await self._extract_member_detail_with_retry(member_page)

                info = GoogleFamilyMemberInfo(
                    member_name=member_detail.get("member_name") or item.get("member_name"),
                    member_role=member_detail.get("member_role") or item.get("member_role"),
                    member_email=member_detail.get("member_email"),
                    member_href=href,
                )

                logger.info(
                    "%s 成员详情解析完成 | name=%s | role=%s | email=%s | href=%s",
                    self._LOG_PREFIX,
                    info.member_name,
                    info.member_role,
                    self._mask_email(info.member_email or ""),
                    href,
                )

                # 已移除可能导致 nodriver 底层 WebSocket 崩溃的 await member_page.close()

                return info
            except Exception as exc:
                logger.error("%s 抓取成员详情异常 | href=%s | 原因=%s", self._LOG_PREFIX, href, exc)
                return None

    async def _wait_for_family_page_ready(self, page: Any) -> None:
        script = """
        (() => {
            const ready = document.readyState;
            const url = window.location.href.toLowerCase();
            if (url.includes('signin') || url.includes('challenge')) return true;

            const links = Array.from(document.querySelectorAll('a'));
            const hasCards = links.some(a => a.href && a.href.includes('family/member/'));
            const hasGetStarted = links.some(a => a.href && a.href.includes('family/create'));
            const hasInvite = links.some(a => a.href && a.href.includes('family/invitemembers'));

            return (ready === 'interactive' || ready === 'complete') && (hasCards || hasGetStarted || hasInvite);
        })();
        """
        for _ in range(40):
            try:
                if await page.evaluate(script):
                    return
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.3, 0.6))
        logger.warning("家庭组主页等待超时，继续尝试解析。")

    async def _wait_for_member_page_ready(self, page: Any) -> None:
        script = """
        (() => {
            const ready = document.readyState;
            const hasHeader = document.querySelector('h2.f0YdKf') || document.querySelector('h2');
            const hasEmail = document.body && document.body.innerText.includes('@');
            return (ready === 'interactive' || ready === 'complete') && !!(hasHeader || hasEmail);
        })();
        """
        for _ in range(25):
            try:
                if await page.evaluate(script):
                    return
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.2, 0.5))
        logger.warning("成员详情页等待超时，继续尝试提取。")

    async def _extract_family_summary(self, page: Any) -> dict[str, Any]:
        script = """
        (() => {
          try {
              const links = Array.from(document.querySelectorAll('a'));
              const getStartedNode = links.find(a => a.href && a.href.includes('family/create'));
              const hasGetStarted = Boolean(getStartedNode);

              const inviteBtn = links.find(a => a.href && a.href.includes('invitemembers'));
              const invitationsText = inviteBtn ? (inviteBtn.textContent || inviteBtn.getAttribute('aria-label') || '').trim() : null;

              const cards = links.filter(a => a.href && a.href.includes('family/member/'));

              const memberCandidates = [];
              for (const a of cards) {
                  const nameNode = a.querySelector('.IlKlLe');
                  const roleNode = a.querySelector('.ImPZoc');
                  const lines = (a.innerText || a.textContent || '')
                      .split('\\n')
                      .map(s => s.trim())
                      .filter(Boolean);
                  const role = (roleNode ? roleNode.textContent : '') || (lines.length > 1 ? lines[1] : '');
                  const name = (nameNode ? nameNode.textContent : '') || (lines.length > 0 ? lines[0] : '');
                  memberCandidates.push({
                      href: a.href,
                      member_name: (name || '').trim() || null,
                      member_role: (role || '').trim() || null
                  });
              }
              return JSON.stringify({
                has_get_started: hasGetStarted,
                invitations_text: invitationsText,
                member_candidates: memberCandidates,
              });
          } catch(e) {
              return JSON.stringify({error: e.toString()});
          }
        })();
        """
        try:
            result_str = await page.evaluate(script)
            if isinstance(result_str, str):
                return json.loads(result_str)
            elif isinstance(result_str, dict):
                return result_str
        except Exception as exc:
            logger.error("%s 提取家庭组概要失败 | 原因=%s", self._LOG_PREFIX, exc)
        return {}

    async def _extract_member_detail(self, page: Any) -> dict[str, Any]:
        script = """
        (() => {
          try {
              const root = document.querySelector('.c0puDb') || document.body;
              if (!root) return JSON.stringify({ member_name: null, member_email: null, member_role: null });

              let nameNode = root.querySelector('h2.f0YdKf') || root.querySelector('h2');
              const name = nameNode ? (nameNode.textContent || '').trim() : null;

              const pList = Array.from(root.querySelectorAll('p')).map((el) => (el.textContent || '').trim()).filter(Boolean);
              const emailFromText = pList.find((x) => x.includes('@')) || null;
              const emailFromMailto = root.querySelector('a[href^="mailto:"]')?.getAttribute('href') || null;
              const emailFromBody = (document.body && document.body.innerText || '').match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}/ig);
              const email = emailFromText || (emailFromMailto ? emailFromMailto.replace(/^mailto:/i, '') : null) || (emailFromBody ? emailFromBody[0] : null);
              const role = pList.find((x) => /member|manager|成员|管理/i.test(x)) || null;

              return JSON.stringify({
                member_name: name,
                member_email: email,
                member_role: role,
              });
          } catch(e) {
              return JSON.stringify({ error: e.toString() });
          }
        })();
        """
        try:
            result_str = await page.evaluate(script)
            if isinstance(result_str, str):
                result = json.loads(result_str)
                result["member_email"] = self._extract_email(result.get("member_email"))
                return result
            elif isinstance(result_str, dict):
                result_str["member_email"] = self._extract_email(result_str.get("member_email"))
                return result_str
        except Exception as exc:
            logger.error("%s 提取成员详情失败 | 原因=%s", self._LOG_PREFIX, exc)
        return {}

    async def _extract_member_detail_with_retry(self, page: Any) -> dict[str, Any]:
        detail: dict[str, Any] = {}
        for _ in range(8):
            detail = await self._extract_member_detail(page)
            if detail.get("member_email"):
                return detail
            await asyncio.sleep(random.uniform(0.3, 0.5))
        return detail

    def _dedupe_members(self, members: list[GoogleFamilyMemberInfo]) -> list[GoogleFamilyMemberInfo]:
        deduped: list[GoogleFamilyMemberInfo] = []
        seen_keys: set[str] = set()

        for item in members:
            key = self._build_member_dedupe_key(item)
            if key in seen_keys:
                logger.warning("%s 检测到重复家庭成员，已去重 | key=%s", self._LOG_PREFIX, key)
                continue
            seen_keys.add(key)
            deduped.append(item)
        return deduped

    def _build_member_dedupe_key(self, item: GoogleFamilyMemberInfo) -> str:
        email = self._extract_email(item.member_email)
        if email:
            return f"email:{email}"

        href = self._to_absolute_member_url(item.member_href)
        if href:
            return f"href:{href.lower()}"

        name = (self._norm_text(item.member_name) or "-").lower()
        role = (self._norm_text(item.member_role) or "-").lower()
        return f"name-role:{name}|{role}"

    # 下方辅助方法保持不变
    def _to_absolute_member_url(self, href: Any) -> str | None:
        text = self._norm_text(href)
        if not text: return None
        if text.startswith("http://") or text.startswith("https://"): return text
        return f"https://myaccount.google.com/{text.lstrip('/')}"

    def _parse_invitations_left(self, text: str | None) -> int | None:
        if not text: return None
        m = re.search(r"\((\d+)\s*left\)", text, re.IGNORECASE)
        if m: return int(m.group(1))
        m = re.search(r"\((\d+)\)", text)
        if m: return int(m.group(1))
        return None

    def _norm_text(self, value: Any) -> str | None:
        if value is None: return None
        text = str(value).strip()
        return text or None

    def _extract_email(self, value: Any) -> str | None:
        text = self._norm_text(value)
        if not text: return None
        text = text.replace("mailto:", "").strip()
        match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
        if not match: return None
        return match.group(0).lower()

    async def _get_current_url(self, page: Any) -> str:
        current_url = getattr(page, "url", "")
        if current_url: return str(current_url)
        try:
            result = await page.evaluate("window.location.href")
            return str(result or "")
        except Exception:
            return ""

    @staticmethod
    def _mask_email(email: str) -> str:
        normalized = (email or "").strip()
        if "@" not in normalized:
            return normalized

        local_part, domain = normalized.split("@", 1)
        if len(local_part) <= 4:
            masked_local = f"{local_part[:1]}***"
        else:
            masked_local = f"{local_part[:2]}***{local_part[-2:]}"
        return f"{masked_local}@{domain}"
