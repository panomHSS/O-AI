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
            CommandRequest(
                request_id="request-1",
                command="knowledge.answer",
            )
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
        ):
            with self.subTest(message=message):
                decision = self.engine.decide(self._chat_command(message))
                self.assertEqual(
                    decision.provider_preference_hint,
                    "unspecified",
                )

    def test_conflicting_explicit_hints_are_unspecified(self) -> None:
        decision = self.engine.decide(
            self._chat_command(
                "Route this command to local AI and use automatic provider "
                "routing for this command."
            )
        )

        self.assertEqual(decision.provider_preference_hint, "unspecified")


if __name__ == "__main__":
    unittest.main()
