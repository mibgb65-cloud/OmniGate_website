from __future__ import annotations

from dataclasses import dataclass

import asyncpg


@dataclass(slots=True)
class CloudMailAuthSettingRecord:
    """CloudMail 登录所需的系统配置。"""

    account_email: str | None
    password: str | None
    auth_url: str | None


class SystemSettingsRepository:
    """读取 `system_settings` 配置表。"""

    CLOUDMAIL_ACCOUNT_EMAIL_KEY = "cloudmail.account_email"
    CLOUDMAIL_PASSWORD_KEY = "cloudmail.password"
    CLOUDMAIL_AUTH_URL_KEY = "cloudmail.auth_url"
    CHATGPT_REGISTRATION_EMAIL_SUFFIX_KEY = "chatgpt.registration_email_suffix"

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_many(self, keys: list[str]) -> dict[str, str]:
        """
        按 key 批量取配置。

        返回结构是 `{key: value}`，方便业务层直接按名字取值。
        """

        if not keys:
            return {}
        query = """
            SELECT key, value
            FROM system_settings
            WHERE key = ANY($1::varchar[])
        """
        try:
            rows = await self._pool.fetch(query, keys)
        except asyncpg.UndefinedTableError:
            # 新环境里可能 worker 先启动、迁移后完成，这里降级为空配置更稳妥。
            return {}
        return {row["key"]: row["value"] for row in rows}

    async def get_cloudmail_auth_settings(self) -> CloudMailAuthSettingRecord:
        """
        读取 CloudMail 登录需要的 3 个配置项。

        这里只负责取值和基础清洗，不负责校验“是否必填”；
        由上层 service 决定缺失配置时如何报错。
        """

        settings = await self.get_many(
            [
                self.CLOUDMAIL_ACCOUNT_EMAIL_KEY,
                self.CLOUDMAIL_PASSWORD_KEY,
                self.CLOUDMAIL_AUTH_URL_KEY,
            ]
        )
        return CloudMailAuthSettingRecord(
            account_email=self._normalize_optional_text(settings.get(self.CLOUDMAIL_ACCOUNT_EMAIL_KEY)),
            password=self._normalize_optional_text(settings.get(self.CLOUDMAIL_PASSWORD_KEY)),
            auth_url=self._normalize_optional_text(settings.get(self.CLOUDMAIL_AUTH_URL_KEY)),
        )

    async def get_chatgpt_registration_email_suffix(self) -> str | None:
        """读取 ChatGPT 注册邮箱后缀，例如 `example.com`。"""

        settings = await self.get_many([self.CHATGPT_REGISTRATION_EMAIL_SUFFIX_KEY])
        return self._normalize_optional_text(settings.get(self.CHATGPT_REGISTRATION_EMAIL_SUFFIX_KEY))

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
