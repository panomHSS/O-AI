import unittest

from app.api.v1.oauth import router
from app.schemas.oauth import OAuthConnectionStatusResponse


class OAuthRouteContractTests(unittest.TestCase):
    def test_exact_google_calendar_oauth_routes_exist(self):
        routes = {
            (route.path, tuple(sorted(route.methods or ())))
            for route in router.routes
        }
        self.assertIn(
            ("/oauth/google-calendar/start", ("GET",)),
            routes,
        )
        self.assertIn(
            ("/oauth/google-calendar/callback", ("GET",)),
            routes,
        )
        self.assertIn(
            ("/oauth/google-calendar/status", ("GET",)),
            routes,
        )
        self.assertIn(
            ("/oauth/google-calendar/disconnect", ("POST",)),
            routes,
        )

    def test_status_schema_has_only_non_secret_control_surface_fields(self):
        fields = set(OAuthConnectionStatusResponse.model_fields)
        self.assertEqual(
            fields,
            {
                "connector_enabled",
                "configuration_present",
                "connected",
                "status",
                "scope",
                "owner_timezone",
            },
        )
        self.assertTrue(
            {
                "access_token",
                "refresh_token",
                "client_secret",
                "encryption_key",
                "ciphertext",
                "nonce",
                "authorization_code",
            }.isdisjoint(fields)
        )


if __name__ == "__main__":
    unittest.main()
