import unittest

from app.models.oauth_credential import OAuthCredentialRecord


class OAuthCredentialModelTests(unittest.TestCase):
    def test_model_has_no_access_token_or_plain_refresh_token_column(self) -> None:
        columns = set(OAuthCredentialRecord.__table__.columns.keys())
        self.assertIn("encrypted_refresh_token", columns)
        self.assertIn("encryption_nonce", columns)
        self.assertNotIn("access_token", columns)
        self.assertNotIn("refresh_token", columns)
        self.assertNotIn("client_secret", columns)
        self.assertNotIn("authorization_code", columns)


if __name__ == "__main__":
    unittest.main()
