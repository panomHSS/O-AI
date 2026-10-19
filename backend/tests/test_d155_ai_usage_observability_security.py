from __future__ import annotations

import inspect
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1 import ai_usage as ai_usage_api
from app.contracts.ai import AIResult
from app.contracts.ai_usage import AI_USAGE_METADATA_KEY, AIUsageMeasurement
from app.models.ai_usage_event import AIUsageEventRecord
from app.repositories.ai_usage_events import AIUsageEventRepository
from app.schemas.ai_usage import AIUsageSummaryResponse
from app.services import ai_usage_metering, ai_usage_pricing, ai_usage_summary
from app.services.ai_usage_metering import AIUsageMeter
from app.services.ai_usage_summary import AIUsageSummaryService


class D155SecurityTests(unittest.TestCase):
    def test_ledger_schema_has_no_prompt_completion_secret_or_reasoning_content_fields(self) -> None:
        columns = {column.name.lower() for column in AIUsageEventRecord.__table__.columns}
        forbidden = {
            "prompt",
            "message",
            "content",
            "response",
            "completion",
            "api_key",
            "access_token",
            "refresh_token",
            "chain_of_thought",
            "reasoning_text",
            "context",
            "memory",
            "request_id",
        }
        self.assertTrue(columns.isdisjoint(forbidden))

    def test_summary_schema_does_not_expose_invocation_or_plan_identifiers(self) -> None:
        fields = set(AIUsageSummaryResponse.model_fields)
        self.assertTrue(
            fields.isdisjoint(
                {
                    "request_id",
                    "request_digest",
                    "plan_digest",
                    "invocation_digest",
                    "prompt",
                    "response",
                    "content",
                }
            )
        )

    def test_api_is_read_only_and_exposes_only_summary_route(self) -> None:
        routes = [route for route in ai_usage_api.router.routes]
        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route.path, "/ai-usage/summary")
        self.assertEqual(route.methods, {"GET"})

    def test_usage_services_have_no_execution_or_cognitive_authority_imports(self) -> None:
        sources = "\n".join(
            inspect.getsource(module)
            for module in (
                ai_usage_metering,
                ai_usage_pricing,
                ai_usage_summary,
            )
        )
        for forbidden in (
            "ExecutionPlanner",
            "ExecutionGuard",
            "AIRouter",
            "CognitiveExecutive",
            "TrustedExperience",
            "MemoryRepository",
            "ConversationRepository",
        ):
            self.assertNotIn(forbidden, sources)

    def test_private_prompt_and_completion_are_not_persisted(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            path = Path(temp.name) / "privacy.db"
            engine = create_engine(f"sqlite:///{path.as_posix()}")
            AIUsageEventRecord.__table__.create(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            usage = AIUsageMeasurement(
                provider_id="openai",
                model_id="gpt-5.5",
                pricing_mode="default",
                input_tokens=50,
                cached_input_tokens=0,
                cache_write_tokens=0,
                output_tokens=10,
                reasoning_tokens=5,
                total_tokens=60,
            )
            result = AIResult(
                content="PRIVATE-COMPLETION-SHOULD-NOT-PERSIST",
                metadata={AI_USAGE_METADATA_KEY: usage},
            )
            meter = AIUsageMeter(
                session_factory=Session,
                clock=lambda: datetime(2026, 10, 19, tzinfo=timezone.utc),
            )
            self.assertTrue(
                meter.try_record_success(
                    request_id="PRIVATE-REQUEST-IDENTITY-SHOULD-BE-HASHED",
                    plan_digest="a" * 64,
                    adapter_id="chatgpt.default",
                    authorized_model_id="gpt-5.5",
                    result=result,
                )
            )
            with Session() as session:
                record = AIUsageEventRepository(session).list_for_summary()[0]
                record_text = repr(
                    {
                        column.name: getattr(record, column.name)
                        for column in AIUsageEventRecord.__table__.columns
                    }
                )
                response_text = AIUsageSummaryResponse.from_contract(
                    AIUsageSummaryService(
                        AIUsageEventRepository(session)
                    ).summarize()
                ).model_dump_json()
            self.assertNotIn("PRIVATE-COMPLETION", record_text)
            self.assertNotIn("PRIVATE-REQUEST-IDENTITY", record_text)
            self.assertNotIn("PRIVATE-COMPLETION", response_text)
            self.assertNotIn("PRIVATE-REQUEST-IDENTITY", response_text)
            self.assertNotIn("prompt", response_text.lower())
            engine.dispose()
        finally:
            temp.cleanup()

    def test_migration_preserves_sqlite_and_postgresql_append_only_support(self) -> None:
        migration = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0015_ai_usage_observability.py"
        ).read_text(encoding="utf-8")
        self.assertIn('dialect == "sqlite"', migration)
        self.assertIn('dialect == "postgresql"', migration)
        self.assertIn("reject_ai_usage_event_mutation", migration)
        self.assertIn("trg_ai_usage_events_immutable_update", migration)
        self.assertIn("trg_ai_usage_events_immutable_delete", migration)

    def test_forged_usage_metadata_cannot_make_local_ai_billable(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            path = Path(temp.name) / "local.db"
            engine = create_engine(f"sqlite:///{path.as_posix()}")
            AIUsageEventRecord.__table__.create(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            forged = AIUsageMeasurement(
                provider_id="openai",
                model_id="gpt-5.5",
                pricing_mode="default",
                input_tokens=100,
                cached_input_tokens=0,
                cache_write_tokens=0,
                output_tokens=10,
                reasoning_tokens=0,
                total_tokens=110,
            )
            meter = AIUsageMeter(session_factory=Session)
            self.assertTrue(
                meter.try_record_success(
                    request_id="local-forged",
                    plan_digest="b" * 64,
                    adapter_id="local_ai.default",
                    authorized_model_id="qwen3.5:9b",
                    result=AIResult(
                        content="local",
                        metadata={AI_USAGE_METADATA_KEY: forged},
                    ),
                )
            )
            with Session() as session:
                record = AIUsageEventRepository(session).list_for_summary()[0]
            self.assertEqual(record.provider_id, "local")
            self.assertEqual(record.billing_status, "not_applicable")
            self.assertIsNone(record.estimated_cost_nano_usd)
            engine.dispose()
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
