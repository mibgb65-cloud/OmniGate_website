"""2FA 提供器：基于 pyotp 在本地生成/校验 TOTP 验证码。"""

import re
from urllib.parse import parse_qs, urlparse

import pyotp


class TwoFAProvider:
    """本地 TOTP 工具类。"""

    @staticmethod
    def _normalize_secret(secret: str) -> str:
        raw = (secret or "").strip()
        if not raw:
            raise ValueError("twofa secret 不能为空")

        # 兼容 otpauth://totp/...?...&secret=XXXX
        if raw.lower().startswith("otpauth://"):
            parsed = urlparse(raw)
            query = parse_qs(parsed.query)
            raw = (query.get("secret", [""])[0] or "").strip()
            if not raw:
                raise ValueError("otpauth 链接中缺少 secret 参数")

        # 常见粘贴格式容错：去空格/短横线并统一大写
        normalized = raw.replace(" ", "").replace("-", "").upper()
        if not normalized:
            raise ValueError("twofa secret 不能为空")

        # base32 仅允许 A-Z2-7 和可选填充 '='
        if re.search(r"[^A-Z2-7=]", normalized):
            raise ValueError("twofa secret 含有非 Base32 字符")
        return normalized

    def generate_code(self, secret: str) -> str:
        """
        根据 TOTP 密钥生成当前验证码。
        默认行为：6位验证码、30秒周期（由 pyotp 默认参数决定）。
        """
        try:
            totp = pyotp.TOTP(self._normalize_secret(secret))
            return totp.now()
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"twofa secret 无法生成验证码: {exc}") from exc

    def verify_code(self, secret: str, code: str, valid_window: int = 1) -> bool:
        """
        校验验证码是否有效。

        valid_window:
        - 0: 仅当前时间片
        - 1: 允许前后各一个时间片（常用，缓解轻微时钟偏差）
        """
        if not code or not code.strip():
            return False
        try:
            totp = pyotp.TOTP(self._normalize_secret(secret))
            return bool(totp.verify(code.strip(), valid_window=valid_window))
        except Exception:
            return False
