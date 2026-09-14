import unittest
from dataclasses import FrozenInstanceError

from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION,
    AI_DISCOVERY_STATUS_AVAILABLE,
    AIAdapterDiscovery,
    AIModelDescriptor,
)


class AIDiscoveryContractTests(unittest.TestCase):
    def test_model_descriptor_is_immutable_and_canonical(self) -> None:
        descriptor = AIModelDescriptor(
            model_id="model-b",
            capability_ids=("zeta", AI_CAPABILITY_TEXT_GENERATION),
        )
        self.assertEqual(descriptor.capability_ids, (AI_CAPABILITY_TEXT_GENERATION, "zeta"))
        with self.assertRaises(FrozenInstanceError):
            descriptor.model_id = "model-c"  # type: ignore[misc]

    def test_descriptor_rejects_invalid_or_duplicate_capability_ids(self) -> None:
        for capabilities in (("",), (" spaced ",), ("same", "same")):
            with self.subTest(capabilities=capabilities):
                with self.assertRaises(ValueError):
                    AIModelDescriptor(model_id="model-a", capability_ids=capabilities)

    def test_discovery_canonicalizes_model_order(self) -> None:
        result = AIAdapterDiscovery(
            adapter_id="ai.test",
            status=AI_DISCOVERY_STATUS_AVAILABLE,
            configured_model_id="model-b",
            capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
            models=(
                AIModelDescriptor("model-b", (AI_CAPABILITY_TEXT_GENERATION,)),
                AIModelDescriptor("model-a", (AI_CAPABILITY_TEXT_GENERATION,)),
            ),
            reason_code="models_discovered",
        )
        self.assertEqual(tuple(model.model_id for model in result.models), ("model-a", "model-b"))

    def test_discovery_rejects_duplicate_models_and_invalid_status(self) -> None:
        descriptor = AIModelDescriptor("model-a", (AI_CAPABILITY_TEXT_GENERATION,))
        with self.assertRaises(ValueError):
            AIAdapterDiscovery(
                adapter_id="ai.test",
                status=AI_DISCOVERY_STATUS_AVAILABLE,
                configured_model_id="model-a",
                capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
                models=(descriptor, descriptor),
                reason_code="models_discovered",
            )
        with self.assertRaises(ValueError):
            AIAdapterDiscovery(
                adapter_id="ai.test",
                status="mystery",  # type: ignore[arg-type]
                configured_model_id=None,
                capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
                models=(),
                reason_code="unknown",
            )


if __name__ == "__main__":
    unittest.main()
