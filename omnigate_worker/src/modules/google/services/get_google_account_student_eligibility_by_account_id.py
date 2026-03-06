"""Load Google account by id, login, then fetch student eligibility info."""

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
from src.modules.google.action.google_student_eligibility_actions import GoogleStudentEligibilityActions
from src.modules.google.models.google_action_params import GoogleAuthParams
from src.modules.google.models.google_service_params import GetGoogleAccountStudentEligibilityByAccountIdParams
from src.modules.google.services.google_account_persistence import GoogleAccountPersistence
from src.utils import AesTypeHandlerCompat


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GoogleAccountCredential:
    account_id: int
    email: str
    password: str
    totp_secret: str


class GetGoogleAccountStudentEligibilityByAccountIdService:
    """Service flow: load account -> login -> fetch student eligibility."""

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        browser_actions: BrowserActions | None = None,
        auth_actions: GoogleAuthActions | None = None,
        student_actions: GoogleStudentEligibilityActions | None = None,
    ) -> None:
        self._db_pool = db_pool
        self._owned_database: Database | None = None
        self.browser_actions = browser_actions or BrowserActions()
        self.auth_actions = auth_actions or GoogleAuthActions(browser_actions=self.browser_actions)
        self.student_actions = student_actions or GoogleStudentEligibilityActions(browser_actions=self.browser_actions)
        self._last_browser: Any | None = None
        self._decryptor = AesTypeHandlerCompat()

    async def execute(
        self,
        params: GetGoogleAccountStudentEligibilityByAccountIdParams | int,
        *,
        keep_page_open: bool = True,
        max_wait_seconds: int | None = None,
        persist_to_db: bool = True,
    ) -> dict[str, Any]:
        action = "get_google_account_student_eligibility_by_account_id"
        trace_id = uuid4().hex[:12]
        total_steps = 6
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
        log_step(1, f"读取账号凭据 account_id={req.google_account_id}")

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

        student_eligibility: dict[str, Any] | None = None
        if login_result.get("ok"):
            log_step(4, "抓取学生资格信息")
            try:
                raw = await self.student_actions.get_student_eligibility(browser)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Fetch student eligibility failed trace_id=%s: %s", trace_id, exc)
                student_eligibility = {"error": str(exc)}
            else:
                student_eligibility = self._to_plain_dict(raw)
                if persist_to_db:
                    log_step(5, "写入业务表")
                    await self._persist_student_eligibility(
                        account_id=credential.account_id,
                        student_eligibility=student_eligibility,
                        trace_id=trace_id,
                    )
        else:
            logger.warning("Login not successful, skip student eligibility fetch. trace_id=%s", trace_id)

        result: dict[str, Any] = {
            "account_id": credential.account_id,
            "email": credential.email,
            "trace_id": trace_id,
            "login_result": login_result,
            "student_eligibility": student_eligibility,
            "browser_kept_open": keep_page_open,
        }

        if keep_page_open:
            log_step(6, "等待手动操作")
            await self._wait_for_manual_operation(max_wait_seconds=max_wait_seconds)
        else:
            log_step(6, "跳过手动等待（keep_page_open=false）")

        logger.info(
            "服务流程完成[%s/%s] action=%s trace_id=%s account_id=%s elapsed=%.2fs",
            total_steps,
            total_steps,
            action,
            trace_id,
            credential.account_id,
            elapsed_seconds(),
        )
        return result

    async def _persist_student_eligibility(
        self,
        *,
        account_id: int,
        student_eligibility: dict[str, Any] | None,
        trace_id: str,
    ) -> None:
        pool = await self._ensure_pool()
        persistence = GoogleAccountPersistence(pool)
        await persistence.persist_student_eligibility(
            account_id=account_id,
            student_eligibility=student_eligibility,
        )
        logger.info("学生资格数据已写入业务表 trace_id=%s account_id=%s", trace_id, account_id)

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
        params: GetGoogleAccountStudentEligibilityByAccountIdParams | int,
    ) -> GetGoogleAccountStudentEligibilityByAccountIdParams:
        if isinstance(params, GetGoogleAccountStudentEligibilityByAccountIdParams):
            return params
        return GetGoogleAccountStudentEligibilityByAccountIdParams(google_account_id=int(params))

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
