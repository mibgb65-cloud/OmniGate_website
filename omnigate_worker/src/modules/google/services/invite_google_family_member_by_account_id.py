"""Load Google account by id, login, then invite a family member."""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import re
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import asyncpg

from src.browser.browser_actions import BrowserActions
from src.config import settings
from src.db.database import Database
from src.modules.google.action.google_auth_actions import GoogleAuthActions
from src.modules.google.action.google_family_invite_actions import GoogleFamilyInviteActions
from src.modules.google.action.google_family_status_actions import GoogleFamilyActions
from src.modules.google.models.google_action_params import GoogleAuthParams, GoogleFamilyInviteParams
from src.modules.google.models.google_service_params import InviteGoogleFamilyMemberByAccountIdParams
from src.modules.google.services.google_account_persistence import GoogleAccountPersistence
from src.utils import AesTypeHandlerCompat


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GoogleAccountCredential:
    account_id: int
    email: str
    password: str
    totp_secret: str


class InviteGoogleFamilyMemberByAccountIdService:
    """Service flow: load account -> login -> invite target email."""

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        browser_actions: BrowserActions | None = None,
        auth_actions: GoogleAuthActions | None = None,
        family_invite_actions: GoogleFamilyInviteActions | None = None,
        family_actions: GoogleFamilyActions | None = None,
    ) -> None:
        self._db_pool = db_pool
        self._owned_database: Database | None = None
        self.browser_actions = browser_actions or BrowserActions()
        self.auth_actions = auth_actions or GoogleAuthActions(browser_actions=self.browser_actions)
        self.family_invite_actions = (
            family_invite_actions or GoogleFamilyInviteActions(browser_actions=self.browser_actions)
        )
        self.family_actions = family_actions or GoogleFamilyActions(browser_actions=self.browser_actions)
        self._last_browser: Any | None = None
        self._decryptor = AesTypeHandlerCompat()

    async def execute(
        self,
        params: InviteGoogleFamilyMemberByAccountIdParams | dict[str, Any],
        *,
        keep_page_open: bool = True,
        max_wait_seconds: int | None = None,
        persist_to_db: bool = True,
    ) -> dict[str, Any]:
        action = "invite_google_family_member_by_account_id"
        trace_id = uuid4().hex[:12]
        total_steps = 7
        started_at = time.monotonic()

        def elapsed_seconds() -> float:
            return round(time.monotonic() - started_at, 2)

        def log_step(step_no: int, title: str) -> None:
            logger.info(
                "服务流程[%s/%s] action=%s trace_id=%s %s",
                step_no,
                total_steps,
                action,
                trace_id,
                title,
            )

        req = self._normalize_params(params)
        log_step(1, f"读取账号凭据 account_id={req.google_account_id} target_email={req.invited_account_email}")

        credential = await self._load_credential(req.google_account_id)
        log_step(2, "启动浏览器")
        browser = await self.browser_actions.start_browser()
        self._last_browser = browser

        log_step(3, "执行登录")
        auth_params = GoogleAuthParams(
            google_account=credential.email,
            password=credential.password,
            twofa=credential.totp_secret,
        )
        login_result = await self.auth_actions.login_google(browser, auth_params)

        invite_result: dict[str, Any] | None = None
        if login_result.get("ok"):
            log_step(4, "执行家庭组邀请动作")
            try:
                raw = await self.family_invite_actions.invite_family_member(
                    browser=browser,
                    params=GoogleFamilyInviteParams(target_email=req.invited_account_email),
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Invite family member failed trace_id=%s: %s", trace_id, exc)
                invite_result = {"error": str(exc)}
            else:
                invite_result = self._to_plain_dict(raw)
                if persist_to_db:
                    log_step(5, "邀请后页面确认成员信息")
                    confirmed_family_status = await self._confirm_family_status_after_invite(
                        browser=browser,
                        target_email=req.invited_account_email,
                        trace_id=trace_id,
                    )
                    log_step(6, "写入业务表")
                    await self._persist_invite_result(
                        account_id=credential.account_id,
                        invite_result=invite_result,
                        family_status=confirmed_family_status,
                        trace_id=trace_id,
                    )
        else:
            logger.warning("Login not successful, skip family invite. trace_id=%s", trace_id)

        result: dict[str, Any] = {
            "account_id": credential.account_id,
            "email": credential.email,
            "trace_id": trace_id,
            "target_email": req.invited_account_email,
            "login_result": login_result,
            "invite_result": invite_result,
            "browser_kept_open": keep_page_open,
        }

        if keep_page_open:
            log_step(7, "等待手动操作")
            await self._wait_for_manual_operation(max_wait_seconds=max_wait_seconds)
        else:
            log_step(7, "跳过手动等待（keep_page_open=false）")

        logger.info(
            "服务流程完成[%s/%s] action=%s trace_id=%s account_id=%s target_email=%s elapsed=%.2fs",
            total_steps,
            total_steps,
            action,
            trace_id,
            credential.account_id,
            req.invited_account_email,
            elapsed_seconds(),
        )
        return result

    async def _persist_invite_result(
        self,
        *,
        account_id: int,
        invite_result: dict[str, Any] | None,
        family_status: dict[str, Any] | None,
        trace_id: str,
    ) -> None:
        pool = await self._ensure_pool()
        persistence = GoogleAccountPersistence(pool)
        await persistence.persist_family_invite_result(
            account_id=account_id,
            invite_result=invite_result,
            family_status=family_status,
        )
        logger.info("家庭组邀请结果已写入业务表 trace_id=%s account_id=%s", trace_id, account_id)

    async def _confirm_family_status_after_invite(
        self,
        *,
        browser: Any,
        target_email: str,
        trace_id: str,
        max_rounds: int = 3,
    ) -> dict[str, Any] | None:
        target = (target_email or "").strip().lower()
        if not target:
            return None

        latest_payload: dict[str, Any] | None = None
        for round_no in range(1, max(1, max_rounds) + 1):
            try:
                family_raw = await self.family_actions.check_family_group(browser)
                family_payload = self._to_plain_dict(family_raw)
            except Exception as exc:  # noqa: BLE001
                logger.warning("邀请后确认家庭组成员失败 trace_id=%s round=%s error=%s", trace_id, round_no, exc)
                family_payload = None

            if isinstance(family_payload, dict):
                latest_payload = family_payload
                members_raw = family_payload.get("members")
                members = members_raw if isinstance(members_raw, list) else []
                for item in members:
                    if not isinstance(item, dict):
                        continue
                    member_email = str(item.get("member_email") or "").strip().lower()
                    member_name = str(item.get("member_name") or "").strip()
                    member_role = str(item.get("member_role") or "").strip()
                    if member_email == target and member_name and member_role:
                        logger.info(
                            "邀请后成员确认成功 trace_id=%s email=%s name=%s role=%s",
                            trace_id,
                            member_email,
                            member_name,
                            member_role,
                        )
                        return family_payload

            if round_no < max_rounds:
                await asyncio.sleep(2.0)

        logger.warning("邀请后未确认到完整成员信息 trace_id=%s target_email=%s", trace_id, target)
        return latest_payload

    async def close_browser(self) -> None:
        if self._last_browser is not None:
            await self.browser_actions.close_browser()
            self._last_browser = None
            logger.info("Browser closed.")

    async def close(self) -> None:
        await self.close_browser()
        if self._owned_database is not None:
            await self._owned_database.close()
            self._owned_database = None
            self._db_pool = None

    async def _load_credential(self, account_id: int) -> GoogleAccountCredential:
        pool = await self._ensure_pool()
        query = """
            SELECT id, email, password, COALESCE(totp_secret, '') AS totp_secret
            FROM acc_google_base
            WHERE id = $1
              AND deleted = 0
            LIMIT 1
        """
        row = await pool.fetchrow(query, account_id)
        if row is None:
            raise ValueError(f"Google account not found or deleted: account_id={account_id}")

        email = str(row["email"] or "").strip()
        encrypted_password = str(row["password"] or "")
        encrypted_totp = str(row["totp_secret"] or "")

        if not self._decryptor.is_backend_available():
            if self._looks_like_cipher_text(encrypted_password) or self._looks_like_cipher_text(encrypted_totp):
                raise RuntimeError(
                    "AES-like ciphertext detected, but pycryptodome is missing. "
                    "Run: pip install pycryptodome"
                )

        password = str(self._decryptor.decrypt_safely(encrypted_password) or "")
        if not email:
            raise ValueError(f"Google account email is empty: account_id={account_id}")
        if not password:
            raise ValueError(f"Google account password is empty: account_id={account_id}")

        return GoogleAccountCredential(
            account_id=int(row["id"]),
            email=email,
            password=password,
            totp_secret=str(self._decryptor.decrypt_safely(encrypted_totp) or "").strip(),
        )

    async def _ensure_pool(self) -> asyncpg.Pool:
        if self._db_pool is not None:
            return self._db_pool
        if self._owned_database is None:
            self._owned_database = Database(settings.postgres_dsn)
            await self._owned_database.connect()
            self._db_pool = self._owned_database.pool
        return self._db_pool

    async def _wait_for_manual_operation(self, *, max_wait_seconds: int | None) -> None:
        start = time.monotonic()
        logger.info("Browser is kept open for manual operation.")
        while True:
            if max_wait_seconds is not None and max_wait_seconds >= 0:
                elapsed = time.monotonic() - start
                if elapsed >= max_wait_seconds:
                    logger.info("Reach max_wait_seconds=%s, stop waiting.", max_wait_seconds)
                    return
            await asyncio.sleep(0.5)

    @staticmethod
    def _normalize_params(
        params: InviteGoogleFamilyMemberByAccountIdParams | dict[str, Any],
    ) -> InviteGoogleFamilyMemberByAccountIdParams:
        if isinstance(params, InviteGoogleFamilyMemberByAccountIdParams):
            return params
        if isinstance(params, dict):
            return InviteGoogleFamilyMemberByAccountIdParams.model_validate(params)
        raise TypeError("params must be InviteGoogleFamilyMemberByAccountIdParams or dict")

    @staticmethod
    def _looks_like_cipher_text(value: str) -> bool:
        raw = (value or "").strip()
        if len(raw) < 24 or len(raw) % 4 != 0:
            return False
        if not re.fullmatch(r"[A-Za-z0-9+/=]+", raw):
            return False
        if not any(ch in raw for ch in "+/=") and not any(ch.islower() for ch in raw):
            return False
        try:
            decoded = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError):
            return False
        if not decoded or len(decoded) % 16 != 0:
            return False
        return True

    @staticmethod
    def _to_plain_dict(value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return model_dump()
        return {"value": str(value)}
