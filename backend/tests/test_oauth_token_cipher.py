import base64
import os
import unittest

from pydantic import SecretStr

from app.services.oauth_token_cipher import (
    OAUTH_CIPHER_ERROR_DECRYPTION_FAILED,
    OAUTH_CIPHER_ERROR_INVALID_KEY,
    OAuthTokenCipher,
    OAuthTokenCipherError,
)


class OAuthTokenCipherTests(unittest.TestCase):
    SECRET = "refresh-secret-never-log"

    @staticmethod
    def key():
        return SecretStr(
            base64.b64encode(os.urandom(32)).decode("ascii")
        )

    def test_round_trip_encrypts_refresh_token(self) -> None:
        cipher = OAuthTokenCipher.from_base64_key(self.key())
        encrypted = cipher.encrypt(
            SecretStr(self.SECRET),
            aad=b"subject-a",
        )
        self.assertNotIn(
            self.SECRET.encode("utf-8"),
            encrypted.ciphertext,
        )
        self.assertEqual(len(encrypted.nonce), 12)
        resolved = cipher.decrypt(
            encrypted.ciphertext,
            encrypted.nonce,
            aad=b"subject-a",
        )
        self.assertEqual(
            resolved.get_secret_value(),
            self.SECRET,
        )
        self.assertNotIn(self.SECRET, repr(resolved))

    def test_wrong_aad_fails_closed_without_leak(self) -> None:
        cipher = OAuthTokenCipher.from_base64_key(self.key())
        encrypted = cipher.encrypt(
            SecretStr(self.SECRET),
            aad=b"subject-a",
        )
        with self.assertRaises(OAuthTokenCipherError) as caught:
            cipher.decrypt(
                encrypted.ciphertext,
                encrypted.nonce,
                aad=b"subject-b",
            )
        self.assertEqual(
            caught.exception.code,
            OAUTH_CIPHER_ERROR_DECRYPTION_FAILED,
        )
        self.assertNotIn(self.SECRET, str(caught.exception))

    def test_invalid_key_is_rejected(self) -> None:
        with self.assertRaises(OAuthTokenCipherError) as caught:
            OAuthTokenCipher.from_base64_key(
                SecretStr(base64.b64encode(b"short").decode("ascii"))
            )
        self.assertEqual(
            caught.exception.code,
            OAUTH_CIPHER_ERROR_INVALID_KEY,
        )


if __name__ == "__main__":
    unittest.main()
