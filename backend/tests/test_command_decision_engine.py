import unittest

from app.contracts.command import CommandRequest
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_input_pipeline import CHAT_MESSAGE_COMMAND


class CommandDecisionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CommandDecisionEngine()

    def _chat_command(self, message: str) -> CommandRequest:
        return CommandRequest(
            request_id="request-1",
            command=CHAT_MESSAGE_COMMAND,
            arguments={"message": message},
        )

    def test_chat_message_defers_to_existing_chat(self) -> None:
        decision = self.engine.decide(self._chat_command("Hello"))
        self.assertEqual(decision.intent, "chat_message")
        self.assertEqual(decision.disposition, "defer_to_existing_chat")
        self.assertEqual(decision.provider_preference_hint, "unspecified")

    def test_unsupported_command_is_rejected(self) -> None:
        decision = self.engine.decide(
            CommandRequest(request_id="request-1", command="knowledge.answer")
        )
        self.assertEqual(decision.intent, "unknown")
        self.assertEqual(decision.disposition, "reject")
        self.assertEqual(decision.reason_code, "unsupported_command")

    def test_explicit_local_ai_routing_phrase_is_a_hint_only(self) -> None:
        decision = self.engine.decide(
            self._chat_command("Please route this command to Local AI.")
        )
        self.assertEqual(
            decision.provider_preference_hint,
            "local_ai_explicit",
        )
        self.assertEqual(decision.disposition, "defer_to_existing_chat")

    def test_natural_thai_local_ai_routing_phrases_are_hints_only(self) -> None:
        for message in (
            "ใช้ Local AI ตอบข้อนี้: อธิบาย Python decorators",
            "ให้ Ollama ช่วยตอบคำถามนี้",
            "ใช้โมเดลในเครื่องตอบเรื่อง list comprehension",
            "ช่วยใช้ Local AI อธิบาย recursion",
        ):
            with self.subTest(message=message):
                decision = self.engine.decide(self._chat_command(message))
                self.assertEqual(
                    decision.provider_preference_hint,
                    "local_ai_explicit",
                )

    def test_explicit_cloud_ai_routing_phrase_is_a_hint_only(self) -> None:
        for message in (
            "Please use cloud AI for this command.",
            "Please use ChatGPT for this chat message.",
            "ใช้ Cloud AI ตอบข้อนี้",
            "ให้ ChatGPT ช่วยตอบคำถามนี้",
        ):
            with self.subTest(message=message):
                decision = self.engine.decide(self._chat_command(message))
                self.assertEqual(
                    decision.provider_preference_hint,
                    "cloud_ai_explicit",
                )
                self.assertEqual(
                    decision.disposition,
                    "defer_to_existing_chat",
                )

    def test_provider_mentions_without_routing_instruction_are_unspecified(
        self,
    ) -> None:
        for message in (
            "Ollama คืออะไร",
            "Local AI ดีไหม",
            "ChatGPT คืออะไร",
            "Cloud AI มีข้อดีอะไร",
            "ผมติดตั้ง Ollama ไว้ในเครื่อง",
        ):
            with self.subTest(message=message):
                decision = self.engine.decide(self._chat_command(message))
                self.assertEqual(
                    decision.provider_preference_hint,
                    "unspecified",
                )

    def test_negated_routing_phrases_are_unspecified(self) -> None:
        for message in (
            "อย่าใช้ Local AI ตอบข้อนี้",
            "ไม่ต้องใช้ Ollama ตอบคำถามนี้",
            "ห้ามใช้โมเดลในเครื่องตอบเรื่องนี้",
            "Don't use cloud AI for this command.",
            "Do not use ChatGPT for this chat message.",
            "Do not route this command automatically.",
        ):
            with self.subTest(message=message):
                decision = self.engine.decide(self._chat_command(message))
                self.assertEqual(
                    decision.provider_preference_hint,
                    "unspecified",
                )
                self.assertEqual(
                    decision.disposition,
                    "defer_to_existing_chat",
                )

    def test_quoted_or_example_routing_phrases_are_unspecified(self) -> None:
        for message in (
            'คำว่า "ใช้ Local AI ตอบข้อนี้" หมายความว่าอะไร',
            "ตัวอย่าง: ใช้ Local AI ตอบข้อนี้",
            "`ให้ Ollama ช่วยตอบคำถามนี้` เป็นตัวอย่างข้อความ",
            'The phrase "use cloud AI for this command" is an example.',
            "For example: use ChatGPT for this command.",
            "`route this command automatically` is documentation text.",
        ):
            with self.subTest(message=message):
                decision = self.engine.decide(self._chat_command(message))
                self.assertEqual(
                    decision.provider_preference_hint,
                    "unspecified",
                )

    def test_explicit_automatic_routing_phrase_is_a_hint_only(self) -> None:
        decision = self.engine.decide(
            self._chat_command(
                "Please use automatic provider routing for this command."
            )
        )
        self.assertEqual(decision.provider_preference_hint, "automatic")

    def test_generic_default_and_automatic_words_do_not_trigger_hints(self) -> None:
        for message in (
            "Use the default model.",
            "Please answer automatically.",
            "Local AI is interesting.",
            "Cloud AI is interesting.",
        ):
            with self.subTest(message=message):
                decision = self.engine.decide(self._chat_command(message))
                self.assertEqual(
                    decision.provider_preference_hint,
                    "unspecified",
                )

    def test_conflicting_explicit_hints_fail_closed(self) -> None:
        for message in (
            "Use local AI for this command and use cloud AI for this command.",
            "Route this command to local AI and use automatic provider routing "
            "for this command.",
            "Use ChatGPT for this command and route this command automatically.",
        ):
            with self.subTest(message=message):
                decision = self.engine.decide(self._chat_command(message))
                self.assertEqual(decision.disposition, "reject")
                self.assertEqual(
                    decision.provider_preference_hint,
                    "unspecified",
                )
                self.assertEqual(
                    decision.reason_code,
                    "conflicting_provider_preference",
                )


if __name__ == "__main__":
    unittest.main()
