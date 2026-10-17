from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from app.contracts.cognitive_runtime_assurance import D141_COUNTER_MAX
from app.contracts.cognitive_runtime_incident_governance import (
    D145_REFERENCE_BASELINE,
    CognitiveRuntimeIncidentBlastRadius,
    CognitiveRuntimeIncidentOwnerAction,
    CognitiveRuntimeIncidentSeverity,
    CognitiveRuntimeIncidentStatus,
)
from app.contracts.cognitive_outcome_quality_feedback import (
    D146_COUNTER_MAX,
    D146_REFERENCE_BASELINE,
    D146_SAMPLE_SCOPE,
)
from app.contracts.cognitive_runtime_promotion_advisory import (
    D143_REFERENCE_BASELINE,
    CognitiveRuntimePromotionReasonCode,
    CognitiveRuntimePromotionRecommendation,
)
from app.contracts.cognitive_runtime_rollout import (
    D144_REFERENCE_BASELINE,
    D144_ROLLOUT_BUCKET_COUNT,
    CognitiveRuntimeRolloutStage,
)
from app.contracts.cognitive_runtime_readiness import (
    D142_MAX_FAILED_RATE_BPS,
    D142_MAX_RESPONSE_BLOCKED_RATE_BPS,
    D142_MAX_RUNTIME_BUSY_RATE_BPS,
    D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS,
    D142_MIN_TERMINAL_SAMPLES,
    D142_RATE_SCALE_BPS,
)
from app.contracts.runtime_capability import RuntimeCapabilityConnectionStatus

ExecutionAuditDiagnosticStatus: TypeAlias = Literal["ok", "unavailable"]
GoogleCalendarDiagnosticStatus: TypeAlias = RuntimeCapabilityConnectionStatus
GmailDiagnosticStatus: TypeAlias = RuntimeCapabilityConnectionStatus
CognitiveRuntimeDiagnosticStatus: TypeAlias = Literal[
    "disabled", "idle", "observing", "unavailable"
]
CognitiveRuntimeDiagnosticCounter: TypeAlias = Annotated[
    StrictInt, Field(ge=0, le=D141_COUNTER_MAX)
]
CognitiveRuntimeReadinessDiagnosticStatus: TypeAlias = Literal[
    "disabled", "collecting", "ready", "degraded", "unavailable"
]
CognitiveRuntimeReadinessDiagnosticRate: TypeAlias = Annotated[
    StrictInt, Field(ge=0, le=D142_RATE_SCALE_BPS)
]
CognitiveOutcomeQualityFeedbackDiagnosticStatus: TypeAlias = Literal[
    "idle", "observing", "unavailable"
]
CognitiveOutcomeQualityFeedbackDiagnosticCounter: TypeAlias = Annotated[
    StrictInt, Field(ge=0, le=D146_COUNTER_MAX)
]


class ExecutionAuditDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ExecutionAuditDiagnosticStatus


class RuntimeCapabilityDiagnostics(BaseModel):
    """D81 status-query capability; never an execution grant."""
    model_config = ConfigDict(extra="forbid")
    implemented: Literal[True] = True
    status_chat_routable: StrictBool = False
    execution_authority: Literal[False] = False


class CognitiveRuntimeDiagnostics(BaseModel):
    """D141 aggregate process-local operational assurance only."""
    model_config = ConfigDict(extra="forbid")
    implemented: Literal[True] = True
    enabled: StrictBool
    status: CognitiveRuntimeDiagnosticStatus
    reference_baseline: Literal[
        "71e6af0bd01ab06a3fd22ee6f472db3a206b059a"
    ] = "71e6af0bd01ab06a3fd22ee6f472db3a206b059a"
    sample_scope: Literal["process_lifetime"] = "process_lifetime"
    reset_on_restart: Literal[True] = True
    cognitive_selected: CognitiveRuntimeDiagnosticCounter | None = None
    legacy_selected: CognitiveRuntimeDiagnosticCounter | None = None
    completed: CognitiveRuntimeDiagnosticCounter | None = None
    insufficient: CognitiveRuntimeDiagnosticCounter | None = None
    failed: CognitiveRuntimeDiagnosticCounter | None = None
    runtime_busy: CognitiveRuntimeDiagnosticCounter | None = None
    runtime_unavailable: CognitiveRuntimeDiagnosticCounter | None = None
    response_blocked: CognitiveRuntimeDiagnosticCounter | None = None
    execution_authority: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_rollback: Literal[False] = False


class CognitiveRuntimeReadinessDiagnostics(BaseModel):
    """D142 deterministic production-readiness advisory; never control authority."""
    model_config = ConfigDict(extra="forbid")
    implemented: Literal[True] = True
    status: CognitiveRuntimeReadinessDiagnosticStatus
    reference_baseline: Literal[
        "6f8e803da9e77d43e1eeb06a8ae3d5e69fb80299"
    ] = "6f8e803da9e77d43e1eeb06a8ae3d5e69fb80299"
    sample_scope: Literal["process_lifetime"] = "process_lifetime"
    reset_on_restart: Literal[True] = True
    terminal_samples: CognitiveRuntimeDiagnosticCounter | None = None
    failed_rate_bps: CognitiveRuntimeReadinessDiagnosticRate | None = None
    insufficient_rate_bps: CognitiveRuntimeReadinessDiagnosticRate | None = None
    runtime_busy_rate_bps: CognitiveRuntimeReadinessDiagnosticRate | None = None
    runtime_unavailable_rate_bps: CognitiveRuntimeReadinessDiagnosticRate | None = None
    response_blocked_rate_bps: CognitiveRuntimeReadinessDiagnosticRate | None = None
    minimum_terminal_samples: Literal[100] = D142_MIN_TERMINAL_SAMPLES
    max_failed_rate_bps: Literal[100] = D142_MAX_FAILED_RATE_BPS
    max_runtime_busy_rate_bps: Literal[100] = D142_MAX_RUNTIME_BUSY_RATE_BPS
    max_runtime_unavailable_rate_bps: Literal[50] = (
        D142_MAX_RUNTIME_UNAVAILABLE_RATE_BPS
    )
    max_response_blocked_rate_bps: Literal[100] = (
        D142_MAX_RESPONSE_BLOCKED_RATE_BPS
    )
    execution_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    promotion_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_rollback: Literal[False] = False


class CognitiveRuntimePromotionAdvisoryDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    implemented: Literal[True] = True
    reference_baseline: Literal[
        "1b24f231a09bf6f03ad6fb796aeecffa484ed9f0"
    ] = D143_REFERENCE_BASELINE
    recommendation: CognitiveRuntimePromotionRecommendation
    reason_code: CognitiveRuntimePromotionReasonCode
    source_readiness_status: CognitiveRuntimeReadinessDiagnosticStatus | None
    owner_decision_required: StrictBool
    promotion_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_rollback: Literal[False] = False


class CognitiveRuntimeRolloutDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    implemented: Literal[True] = True
    reference_baseline: Literal[
        "9f6fa3557e3c9b91a3549c1175b8273c24fad20c"
    ] = D144_REFERENCE_BASELINE
    stage: CognitiveRuntimeRolloutStage
    rollout_bps: Annotated[StrictInt, Field(ge=0, le=10_000)]
    bucket_count: Literal[10000] = D144_ROLLOUT_BUCKET_COUNT
    selection_scope: Literal[
        "d140_cognitive_eligible_turns"
    ] = "d140_cognitive_eligible_turns"
    selection_strategy: Literal[
        "sha256_server_bound_conversation_uuid_v1"
    ] = "sha256_server_bound_conversation_uuid_v1"
    sticky_by_conversation: Literal[True] = True
    owner_controlled: Literal[True] = True
    source_promotion_recommendation: CognitiveRuntimePromotionRecommendation
    source_promotion_reason_code: CognitiveRuntimePromotionReasonCode
    automatic_stage_increase: Literal[False] = False
    automatic_stage_decrease: Literal[False] = False
    execution_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    configuration_authority: Literal[False] = False


class CognitiveRuntimeIncidentGovernanceDiagnostics(BaseModel):
    """D145 deterministic incident posture; never containment authority."""
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"] = "1"
    implemented: Literal[True] = True
    reference_baseline: Literal[
        "b30d15befe3a53ccab1946411c9cf4be3a0c147a"
    ] = D145_REFERENCE_BASELINE
    status: CognitiveRuntimeIncidentStatus
    severity: CognitiveRuntimeIncidentSeverity
    incident_active: StrictBool
    blast_radius: CognitiveRuntimeIncidentBlastRadius
    recommended_owner_action: CognitiveRuntimeIncidentOwnerAction
    source_readiness_status: CognitiveRuntimeReadinessDiagnosticStatus | None
    source_promotion_recommendation: (
        CognitiveRuntimePromotionRecommendation | None
    )
    source_promotion_reason_code: CognitiveRuntimePromotionReasonCode | None
    source_rollout_stage: CognitiveRuntimeRolloutStage | None
    source_rollout_bps: Annotated[StrictInt, Field(ge=0, le=10_000)] | None

    rollback_authority: Literal[False] = False
    rollout_stage_authority: Literal[False] = False
    runtime_disable_authority: Literal[False] = False
    promotion_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False

    automatic_containment: Literal[False] = False
    automatic_rollback: Literal[False] = False
    automatic_runtime_disable: Literal[False] = False


class CognitiveOutcomeQualityFeedbackDiagnostics(BaseModel):
    """D146 process-local aggregate quality feedback; never learning authority."""
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"] = "1"
    implemented: Literal[True] = True
    reference_baseline: Literal[
        "bd773c16b154b23bdd57381ca8f6b25def29adb4"
    ] = D146_REFERENCE_BASELINE
    status: CognitiveOutcomeQualityFeedbackDiagnosticStatus
    sample_scope: Literal[
        "cognitive_experience_candidates"
    ] = D146_SAMPLE_SCOPE
    reset_on_restart: Literal[True] = True

    observed: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None
    verified_success: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None
    bounded_insufficiency: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None
    adverse_outcome: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None
    invalid_evidence: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None

    lesson_verified_success: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None
    lesson_bounded_insufficiency: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None
    lesson_critic_exhausted: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None
    lesson_invalid_cognition: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None
    lesson_terminal_failure: CognitiveOutcomeQualityFeedbackDiagnosticCounter | None = None

    learning_authority: Literal[False] = False
    retention_authority: Literal[False] = False
    experience_promotion_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False


class GoogleCalendarDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: GoogleCalendarDiagnosticStatus
    connector_enabled: bool
    configuration_present: bool
    read_implemented: Literal[True] = True
    read_chat_routable: StrictBool = False
    write_backend_implemented: Literal[True] = True
    write_chat_routable: StrictBool = False
    execution_authority: Literal[False] = False


class GmailDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: GmailDiagnosticStatus
    connector_enabled: bool
    configuration_present: bool
    read_implemented: Literal[True] = True
    read_chat_routable: StrictBool = False
    write_implemented: StrictBool = True
    send_enabled: StrictBool = False
    send_configuration_present: StrictBool = False
    send_connected: StrictBool = False
    write_chat_routable: Literal[False] = False
    execution_authority: Literal[False] = False


class CrossConnectorAIDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool
    implemented: Literal[True] = True
    chat_routable: StrictBool
    execution_authority: Literal[False] = False


class AutomationDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool
    local_reminder_implemented: Literal[True] = True
    local_reminder_delivery_ui_implemented: Literal[True] = True
    local_reminder_chat_routable: Literal[False] = False
    connector_actions_implemented: Literal[False] = False
    ai_actions_implemented: Literal[False] = False
    execution_authority: Literal[False] = False


class RuntimeDiagnosticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"] = "1"
    service: str
    environment: str
    database_revision: str
    execution_audit: ExecutionAuditDiagnostics
    runtime: RuntimeCapabilityDiagnostics
    cognitive_runtime: CognitiveRuntimeDiagnostics
    cognitive_runtime_readiness: CognitiveRuntimeReadinessDiagnostics
    cognitive_runtime_promotion_advisory: CognitiveRuntimePromotionAdvisoryDiagnostics
    cognitive_runtime_rollout: CognitiveRuntimeRolloutDiagnostics
    cognitive_runtime_incident_governance: (
        CognitiveRuntimeIncidentGovernanceDiagnostics
    )
    cognitive_outcome_quality_feedback: CognitiveOutcomeQualityFeedbackDiagnostics
    google_calendar: GoogleCalendarDiagnostics
    gmail: GmailDiagnostics
    cross_connector_ai: CrossConnectorAIDiagnostics
    automation: AutomationDiagnostics
