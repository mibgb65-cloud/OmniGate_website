"""从 CloudMail 邮件列表中提取验证码。"""

from __future__ import annotations

import html
import re

from src.modules.cloudmail.models.cloudmail_action_results import CloudMailEmailItemResult, CloudMailReadEmailResult


class CloudMailVerificationCodeExtractor:
    """只基于最新一封邮件提取验证码。"""

    _KEYWORD_PATTERNS = (
        re.compile(r"(?:verification\s*code|login\s*code|code|验证码|校验码|OTP)[^0-9]{0,24}([0-9]{6})", re.IGNORECASE),
        re.compile(r"(?<!\d)([0-9]{6})(?!\d)"),
        re.compile(r"(?<!\d)([0-9]{4,8})(?!\d)"),
    )
    _HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

    def get_latest_email(
        self,
        email_result: CloudMailReadEmailResult | list[CloudMailEmailItemResult],
    ) -> CloudMailEmailItemResult | None:
        """邮件列表已按时间倒序时，直接取第一封就是最新邮件。"""

        if isinstance(email_result, CloudMailReadEmailResult):
            emails = email_result.emails
        else:
            emails = email_result
        return emails[0] if emails else None

    def extract_latest_verification_code(
        self,
        email_result: CloudMailReadEmailResult | list[CloudMailEmailItemResult],
    ) -> str | None:
        """从最新一封邮件中提取验证码。"""

        latest_email = self.get_latest_email(email_result)
        if latest_email is None:
            return None

        for candidate_text in self._build_candidate_texts(latest_email):
            verification_code = self._extract_code_from_text(candidate_text)
            if verification_code:
                return verification_code
        return None

    def _build_candidate_texts(self, email: CloudMailEmailItemResult) -> list[str]:
        """按纯文本、标题、HTML 文本化结果的顺序尝试提码。"""

        candidates: list[str] = []
        for raw_value in (email.text, email.subject, email.content):
            normalized = self._normalize_text(raw_value)
            if normalized:
                candidates.append(normalized)
        return candidates

    def _extract_code_from_text(self, text: str) -> str | None:
        for pattern in self._KEYWORD_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None

    def _normalize_text(self, value: str | None) -> str:
        if not value:
            return ""
        unescaped = html.unescape(value)
        stripped = self._HTML_TAG_PATTERN.sub(" ", unescaped)
        return re.sub(r"\s+", " ", stripped).strip()
