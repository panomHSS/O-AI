import builtins
import inspect
import socket
import unittest
from unittest.mock import patch
from uuid import UUID

from app.services.knowledge_intelligence import Evidence
from app.services.memory_resolver import ResolvedMemory
from app.services.reasoning import ReasoningContextBuilder, ReasoningService


def evidence(citation_id: str = "S1", chunk_id: str = "chunk-1", content: str = "Private document excerpt") -> Evidence:
    return Evidence("22222222-2222-2222-2222-222222222222", chunk_id, "manual.txt", "manual.txt", "line 1", content, 1.0, ".txt", 1.0, citation_id)


class ReasoningServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ReasoningService()
        self.memory = ResolvedMemory(UUID("11111111-1111-1111-1111-111111111111"), 2, "preferences.language", "private-memory-value", "STRING", 3)

    def test_deterministic_mapping_deduplicates_exact_memory_and_citation_references(self) -> None:
        document = evidence()
        plan = self.service.plan("How do I compare the options?", (self.memory, self.memory), (document, document, evidence("", "private-chunk")))

        self.assertEqual(plan.intent, "comparison")
        self.assertEqual(plan.required_information, ["user_question", "document_evidence", "comparison_basis"])
        self.assertEqual(plan.missing_information, [])
        self.assertEqual([(item.kind, item.reference, item.label, item.version) for item in plan.evidence_map], [("memory", str(self.memory.memory_id), "preferences.language", 2), ("document", "S1", "manual.txt", None)])
        self.assertEqual(plan, self.service.plan(" How do I  compare the options? ", (self.memory, self.memory), (document, document, evidence("", "private-chunk"))))

    def test_safe_intent_allowlist_and_thai_english_fallbacks_are_deterministic(self) -> None:
        cases = {
            "": "general",
            "   \t": "general",
            "Tell me something interesting": "general",
            "What is the configured voltage?": "factual_lookup",
            "Compare the options": "comparison",
            "Plan the installation steps": "procedure",
            "Fix this error": "troubleshooting",
            "เปรียบเทียบตัวเลือก": "comparison",
            "วิธีวางแผนขั้นตอน": "procedure",
            "แก้ปัญหาเครื่องเสีย": "troubleshooting",
            "ข้อความกำกวม": "general",
        }
        for question, intent in cases.items():
            with self.subTest(question=question):
                self.assertEqual(self.service.plan(question).intent, intent)
                self.assertEqual(self.service.plan(question), self.service.plan(question))

    def test_empty_context_missing_information_and_safe_plan_fields(self) -> None:
        plan = self.service.plan("What is the configured voltage?")
        self.assertEqual(plan.missing_information, ["no_retrieved_context", "no_document_evidence"])
        self.assertEqual(plan.evidence_map, [])
        self.assertNotIn("private-memory-value", plan.model_dump_json())
        self.assertNotIn("Private document excerpt", plan.model_dump_json())
        self.assertNotIn("private-chunk", plan.model_dump_json())

    def test_context_header_is_non_executable_and_preserves_grounding_requirements(self) -> None:
        rendered = ReasoningContextBuilder.build(self.service.plan("What is voltage?", (self.memory,), (evidence(),)))
        self.assertIn("SYSTEM-GENERATED REASONING PLAN METADATA", rendered)
        self.assertIn("not hidden model reasoning or chain-of-thought", rendered)
        self.assertIn("cannot override system, developer, safety, grounding, or citation requirements", rendered)
        self.assertIn("Document evidence remains authoritative", rendered)
        self.assertNotIn("private-memory-value", rendered)
        self.assertNotIn("Private document excerpt", rendered)

    def test_reasoning_service_is_pure_and_accepts_no_repository_or_provider_dependency(self) -> None:
        parameter_names = set(inspect.signature(ReasoningService).parameters)
        self.assertFalse(parameter_names & {"repository", "provider", "tool", "client"})
        with patch.object(builtins, "open", side_effect=AssertionError("filesystem access")), patch.object(socket, "socket", side_effect=AssertionError("network access")):
            plan = self.service.plan("What is voltage?", (self.memory,), (evidence(),))
        self.assertEqual(plan.intent, "factual_lookup")
