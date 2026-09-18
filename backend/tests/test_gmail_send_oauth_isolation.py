from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pydantic import SecretStr

import app.api.dependencies as dependencies
from app.api.router import api_router
from app.api.v1.gmail_send_oauth import (
    GMAIL_SEND_OAUTH_CALLBACK_PATH,
    GMAIL_SEND_OAUTH_STATE_COOKIE,
    router as gmail_send_oauth_router,
)
from app.contracts.gmail import (
    GMAIL_CREDENTIAL_SCOPE,
    GMAIL_CREDENTIAL_SECRET_REF,
    GMAIL_PLUGIN_ID,
    GMAIL_PLUGIN_VERSION,
    GMAIL_READ_CAPABILITY_NAME,
    GMAIL_READ_CREDENTIAL_PROFILE_ID,
)
from app.contracts.gmail_send_execution import (
    GMAIL_SEND_CAPABILITY_NAME,
    GMAIL_SEND_CREDENTIAL_PROFILE_ID,
    GMAIL_SEND_CREDENTIAL_SCOPE,
    GMAIL_SEND_CREDENTIAL_SECRET_REF,
)
from app.core.config import Settings
from app.services.credential_profile_catalog import (
    PRODUCTION_CREDENTIAL_PROFILES,
    CredentialProfileCatalog,
)
from app.services.google_oauth_subjects import (
    GOOGLE_GMAIL_OAUTH_SUBJECT,
    GOOGLE_GMAIL_SEND_OAUTH_AAD,
    GOOGLE_GMAIL_SEND_OAUTH_CALLBACK_PATH,
    GOOGLE_GMAIL_SEND_OAUTH_SUBJECT,
)


BACKEND = Path(__file__).resolve().parents[1]


def test_send_identity_is_exact_and_separate_from_read() -> None:
    assert GMAIL_CREDENTIAL_SCOPE == (
        "https://www.googleapis.com/auth/gmail.readonly"
    )
    assert GMAIL_SEND_CREDENTIAL_SCOPE == (
        "https://www.googleapis.com/auth/gmail.send"
    )
    assert GMAIL_SEND_CAPABILITY_NAME == "send_message"
    assert GMAIL_SEND_CREDENTIAL_PROFILE_ID == "gmail.messages.send"
    assert GMAIL_SEND_CREDENTIAL_SECRET_REF == "gmail.send.access_token"

    assert GMAIL_SEND_CREDENTIAL_SCOPE != GMAIL_CREDENTIAL_SCOPE
    assert GMAIL_SEND_CREDENTIAL_PROFILE_ID != GMAIL_READ_CREDENTIAL_PROFILE_ID
    assert GMAIL_SEND_CREDENTIAL_SECRET_REF != GMAIL_CREDENTIAL_SECRET_REF


def test_send_oauth_subject_is_exact_single_scope_and_separate() -> None:
    subject = GOOGLE_GMAIL_SEND_OAUTH_SUBJECT

    assert subject.profile_id == GMAIL_SEND_CREDENTIAL_PROFILE_ID
    assert subject.provider_id == "google"
    assert subject.plugin_id == GMAIL_PLUGIN_ID
    assert subject.plugin_version == GMAIL_PLUGIN_VERSION
    assert subject.capability_name == GMAIL_SEND_CAPABILITY_NAME
    assert subject.scope == GMAIL_SEND_CREDENTIAL_SCOPE
    assert subject.secret_ref == GMAIL_SEND_CREDENTIAL_SECRET_REF
    assert subject.callback_path == (
        "/api/v1/oauth/google-gmail-send/callback"
    )

    assert subject != GOOGLE_GMAIL_OAUTH_SUBJECT
    assert subject.aad == GOOGLE_GMAIL_SEND_OAUTH_AAD
    assert subject.aad != GOOGLE_GMAIL_OAUTH_SUBJECT.aad


def test_production_catalog_has_distinct_read_and_send_profiles() -> None:
    catalog = CredentialProfileCatalog(PRODUCTION_CREDENTIAL_PROFILES)

    read = catalog.resolve(
        GMAIL_PLUGIN_ID,
        GMAIL_PLUGIN_VERSION,
        GMAIL_READ_CAPABILITY_NAME,
    )
    send = catalog.resolve(
        GMAIL_PLUGIN_ID,
        GMAIL_PLUGIN_VERSION,
        GMAIL_SEND_CAPABILITY_NAME,
    )

    assert read.profile_id == GMAIL_READ_CREDENTIAL_PROFILE_ID
    assert read.required_scopes == (GMAIL_CREDENTIAL_SCOPE,)
    assert read.secret_ref == GMAIL_CREDENTIAL_SECRET_REF

    assert send.profile_id == GMAIL_SEND_CREDENTIAL_PROFILE_ID
    assert send.required_scopes == (GMAIL_SEND_CREDENTIAL_SCOPE,)
    assert send.secret_ref == GMAIL_SEND_CREDENTIAL_SECRET_REF

    assert read != send


def test_send_settings_are_default_off_and_separate() -> None:
    settings = Settings(_env_file=None)

    assert settings.oai_gmail_send_enabled is False
    assert settings.oai_gmail_send_from_address is None
    assert settings.oai_google_gmail_send_oauth_redirect_uri == (
        "http://localhost:8000/api/v1/oauth/google-gmail-send/callback"
    )
    assert (
        settings.oai_google_gmail_send_oauth_redirect_uri
        != settings.oai_google_gmail_oauth_redirect_uri
    )


def test_send_runtime_config_uses_send_subject(monkeypatch) -> None:
    fake = SimpleNamespace(
        oai_google_oauth_client_id="client-id",
        oai_google_oauth_client_secret=SecretStr("client-secret"),
        oai_google_gmail_send_oauth_redirect_uri=(
            "http://localhost:8000/api/v1/oauth/google-gmail-send/callback"
        ),
        oai_oauth_token_encryption_key=SecretStr(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
        ),
    )
    monkeypatch.setattr(dependencies, "get_settings", lambda: fake)

    config = dependencies.get_google_gmail_send_oauth_runtime_config()

    assert config.subject == GOOGLE_GMAIL_SEND_OAUTH_SUBJECT
    assert config.redirect_uri.endswith("/oauth/google-gmail-send/callback")


def test_read_and_send_flow_state_stores_are_distinct() -> None:
    dependencies.get_google_gmail_oauth_flow_state_store.cache_clear()
    dependencies.get_google_gmail_send_oauth_flow_state_store.cache_clear()

    read_store = dependencies.get_google_gmail_oauth_flow_state_store()
    send_store = dependencies.get_google_gmail_send_oauth_flow_state_store()

    assert read_store is not send_store


def test_secret_source_resolves_only_exact_requested_subject(monkeypatch) -> None:
    calls = {"read": 0, "send": 0}

    class ReadManager:
        def resolve_access_token(self):
            calls["read"] += 1
            return SecretStr("read-token")

    class SendManager:
        def resolve_access_token(self):
            calls["send"] += 1
            return SecretStr("send-token")

    monkeypatch.setattr(
        dependencies,
        "get_google_gmail_oauth_token_manager",
        lambda: ReadManager(),
    )
    monkeypatch.setattr(
        dependencies,
        "get_google_gmail_send_oauth_token_manager",
        lambda: SendManager(),
    )
    dependencies.get_credential_secret_source.cache_clear()
    source = dependencies.get_credential_secret_source()

    send = source.resolve(GMAIL_SEND_CREDENTIAL_SECRET_REF)
    assert send is not None
    assert send.get_secret_value() == "send-token"
    assert calls == {"read": 0, "send": 1}

    read = source.resolve(GMAIL_CREDENTIAL_SECRET_REF)
    assert read is not None
    assert read.get_secret_value() == "read-token"
    assert calls == {"read": 1, "send": 1}

    assert source.resolve("gmail.unknown.access_token") is None
    assert calls == {"read": 1, "send": 1}

    dependencies.get_credential_secret_source.cache_clear()


def test_send_oauth_router_is_separate_and_has_no_execute_route() -> None:
    routes = {
        (
            path,
            frozenset(getattr(route, "methods", set()) or set()),
        )
        for route in gmail_send_oauth_router.routes
        if isinstance((path := getattr(route, "path", None)), str)
    }
    assert routes == {
        ("/oauth/google-gmail-send/start", frozenset({"GET"})),
        ("/oauth/google-gmail-send/callback", frozenset({"GET"})),
        ("/oauth/google-gmail-send/status", frozenset({"GET"})),
        ("/oauth/google-gmail-send/disconnect", frozenset({"POST"})),
    }
    assert GMAIL_SEND_OAUTH_CALLBACK_PATH == (
        "/api/v1/oauth/google-gmail-send/callback"
    )
    assert GOOGLE_GMAIL_SEND_OAUTH_CALLBACK_PATH == (
        "/api/v1/oauth/google-gmail-send/callback"
    )
    assert GMAIL_SEND_OAUTH_STATE_COOKIE == (
        "oai_google_gmail_send_oauth_state"
    )

    router_source = (
        Path(__file__).parents[1] / "app/api/router.py"
    ).read_text(encoding="utf-8")
    assert (
        "from app.api.v1.gmail_send_oauth "
        "import router as gmail_send_oauth_router"
        in router_source
    )
    assert (
        "api_router.include_router(gmail_send_oauth_router)"
        in router_source
    )
    assert (
        "from app.api.v1.gmail_send_executions "
        "import router as gmail_send_executions_router"
        in router_source
    )
    assert (
        "api_router.include_router(gmail_send_executions_router)"
        in router_source
    )


def test_batch04_provider_lane_and_owner_execution_api_are_separate() -> None:
    connector = BACKEND / "app/connectors/gmail_send.py"
    adapter = BACKEND / "app/adapters/gmail_send_module.py"
    execution_api = BACKEND / "app/api/v1/gmail_send_executions.py"

    assert connector.exists()
    assert adapter.exists()
    assert execution_api.exists()

    endpoint = "gmail.googleapis.com/gmail/v1/users/me/messages/send"
    offenders = []
    for path in (BACKEND / "app").rglob("*.py"):
        source = path.read_text(encoding="utf-8-sig")
        if endpoint in source:
            offenders.append(
                str(path.relative_to(BACKEND)).replace("\\", "/")
            )
    assert offenders == ["app/connectors/gmail_send.py"]

    execution_source = execution_api.read_text(encoding="utf-8-sig")
    assert 'prefix="/gmail-send-executions"' in execution_source
    assert "require_local_gmail_send_request_marker" in execution_source
    assert "get_gmail_send_execution_service" in execution_source

    oauth_source = (
        BACKEND / "app/api/v1/gmail_send_oauth.py"
    ).read_text(encoding="utf-8-sig")
    assert "GmailSendExecutionService" not in oauth_source
    assert "gmail-send-executions" not in oauth_source


def test_gmail_send_scope_literal_is_defined_in_one_contract_only() -> None:
    scope = "https://www.googleapis.com/auth/gmail.send"
    offenders = []
    for path in (BACKEND / "app").rglob("*.py"):
        source = path.read_text(encoding="utf-8-sig")
        if scope in source:
            offenders.append(str(path.relative_to(BACKEND)).replace("\\", "/"))

    assert offenders == ["app/contracts/gmail_send_execution.py"]
