"""Persist Google scraping results into existing business tables."""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

import asyncpg


class GoogleAccountPersistence:
    """Map worker results to acc_google_* tables with snapshot-style updates."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def persist_feature_snapshot(
        self,
        *,
        account_id: int,
        subscription_and_invite: dict[str, Any] | None,
        family_status: dict[str, Any] | None,
    ) -> None:
        sub_payload = self._normalize_payload(subscription_and_invite)
        family_payload = self._normalize_payload(family_status)
        if sub_payload is None and family_payload is None:
            return

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await self._upsert_status_from_features(
                    conn=conn,
                    account_id=account_id,
                    sub_payload=sub_payload,
                    family_payload=family_payload,
                )
                if family_payload is not None:
                    await self._replace_family_members(conn=conn, account_id=account_id, family_payload=family_payload)
                if sub_payload is not None:
                    await self._sync_invite_links(conn=conn, account_id=account_id, sub_payload=sub_payload)

    async def persist_student_eligibility(
        self,
        *,
        account_id: int,
        student_eligibility: dict[str, Any] | None,
    ) -> None:
        payload = self._normalize_payload(student_eligibility)
        if payload is None:
            return

        status = self._norm_text(payload.get("status")) or ""
        link = self._norm_text(payload.get("eligibility_link"))

        should_clear = status in {"已订阅", "已认证/未订阅"}
        if not link and not should_clear:
            return

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO acc_google_status (
                    account_id,
                    sub_tier,
                    family_status,
                    invite_link_status,
                    student_link,
                    invited_count,
                    deleted,
                    created_at,
                    updated_at
                )
                VALUES ($1, 'NONE', 0, 0, $2, 0, 0, now(), now())
                ON CONFLICT (account_id) DO UPDATE SET
                    student_link = $2,
                    deleted = 0,
                    updated_at = now()
                """,
                account_id,
                link if link else None,
            )

    async def persist_family_invite_result(
        self,
        *,
        account_id: int,
        invite_result: dict[str, Any] | None,
        family_status: dict[str, Any] | None = None,
    ) -> None:
        payload = self._normalize_payload(invite_result)
        if payload is None or not bool(payload.get("success")):
            return

        normalized_family_status = self._normalize_payload(family_status)
        if normalized_family_status is None:
            return

        await self.persist_feature_snapshot(
            account_id=account_id,
            subscription_and_invite=None,
            family_status=normalized_family_status,
        )

    async def _upsert_status_from_features(
        self,
        *,
        conn: asyncpg.Connection,
        account_id: int,
        sub_payload: dict[str, Any] | None,
        family_payload: dict[str, Any] | None,
    ) -> None:
        sub_tier: str | None = None
        family_status: int | None = None
        invite_link_status: int | None = None
        expire_date: date | None = None
        invited_count: int | None = None

        if sub_payload is not None:
            sub_tier = self._map_sub_tier(sub_payload)
            invite_link_status = 1 if (
                self._as_bool(sub_payload.get("has_referral_invite"))
                or self._norm_text(sub_payload.get("referral_link"))
            ) else 0
            expire_date = self._parse_date_text(self._norm_text(sub_payload.get("expires_at_text")))
            invited_count = self._clamp_invited_count(self._to_int(sub_payload.get("invitations_used")))

        if family_payload is not None:
            family_status = 1 if self._as_bool(family_payload.get("family_group_opened")) else 0
            family_member_count = self._clamp_invited_count(self._to_int(family_payload.get("member_count")))
            if family_member_count is not None:
                invited_count = family_member_count

        await conn.execute(
            """
            INSERT INTO acc_google_status (
                account_id,
                sub_tier,
                family_status,
                expire_date,
                invite_link_status,
                student_link,
                invited_count,
                deleted,
                created_at,
                updated_at
            )
            VALUES (
                $1,
                COALESCE($2, 'NONE'),
                COALESCE($3, 0),
                $4,
                COALESCE($5, 0),
                NULL,
                COALESCE($6, 0),
                0,
                now(),
                now()
            )
            ON CONFLICT (account_id) DO UPDATE SET
                sub_tier = COALESCE($2, acc_google_status.sub_tier),
                family_status = COALESCE($3, acc_google_status.family_status),
                expire_date = COALESCE($4, acc_google_status.expire_date),
                invite_link_status = COALESCE($5, acc_google_status.invite_link_status),
                invited_count = COALESCE($6, acc_google_status.invited_count),
                deleted = 0,
                updated_at = now()
            """,
            account_id,
            sub_tier,
            family_status,
            expire_date,
            invite_link_status,
            invited_count,
        )

    async def _replace_family_members(
        self,
        *,
        conn: asyncpg.Connection,
        account_id: int,
        family_payload: dict[str, Any],
    ) -> None:
        members_raw = family_payload.get("members")
        members = members_raw if isinstance(members_raw, list) else []

        await conn.execute("DELETE FROM acc_google_family_member WHERE account_id = $1", account_id)

        rows: list[tuple[int, str, str, date | None, int]] = []
        for item in members:
            if not isinstance(item, dict):
                continue
            email = self._norm_text(item.get("member_email"))
            if not email:
                continue
            member_name = self._norm_text(item.get("member_name"))
            if not member_name:
                continue
            invite_date = self._parse_date_text(self._norm_text(item.get("invite_date")))
            member_role = self._map_member_role(item.get("member_role"))
            if member_role is None:
                continue
            rows.append((account_id, member_name, email, invite_date, member_role))

        if not rows:
            return

        await conn.executemany(
            """
            INSERT INTO acc_google_family_member (
                account_id,
                member_name,
                member_email,
                invite_date,
                member_role,
                deleted,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, 0, now(), now())
            """,
            rows,
        )

    async def _sync_invite_links(
        self,
        *,
        conn: asyncpg.Connection,
        account_id: int,
        sub_payload: dict[str, Any],
    ) -> None:
        referral_link = self._norm_text(sub_payload.get("referral_link"))
        has_referral_invite = self._as_bool(sub_payload.get("has_referral_invite"))
        used_count = self._clamp_invited_count(self._to_int(sub_payload.get("invitations_used")))
        used_count = used_count if used_count is not None else 0

        # 这里按“快照同步”处理，避免历史脏数据影响前端展示。
        if not referral_link and has_referral_invite:
            return

        await conn.execute("DELETE FROM acc_google_invite_link WHERE account_id = $1", account_id)
        if not referral_link:
            return

        await conn.execute(
            """
            INSERT INTO acc_google_invite_link (
                account_id,
                invite_url,
                used_count,
                deleted,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, 0, now(), now())
            """,
            account_id,
            referral_link,
            used_count,
        )

    @staticmethod
    def _normalize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        if "error" in payload:
            return None
        return payload

    @staticmethod
    def _map_sub_tier(sub_payload: dict[str, Any]) -> str:
        if not bool(sub_payload.get("found_onepro")):
            return "NONE"

        status = str(sub_payload.get("subscription_status") or "").upper()
        if status == "INACTIVE":
            return "NONE"

        name = str(sub_payload.get("subscription_name") or "").lower()
        if "ultra" in name:
            return "AI_ULTRA"
        if "plus" in name:
            return "AI_PLUS"
        return "AI_PRO"

    @staticmethod
    def _map_member_role(raw_role: Any) -> int | None:
        if isinstance(raw_role, int):
            if raw_role in {1, 2}:
                return raw_role
            return None
        role_text = str(raw_role or "").strip().lower()
        if not role_text:
            return None
        manager_keywords = ("manager", "admin", "owner", "管理员", "管理者", "组织者")
        member_keywords = ("member", "成员")
        if any(keyword in role_text for keyword in manager_keywords):
            return 1
        if any(keyword in role_text for keyword in member_keywords):
            return 2
        return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clamp_invited_count(value: int | None) -> int | None:
        if value is None:
            return None
        return max(0, min(5, value))

    @staticmethod
    def _norm_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _as_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n", ""}:
            return False
        return bool(value)

    @staticmethod
    def _parse_date_text(raw: str | None) -> date | None:
        text = (raw or "").strip()
        if not text:
            return None

        text = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE)
        text = text.replace("，", ",").replace("年", "-").replace("月", "-").replace("日", "")
        text = re.sub(r"\s+", " ", text).strip()

        candidates = [
            text,
            *GoogleAccountPersistence._extract_date_candidates(text),
        ]
        for candidate in candidates:
            parsed = GoogleAccountPersistence._try_parse_date(candidate)
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _extract_date_candidates(text: str) -> list[str]:
        patterns = [
            r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",
            r"\d{1,2}[-/.]\d{1,2}[-/.]\d{4}",
            r"[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}",
            r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}",
        ]
        results: list[str] = []
        for pattern in patterns:
            results.extend(re.findall(pattern, text))
        return results

    @staticmethod
    def _try_parse_date(text: str) -> date | None:
        normalized = text.strip()
        if not normalized:
            return None
        formats = (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%m-%d-%Y",
            "%d-%m-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %d %Y",
            "%b %d %Y",
            "%d %B %Y",
            "%d %b %Y",
        )
        for fmt in formats:
            try:
                return datetime.strptime(normalized, fmt).date()
            except ValueError:
                continue
        return None
