"""D68 safe reason-code projection for execution audit events."""

from __future__ import annotations

import re
from typing import Literal

from app.contracts.command import Result


_SAFE_REASON_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")


def execution_result_audit_reason(
    result: Result,
    *,
    target_kind: Literal["tool", "module"],
) -> str | None:
    """Return only a machine-safe adapter reason or a generic fallback."""
    if not isinstance(result, Result):
        raise TypeError("result must be a Result.")
    if target_kind not in {"tool", "module"}:
        raise ValueError("Unsupported execution target kind.")

    if result.status == "succeeded":
        return None

    error = result.error
    if isinstance(error, str) and _SAFE_REASON_CODE_RE.fullmatch(error):
        return error

    return f"{target_kind}_result_{result.status}"
