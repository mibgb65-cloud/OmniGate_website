from __future__ import annotations

import unittest
from unittest.mock import patch

from src.modules.chatgpt.utils.account_generator import (
    generate_random_email,
    generate_random_email_prefix,
    generate_random_name,
    generate_random_password,
)


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

    def test_should_generate_email_prefix_with_name_fragment(self) -> None:
        prefix = generate_random_email_prefix(length=12, preferred_name="James Allen Smith")

        self.assertEqual(12, len(prefix))
        self.assertTrue(prefix.startswith("jamesall"))
        self.assertTrue(prefix.islower())
        self.assertTrue(prefix.isalnum())

    def test_should_generate_name_with_middle_name(self) -> None:
        with patch(
            "src.modules.chatgpt.utils.account_generator.random.choice",
            side_effect=["James", "Allen", "Smith"],
        ):
            name = generate_random_name()

        self.assertEqual("James Allen Smith", name)

    def test_should_generate_password_with_letter_boundaries_and_limited_symbols(self) -> None:
        for _ in range(50):
            password = generate_random_password()

            self.assertGreaterEqual(len(password), 13)
            self.assertLessEqual(len(password), 17)
            self.assertTrue(password[0].isalpha())
            self.assertTrue(password[-1].isalpha())
            self.assertTrue(any(char.islower() for char in password))
            self.assertTrue(any(char.isupper() for char in password))
            self.assertTrue(any(char.isdigit() for char in password))

            symbol_count = sum(not char.isalnum() for char in password)
            self.assertGreaterEqual(symbol_count, 1)
            self.assertLessEqual(symbol_count, 2)
            self.assertGreater(sum(char.isalnum() for char in password), symbol_count)

    def test_should_honor_requested_password_length(self) -> None:
        with patch("src.modules.chatgpt.utils.account_generator.random.randint", return_value=16):
            password = generate_random_password(min_length=13, max_length=17)

        self.assertEqual(16, len(password))
        self.assertTrue(password[0].isalpha())
        self.assertTrue(password[-1].isalpha())

    async def test_should_pass_preferred_name_into_email_prefix_generation(self) -> None:
        settings_repository = _FakeSettingsRepository()
        account_persistence = _FakeChatGptAccountPersistence()

        with patch(
            "src.modules.chatgpt.utils.account_generator.generate_random_email_prefix",
            return_value="jamessmi42ab",
        ) as prefix_mock:
            result = await generate_random_email(
                settings_repository=settings_repository,
                account_persistence=account_persistence,
                preferred_name="James Allen Smith",
            )

        self.assertEqual("jamessmi42ab@198994216.xyz", result)
        prefix_mock.assert_called_once_with(12, preferred_name="James Allen Smith")
