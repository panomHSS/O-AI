"""D64 bounded single-use OAuth state store."""

from __future__ import annotations

import hashlib
import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Callable

OAUTH_FLOW_ERROR_INVALID_STATE = "oauth_flow_invalid_state"
OAUTH_FLOW_ERROR_EXPIRED_STATE = "oauth_flow_expired_state"
OAUTH_FLOW_ERROR_STORE_FULL = "oauth_flow_store_full"

OAUTH_FLOW_TTL_SECONDS = 600
OAUTH_FLOW_MAX_PENDING = 16


class OAuthFlowStateError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class OAuthFlowStateStore:
    """Keep only SHA-256 digests of pending state values in process memory."""

    def __init__(
        self,
        *,
        max_pending: int = OAUTH_FLOW_MAX_PENDING,
        ttl_seconds: int = OAUTH_FLOW_TTL_SECONDS,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if (
            isinstance(max_pending, bool)
            or not isinstance(max_pending, int)
            or max_pending < 1
        ):
            raise ValueError("max_pending must be positive.")
        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, int)
            or ttl_seconds < 1
        ):
            raise ValueError("ttl_seconds must be positive.")
        self._max_pending = max_pending
        self._ttl = timedelta(seconds=ttl_seconds)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._items: dict[bytes, datetime] = {}
        self._lock = threading.Lock()

    def issue(self) -> str:
        now = self._now()
        with self._lock:
            self._prune(now)
            if len(self._items) >= self._max_pending:
                raise OAuthFlowStateError(OAUTH_FLOW_ERROR_STORE_FULL)
            state = secrets.token_urlsafe(32)
            digest = self._digest(state)
            while digest in self._items:
                state = secrets.token_urlsafe(32)
                digest = self._digest(state)
            self._items[digest] = now + self._ttl
            return state

    def consume(self, state: str) -> None:
        if (
            not isinstance(state, str)
            or not state
            or state != state.strip()
            or len(state) > 256
        ):
            raise OAuthFlowStateError(OAUTH_FLOW_ERROR_INVALID_STATE)
        digest = self._digest(state)
        now = self._now()
        with self._lock:
            expires_at = self._items.pop(digest, None)
            if expires_at is None:
                raise OAuthFlowStateError(OAUTH_FLOW_ERROR_INVALID_STATE)
            if expires_at <= now:
                raise OAuthFlowStateError(OAUTH_FLOW_ERROR_EXPIRED_STATE)

    @property
    def count(self) -> int:
        now = self._now()
        with self._lock:
            self._prune(now)
            return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _now(self) -> datetime:
        value = self._clock()
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError("OAuth state clock must be timezone-aware.")
        return value.astimezone(timezone.utc)

    def _prune(self, now: datetime) -> None:
        expired = [
            digest
            for digest, expires_at in self._items.items()
            if expires_at <= now
        ]
        for digest in expired:
            del self._items[digest]

    @staticmethod
    def _digest(state: str) -> bytes:
        return hashlib.sha256(state.encode("utf-8")).digest()
