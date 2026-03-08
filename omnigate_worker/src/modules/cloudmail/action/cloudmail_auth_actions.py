"""CloudMail 鉴权动作。"""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import httpx

from src.modules.cloudmail.models.cloudmail_action_params import CloudMailAuthParams
from src.modules.cloudmail.models.cloudmail_action_results import CloudMailAuthResult

logger = logging.getLogger(__name__)


class CloudMailAuthActions:
    """cloudmail 登录动作集合。"""

    _LOG_PREFIX = "[CloudMail鉴权]"

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def login_cloudmail(self, params: CloudMailAuthParams) -> CloudMailAuthResult:
        """调用 CloudMail 鉴权接口，生成全局唯一 token。"""
        # 统一清洗账号/地址，避免把空白字符或非法 URL 带进请求层。
        normalized = self._normalize_auth_params(params)
        token_url = self._build_token_url(normalized.auth_url)
        payload = {
            "email": normalized.cloudmail_account,
            "password": normalized.password,
        }

        logger.info("%s 开始请求 token 接口 | URL=%s", self._LOG_PREFIX, token_url)
        response_data = await self._post_token_request(token_url, payload)

        # 接口成功与否不只看 HTTP 状态，还要看业务 code 和 token 字段。
        code = response_data.get("code")
        message = str(response_data.get("message") or "")
        data = response_data.get("data")
        token = data.get("token") if isinstance(data, dict) else None
        token = token.strip() if isinstance(token, str) else None

        if code != 200:
            raise RuntimeError(
                f"CloudMail 鉴权失败: code={code}, message={message or 'unknown error'}"
            )
        if not token:
            raise RuntimeError("CloudMail 鉴权失败: 响应中缺少 data.token")

        logger.info("%s 鉴权成功，token 已生成", self._LOG_PREFIX)
        return CloudMailAuthResult(cloudmail_token=token)

    async def generate_token(self, params: CloudMailAuthParams) -> CloudMailAuthResult:
        """`login_cloudmail` 的语义化别名。"""
        return await self.login_cloudmail(params)

    async def _post_token_request(self, token_url: str, payload: dict[str, str]) -> dict:
        # 允许注入外部 client，便于上层复用连接或做测试 mock。
        owned_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout_seconds)

        try:
            response = await client.post(
                token_url,
                json=payload,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"CloudMail 鉴权接口请求失败: {exc}") from exc
        finally:
            if owned_client:
                await client.aclose()

        try:
            # CloudMail 约定返回 JSON 对象，后续逻辑按该结构取 code/data/token。
            response_data = response.json()
        except ValueError as exc:
            raise RuntimeError("CloudMail 鉴权失败: 接口未返回合法 JSON") from exc

        if not isinstance(response_data, dict):
            raise RuntimeError("CloudMail 鉴权失败: 接口返回结构不是对象")

        return response_data

    @staticmethod
    def _normalize_auth_params(params: CloudMailAuthParams) -> CloudMailAuthParams:
        # 账号统一转小写，和邮箱类登录接口的常见用法保持一致。
        cloudmail_account = params.cloudmail_account.strip().lower()
        password = params.password
        auth_url = params.auth_url.strip()

        if not cloudmail_account:
            raise ValueError("cloudmail_account 不能为空")
        if not password:
            raise ValueError("password 不能为空")
        if not auth_url:
            raise ValueError("auth_url 不能为空")

        parsed = urlparse(auth_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("auth_url 必须是完整 URL")

        return CloudMailAuthParams(
            cloudmail_account=cloudmail_account,
            password=password,
            auth_url=auth_url,
        )

    @staticmethod
    def _build_token_url(auth_url: str) -> str:
        # 无论传进来的是域名根地址还是某个登录页，都统一落到固定鉴权接口。
        return urljoin(auth_url, "/api/public/genToken")
