import json
import logging
import logging.config
import re
from collections.abc import Mapping
from datetime import datetime

from app.contracts.execution_audit import ExecutionAuditEvent


GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH = (
    "/api/v1/oauth/google-calendar/callback"
)
GOOGLE_GMAIL_OAUTH_CALLBACK_PATH = (
    "/api/v1/oauth/google-gmail/callback"
)
OAUTH_CALLBACK_PATHS = (
    GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH,
    GOOGLE_GMAIL_OAUTH_CALLBACK_PATH,
)

EXECUTION_AUDIT_LOGGER_NAME = "oai.execution_audit"
EXECUTION_AUDIT_EVENT_NAME = "oai.execution_audit"

_EXECUTION_AUDIT_FIELDS = (
    "contract_version",
    "request_id",
    "stage",
    "action",
    "status",
    "occurred_at",
    "target_kind",
    "adapter_id",
    "reason_code",
    "plan_digest",
)

_MALFORMED_EXECUTION_AUDIT_RECORD = (
    '{"event":"oai.execution_audit","status":"malformed_payload"}'
)

_SAFE_EXECUTION_AUDIT_REASON_CODE_RE = re.compile(
    r"^[a-z][a-z0-9_]{0,127}$"
)


class SafeExecutionAuditFormatter(logging.Formatter):
    """Render only validated D39 execution-audit fields as one-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        try:
            payload = getattr(record, "execution_audit", None)
            if not isinstance(payload, Mapping):
                return _MALFORMED_EXECUTION_AUDIT_RECORD

            normalized = self._validated_payload(payload)
            rendered = {
                "event": EXECUTION_AUDIT_EVENT_NAME,
                **normalized,
            }
            return json.dumps(
                rendered,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except Exception:
            return _MALFORMED_EXECUTION_AUDIT_RECORD

    @staticmethod
    def _validated_payload(payload: Mapping[object, object]) -> dict[str, object]:
        if any(field not in payload for field in _EXECUTION_AUDIT_FIELDS):
            raise ValueError("execution_audit payload is incomplete.")

        occurred_at_value = payload["occurred_at"]
        if not isinstance(occurred_at_value, str):
            raise ValueError("occurred_at must be an ISO datetime string.")

        occurred_at = datetime.fromisoformat(occurred_at_value)

        reason_code = payload["reason_code"]
        if (
            reason_code is not None
            and (
                not isinstance(reason_code, str)
                or _SAFE_EXECUTION_AUDIT_REASON_CODE_RE.fullmatch(reason_code) is None
            )
        ):
            raise ValueError(
                "reason_code must be a machine-safe audit reason code."
            )

        event = ExecutionAuditEvent(
            contract_version=payload["contract_version"],  # type: ignore[arg-type]
            request_id=payload["request_id"],  # type: ignore[arg-type]
            stage=payload["stage"],  # type: ignore[arg-type]
            action=payload["action"],  # type: ignore[arg-type]
            status=payload["status"],  # type: ignore[arg-type]
            occurred_at=occurred_at,
            target_kind=payload["target_kind"],  # type: ignore[arg-type]
            adapter_id=payload["adapter_id"],  # type: ignore[arg-type]
            reason_code=reason_code,
            plan_digest=payload["plan_digest"],  # type: ignore[arg-type]
        )
        return {
            "contract_version": event.contract_version,
            "request_id": event.request_id,
            "stage": event.stage,
            "action": event.action,
            "status": event.status,
            "occurred_at": event.occurred_at.isoformat(),
            "target_kind": event.target_kind,
            "adapter_id": event.adapter_id,
            "reason_code": event.reason_code,
            "plan_digest": event.plan_digest,
        }


class OAuthCallbackAccessLogFilter(logging.Filter):
    """Remove OAuth callback query data from Uvicorn access records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            args = record.args
            if (
                isinstance(args, tuple)
                and len(args) == 5
                and isinstance(args[2], str)
            ):
                request_target = args[2]
                for callback_path in OAUTH_CALLBACK_PATHS:
                    if request_target == callback_path:
                        return True
                    if request_target.startswith(callback_path + "?"):
                        sanitized = list(args)
                        sanitized[2] = callback_path
                        record.args = tuple(sanitized)
                        return True

            if self._contains_callback_target(record.msg):
                return False
            if self._contains_callback_target(args):
                return False
        except Exception:
            return False
        return True

    @classmethod
    def _contains_callback_target(cls, value: object) -> bool:
        if isinstance(value, str):
            return any(
                callback_path + "?" in value
                or value == callback_path
                for callback_path in OAUTH_CALLBACK_PATHS
            )
        if isinstance(value, tuple):
            return any(cls._contains_callback_target(item) for item in value)
        if isinstance(value, Mapping):
            return any(
                cls._contains_callback_target(item)
                for item in value.values()
            )
        return False


def _install_oauth_callback_access_log_filter() -> None:
    logger = logging.getLogger("uvicorn.access")
    if any(
        isinstance(item, OAuthCallbackAccessLogFilter)
        for item in logger.filters
    ):
        return
    logger.addFilter(OAuthCallbackAccessLogFilter())


def configure_logging(log_level: str) -> None:
    """Configure consistent, process-wide logging for API and server events."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                },
                "execution_audit": {
                    "()": "app.core.logging.SafeExecutionAuditFormatter",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
                "execution_audit_console": {
                    "class": "logging.StreamHandler",
                    "formatter": "execution_audit",
                },
            },
            "loggers": {
                EXECUTION_AUDIT_LOGGER_NAME: {
                    "handlers": ["execution_audit_console"],
                    "level": log_level.upper(),
                    "propagate": False,
                },
            },
            "root": {"handlers": ["console"], "level": log_level.upper()},
        }
    )
    _install_oauth_callback_access_log_filter()
