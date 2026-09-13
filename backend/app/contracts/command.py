"""Command contracts for the owner-controlled execution boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping, TypeAlias


ResultStatus: TypeAlias = Literal["succeeded", "failed", "blocked"]


@dataclass(frozen=True, slots=True)
class CommandRequest:
    """A requested command; creating it does not authorize execution."""

    request_id: str
    command: str
    arguments: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    """One declarative step in a proposed execution plan."""

    sequence: int
    operation: str
    parameters: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """A proposed plan that remains non-executable without orchestration."""

    request_id: str
    adapter_id: str
    steps: tuple[ExecutionStep, ...] = ()
    owner_approval_required: bool = True


@dataclass(frozen=True, slots=True)
class Result:
    """The provider-neutral outcome of an explicitly authorized operation."""

    request_id: str
    status: ResultStatus
    output: Mapping[str, object] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True, slots=True)
class Response:
    """A presentation-neutral response derived from a command result."""

    request_id: str
    message: str
    result: Result
