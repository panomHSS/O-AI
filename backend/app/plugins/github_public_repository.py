"""D59 first read-only external connector Plugin."""

from __future__ import annotations

import json

from app.connectors.github_public_repository import (
    GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE,
    GITHUB_CONNECTOR_ERROR_NETWORK,
    GitHubPublicRepositoryClient,
    GitHubPublicRepositoryConnectorError,
    GitHubPublicRepositoryMetadata,
    GitHubPublicRepositoryReader,
    validate_repository_reference,
)
from app.plugins.base import Plugin
from app.plugins.context import PluginExecutionContext
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult

GITHUB_PUBLIC_REPOSITORY_PLUGIN_ID = "github_public_repo"
GITHUB_PUBLIC_REPOSITORY_PLUGIN_VERSION = "1.0.0"
GITHUB_PUBLIC_REPOSITORY_CAPABILITY = "repository_metadata"
GITHUB_PUBLIC_REPOSITORY_ADAPTER_ID = "module.plugin.github_public_repo"
GITHUB_PUBLIC_REPOSITORY_OPERATION = "get_repository_metadata"
GITHUB_PUBLIC_REPOSITORY_CAPABILITY_ID = (
    "exec.plugin.github_public_repo.repository_metadata"
)
_GITHUB_PUBLIC_REPOSITORY_MAX_PLUGIN_OUTPUT_BYTES = 16 * 1024


class GitHubPublicRepositoryPlugin(Plugin):
    """Read bounded metadata for one public GitHub repository."""

    def __init__(
        self,
        client: GitHubPublicRepositoryReader | None = None,
    ) -> None:
        self._client = GitHubPublicRepositoryClient() if client is None else client

    @property
    def id(self) -> str:
        return GITHUB_PUBLIC_REPOSITORY_PLUGIN_ID

    @property
    def name(self) -> str:
        return "GitHub Public Repository Metadata"

    @property
    def version(self) -> str:
        return GITHUB_PUBLIC_REPOSITORY_PLUGIN_VERSION

    def execute(
        self,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        if not isinstance(request, PluginRequest):
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )
        validate_repository_reference(request.content)
        try:
            metadata = self._client.get_repository_metadata(request.content)
        except GitHubPublicRepositoryConnectorError:
            raise
        except Exception:
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_NETWORK
            ) from None
        if not isinstance(metadata, GitHubPublicRepositoryMetadata):
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )

        content = json.dumps(
            metadata.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(content.encode("utf-8")) > _GITHUB_PUBLIC_REPOSITORY_MAX_PLUGIN_OUTPUT_BYTES:
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )
        return PluginResult(content=content)
