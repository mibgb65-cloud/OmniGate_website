"""根据账号 ID 查询账号并执行 Google 登录。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any
import base64
import binascii
import re
from uuid import uuid4

import asyncpg

from src.browser.browser_actions import BrowserActions
from src.config import settings
from src.db.database import Database
from src.modules.google.action.google_auth_actions import GoogleAuthActions
from src.modules.google.action.google_family_status_actions import GoogleFamilyActions
from src.modules.google.action.google_subscription_actions import GoogleSubscriptionActions
from src.modules.google.models.google_action_params import GoogleAuthParams
from src.modules.google.models.google_service_params import GetGoogleAccountFeatureByAccountIdParams
from src.modules.google.services.google_account_persistence import GoogleAccountPersistence
from src.utils import AesTypeHandlerCompat


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GoogleAccountCredential:
    account_id: int
    email: str
    password: str
    totp_secret: str


class GetGoogleAccountFeatureByAccountIdService:
    """
    服务职责：
    1. 根据账号 ID 从 acc_google_base 读取账号凭据
    2. 调用 GoogleAuthActions 执行登录
    3. 登录后默认保持页面打开，便于人工后续操作
    """

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        browser_actions: BrowserActions | None = None,
        auth_actions: GoogleAuthActions | None = None,
        subscription_actions: GoogleSubscriptionActions | None = None,
        family_actions: GoogleFamilyActions | None = None,
    ) -> None:
        self._db_pool = db_pool
        self._owned_database: Database | None = None
        self.browser_actions = browser_actions or BrowserActions()
        self.auth_actions = auth_actions or GoogleAuthActions(browser_actions=self.browser_actions)
        self.subscription_actions = subscription_actions or GoogleSubscriptionActions(browser_actions=self.browser_actions)
        self.family_actions = family_actions or GoogleFamilyActions(browser_actions=self.browser_actions)
        self._last_browser: Any | None = None
        self._decryptor = AesTypeHandlerCompat()

    async def execute(
        self,
        params: GetGoogleAccountFeatureByAccountIdParams | int,
        *,
        keep_page_open: bool = True,
        max_wait_seconds: int | None = None,
        collect_features: bool = True,
        persist_to_db: bool = True,
    ) -> dict[str, Any]:
        action = "get_google_account_feature_by_account_id"
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
        logger.info("账号信息读取完成 trace_id=%s email=%s", trace_id, credential.email)

        log_step(2, "启动浏览器")
        browser = await self.browser_actions.start_browser()
        self._last_browser = browser
        logger.info("浏览器已启动 trace_id=%s", trace_id)

        log_step(3, "执行登录")
        auth_params = GoogleAuthParams(
            google_account=credential.email,
            password=credential.password,
            twofa=credential.totp_secret,
        )
        login_result = await self.auth_actions.login_google(browser, auth_params)
        logger.info(
            "登录动作执行结束 trace_id=%s ok=%s step=%s",
            trace_id,
            login_result.get("ok"),
            login_result.get("step"),
        )

        subscription_and_invite: dict[str, Any] | None = None
        family_status: dict[str, Any] | None = None
        if collect_features and login_result.get("ok"):
            log_step(4, "抓取订阅与家庭组信息")
            (
                subscription_and_invite,
                family_status,
            ) = await self._collect_account_features(browser=browser, trace_id=trace_id)
            if persist_to_db:
                log_step(5, "写入业务表")
                await self._persist_account_features(
                    account_id=credential.account_id,
                    subscription_and_invite=subscription_and_invite,
                    family_status=family_status,
                    trace_id=trace_id,
                )
        elif collect_features:
            logger.warning("登录未成功，跳过订阅与家庭组信息抓取 trace_id=%s", trace_id)
        else:
            logger.info("collect_features=false，跳过特征抓取 trace_id=%s", trace_id)

        result: dict[str, Any] = {
            "account_id": credential.account_id,
            "email": credential.email,
            "trace_id": trace_id,
            "login_result": login_result,
            "subscription_and_invite": subscription_and_invite,
            "family_status": family_status,
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

    async def _collect_account_features(
        self,
        *,
        browser: Any,
        trace_id: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        subscription_and_invite: dict[str, Any] | None = None
        family_status: dict[str, Any] | None = None

        logger.info("开始顺序抓取账号特征 trace_id=%s：先订阅信息，再家庭组信息。", trace_id)
        try:
            sub_raw = await self.subscription_actions.get_onepro_subscription_status(browser)
        except Exception as exc:  # noqa: BLE001
            logger.exception("抓取订阅信息失败 trace_id=%s: %s", trace_id, exc)
            subscription_and_invite = {"error": str(exc)}
        else:
            subscription_and_invite = self._to_plain_dict(sub_raw)

        try:
            family_raw = await self.family_actions.check_family_group(browser)
        except Exception as exc:  # noqa: BLE001
            logger.exception("抓取家庭组信息失败 trace_id=%s: %s", trace_id, exc)
            family_status = {"error": str(exc)}
        else:
            family_status = self._to_plain_dict(family_raw)
        return subscription_and_invite, family_status

    async def _persist_account_features(
        self,
        *,
        account_id: int,
        subscription_and_invite: dict[str, Any] | None,
        family_status: dict[str, Any] | None,
        trace_id: str,
    ) -> None:
        pool = await self._ensure_pool()
        persistence = GoogleAccountPersistence(pool)
        await persistence.persist_feature_snapshot(
            account_id=account_id,
            subscription_and_invite=subscription_and_invite,
            family_status=family_status,
        )
        logger.info("账号特征数据已写入业务表 trace_id=%s account_id=%s", trace_id, account_id)

    async def close_browser(self) -> None:
        if self._last_browser is not None:
            await self.browser_actions.close_browser()
            self._last_browser = None
            logger.info("浏览器已关闭。")

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
            raise ValueError(f"Google 账号不存在或已删除: account_id={account_id}")

        email = str(row["email"] or "").strip()
        encrypted_password = str(row["password"] or "")
        encrypted_totp = str(row["totp_secret"] or "")

        if not self._decryptor.is_backend_available():
            if self._looks_like_cipher_text(encrypted_password) or self._looks_like_cipher_text(encrypted_totp):
                raise RuntimeError(
                    "检测到数据库可能为 AES 密文，但当前环境缺少 pycryptodome，无法解密。"
                    "请先执行: pip install pycryptodome"
                )

        password = str(self._decryptor.decrypt_safely(encrypted_password) or "")
        if not email:
            raise ValueError(f"Google 账号邮箱为空: account_id={account_id}")
        if not password:
            raise ValueError(f"Google 账号密码为空: account_id={account_id}")

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
        """
        保持页面打开：
        - max_wait_seconds=None: 一直等待，直到进程被手动中断（Ctrl+C）
        - max_wait_seconds>0: 等待固定秒数，便于自动化测试
        """
        start = time.monotonic()
        logger.info("页面已保持打开，等待手动操作。")
        while True:
            if max_wait_seconds is not None and max_wait_seconds >= 0:
                elapsed = time.monotonic() - start
                if elapsed >= max_wait_seconds:
                    logger.info("达到 max_wait_seconds=%s，结束等待。", max_wait_seconds)
                    return
            await asyncio.sleep(0.5)

    @staticmethod
    def _normalize_params(
        params: GetGoogleAccountFeatureByAccountIdParams | int,
    ) -> GetGoogleAccountFeatureByAccountIdParams:
        if isinstance(params, GetGoogleAccountFeatureByAccountIdParams):
            return params
        return GetGoogleAccountFeatureByAccountIdParams(google_account_id=int(params))

    @staticmethod
    def _looks_like_cipher_text(value: str) -> bool:
        raw = (value or "").strip()
        if len(raw) < 24 or len(raw) % 4 != 0:
            return False
        if not re.fullmatch(r"[A-Za-z0-9+/=]+", raw):
            return False
        # 避免把常见的明文 base32（如 TOTP secret）误识别为密文
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
