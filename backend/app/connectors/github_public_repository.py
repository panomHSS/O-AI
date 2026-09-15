"""D59 bounded unauthenticated read-only GitHub repository connector."""

from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

GITHUB_PUBLIC_REPOSITORY_API_BASE = "https://api.github.com/repos"
GITHUB_PUBLIC_REPOSITORY_TIMEOUT_SECONDS = 5.0
GITHUB_PUBLIC_REPOSITORY_MAX_RESPONSE_BYTES = 64 * 1024

GITHUB_CONNECTOR_ERROR_INVALID_REFERENCE = "invalid_repository_reference"
GITHUB_CONNECTOR_ERROR_TIMEOUT = "connector_timeout"
GITHUB_CONNECTOR_ERROR_NETWORK = "connector_network_error"
GITHUB_CONNECTOR_ERROR_HTTP = "connector_http_error"
GITHUB_CONNECTOR_ERROR_RESPONSE_TOO_LARGE = "connector_response_too_large"
GITHUB_CONNECTOR_ERROR_INVALID_JSON = "connector_invalid_json"
GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE = "connector_invalid_response"

_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class GitHubPublicRepositoryConnectorError(ValueError):
    """Safe D59 connector error with a stable reason code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GitHubPublicRepositoryMetadata:
    """Normalized public repository metadata returned by the D59 connector."""

    full_name: str
    description: str | None
    html_url: str
    default_branch: str
    language: str | None
    visibility: str
    archived: bool
    fork: bool
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    license: str | None
    updated_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "archived": self.archived,
            "default_branch": self.default_branch,
            "description": self.description,
            "fork": self.fork,
            "forks_count": self.forks_count,
            "full_name": self.full_name,
            "html_url": self.html_url,
            "language": self.language,
            "license": self.license,
            "open_issues_count": self.open_issues_count,
            "stargazers_count": self.stargazers_count,
            "updated_at": self.updated_at,
            "visibility": self.visibility,
        }


class GitHubPublicRepositoryReader(Protocol):
    def get_repository_metadata(
        self,
        repository_reference: str,
    ) -> GitHubPublicRepositoryMetadata:
        ...


def validate_repository_reference(reference: object) -> tuple[str, str]:
    """Accept only one bounded ASCII ``owner/repository`` identifier."""

    if (
        not isinstance(reference, str)
        or not reference
        or reference != reference.strip()
        or reference.count("/") != 1
    ):
        raise GitHubPublicRepositoryConnectorError(
            GITHUB_CONNECTOR_ERROR_INVALID_REFERENCE
        )
    owner, repository = reference.split("/", 1)
    for segment in (owner, repository):
        if (
            not _SEGMENT_RE.fullmatch(segment)
            or ".." in segment
            or segment.endswith(".")
        ):
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_REFERENCE
            )
    return owner, repository


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects instead of granting a second network hop."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_without_redirects(
    request: urllib.request.Request,
    timeout_seconds: float,
):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout_seconds)


Transport = Callable[[urllib.request.Request, float], object]


class GitHubPublicRepositoryClient:
    """Read public repository metadata through one fixed GitHub API endpoint."""

    def __init__(
        self,
        *,
        timeout_seconds: float = GITHUB_PUBLIC_REPOSITORY_TIMEOUT_SECONDS,
        transport: Transport | None = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive.")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = _open_without_redirects if transport is None else transport

    def get_repository_metadata(
        self,
        repository_reference: str,
    ) -> GitHubPublicRepositoryMetadata:
        owner, repository = validate_repository_reference(repository_reference)
        requested_reference = f"{owner}/{repository}"
        url = f"{GITHUB_PUBLIC_REPOSITORY_API_BASE}/{owner}/{repository}"
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "O-AI-D59-GitHub-Public-Repository-Connector",
            },
        )

        try:
            response_context = self._transport(request, self._timeout_seconds)
            with response_context as response:
                status = getattr(response, "status", None)
                if status != 200:
                    raise GitHubPublicRepositoryConnectorError(
                        GITHUB_CONNECTOR_ERROR_HTTP
                    )
                body = response.read(
                    GITHUB_PUBLIC_REPOSITORY_MAX_RESPONSE_BYTES + 1
                )
        except GitHubPublicRepositoryConnectorError:
            raise
        except (socket.timeout, TimeoutError):
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_TIMEOUT
            ) from None
        except urllib.error.HTTPError:
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_HTTP
            ) from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, (socket.timeout, TimeoutError)):
                raise GitHubPublicRepositoryConnectorError(
                    GITHUB_CONNECTOR_ERROR_TIMEOUT
                ) from None
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_NETWORK
            ) from None
        except Exception:
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_NETWORK
            ) from None

        if not isinstance(body, bytes):
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )
        if len(body) > GITHUB_PUBLIC_REPOSITORY_MAX_RESPONSE_BYTES:
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_RESPONSE_TOO_LARGE
            )

        try:
            decoded = body.decode("utf-8")
            payload = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_JSON
            ) from None
        if not isinstance(payload, dict):
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )

        return self._normalize(payload, requested_reference=requested_reference)

    @classmethod
    def _normalize(
        cls,
        payload: dict[str, object],
        *,
        requested_reference: str,
    ) -> GitHubPublicRepositoryMetadata:
        private = payload.get("private")
        archived = payload.get("archived")
        fork = payload.get("fork")
        if (
            type(private) is not bool
            or private is not False
            or type(archived) is not bool
            or type(fork) is not bool
        ):
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )

        full_name = cls._bounded_string(payload.get("full_name"), max_bytes=201)
        try:
            validate_repository_reference(full_name)
        except GitHubPublicRepositoryConnectorError:
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            ) from None
        if full_name.casefold() != requested_reference.casefold():
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )

        description = cls._nullable_bounded_string(
            payload.get("description"), max_bytes=4096
        )
        default_branch = cls._bounded_string(
            payload.get("default_branch"), max_bytes=255
        )
        language = cls._nullable_bounded_string(
            payload.get("language"), max_bytes=128
        )
        updated_at = cls._bounded_string(payload.get("updated_at"), max_bytes=64)

        license_value = payload.get("license")
        if license_value is None:
            license_id = None
        elif isinstance(license_value, dict):
            license_id = cls._nullable_bounded_string(
                license_value.get("spdx_id"), max_bytes=128
            )
        else:
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )

        stargazers_count = cls._non_negative_int(payload.get("stargazers_count"))
        forks_count = cls._non_negative_int(payload.get("forks_count"))
        open_issues_count = cls._non_negative_int(payload.get("open_issues_count"))

        return GitHubPublicRepositoryMetadata(
            full_name=full_name,
            description=description,
            html_url=f"https://github.com/{full_name}",
            default_branch=default_branch,
            language=language,
            visibility="public",
            archived=archived,
            fork=fork,
            stargazers_count=stargazers_count,
            forks_count=forks_count,
            open_issues_count=open_issues_count,
            license=license_id,
            updated_at=updated_at,
        )

    @staticmethod
    def _bounded_string(value: object, *, max_bytes: int) -> str:
        if (
            not isinstance(value, str)
            or not value
            or len(value.encode("utf-8")) > max_bytes
        ):
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )
        return value

    @classmethod
    def _nullable_bounded_string(
        cls,
        value: object,
        *,
        max_bytes: int,
    ) -> str | None:
        if value is None:
            return None
        return cls._bounded_string(value, max_bytes=max_bytes)

    @staticmethod
    def _non_negative_int(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )
        return value
