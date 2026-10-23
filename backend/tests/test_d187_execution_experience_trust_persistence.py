from __future__ import annotations

import os
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.repositories.execution_experience_reviews import (
    ExecutionExperienceReviewRepository,
)
from app.repositories.trusted_execution_experiences import (
    TrustedExecutionExperienceRepository,
)
from app.services.execution_experience_review_lifecycle import (
    ExecutionExperienceReviewLifecycleService,
)
from app.services.execution_experience_trust_lifecycle import (
    ExecutionExperienceTrustLifecycleService,
)
from app.services.governed_execution_experience_runtime import (
    GovernedExecutionExperienceRuntimeIntegration,
    GovernedExecutionExperienceRuntimeStore,
)
from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackStore,
)
from tests.test_d183_governed_execution_experience_candidate import feedback_for

REVISION = "0018_trusted_execution_experience_lifecycle"


def config() -> Config:
    root = Path(__file__).resolve().parents[2]
    return Config(str(root / "alembic.ini"))


def test_d187_fresh_database_has_exact_trust_tables_indexes_and_head():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "d187-fresh.db"
        previous = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{path.as_posix()}"
        get_settings.cache_clear()
        engine = None
        try:
            command.upgrade(config(), "head")
            engine = create_database_engine(os.environ["OAI_DATABASE_URL"])
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            assert "trusted_execution_experiences" in tables
            assert "trusted_execution_experience_events" in tables
            assert {
                item["name"]
                for item in inspector.get_indexes("trusted_execution_experiences")
            } == {
                "ix_trusted_execution_experiences_workspace_state",
                "ix_trusted_execution_experiences_updated_at",
            }
            assert {
                item["name"]
                for item in inspector.get_indexes(
                    "trusted_execution_experience_events"
                )
            } == {
                "ix_trusted_execution_experience_events_experience_id"
            }
            foreign_keys = inspector.get_foreign_keys(
                "trusted_execution_experiences"
            )
            assert any(
                item["constrained_columns"] == ["source_review_id"]
                and item["referred_table"] == "execution_experience_reviews"
                for item in foreign_keys
            )
            with engine.connect() as connection:
                assert connection.scalar(
                    text("SELECT version_num FROM alembic_version")
                ) == REVISION
        finally:
            if engine is not None:
                engine.dispose()
            if previous is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous
            get_settings.cache_clear()


def test_d187_trusted_root_survives_database_session_restart():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "d187-restart.db"
        previous = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{path.as_posix()}"
        get_settings.cache_clear()
        engine = None
        first = None
        second = None
        try:
            command.upgrade(config(), "head")
            engine = create_database_engine(os.environ["OAI_DATABASE_URL"])
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            first = Session()
            scope = WorkspaceScope(WorkspaceId.PERSONAL)

            feedback_store = GovernedExecutionOutcomeFeedbackStore()
            runtime_store = GovernedExecutionExperienceRuntimeStore()
            integration = GovernedExecutionExperienceRuntimeIntegration(
                feedback_store=feedback_store,
                runtime_store=runtime_store,
            )
            feedback = feedback_for(
                approval_id="approval-d187-restart",
                request_id="request-d187-restart",
            )
            feedback_store.register(feedback)
            assert integration.try_integrate(feedback.approval_id)

            d186 = ExecutionExperienceReviewLifecycleService(
                repository=ExecutionExperienceReviewRepository(first, scope),
                runtime_store=runtime_store,
            )
            review = d186.capture(feedback.approval_id)
            assert review is not None
            review = d186.accept(
                review.id,
                1,
                review.source_review_fingerprint,
            )

            d187 = ExecutionExperienceTrustLifecycleService(
                review_repository=ExecutionExperienceReviewRepository(first, scope),
                trusted_repository=TrustedExecutionExperienceRepository(first, scope),
            )
            eligibility = d187.evaluate(review.id)
            assert eligibility.proposal is not None
            trusted = d187.promote(
                review_id=review.id,
                expected_revision=2,
                source_record_fingerprint=(
                    eligibility.proposal.source_d186_record_fingerprint
                ),
                promotion_fingerprint=eligibility.proposal.promotion_fingerprint,
            )
            trusted_id = trusted.id
            first.close()
            first = None

            second = Session()
            reopened = ExecutionExperienceTrustLifecycleService(
                review_repository=ExecutionExperienceReviewRepository(second, scope),
                trusted_repository=TrustedExecutionExperienceRepository(second, scope),
            )
            loaded = reopened.get(trusted_id)
            assert loaded.state == "TRUSTED"
            assert loaded.current_revision == 1
            assert loaded.source_review_id == review.id
        finally:
            if first is not None:
                first.close()
            if second is not None:
                second.close()
            if engine is not None:
                engine.dispose()
            if previous is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous
            get_settings.cache_clear()


def test_d187_upgrade_from_0017_preserves_d186_data_and_d147_schema():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "d187-upgrade.db"
        previous = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{path.as_posix()}"
        get_settings.cache_clear()
        engine = None
        try:
            command.upgrade(config(), "0017_execution_experience_review_lifecycle")
            engine = create_database_engine(os.environ["OAI_DATABASE_URL"])
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO execution_experience_reviews "
                        "(id,workspace_id,conversation_id,source_turn_id,"
                        "source_artifact_digest,intent_digest,approval_id,"
                        "execution_request_id,plan_digest,"
                        "source_feedback_fingerprint,source_candidate_fingerprint,"
                        "source_review_fingerprint,target_kind,capability_id,"
                        "adapter_id,operation,effect,risk_class,"
                        "source_classification,experience_outcome_class,"
                        "experience_lesson_code,review_reason_code,"
                        "record_fingerprint,contract_version,state,current_revision,"
                        "created_at,updated_at) VALUES "
                        "('d187-source','personal',"
                        "'00000000-0000-0000-0000-000000000187','turn',"
                        ":a,:b,'approval','request',:c,:d,:e,:f,"
                        "'tool','capability','adapter','read','read','R0',"
                        "'execution_succeeded','success',"
                        "'authorized_execution_succeeded',"
                        "'authorized_execution_succeeded',:g,"
                        "'o-ai.governed-execution-experience-owner-review.v1',"
                        "'REVIEW_ACCEPTED',2,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
                    ),
                    {
                        "a": "a" * 64,
                        "b": "b" * 64,
                        "c": "c" * 64,
                        "d": "d" * 64,
                        "e": "e" * 64,
                        "f": "f" * 64,
                        "g": "0" * 64,
                    },
                )
                connection.execute(
                    text(
                        "INSERT INTO execution_experience_review_events "
                        "(id,execution_experience_review_id,sequence,event_type,"
                        "from_state,to_state,actor,created_at) VALUES "
                        "('event-1','d187-source',1,'PROPOSED',NULL,"
                        "'PENDING_REVIEW','SYSTEM',CURRENT_TIMESTAMP),"
                        "('event-2','d187-source',2,'OWNER_ACCEPTED',"
                        "'PENDING_REVIEW','REVIEW_ACCEPTED','OWNER',CURRENT_TIMESTAMP)"
                    )
                )
                d147_columns_before = {
                    row[1]
                    for row in connection.execute(
                        text("PRAGMA table_info(trusted_experiences)")
                    )
                }
            engine.dispose()
            engine = None

            command.upgrade(config(), "head")
            engine = create_database_engine(os.environ["OAI_DATABASE_URL"])
            with engine.connect() as connection:
                assert connection.scalar(
                    text(
                        "SELECT count(*) FROM execution_experience_reviews "
                        "WHERE id='d187-source'"
                    )
                ) == 1
                assert connection.scalar(
                    text("SELECT count(*) FROM trusted_execution_experiences")
                ) == 0
                assert connection.scalar(
                    text("SELECT version_num FROM alembic_version")
                ) == REVISION
                d147_columns_after = {
                    row[1]
                    for row in connection.execute(
                        text("PRAGMA table_info(trusted_experiences)")
                    )
                }
                assert d147_columns_after == d147_columns_before
        finally:
            if engine is not None:
                engine.dispose()
            if previous is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous
            get_settings.cache_clear()
