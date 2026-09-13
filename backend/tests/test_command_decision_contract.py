import unittest

from app.contracts.command_decision import CommandDecision


class CommandDecisionContractTests(unittest.TestCase):
    def test_decision_is_immutable(self) -> None:
        decision = CommandDecision(
            request_id="request-1",
            intent="chat_message",
            disposition="defer_to_existing_chat",
            provider_preference_hint="unspecified",
            reason_code="chat_message",
        )

        with self.assertRaises(AttributeError):
            decision.intent = "unknown"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
