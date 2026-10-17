from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.contracts.cognitive_trusted_experience import (
    compute_cognitive_trusted_experience_proposal_fingerprint,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.models.trusted_experience import (
    TrustedExperienceEventRecord,
    TrustedExperienceRecord,
)
from app.repositories.trusted_experiences import TrustedExperienceRepository
from app.services.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackEvaluator,
)
from app.services.trusted_experience_lifecycle import TrustedExperienceLifecycleService
from tests.test_d146_cognitive_outcome_quality_feedback import candidate_for_lesson


def proposal():
    engine = create_engine("sqlite:///:memory:")
    TrustedExperienceRecord.__table__.create(engine)
    TrustedExperienceEventRecord.__table__.create(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    service = TrustedExperienceLifecycleService(
        TrustedExperienceRepository(
            session,
            WorkspaceScope(workspace_id=WorkspaceId.PERSONAL),
        )
    )
    value = service.evaluate(candidate_for_lesson("verified_success")).proposal
    session.close()
    engine.dispose()
    assert value is not None
    return value


def run_case(case: int) -> None:
    slot = (case - 1) % 8
    if slot == 0:
        assert proposal() == proposal()
    elif slot == 1:
        left = proposal()
        right = compute_cognitive_trusted_experience_proposal_fingerprint(
            workspace_id=left.workspace_id,
            source_candidate_fingerprint=left.source_candidate_fingerprint,
            source_feedback_fingerprint=left.source_feedback_fingerprint,
            interaction_intent=left.interaction_intent,
            cognitive_intent=left.cognitive_intent,
            authoritative_ai_task_kind=left.authoritative_ai_task_kind,
            observed_confidence_class=left.observed_confidence_class,
            authorized_adapter_id=left.authorized_adapter_id,
            authorized_model_id=left.authorized_model_id,
            authorized_profile_id=left.authorized_profile_id,
            source_revision_count=left.source_revision_count,
        )
        assert right == left.proposal_fingerprint
    elif slot == 2:
        candidate = candidate_for_lesson("verified_success")
        left = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)
        right = CognitiveOutcomeQualityFeedbackEvaluator.evaluate(candidate)
        assert left == right
    elif slot == 3:
        left = proposal()
        assert left.proposal_fingerprint == proposal().proposal_fingerprint
    elif slot == 4:
        left = proposal()
        payload = (
            left.workspace_id.value,
            left.source_candidate_fingerprint,
            left.source_feedback_fingerprint,
            left.quality_classification,
            left.quality_reason_code,
            left.lesson_code,
            left.interaction_intent,
            left.cognitive_intent,
            left.authoritative_ai_task_kind.value,
            left.observed_confidence_class,
            left.authorized_adapter_id,
            left.authorized_model_id,
            left.authorized_profile_id,
            left.source_revision_count,
        )
        right = proposal()
        assert payload == (
            right.workspace_id.value,
            right.source_candidate_fingerprint,
            right.source_feedback_fingerprint,
            right.quality_classification,
            right.quality_reason_code,
            right.lesson_code,
            right.interaction_intent,
            right.cognitive_intent,
            right.authoritative_ai_task_kind.value,
            right.observed_confidence_class,
            right.authorized_adapter_id,
            right.authorized_model_id,
            right.authorized_profile_id,
            right.source_revision_count,
        )
    elif slot == 5:
        left = proposal()
        assert len(left.proposal_fingerprint) == 64
        int(left.proposal_fingerprint, 16)
    elif slot == 6:
        left = proposal()
        altered = compute_cognitive_trusted_experience_proposal_fingerprint(
            workspace_id=WorkspaceId.COMPANY,
            source_candidate_fingerprint=left.source_candidate_fingerprint,
            source_feedback_fingerprint=left.source_feedback_fingerprint,
            interaction_intent=left.interaction_intent,
            cognitive_intent=left.cognitive_intent,
            authoritative_ai_task_kind=left.authoritative_ai_task_kind,
            observed_confidence_class=left.observed_confidence_class,
            authorized_adapter_id=left.authorized_adapter_id,
            authorized_model_id=left.authorized_model_id,
            authorized_profile_id=left.authorized_profile_id,
            source_revision_count=left.source_revision_count,
        )
        assert altered != left.proposal_fingerprint
    else:
        left = proposal()
        assert left.authoritative_ai_task_kind is AITaskKind.GENERAL_CHAT


@pytest.mark.parametrize("case", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)])
def test_d147_reproducibility_matrix(case: int) -> None:
    run_case(case)
