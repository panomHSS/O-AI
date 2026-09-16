"""D70 safe, read-only runtime diagnostics composition."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.config import Settings
from app.core.logging import (
    EXECUTION_AUDIT_LOGGER_NAME,
    SafeExecutionAuditFormatter,
)
from app.schemas.diagnostics import (
    ExecutionAuditDiagnostics,
    GoogleCalendarDiagnostics,
    RuntimeDiagnosticsResponse,
)
from app.services.google_oauth_config import (
    GoogleOAuthConfigError,
    GoogleOAuthRuntimeConfig,
)
from app.services.google_oauth_connection_status import (
    GoogleOAuthConnectionStatusReader,
)


class RuntimeDiagnosticsService:
    """Project allowlisted runtime status without execution or secret access."""

    def __init__(
        self,
        *,
        settings: Settings,
        google_oauth_status_reader: GoogleOAuthConnectionStatusReader,
        google_oauth_config_factory: Callable[[], GoogleOAuthRuntimeConfig],
    ) -> None:
        self._settings = settings
        self._google_oauth_status_reader = google_oauth_status_reader
        self._google_oauth_config_factory = google_oauth_config_factory

    def snapshot(self, *, database_revision: str) -> RuntimeDiagnosticsResponse:
        return RuntimeDiagnosticsResponse(
            service=self._settings.app_name,
            environment=self._settings.environment,
            database_revision=database_revision,
            execution_audit=self._execution_audit_diagnostics(),
            google_calendar=self._google_calendar_diagnostics(),
        )

    @staticmethod
    def _execution_audit_diagnostics() -> ExecutionAuditDiagnostics:
        try:
            logger = logging.getLogger(EXECUTION_AUDIT_LOGGER_NAME)
            if logger.propagate:
                return ExecutionAuditDiagnostics(status="unavailable")
            if len(logger.handlers) != 1:
                return ExecutionAuditDiagnostics(status="unavailable")
            formatter = logger.handlers[0].formatter
            if not isinstance(formatter, SafeExecutionAuditFormatter):
                return ExecutionAuditDiagnostics(status="unavailable")
            return ExecutionAuditDiagnostics(status="ok")
        except Exception:
            return ExecutionAuditDiagnostics(status="unavailable")

    def _google_calendar_diagnostics(self) -> GoogleCalendarDiagnostics:
        connector_enabled = bool(
            self._settings.oai_google_calendar_connector_enabled
        )

        try:
            runtime_config = self._google_oauth_config_factory()
            configuration_present = runtime_config.configuration_present
        except GoogleOAuthConfigError:
            return GoogleCalendarDiagnostics(
                status=("disabled" if not connector_enabled else "not_configured"),
                connector_enabled=connector_enabled,
                configuration_present=False,
            )
        except Exception:
            return GoogleCalendarDiagnostics(
                status=("disabled" if not connector_enabled else "unavailable"),
                connector_enabled=connector_enabled,
                configuration_present=False,
            )

        if not connector_enabled:
            return GoogleCalendarDiagnostics(
                status="disabled",
                connector_enabled=False,
                configuration_present=configuration_present,
            )

        if not configuration_present:
            return GoogleCalendarDiagnostics(
                status="not_configured",
                connector_enabled=True,
                configuration_present=False,
            )

        try:
            connection_status = self._google_oauth_status_reader.read_status()
        except Exception:
            return GoogleCalendarDiagnostics(
                status="unavailable",
                connector_enabled=True,
                configuration_present=True,
            )

        if connection_status == "active":
            status = "connected"
        elif connection_status == "disconnected":
            status = "disconnected"
        elif connection_status == "reauthorization_required":
            status = "reauthorization_required"
        else:
            status = "unavailable"

        return GoogleCalendarDiagnostics(
            status=status,
            connector_enabled=True,
            configuration_present=True,
        )
