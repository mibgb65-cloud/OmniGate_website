"""与后端 AesEncryptTypeHandler 兼容的 AES 加解密工具。"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Final


AES_KEY_ENV: Final[str] = "OMNIGATE_SECURITY_AES_KEY"
DEFAULT_AES_KEY_SOURCE: Final[str] = "OmniGate-Default-AES-Key"
AES_BLOCK_SIZE: Final[int] = 16


def _pkcs7_pad(data: bytes, block_size: int = AES_BLOCK_SIZE) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)


def _pkcs7_unpad(data: bytes, block_size: int = AES_BLOCK_SIZE) -> bytes:
    if not data or len(data) % block_size != 0:
        raise ValueError("Invalid padded bytes length")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > block_size:
        raise ValueError("Invalid padding length")
    if data[-pad_len:] != bytes([pad_len] * pad_len):
        raise ValueError("Invalid padding content")
    return data[:-pad_len]


class AesTypeHandlerCompat:
    """
    兼容后端 com.omnigate.common.handler.AesEncryptTypeHandler：
    - key = SHA-256(keySource).digest()
    - AES/ECB/PKCS5Padding
    - DB 存储 Base64(ciphertext)
    """

    def __init__(self, key_source: str | None = None) -> None:
        source = (key_source or "").strip() or os.getenv(AES_KEY_ENV, "").strip() or DEFAULT_AES_KEY_SOURCE
        self._key = hashlib.sha256(source.encode("utf-8")).digest()

    @staticmethod
    def is_backend_available() -> bool:
        try:
            from Crypto.Cipher import AES as _  # type: ignore # noqa: F401
            return True
        except Exception:  # noqa: BLE001
            return False

    def decrypt_safely(self, cipher_text: str | None) -> str | None:
        """
        对齐后端行为：解密失败时返回原值。
        """
        if cipher_text is None or cipher_text == "":
            return cipher_text
        try:
            return self.decrypt_base64(cipher_text)
        except Exception:  # noqa: BLE001
            return cipher_text

    def decrypt_base64(self, cipher_text: str) -> str:
        aes = self._build_aes()
        encrypted = base64.b64decode(cipher_text)
        plain_padded = aes.decrypt(encrypted)
        plain = _pkcs7_unpad(plain_padded, AES_BLOCK_SIZE)
        return plain.decode("utf-8")

    def encrypt_base64(self, plain_text: str) -> str:
        if plain_text == "":
            return ""
        aes = self._build_aes()
        padded = _pkcs7_pad(plain_text.encode("utf-8"), AES_BLOCK_SIZE)
        encrypted = aes.encrypt(padded)
        return base64.b64encode(encrypted).decode("utf-8")

    def _build_aes(self):
        try:
            from Crypto.Cipher import AES  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Missing dependency 'pycryptodome'. Run: pip install pycryptodome"
            ) from exc
        return AES.new(self._key, AES.MODE_ECB)
