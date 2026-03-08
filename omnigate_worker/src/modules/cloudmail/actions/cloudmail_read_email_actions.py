
"""CloudMail 读取邮件动作。"""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import httpx

from src.modules.cloudmail.models.cloudmail_action_params import CloudMailReadEmailParams
from src.modules.cloudmail.models.cloudmail_action_results import (
    CloudMailEmailItemResult,
    CloudMailReadEmailResult,
)

logger = logging.getLogger(__name__)


class CloudMailReadEmailActions:
    """cloudmail 邮件读取动作集合。"""

    _LOG_PREFIX = "[CloudMail查信]"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.strip() if isinstance(base_url, str) and base_url.strip() else None
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def read_email(self, params: CloudMailReadEmailParams) -> CloudMailReadEmailResult:
        """调用邮件列表接口，返回包含 content 和 text 的邮件列表。"""
        # token、收件人和服务地址先归一化，避免把空白/非法值传给接口。
        normalized = self._normalize_read_params(params, default_base_url=self._base_url)
        email_list_url = self._build_email_list_url(normalized.auth_url or "")
        payload: dict[str, object] = {
            "toEmail": normalized.cloudmail_toEmail,
        }

        if normalized.cloudmail_sendName:
            payload["sendName"] = normalized.cloudmail_sendName
        if normalized.cloudmail_subject:
            payload["subject"] = normalized.cloudmail_subject
        if normalized.cloudmail_type is not None:
            payload["type"] = normalized.cloudmail_type

        logger.info(
            "%s 开始请求邮件列表接口 | URL=%s | 收件邮箱=%s",
            self._LOG_PREFIX,
            email_list_url,
            self._mask_email(normalized.cloudmail_toEmail),
        )
        response_data = await self._post_email_list_request(
            email_list_url,
            normalized.cloudmail_token,
            payload,
        )

        # 接口成功与否除了看 HTTP，还要校验业务 code 和 data 数组结构。
        code = response_data.get("code")
        message = str(response_data.get("message") or "")
        data = response_data.get("data")

        if code != 200:
            raise RuntimeError(
                f"CloudMail 读取邮件失败: code={code}, message={message or 'unknown error'}"
            )
        if not isinstance(data, list):
            raise RuntimeError("CloudMail 读取邮件失败: 响应中的 data 不是数组")

        emails: list[CloudMailEmailItemResult] = []
        for item in data:
            if not isinstance(item, dict):
                raise RuntimeError("CloudMail 读取邮件失败: data 中存在非对象元素")
            emails.append(CloudMailEmailItemResult.model_validate(item))

        logger.info(
            "%s 读取邮件成功 | 收件邮箱=%s | 邮件数=%s",
            self._LOG_PREFIX,
            self._mask_email(normalized.cloudmail_toEmail),
            len(emails),
        )
        return CloudMailReadEmailResult(emails=emails)

    async def email_list(self, params: CloudMailReadEmailParams) -> CloudMailReadEmailResult:
        """`read_email` 的语义化别名。"""
        return await self.read_email(params)

    async def _post_email_list_request(
        self,
        email_list_url: str,
        cloudmail_token: str,
        payload: dict[str, object],
    ) -> dict:
        # 允许外部注入 client，便于连接复用或单元测试。
        owned_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout_seconds)

        try:
            response = await client.post(
                email_list_url,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Authorization": cloudmail_token,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"CloudMail 读取邮件接口请求失败: {exc}") from exc
        finally:
            if owned_client:
                await client.aclose()

        try:
            response_data = response.json()
        except ValueError as exc:
            raise RuntimeError("CloudMail 读取邮件失败: 接口未返回合法 JSON") from exc

        if not isinstance(response_data, dict):
            raise RuntimeError("CloudMail 读取邮件失败: 接口返回结构不是对象")

        return response_data

    @staticmethod
    def _normalize_read_params(
        params: CloudMailReadEmailParams,
        *,
        default_base_url: str | None = None,
    ) -> CloudMailReadEmailParams:
        cloudmail_token = params.cloudmail_token.strip()
        cloudmail_to_email = params.cloudmail_toEmail.strip()
        cloudmail_send_name = CloudMailReadEmailActions._normalize_optional_text(params.cloudmail_sendName)
        cloudmail_subject = CloudMailReadEmailActions._normalize_optional_text(params.cloudmail_subject)
        auth_url = CloudMailReadEmailActions._normalize_optional_text(params.auth_url) or default_base_url
        cloudmail_type = CloudMailReadEmailActions._normalize_mail_type(params.cloudmail_type)

        if not cloudmail_token:
            raise ValueError("cloudmail_token 不能为空")
        if not cloudmail_to_email:
            raise ValueError("cloudmail_toEmail 不能为空")
        if not auth_url:
            raise ValueError("auth_url 或 base_url 不能为空")

        parsed = urlparse(auth_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("auth_url/base_url 必须是完整 URL")

        return CloudMailReadEmailParams(
            cloudmail_token=cloudmail_token,
            cloudmail_toEmail=cloudmail_to_email,
            cloudmail_sendName=cloudmail_send_name,
            cloudmail_subject=cloudmail_subject,
            cloudmail_type=cloudmail_type,
            auth_url=auth_url,
        )

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @staticmethod
    def _normalize_mail_type(value: str | int | None) -> int | None:
        if value in (None, ""):
            return None

        try:
            mail_type = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("cloudmail_type 只能是 0、1 或空") from exc

        if mail_type not in {0, 1}:
            raise ValueError("cloudmail_type 只能是 0、1 或空")
        return mail_type

    @staticmethod
    def _build_email_list_url(auth_url: str) -> str:
        # 无论传入根域名还是某个页面地址，都统一拼到固定接口路径。
        return urljoin(auth_url, "/api/public/emailList")

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
