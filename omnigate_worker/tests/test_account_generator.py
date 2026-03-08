from __future__ import annotations

import unittest
from unittest.mock import patch

from src.modules.chatgpt.utils.account_generator import generate_random_email


class _FakeSettingsRepository:
    async def get_chatgpt_registration_email_suffix(self) -> str:
        return "198994216.xyz"


class _FakeChatGptAccountPersistence:
    def __init__(self, existing_emails: set[str] | None = None) -> None:
        self._existing_emails = {item.strip().lower() for item in (existing_emails or set())}
        self.checked_emails: list[str] = []

    async def email_exists(self, email: str) -> bool:
        normalized_email = email.strip().lower()
        self.checked_emails.append(normalized_email)
        return normalized_email in self._existing_emails


class TestAccountGenerator(unittest.IsolatedAsyncioTestCase):
    async def test_should_retry_when_generated_email_already_exists(self) -> None:
        settings_repository = _FakeSettingsRepository()
        account_persistence = _FakeChatGptAccountPersistence(
            {"exist123@198994216.xyz"}
        )

        with patch(
            "src.modules.chatgpt.utils.account_generator.generate_random_email_prefix",
            side_effect=["exist123", "fresh456"],
        ):
            result = await generate_random_email(
                settings_repository=settings_repository,
                account_persistence=account_persistence,
                prefix_length=8,
                max_attempts=2,
            )

        self.assertEqual("fresh456@198994216.xyz", result)
        self.assertEqual(
            [
                "exist123@198994216.xyz",
                "fresh456@198994216.xyz",
            ],
            account_persistence.checked_emails,
        )

    async def test_should_raise_when_all_generated_emails_already_exist(self) -> None:
        settings_repository = _FakeSettingsRepository()
        account_persistence = _FakeChatGptAccountPersistence(
            {
                "dup11111@198994216.xyz",
                "dup22222@198994216.xyz",
            }
        )

        with patch(
            "src.modules.chatgpt.utils.account_generator.generate_random_email_prefix",
            side_effect=["dup11111", "dup22222"],
        ):
            with self.assertRaisesRegex(RuntimeError, "生成唯一 ChatGPT 注册邮箱失败"):
                await generate_random_email(
                    settings_repository=settings_repository,
                    account_persistence=account_persistence,
                    prefix_length=8,
                    max_attempts=2,
                )
