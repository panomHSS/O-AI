from __future__ import annotations

from app.api.v1.execution_experience_reviews import (
    get_execution_experience_trust_eligibility,
    promote_execution_experience_trust,
)
from app.api.v1.trusted_execution_experiences import (
    get_trusted_execution_experience,
    list_trusted_execution_experiences,
    revoke_trusted_execution_experience,
    router,
    trusted_execution_experience_history,
)
from app.schemas.trusted_execution_experiences import (
    ExecutionExperienceTrustPromotionRequest,
    TrustedExecutionExperienceRevokeRequest,
)
from tests.test_d187_execution_experience_trust import build_services


def test_d187_api_eligibility_promotion_and_trusted_read_surfaces():
    engine, session, _, service, review = build_services()
    try:
        eligibility = get_execution_experience_trust_eligibility(
            review.id,
            service,
        )
        assert eligibility.success is True
        assert eligibility.data.eligibility == "eligible_for_owner_promotion"
        proposal = eligibility.data.proposal
        assert proposal is not None

        promoted = promote_execution_experience_trust(
            review_id=review.id,
            revision=2,
            payload=ExecutionExperienceTrustPromotionRequest(
                source_record_fingerprint=proposal.source_d186_record_fingerprint,
                promotion_fingerprint=proposal.promotion_fingerprint,
            ),
            service=service,
        )
        assert promoted.success is True
        assert promoted.data.state == "TRUSTED"
        assert promoted.data.execution_authority is False

        listed = list_trusted_execution_experiences(
            service=service,
            page=1,
            page_size=25,
            state=None,
        )
        assert listed.data.total == 1

        fetched = get_trusted_execution_experience(promoted.data.id, service)
        assert fetched.data.id == promoted.data.id

        history = trusted_execution_experience_history(
            promoted.data.id,
            service,
        )
        assert [item.event_type for item in history.data.items] == [
            "OWNER_PROMOTED"
        ]

        revoked = revoke_trusted_execution_experience(
            trusted_id=promoted.data.id,
            revision=1,
            payload=TrustedExecutionExperienceRevokeRequest(
                promotion_fingerprint=promoted.data.promotion_fingerprint
            ),
            service=service,
        )
        assert revoked.data.state == "REVOKED"
        assert revoked.data.current_revision == 2
    finally:
        session.close()
        engine.dispose()


def test_d187_trusted_api_exposes_no_public_create_endpoint():
    routes = {
        (route.path, frozenset(route.methods or set()))
        for route in router.routes
    }
    assert not any(
        path == "/trusted-execution-experiences" and "POST" in methods
        for path, methods in routes
    )
