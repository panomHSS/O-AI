"""D64 AES-256-GCM refresh-token encryption boundary."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

OAUTH_CIPHER_VERSION = "aesgcm-v1"
OAUTH_CIPHER_ERROR_INVALID_KEY = "oauth_cipher_invalid_key"
OAUTH_CIPHER_ERROR_INVALID_SECRET = "oauth_cipher_invalid_secret"
OAUTH_CIPHER_ERROR_ENCRYPTION_FAILED = "oauth_cipher_encryption_failed"
OAUTH_CIPHER_ERROR_DECRYPTION_FAILED = "oauth_cipher_decryption_failed"


class OAuthTokenCipherError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class EncryptedOAuthSecret:
    ciphertext: bytes
    nonce: bytes
    cipher_version: str = OAUTH_CIPHER_VERSION


class OAuthTokenCipher:
    """Encrypt/decrypt refresh tokens using a deployment-held 256-bit key."""

    def __init__(self, key: bytes) -> None:
        if not isinstance(key, bytes) or len(key) != 32:
            raise OAuthTokenCipherError(OAUTH_CIPHER_ERROR_INVALID_KEY)
        self._cipher = AESGCM(key)

    @classmethod
    def from_base64_key(cls, key: SecretStr) -> "OAuthTokenCipher":
        if not isinstance(key, SecretStr):
            raise OAuthTokenCipherError(OAUTH_CIPHER_ERROR_INVALID_KEY)
        try:
            raw = base64.b64decode(
                key.get_secret_value(),
                validate=True,
            )
        except Exception:
            raise OAuthTokenCipherError(
                OAUTH_CIPHER_ERROR_INVALID_KEY
            ) from None
        return cls(raw)

    def encrypt(
        self,
        secret: SecretStr,
        *,
        aad: bytes,
    ) -> EncryptedOAuthSecret:
        raw = self._validated_secret(secret)
        if not isinstance(aad, bytes) or not aad:
            raise OAuthTokenCipherError(
                OAUTH_CIPHER_ERROR_ENCRYPTION_FAILED
            )
        nonce = os.urandom(12)
        try:
            ciphertext = self._cipher.encrypt(nonce, raw, aad)
        except Exception:
            raise OAuthTokenCipherError(
                OAUTH_CIPHER_ERROR_ENCRYPTION_FAILED
            ) from None
        return EncryptedOAuthSecret(
            ciphertext=ciphertext,
            nonce=nonce,
        )

    def decrypt(
        self,
        ciphertext: bytes,
        nonce: bytes,
        *,
        aad: bytes,
    ) -> SecretStr:
        if (
            not isinstance(ciphertext, bytes)
            or not ciphertext
            or not isinstance(nonce, bytes)
            or len(nonce) != 12
            or not isinstance(aad, bytes)
            or not aad
        ):
            raise OAuthTokenCipherError(
                OAUTH_CIPHER_ERROR_DECRYPTION_FAILED
            )
        try:
            raw = self._cipher.decrypt(nonce, ciphertext, aad)
            text = raw.decode("utf-8")
        except Exception:
            raise OAuthTokenCipherError(
                OAUTH_CIPHER_ERROR_DECRYPTION_FAILED
            ) from None
        secret = SecretStr(text)
        self._validated_secret(secret)
        return secret

    @staticmethod
    def _validated_secret(secret: SecretStr) -> bytes:
        if not isinstance(secret, SecretStr):
            raise OAuthTokenCipherError(
                OAUTH_CIPHER_ERROR_INVALID_SECRET
            )
        raw = secret.get_secret_value()
        if (
            not raw
            or len(raw.encode("utf-8")) > 8192
            or "\r" in raw
            or "\n" in raw
        ):
            raise OAuthTokenCipherError(
                OAUTH_CIPHER_ERROR_INVALID_SECRET
            )
        return raw.encode("utf-8")
