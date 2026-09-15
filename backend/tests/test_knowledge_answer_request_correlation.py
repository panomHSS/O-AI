import asyncio
import json
import unittest
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from app.api.dependencies import get_knowledge_answer_service
from app.main import app
from app.schemas.knowledge_answer import KnowledgeAnswerResponse, RetrievalSummaryResponse
from app.schemas.planning import PlanningPlan
from app.schemas.reasoning import ReasoningPlan
from app.services.knowledge_answer import KnowledgeAnswerService


class RequestIdRecordingKnowledgeService(KnowledgeAnswerService):
    def __init__(self) -> None:
        self.request_ids: list[str | None] = []

    def answer(self, question: str, conversation_id=None, project_id=None, *, request_id: str | None = None) -> KnowledgeAnswerResponse:
        _ = (question, conversation_id, project_id)
        self.request_ids.append(request_id)
        return KnowledgeAnswerResponse(
            answer="Grounded answer S1",
            citations=[],
            evidence_quality="insufficient",
            conversation_id=UUID("11111111-1111-1111-1111-111111111111"),
            retrieval_summary=RetrievalSummaryResponse(
                candidates_considered=0,
                evidence_selected=0,
                duplicates_removed=0,
                filtered_out=0,
                conflicting_evidence_count=0,
                queries_used=[],
            ),
            conflicts=[],
            reasoning_plan=ReasoningPlan(
                intent="general",
                normalized_question="",
                required_information=[],
                missing_information=[],
                evidence_map=[],
            ),
            planning_plan=PlanningPlan(intent="general"),
        )


class EmptyRepository:
    def search(self, query: str, limit: int):
        _ = (query, limit)
        return []


class FakeConversations:
    def begin_turn(self, question, conversation_id, project_id):
        _ = (question, conversation_id, project_id)
        return (SimpleNamespace(id="11111111-1111-1111-1111-111111111111", project_id=None), [])

    def resolve_project_context(self, conversation):
        _ = conversation
        return None

    def complete_turn(self, conversation_id, answer, snapshots) -> None:
        _ = (conversation_id, answer, snapshots)


class FakeAnalyzer:
    def analyze(self, question):
        return SimpleNamespace(question=question, important_terms=())


class FakeRetrievalPlanner:
    def plan(self, intent):
        _ = intent
        return []


class EmptyRanker:
    def rank(self, question, important_terms, records):
        _ = (question, important_terms, records)
        return [], 0, 0


class EmptyConflicts:
    def detect(self, selected, important_terms):
        _ = (selected, important_terms)
        return []


class EmptyContext:
    def build(self, selected):
        _ = selected
        return []


class FakeConfidence:
    def evaluate(self, context, citations, conflicts):
        _ = (context, citations, conflicts)
        return "insufficient"


class ContextRecordingKnowledgeService(KnowledgeAnswerService):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.context_request_ids: list[str] = []

    def _create_execution_context(self, **kwargs):
        context = super()._create_execution_context(**kwargs)
        self.context_request_ids.append(context.request.request_id)
        return context


async def invoke_app(path: str, *, method: str = "GET", body: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], dict[str, Any]]:
    target = urlsplit(path)
    encoded_body = json.dumps(body).encode() if body is not None else b""
    has_received = False
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        nonlocal has_received
        if has_received:
            return {"type": "http.disconnect"}
        has_received = True
        return {"type": "http.request", "body": encoded_body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    request_headers = {"Content-Type": "application/json"} if body is not None else {}
    request_headers.update(headers or {})
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": target.path,
        "raw_path": target.path.encode(),
        "query_string": target.query.encode(),
        "headers": [(key.lower().encode(), value.encode()) for key, value in request_headers.items()],
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    start = next(item for item in messages if item["type"] == "http.response.start")
    payload = b"".join(item.get("body", b"") for item in messages if item["type"] == "http.response.body")
    response_headers = {key.decode().lower(): value.decode() for key, value in start["headers"]}
    return start["status"], response_headers, json.loads(payload)


class KnowledgeAnswerRequestCorrelationTests(unittest.TestCase):
    def test_http_request_id_reaches_real_service_surface(self) -> None:
        service = RequestIdRecordingKnowledgeService()
        app.dependency_overrides[get_knowledge_answer_service] = lambda: service
        try:
            status_code, headers, body = asyncio.run(
                invoke_app(
                    "/api/v1/knowledge/answer",
                    method="POST",
                    body={"question": "What does the manual say?"},
                    headers={"X-Request-ID": "d50-correlation-1"},
                )
            )
        finally:
            app.dependency_overrides.pop(get_knowledge_answer_service, None)

        self.assertEqual(status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(headers["x-request-id"], "d50-correlation-1")
        self.assertEqual(service.request_ids, ["d50-correlation-1"])

    def test_service_request_id_becomes_execution_context_id(self) -> None:
        service = ContextRecordingKnowledgeService(
            repository=EmptyRepository(),  # type: ignore[arg-type]
            conversations=FakeConversations(),  # type: ignore[arg-type]
            chat=SimpleNamespace(),
            analyzer=FakeAnalyzer(),  # type: ignore[arg-type]
            planner=FakeRetrievalPlanner(),  # type: ignore[arg-type]
            ranker=EmptyRanker(),  # type: ignore[arg-type]
            conflict_detector=EmptyConflicts(),  # type: ignore[arg-type]
            context_builder=EmptyContext(),  # type: ignore[arg-type]
            prompt_builder=SimpleNamespace(),
            citations=SimpleNamespace(),
            confidence=FakeConfidence(),  # type: ignore[arg-type]
            candidates_per_query=1,
            selected_limit=1,
        )
        service.answer("No evidence question", None, request_id="d50-context-1")
        self.assertEqual(service.context_request_ids, ["d50-context-1"])


if __name__ == "__main__":
    unittest.main()
