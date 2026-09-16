"""D76 exact Gmail credential identity; no Gmail API execution."""

from __future__ import annotations

GMAIL_PLUGIN_ID = "gmail"
GMAIL_PLUGIN_VERSION = "1.0.0"
GMAIL_READ_CAPABILITY_NAME = "read_messages"
GMAIL_READ_CREDENTIAL_PROFILE_ID = "gmail.messages.readonly"
GMAIL_CREDENTIAL_PROVIDER_ID = "google"
GMAIL_CREDENTIAL_AUTH_SCHEME = "oauth2_bearer"
GMAIL_CREDENTIAL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_CREDENTIAL_SECRET_REF = "gmail.access_token"

__all__ = [
    "GMAIL_PLUGIN_ID",
    "GMAIL_PLUGIN_VERSION",
    "GMAIL_READ_CAPABILITY_NAME",
    "GMAIL_READ_CREDENTIAL_PROFILE_ID",
    "GMAIL_CREDENTIAL_PROVIDER_ID",
    "GMAIL_CREDENTIAL_AUTH_SCHEME",
    "GMAIL_CREDENTIAL_SCOPE",
    "GMAIL_CREDENTIAL_SECRET_REF",
]
