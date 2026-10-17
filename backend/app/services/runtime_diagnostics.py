"""D70 safe diagnostics, extended by D81 runtime capability truth."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.contracts.runtime_capability import ConnectorReadCapabilityTruth
from app.contracts.cognitive_runtime_incident_governance import (
    CognitiveRuntimeIncidentAssessment,
)
from app.contracts.cognitive_runtime_assurance import (
    D141_REFERENCE_BASELINE,
    CognitiveRuntimeAssuranceSnapshot,
)
from app.contracts.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackSnapshot,
)
from app.contracts.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionAdvisory,
)
from app.contracts.cognitive_runtime_rollout import (
    CognitiveRuntimeRolloutStage,
)
from app.contracts.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessAssessment,
)
from app.core.config import Settings
from app.core.cognitive_runtime_rollout_config import (
    get_cognitive_runtime_rollout_settings,
)
from app.core.logging import (
    EXECUTION_AUDIT_LOGGER_NAME,
    SafeExecutionAuditFormatter,
)
from app.schemas.diagnostics import (
    AutomationDiagnostics,
    CrossConnectorAIDiagnostics,
    CognitiveOutcomeQualityFeedbackDiagnostics,
    CognitiveRuntimeDiagnostics,
    CognitiveRuntimeIncidentGovernanceDiagnostics,
    CognitiveRuntimePromotionAdvisoryDiagnostics,
    CognitiveRuntimeReadinessDiagnostics,
    CognitiveRuntimeRolloutDiagnostics,
    ExecutionAuditDiagnostics,
    GmailDiagnostics,
    GoogleCalendarDiagnostics,
    RuntimeCapabilityDiagnostics,
    RuntimeDiagnosticsResponse,
)
from app.services.cognitive_runtime_incident_governance import (
    CognitiveRuntimeIncidentGovernanceEvaluator,
)
from app.services.google_oauth_config import (
    GoogleOAuthConfigError,
    GoogleOAuthRuntimeConfig,
)
from app.services.google_oauth_connection_status import (
    GoogleOAuthConnectionStatusReader,
)
from app.services.cognitive_runtime_assurance import CognitiveRuntimeAssurance
from app.services.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackMonitor,
)
from app.services.cognitive_runtime_promotion_advisory import (
    CognitiveRuntimePromotionGovernanceEvaluator,
)
from app.services.cognitive_runtime_readiness import (
    CognitiveRuntimeReadinessEvaluator,
)
from app.services.cognitive_runtime_rollout import (
    CognitiveRuntimeRolloutSelector,
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
        cognitive_runtime_assurance: CognitiveRuntimeAssurance | None = None,
        cognitive_outcome_quality_feedback: (
            CognitiveOutcomeQualityFeedbackMonitor | None
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
        self._cognitive_runtime_assurance = cognitive_runtime_assurance
        self._cognitive_outcome_quality_feedback = (
            cognitive_outcome_quality_feedback
        )

    def snapshot(self, *, database_revision: str) -> RuntimeDiagnosticsResponse:
        cognitive_enabled = bool(
            getattr(self._settings, "oai_cognitive_runtime_enabled", False)
        )
        cognitive_snapshot = self._cognitive_runtime_assurance_snapshot()
        feedback_snapshot = self._cognitive_outcome_quality_feedback_snapshot()
        readiness_assessment = CognitiveRuntimeReadinessEvaluator.evaluate(
            enabled=cognitive_enabled,
            snapshot=cognitive_snapshot,
        )
        promotion_advisory = (
            CognitiveRuntimePromotionGovernanceEvaluator.evaluate(
                readiness=readiness_assessment,
            )
        )
        rollout_stage = (
            get_cognitive_runtime_rollout_settings()
            .oai_cognitive_runtime_rollout_stage
        )
        rollout_bps = CognitiveRuntimeRolloutSelector.rollout_bps_for_stage(
            rollout_stage
        )
        if rollout_bps is None:
            raise RuntimeError("cognitive_runtime_rollout_stage_invalid")

        rollout_diagnostics = self._cognitive_runtime_rollout_diagnostics(
            stage=rollout_stage,
            rollout_bps=rollout_bps,
            advisory=promotion_advisory,
        )
        incident_assessment = (
            CognitiveRuntimeIncidentGovernanceEvaluator.evaluate(
                readiness=readiness_assessment,
                advisory=promotion_advisory,
                rollout=rollout_diagnostics,
            )
        )

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
            cognitive_runtime=self._cognitive_runtime_diagnostics(
                enabled=cognitive_enabled,
                snapshot=cognitive_snapshot,
            ),
            cognitive_runtime_readiness=self._cognitive_runtime_readiness_diagnostics(
                assessment=readiness_assessment,
            ),
            cognitive_runtime_promotion_advisory=(
                self._cognitive_runtime_promotion_advisory_diagnostics(
                    advisory=promotion_advisory,
                )
            ),
            cognitive_runtime_rollout=rollout_diagnostics,
            cognitive_runtime_incident_governance=(
                self._cognitive_runtime_incident_governance_diagnostics(
                    assessment=incident_assessment,
                )
            ),
            cognitive_outcome_quality_feedback=(
                self._cognitive_outcome_quality_feedback_diagnostics(
                    snapshot=feedback_snapshot,
                )
            ),
            google_calendar=self._google_calendar_diagnostics(),
            gmail=self._gmail_diagnostics(),
            cross_connector_ai=self._cross_connector_ai_diagnostics(),
            automation=self._automation_diagnostics(),
        )

    def _cognitive_runtime_assurance_snapshot(
        self,
    ) -> CognitiveRuntimeAssuranceSnapshot | None:
        assurance = self._cognitive_runtime_assurance
        if assurance is None:
            return None
        try:
            snapshot = assurance.snapshot()
        except Exception:
            return None
        return (
            snapshot
            if isinstance(snapshot, CognitiveRuntimeAssuranceSnapshot)
            else None
        )

    def _cognitive_outcome_quality_feedback_snapshot(
        self,
    ) -> CognitiveOutcomeQualityFeedbackSnapshot | None:
        monitor = self._cognitive_outcome_quality_feedback
        if monitor is None:
            return None
        try:
            snapshot = monitor.snapshot()
        except Exception:
            return None
        return (
            snapshot
            if isinstance(snapshot, CognitiveOutcomeQualityFeedbackSnapshot)
            else None
        )

    @staticmethod
    def _cognitive_runtime_diagnostics(
        *,
        enabled: bool,
        snapshot: CognitiveRuntimeAssuranceSnapshot | None,
    ) -> CognitiveRuntimeDiagnostics:
        if snapshot is None:
            return CognitiveRuntimeDiagnostics(
                enabled=enabled,
                status=("unavailable" if enabled else "disabled"),
                reference_baseline=D141_REFERENCE_BASELINE,
            )

        selections = snapshot.cognitive_selected + snapshot.legacy_selected
        status = (
            "disabled"
            if not enabled
            else ("observing" if selections > 0 else "idle")
        )
        return CognitiveRuntimeDiagnostics(
            enabled=enabled,
            status=status,
            reference_baseline=snapshot.reference_baseline,
            sample_scope=snapshot.sample_scope,
            reset_on_restart=snapshot.reset_on_restart,
            cognitive_selected=snapshot.cognitive_selected,
            legacy_selected=snapshot.legacy_selected,
            completed=snapshot.completed,
            insufficient=snapshot.insufficient,
            failed=snapshot.failed,
            runtime_busy=snapshot.runtime_busy,
            runtime_unavailable=snapshot.runtime_unavailable,
            response_blocked=snapshot.response_blocked,
            execution_authority=False,
            automatic_promotion=False,
            automatic_rollback=False,
        )

    @staticmethod
    def _cognitive_runtime_readiness_diagnostics(
        *,
        assessment: CognitiveRuntimeReadinessAssessment,
    ) -> CognitiveRuntimeReadinessDiagnostics:
        return CognitiveRuntimeReadinessDiagnostics(
            status=assessment.status,
            reference_baseline=assessment.reference_baseline,
            sample_scope=assessment.sample_scope,
            reset_on_restart=assessment.reset_on_restart,
            terminal_samples=assessment.terminal_samples,
            failed_rate_bps=assessment.failed_rate_bps,
            insufficient_rate_bps=assessment.insufficient_rate_bps,
            runtime_busy_rate_bps=assessment.runtime_busy_rate_bps,
            runtime_unavailable_rate_bps=assessment.runtime_unavailable_rate_bps,
            response_blocked_rate_bps=assessment.response_blocked_rate_bps,
            minimum_terminal_samples=assessment.minimum_terminal_samples,
            max_failed_rate_bps=assessment.max_failed_rate_bps,
            max_runtime_busy_rate_bps=assessment.max_runtime_busy_rate_bps,
            max_runtime_unavailable_rate_bps=(
                assessment.max_runtime_unavailable_rate_bps
            ),
            max_response_blocked_rate_bps=assessment.max_response_blocked_rate_bps,
            execution_authority=False,
            routing_authority=False,
            promotion_authority=False,
            rollback_authority=False,
            automatic_promotion=False,
            automatic_rollback=False,
        )

    @staticmethod
    def _cognitive_runtime_promotion_advisory_diagnostics(
        *,
        advisory: CognitiveRuntimePromotionAdvisory,
    ) -> CognitiveRuntimePromotionAdvisoryDiagnostics:
        return CognitiveRuntimePromotionAdvisoryDiagnostics(
            reference_baseline=advisory.reference_baseline,
            recommendation=advisory.recommendation,
            reason_code=advisory.reason_code,
            source_readiness_status=advisory.source_readiness_status,
            owner_decision_required=advisory.owner_decision_required,
            promotion_authority=False,
            rollback_authority=False,
            execution_authority=False,
            routing_authority=False,
            configuration_authority=False,
            automatic_promotion=False,
            automatic_rollback=False,
        )

    @staticmethod
    def _cognitive_runtime_rollout_diagnostics(
        *,
        stage: CognitiveRuntimeRolloutStage,
        rollout_bps: int,
        advisory: CognitiveRuntimePromotionAdvisory,
    ) -> CognitiveRuntimeRolloutDiagnostics:
        return CognitiveRuntimeRolloutDiagnostics(
            stage=stage,
            rollout_bps=rollout_bps,
            source_promotion_recommendation=advisory.recommendation,
            source_promotion_reason_code=advisory.reason_code,
            automatic_stage_increase=False,
            automatic_stage_decrease=False,
            execution_authority=False,
            routing_authority=False,
            configuration_authority=False,
        )

    @staticmethod
    def _cognitive_runtime_incident_governance_diagnostics(
        *,
        assessment: CognitiveRuntimeIncidentAssessment,
    ) -> CognitiveRuntimeIncidentGovernanceDiagnostics:
        return CognitiveRuntimeIncidentGovernanceDiagnostics(
            status=assessment.status,
            severity=assessment.severity,
            incident_active=assessment.incident_active,
            blast_radius=assessment.blast_radius,
            recommended_owner_action=assessment.recommended_owner_action,
            source_readiness_status=assessment.source_readiness_status,
            source_promotion_recommendation=(
                assessment.source_promotion_recommendation
            ),
            source_promotion_reason_code=assessment.source_promotion_reason_code,
            source_rollout_stage=assessment.source_rollout_stage,
            source_rollout_bps=assessment.source_rollout_bps,
            rollback_authority=False,
            rollout_stage_authority=False,
            runtime_disable_authority=False,
            promotion_authority=False,
            routing_authority=False,
            execution_authority=False,
            configuration_authority=False,
            automatic_containment=False,
            automatic_rollback=False,
            automatic_runtime_disable=False,
        )

    @staticmethod
    def _cognitive_outcome_quality_feedback_diagnostics(
        *,
        snapshot: CognitiveOutcomeQualityFeedbackSnapshot | None,
    ) -> CognitiveOutcomeQualityFeedbackDiagnostics:
        if snapshot is None:
            return CognitiveOutcomeQualityFeedbackDiagnostics(
                status="unavailable",
            )

        return CognitiveOutcomeQualityFeedbackDiagnostics(
            status=("observing" if snapshot.observed > 0 else "idle"),
            reference_baseline=snapshot.reference_baseline,
            sample_scope=snapshot.sample_scope,
            reset_on_restart=snapshot.reset_on_restart,
            observed=snapshot.observed,
            verified_success=snapshot.verified_success,
            bounded_insufficiency=snapshot.bounded_insufficiency,
            adverse_outcome=snapshot.adverse_outcome,
            invalid_evidence=snapshot.invalid_evidence,
            lesson_verified_success=snapshot.lesson_verified_success,
            lesson_bounded_insufficiency=snapshot.lesson_bounded_insufficiency,
            lesson_critic_exhausted=snapshot.lesson_critic_exhausted,
            lesson_invalid_cognition=snapshot.lesson_invalid_cognition,
            lesson_terminal_failure=snapshot.lesson_terminal_failure,
            learning_authority=False,
            retention_authority=False,
            experience_promotion_authority=False,
            memory_write_authority=False,
            routing_authority=False,
            model_selection_authority=False,
            execution_authority=False,
            configuration_authority=False,
            rollout_authority=False,
            automatic_learning=False,
            automatic_promotion=False,
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
            # D89 exposes owner-visible delivery UX without granting
            # scheduling, execution, acknowledgement, or Chat authority.
            local_reminder_delivery_ui_implemented=True,
            # D79/D89 Automation remains outside normal Chat scheduling.
            local_reminder_chat_routable=False,
            connector_actions_implemented=False,
            ai_actions_implemented=False,
            execution_authority=False,
        )
