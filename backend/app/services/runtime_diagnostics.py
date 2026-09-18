"""D70 safe diagnostics, extended by D81 runtime capability truth."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.contracts.runtime_capability import ConnectorReadCapabilityTruth
from app.core.config import Settings
from app.core.logging import (
    EXECUTION_AUDIT_LOGGER_NAME,
    SafeExecutionAuditFormatter,
)
from app.schemas.diagnostics import (
    AutomationDiagnostics,
    CrossConnectorAIDiagnostics,
    ExecutionAuditDiagnostics,
    GmailDiagnostics,
    GoogleCalendarDiagnostics,
    RuntimeCapabilityDiagnostics,
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
        gmail_oauth_status_reader: GoogleOAuthConnectionStatusReader | None = None,
        gmail_oauth_config_factory: (
            Callable[[], GoogleOAuthRuntimeConfig] | None
        ) = None,
        gmail_send_oauth_status_reader: (
            GoogleOAuthConnectionStatusReader | None
        ) = None,
        gmail_send_oauth_config_factory: (
            Callable[[], GoogleOAuthRuntimeConfig] | None
        ) = None,
    ) -> None:
        self._settings = settings
        self._google_oauth_status_reader = google_oauth_status_reader
        self._google_oauth_config_factory = google_oauth_config_factory
        self._gmail_oauth_status_reader = gmail_oauth_status_reader
        self._gmail_oauth_config_factory = gmail_oauth_config_factory
        self._gmail_send_oauth_status_reader = (
            gmail_send_oauth_status_reader
        )
        self._gmail_send_oauth_config_factory = (
            gmail_send_oauth_config_factory
        )

    def snapshot(self, *, database_revision: str) -> RuntimeDiagnosticsResponse:
        return RuntimeDiagnosticsResponse(
            service=self._settings.app_name,
            environment=self._settings.environment,
            database_revision=database_revision,
            execution_audit=self._execution_audit_diagnostics(),
            runtime=RuntimeCapabilityDiagnostics(
                implemented=True,
                # Batch 03 wires deterministic status queries before generic AI.
                status_chat_routable=True,
                execution_authority=False,
            ),
            google_calendar=self._google_calendar_diagnostics(),
            gmail=self._gmail_diagnostics(),
            cross_connector_ai=self._cross_connector_ai_diagnostics(),
            automation=self._automation_diagnostics(),
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

    @staticmethod
    def _connector_read_truth(
        *,
        connector_enabled: bool,
        config_factory: Callable[[], GoogleOAuthRuntimeConfig] | None,
        status_reader: GoogleOAuthConnectionStatusReader | None,
    ) -> ConnectorReadCapabilityTruth:
        configuration_present = False

        if config_factory is not None:
            try:
                runtime_config = config_factory()
                configuration_present = bool(
                    runtime_config.configuration_present
                )
            except GoogleOAuthConfigError:
                return ConnectorReadCapabilityTruth(
                    status=(
                        "disabled"
                        if not connector_enabled
                        else "not_configured"
                    ),
                    implemented=True,
                    enabled=connector_enabled,
                    configured=False,
                    connected=False,
                    chat_routable=False,
                    execution_authority=False,
                )
            except Exception:
                return ConnectorReadCapabilityTruth(
                    status=(
                        "disabled"
                        if not connector_enabled
                        else "unavailable"
                    ),
                    implemented=True,
                    enabled=connector_enabled,
                    configured=False,
                    connected=False,
                    chat_routable=False,
                    execution_authority=False,
                )
        elif connector_enabled:
            return ConnectorReadCapabilityTruth(
                status="unavailable",
                implemented=True,
                enabled=True,
                configured=False,
                connected=False,
                chat_routable=False,
                execution_authority=False,
            )

        if not connector_enabled:
            return ConnectorReadCapabilityTruth(
                status="disabled",
                implemented=True,
                enabled=False,
                configured=configuration_present,
                connected=False,
                chat_routable=False,
                execution_authority=False,
            )

        if not configuration_present:
            return ConnectorReadCapabilityTruth(
                status="not_configured",
                implemented=True,
                enabled=True,
                configured=False,
                connected=False,
                chat_routable=False,
                execution_authority=False,
            )

        if status_reader is None:
            return ConnectorReadCapabilityTruth(
                status="unavailable",
                implemented=True,
                enabled=True,
                configured=True,
                connected=False,
                chat_routable=False,
                execution_authority=False,
            )

        try:
            connection_status = status_reader.read_status()
        except Exception:
            return ConnectorReadCapabilityTruth(
                status="unavailable",
                implemented=True,
                enabled=True,
                configured=True,
                connected=False,
                chat_routable=False,
                execution_authority=False,
            )

        if connection_status == "active":
            status = "connected"
        elif connection_status == "disconnected":
            status = "disconnected"
        elif connection_status == "reauthorization_required":
            status = "reauthorization_required"
        else:
            status = "unavailable"

        connected = status == "connected"
        return ConnectorReadCapabilityTruth(
            status=status,
            implemented=True,
            enabled=True,
            configured=True,
            connected=connected,
            chat_routable=connected,
            execution_authority=False,
        )

    def _google_calendar_diagnostics(self) -> GoogleCalendarDiagnostics:
        truth = self._connector_read_truth(
            connector_enabled=bool(
                getattr(
                    self._settings,
                    "oai_google_calendar_connector_enabled",
                    False,
                )
            ),
            config_factory=self._google_oauth_config_factory,
            status_reader=self._google_oauth_status_reader,
        )
        return GoogleCalendarDiagnostics(
            status=truth.status,
            connector_enabled=truth.enabled,
            configuration_present=truth.configured,
            read_implemented=truth.implemented,
            read_chat_routable=truth.chat_routable,
            # D84 exposes only bounded CREATE-via-Chat. D75
            # update/delete authority remains outside normal Chat.
            write_backend_implemented=True,
            write_chat_routable=True,
            execution_authority=False,
        )

    def _gmail_diagnostics(self) -> GmailDiagnostics:
        truth = self._connector_read_truth(
            connector_enabled=bool(
                getattr(self._settings, "oai_gmail_connector_enabled", False)
            ),
            config_factory=self._gmail_oauth_config_factory,
            status_reader=self._gmail_oauth_status_reader,
        )
        send_truth = self._connector_read_truth(
            connector_enabled=bool(
                getattr(self._settings, "oai_gmail_send_enabled", False)
            ),
            config_factory=self._gmail_send_oauth_config_factory,
            status_reader=self._gmail_send_oauth_status_reader,
        )
        return GmailDiagnostics(
            status=truth.status,
            connector_enabled=truth.enabled,
            configuration_present=truth.configured,
            read_implemented=truth.implemented,
            read_chat_routable=truth.chat_routable,
            write_implemented=True,
            send_enabled=send_truth.enabled,
            send_configuration_present=send_truth.configured,
            send_connected=send_truth.connected,
            write_chat_routable=False,
            execution_authority=False,
        )

    def _cross_connector_ai_diagnostics(
        self,
    ) -> CrossConnectorAIDiagnostics:
        enabled = bool(
            getattr(
                self._settings,
                "oai_cross_connector_ai_context_enabled",
                False,
            )
        )
        return CrossConnectorAIDiagnostics(
            enabled=enabled,
            implemented=True,
            chat_routable=enabled,
            execution_authority=False,
        )

    def _automation_diagnostics(self) -> AutomationDiagnostics:
        enabled = bool(
            getattr(self._settings, "oai_automation_enabled", False)
        )
        return AutomationDiagnostics(
            enabled=enabled,
            local_reminder_implemented=True,
            # D79 is exposed by the Automation API, not normal Chat.
            local_reminder_chat_routable=False,
            connector_actions_implemented=False,
            ai_actions_implemented=False,
            execution_authority=False,
        )
