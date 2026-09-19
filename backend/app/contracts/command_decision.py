"""Internal D23 command-intent and decision contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


CommandIntent: TypeAlias = Literal["chat_message", "unknown"]
CommandDisposition: TypeAlias = Literal[
    "defer_to_existing_chat",
    "reject",
]
ProviderPreferenceHint: TypeAlias = Literal[
    "unspecified",
    "automatic",
    "local_ai_explicit",
    "cloud_ai_explicit",
]


@dataclass(frozen=True, slots=True)
class CommandDecision:
    """An ephemeral, non-executable decision for one command request."""

    request_id: str
    intent: CommandIntent
    disposition: CommandDisposition
    provider_preference_hint: ProviderPreferenceHint
    reason_code: str
