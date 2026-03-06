from __future__ import annotations

import unittest

from src.utils import AesTypeHandlerCompat


class TestAesTypeHandlerCompat(unittest.TestCase):
    def test_decrypt_safely_should_return_original_when_not_encrypted(self) -> None:
        cipher = AesTypeHandlerCompat()
        raw = "plain-password"
        self.assertEqual(cipher.decrypt_safely(raw), raw)

    def test_encrypt_decrypt_roundtrip_should_match(self) -> None:
        if not AesTypeHandlerCompat.is_backend_available():
            self.skipTest("pycryptodome is not installed")

        cipher = AesTypeHandlerCompat()
        text = "hello-omnigate"
        encrypted = cipher.encrypt_base64(text)
        decrypted = cipher.decrypt_base64(encrypted)
        self.assertEqual(decrypted, text)
