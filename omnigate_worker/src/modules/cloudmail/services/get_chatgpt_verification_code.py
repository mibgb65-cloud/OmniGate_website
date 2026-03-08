"""通过 CloudMail 获取 ChatGPT 注册/登录验证码。"""

from __future__ import annotations

import logging

import asyncpg

from src.db import SystemSettingsRepository
from src.modules.cloudmail.actions.cloudmail_auth_actions import CloudMailAuthActions
from src.modules.cloudmail.actions.cloudmail_read_email_actions import CloudMailReadEmailActions
from src.modules.cloudmail.models.cloudmail_action_params import CloudMailAuthParams, CloudMailReadEmailParams
from src.modules.cloudmail.models.cloudmail_service_params import GetChatGptVerificationCodeParams
from src.modules.cloudmail.utils import CloudMailVerificationCodeExtractor


logger = logging.getLogger(__name__)


class CloudMailVerificationPendingError(RuntimeError):
    """验证码流程可继续重试的错误，例如邮件尚未到达。"""


class GetChatGptVerificationCodeService:
    """串起 CloudMail 配置读取、登录、查信和验证码提取。"""

    _LOG_PREFIX = "[CloudMail接码]"

    def __init__(
        self,
        *,
        db_pool: asyncpg.Pool | None = None,
        settings_repository: SystemSettingsRepository | None = None,
        auth_actions: CloudMailAuthActions | None = None,
        read_email_actions: CloudMailReadEmailActions | None = None,
        verification_code_extractor: CloudMailVerificationCodeExtractor | None = None,
    ) -> None:
        if settings_repository is None:
            if db_pool is None:
                raise ValueError("db_pool or settings_repository is required")
            settings_repository = SystemSettingsRepository(db_pool)

        self._settings_repository = settings_repository
        self._auth_actions = auth_actions or CloudMailAuthActions()
        self._read_email_actions = read_email_actions or CloudMailReadEmailActions()
        self._verification_code_extractor = verification_code_extractor or CloudMailVerificationCodeExtractor()

    async def execute(
        self,
        params: GetChatGptVerificationCodeParams,
    ) -> str:
        """获取最新验证码邮件，并直接返回验证码字符串。"""

        request = self._normalize_params(params)
        logger.info(
            "%s 开始获取验证码 | 收件邮箱=%s",
            self._LOG_PREFIX,
            self._mask_email(request.cloudmail_toEmail),
        )

        auth_settings = await self._settings_repository.get_cloudmail_auth_settings()
        account_email = self._require_setting(auth_settings.account_email, "cloudmail.account_email")
        password = self._require_setting(auth_settings.password, "cloudmail.password")
        auth_url = self._require_setting(auth_settings.auth_url, "cloudmail.auth_url")

        auth_result = await self._auth_actions.login_cloudmail(
            CloudMailAuthParams(
                cloudmail_account=account_email,
                password=password,
                auth_url=auth_url,
            )
        )
        cloudmail_token = (auth_result.cloudmail_token or "").strip()
        if not cloudmail_token:
            raise RuntimeError("CloudMail 登录成功但未返回 token")

        email_result = await self._read_email_actions.read_email(
            CloudMailReadEmailParams(
                cloudmail_token=cloudmail_token,
                cloudmail_toEmail=request.cloudmail_toEmail,
                cloudmail_sendName=request.cloudmail_sendName,
                cloudmail_subject=request.cloudmail_subject,
                cloudmail_type=request.cloudmail_type,
                auth_url=auth_url,
            )
        )

        latest_email = self._verification_code_extractor.get_latest_email(email_result)
        if latest_email is None:
            raise CloudMailVerificationPendingError(
                f"CloudMail 未查询到匹配邮件: 收件邮箱={self._mask_email(request.cloudmail_toEmail)}"
            )

        verification_code = self._verification_code_extractor.extract_latest_verification_code(email_result)
        if not verification_code:
            raise CloudMailVerificationPendingError("CloudMail 最新邮件中未提取到验证码")

        logger.info(
            "%s 验证码获取完成 | 收件邮箱=%s | 邮件数=%s | 已提取验证码=%s",
            self._LOG_PREFIX,
            self._mask_email(request.cloudmail_toEmail),
            len(email_result.emails),
            bool(verification_code),
        )
        return verification_code

    @staticmethod
    def _normalize_params(params: GetChatGptVerificationCodeParams) -> GetChatGptVerificationCodeParams:
        cloudmail_to_email = params.cloudmail_toEmail.strip()
        cloudmail_send_name = GetChatGptVerificationCodeService._normalize_optional_text(params.cloudmail_sendName)
        cloudmail_subject = GetChatGptVerificationCodeService._normalize_optional_text(params.cloudmail_subject)

        if not cloudmail_to_email:
            raise ValueError("cloudmail_toEmail 不能为空")

        return GetChatGptVerificationCodeParams(
            cloudmail_toEmail=cloudmail_to_email,
            cloudmail_sendName=cloudmail_send_name,
            cloudmail_subject=cloudmail_subject,
            cloudmail_type=params.cloudmail_type,
        )

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _require_setting(value: str | None, key: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise RuntimeError(f"CloudMail 配置缺失: {key}")
        return normalized

    @staticmethod
    def _mask_email(email: str) -> str:
        normalized = email.strip()
        if "@" not in normalized:
            return normalized

        local_part, domain = normalized.split("@", 1)
        if len(local_part) <= 4:
            masked_local = f"{local_part[:1]}***"
        else:
            masked_local = f"{local_part[:2]}***{local_part[-2:]}"
        return f"{masked_local}@{domain}"
