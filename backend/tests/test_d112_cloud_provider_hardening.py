from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from app.api import dependencies
from app.core.config import Settings
from app.providers.openai_provider import OpenAIChatProvider


def test_d112_settings_default_cloud_disabled_and_timeout_bounded() -> None:
    enabled = Settings.model_fields["oai_cloud_ai_enabled"]
    timeout = Settings.model_fields["oai_cloud_ai_timeout_seconds"]

    assert enabled.default is False
    assert timeout.default == 120.0

    annotation_source = inspect.getsource(Settings)
    assert "oai_cloud_ai_enabled: bool = False" in annotation_source
    assert (
        "oai_cloud_ai_timeout_seconds: float = "
        "Field(default=120.0, gt=0, le=600)"
    ) in annotation_source


def test_production_dependency_unwraps_secret_only_at_provider_composition() -> None:
    dependencies.get_chatgpt_adapter.cache_clear()
    settings = SimpleNamespace(
        openai_api_key=SecretStr("server-secret"),
        openai_model="server-model",
        oai_cloud_ai_enabled=True,
        oai_cloud_ai_timeout_seconds=41.0,
    )
    provider = MagicMock()

    try:
        with (
            patch.object(dependencies, "get_settings", return_value=settings),
            patch.object(
                dependencies,
                "OpenAIChatProvider",
                return_value=provider,
            ) as provider_class,
        ):
            adapter = dependencies.get_chatgpt_adapter()

        assert adapter.adapter_id == "chatgpt.default"
        provider_class.assert_called_once_with(
            api_key="server-secret",
            model="server-model",
            enabled=True,
            timeout_seconds=41.0,
        )
    finally:
        dependencies.get_chatgpt_adapter.cache_clear()


def test_openai_provider_has_no_arbitrary_endpoint_or_provider_tools() -> None:
    source = inspect.getsource(OpenAIChatProvider)

    assert "base_url" not in source
    assert "tools=" not in source
    assert "web_search" not in source
    assert "file_search" not in source
    assert "computer" not in source
    assert "max_retries=0" in source
    assert "timeout=self._timeout_seconds" in source


def test_openai_provider_does_not_log_provider_exception_detail() -> None:
    source = inspect.getsource(OpenAIChatProvider.generate_reply)

    assert "logger.exception" not in source
    assert 'logger.warning("OpenAI chat request failed")' in source
    assert "raise ChatProviderError(" in source


def test_frontend_cannot_receive_cloud_secret_or_provider_configuration() -> None:
    source = inspect.getsource(dependencies.get_chatgpt_adapter)

    assert "OPENAI_API_KEY" not in source
    assert "base_url" not in source
    assert "provider_id" not in source
    assert "adapter_id" not in source