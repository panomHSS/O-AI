from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
    parse_workspace_ai_route_mode,
)
from app.services.workspace_ai_policy import (
    DEFAULT_COMPANY_AI_ROUTE_MODE,
    DEFAULT_PERSONAL_AI_ROUTE_MODE,
    WorkspaceAIPolicyResolver,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ("cloud_preferred", WorkspaceAIRouteMode.CLOUD_PREFERRED),
        ("cloud_only", WorkspaceAIRouteMode.CLOUD_ONLY),
        ("local_preferred", WorkspaceAIRouteMode.LOCAL_PREFERRED),
        ("local_only", WorkspaceAIRouteMode.LOCAL_ONLY),
    ),
)
def test_route_mode_parser_accepts_only_exact_values(
    raw: str,
    expected: WorkspaceAIRouteMode,
) -> None:
    assert parse_workspace_ai_route_mode(raw) is expected


@pytest.mark.parametrize(
    "value",
    (
        None,
        1,
        True,
        "",
        " cloud_preferred",
        "cloud_preferred ",
        "CLOUD_PREFERRED",
        "automatic",
        "local",
        "cloud",
    ),
)
def test_route_mode_parser_rejects_aliases_and_normalization(
    value: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="workspace_ai_route_mode_invalid",
    ):
        parse_workspace_ai_route_mode(value)


@pytest.mark.parametrize(
    (
        "mode",
        "default_adapter",
        "permitted",
        "cloud_egress",
    ),
    (
        (
            WorkspaceAIRouteMode.CLOUD_PREFERRED,
            CHATGPT_DEFAULT_ADAPTER_ID,
            frozenset(
                {
                    CHATGPT_DEFAULT_ADAPTER_ID,
                    LOCAL_AI_ADAPTER_ID,
                }
            ),
            True,
        ),
        (
            WorkspaceAIRouteMode.CLOUD_ONLY,
            CHATGPT_DEFAULT_ADAPTER_ID,
            frozenset({CHATGPT_DEFAULT_ADAPTER_ID}),
            True,
        ),
        (
            WorkspaceAIRouteMode.LOCAL_PREFERRED,
            LOCAL_AI_ADAPTER_ID,
            frozenset(
                {
                    CHATGPT_DEFAULT_ADAPTER_ID,
                    LOCAL_AI_ADAPTER_ID,
                }
            ),
            True,
        ),
        (
            WorkspaceAIRouteMode.LOCAL_ONLY,
            LOCAL_AI_ADAPTER_ID,
            frozenset({LOCAL_AI_ADAPTER_ID}),
            False,
        ),
    ),
)
def test_policy_derives_all_provider_permissions_from_mode(
    mode: WorkspaceAIRouteMode,
    default_adapter: str,
    permitted: frozenset[str],
    cloud_egress: bool,
) -> None:
    policy = WorkspaceAIRoutingPolicy(
        workspace_id=WorkspaceId.PERSONAL,
        mode=mode,
    )

    assert policy.default_adapter_id == default_adapter
    assert policy.permitted_adapter_ids == permitted
    assert policy.cloud_egress_allowed is cloud_egress
    assert policy.permits(default_adapter)


def test_policy_is_immutable_and_caller_cannot_supply_derived_authority() -> None:
    policy = WorkspaceAIRoutingPolicy(
        workspace_id=WorkspaceId.PERSONAL,
        mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
    )

    with pytest.raises(FrozenInstanceError):
        policy.mode = WorkspaceAIRouteMode.LOCAL_ONLY  # type: ignore[misc]

    with pytest.raises(TypeError):
        WorkspaceAIRoutingPolicy(  # type: ignore[call-arg]
            workspace_id=WorkspaceId.PERSONAL,
            mode=WorkspaceAIRouteMode.LOCAL_ONLY,
            cloud_egress_allowed=True,
        )


def test_policy_rejects_non_workspace_identity_and_non_mode() -> None:
    with pytest.raises(
        ValueError,
        match="workspace_id_invalid",
    ):
        WorkspaceAIRoutingPolicy(  # type: ignore[arg-type]
            workspace_id="personal",
            mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
        )

    with pytest.raises(
        ValueError,
        match="workspace_ai_route_mode_invalid",
    ):
        WorkspaceAIRoutingPolicy(  # type: ignore[arg-type]
            workspace_id=WorkspaceId.PERSONAL,
            mode="cloud_preferred",
        )


def test_default_policy_is_personal_cloud_preferred_company_local_only() -> None:
    resolver = WorkspaceAIPolicyResolver()

    personal = resolver.resolve(PERSONAL)
    company = resolver.resolve(COMPANY)

    assert DEFAULT_PERSONAL_AI_ROUTE_MODE is (
        WorkspaceAIRouteMode.CLOUD_PREFERRED
    )
    assert DEFAULT_COMPANY_AI_ROUTE_MODE is (
        WorkspaceAIRouteMode.LOCAL_ONLY
    )

    assert personal.workspace_id is WorkspaceId.PERSONAL
    assert personal.mode is WorkspaceAIRouteMode.CLOUD_PREFERRED
    assert personal.default_adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
    assert personal.cloud_egress_allowed is True

    assert company.workspace_id is WorkspaceId.COMPANY
    assert company.mode is WorkspaceAIRouteMode.LOCAL_ONLY
    assert company.default_adapter_id == LOCAL_AI_ADAPTER_ID
    assert company.permitted_adapter_ids == frozenset(
        {LOCAL_AI_ADAPTER_ID}
    )
    assert company.cloud_egress_allowed is False
    assert not company.permits(CHATGPT_DEFAULT_ADAPTER_ID)


def test_resolver_supports_explicit_owner_configured_modes() -> None:
    resolver = WorkspaceAIPolicyResolver(
        personal_mode=WorkspaceAIRouteMode.LOCAL_PREFERRED,
        company_mode=WorkspaceAIRouteMode.CLOUD_ONLY,
    )

    assert resolver.resolve(PERSONAL).mode is (
        WorkspaceAIRouteMode.LOCAL_PREFERRED
    )
    assert resolver.resolve(COMPANY).mode is (
        WorkspaceAIRouteMode.CLOUD_ONLY
    )


def test_resolver_fails_closed_on_invalid_scope_or_mode() -> None:
    resolver = WorkspaceAIPolicyResolver()

    with pytest.raises(
        ValueError,
        match="workspace_scope_invalid",
    ):
        resolver.resolve(object())  # type: ignore[arg-type]

    with pytest.raises(
        ValueError,
        match="workspace_ai_route_mode_invalid",
    ):
        WorkspaceAIPolicyResolver(  # type: ignore[arg-type]
            personal_mode="cloud_preferred",
        )


def test_policy_contains_no_context_execution_or_credential_authority() -> None:
    policy = WorkspaceAIPolicyResolver().resolve(COMPANY)

    for forbidden in (
        "context",
        "prompt",
        "memory",
        "credential",
        "approved",
        "authorized",
        "execution_plan",
        "provider_response",
    ):
        assert not hasattr(policy, forbidden)
